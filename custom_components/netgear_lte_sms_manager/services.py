"""Services for the Netgear LTE SMS Manager integration."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import voluptuous as vol

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall, callback
    from homeassistant.exceptions import ServiceValidationError
    from homeassistant.helpers import config_validation as cv

# Runtime imports required for schema validation and exception handling
from homeassistant.core import callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_COUNT_DELETED,
    ATTR_DRY_RUN,
    ATTR_HOST,
    ATTR_MESSAGES,
    ATTR_RETAIN_COUNT,
    ATTR_RETAIN_DAYS,
    ATTR_SMS_ID,
    ATTR_WHITELIST,
    DEFAULT_DRY_RUN,
    DEFAULT_RETAIN_COUNT,
    DEFAULT_RETAIN_DAYS,
    DOMAIN,
    EVENT_CLEANUP_COMPLETE,
    EVENT_SMS_INBOX_LISTED,
    LOGGER,
    SERVICE_CLEANUP_INBOX,
    SERVICE_DELETE_SMS,
    SERVICE_GET_INBOX_JSON,
    SERVICE_LIST_INBOX,
)
from .helpers import get_netgear_lte_entry, get_saved_options, parse_whitelist_options
from .models import (
    EternalEgyptVersionError,
    ModemCommunicationError,
    ModemConnection,
    NetgearLTECoreMissingError,
)

# Service schemas
LIST_INBOX_SCHEMA = vol.Schema({vol.Optional(ATTR_HOST): cv.string})

DELETE_SMS_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_HOST): cv.string,
        vol.Required(ATTR_SMS_ID): vol.All(cv.ensure_list, [cv.positive_int]),
    }
)

# Operator-specific deletion removed in favor of the policy-based cleanup_inbox

CLEANUP_INBOX_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_HOST): cv.string,
        vol.Optional(ATTR_RETAIN_COUNT): vol.Any(None, cv.positive_int),
        vol.Optional(ATTR_RETAIN_DAYS): vol.Any(None, cv.positive_int),
        vol.Optional(ATTR_WHITELIST): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(ATTR_DRY_RUN): cv.boolean,
    }
)

GET_INBOX_JSON_SCHEMA = vol.Schema({vol.Optional(ATTR_HOST): cv.string})


async def _service_list_inbox(call: ServiceCall) -> None:
    """List SMS inbox and fire event with results.

    This service queries the modem for all SMS in the inbox and fires
    an event containing the list. This list can then be used by automations
    or displayed in a Lovelace card.
    """
    hass = call.hass
    host = call.data.get(ATTR_HOST)

    try:
        entry = get_netgear_lte_entry(hass, host)
        modem = ModemConnection(entry.runtime_data.modem)

        LOGGER.info("Fetching SMS inbox from %s", entry.data.get("host"))
        sms_list = await modem.get_sms_list()

        event_data = {
            ATTR_HOST: entry.data.get("host"),
            ATTR_MESSAGES: [msg.to_dict() for msg in sms_list],
        }

        LOGGER.info("Found %d SMS messages in inbox, firing event", len(sms_list))
        hass.bus.async_fire(EVENT_SMS_INBOX_LISTED, event_data)

    except NetgearLTECoreMissingError as ex:
        LOGGER.error("Configuration error: %s", ex)
        raise ServiceValidationError(str(ex), translation_domain=DOMAIN) from ex
    except EternalEgyptVersionError as ex:
        LOGGER.error("API compatibility error: %s", ex)
        raise ServiceValidationError(
            f"API compatibility issue detected: {ex}",
            translation_domain=DOMAIN,
        ) from ex
    except ModemCommunicationError as ex:
        LOGGER.warning("Modem communication error: %s", ex)
        raise ServiceValidationError(
            f"Failed to reach modem: {ex}",
            translation_domain=DOMAIN,
        ) from ex
    except Exception as ex:
        LOGGER.exception("Unexpected error in list_inbox service")
        raise ServiceValidationError(
            f"Unexpected error: {type(ex).__name__}",
            translation_domain=DOMAIN,
        ) from ex


async def _service_delete_sms(call: ServiceCall) -> None:
    """Delete specific SMS by ID(s).

    This service deletes one or more SMS messages specified by their IDs.
    """
    hass = call.hass
    host = call.data.get(ATTR_HOST)
    sms_ids = call.data[ATTR_SMS_ID]

    try:
        entry = get_netgear_lte_entry(hass, host)
        modem = ModemConnection(entry.runtime_data.modem)

        LOGGER.info("Deleting %d SMS from %s", len(sms_ids), entry.data.get("host"))
        deleted_count = await modem.delete_sms_batch(sms_ids)

        LOGGER.info("Successfully deleted %d SMS", deleted_count)

    except NetgearLTECoreMissingError as ex:
        LOGGER.error("Configuration error: %s", ex)
        raise ServiceValidationError(str(ex), translation_domain=DOMAIN) from ex
    except EternalEgyptVersionError as ex:
        LOGGER.error("API compatibility error: %s", ex)
        raise ServiceValidationError(
            f"API compatibility issue: {ex}",
            translation_domain=DOMAIN,
        ) from ex
    except ModemCommunicationError as ex:
        LOGGER.warning("Failed to delete some/all SMS: %s", ex)
        raise ServiceValidationError(
            f"Deletion error: {ex}",
            translation_domain=DOMAIN,
        ) from ex
    except Exception as ex:
        LOGGER.exception("Unexpected error in delete_sms service")
        raise ServiceValidationError(
            f"Unexpected error: {type(ex).__name__}",
            translation_domain=DOMAIN,
        ) from ex


async def _service_cleanup_inbox(call: ServiceCall) -> None:
    """Clean up the inbox according to provided policy.

    Options:
      - retain_count: keep newest N messages (default 24)
      - retain_days: keep messages newer than N days (0 = ignore)
      - whitelist: list of sender strings to never delete
      - dry_run: if True, do not delete, only report proposed deletions
    """
    hass = call.hass
    host = call.data.get(ATTR_HOST)
    retain_count = call.data.get(ATTR_RETAIN_COUNT, DEFAULT_RETAIN_COUNT)
    retain_days = call.data.get(ATTR_RETAIN_DAYS, DEFAULT_RETAIN_DAYS)
    # Start with options-defined whitelist (direct numbers + contacts)
    options = get_saved_options(hass)
    parsed = parse_whitelist_options(options)
    saved_numbers = parsed.get("phone_numbers", set())
    contacts = parsed.get("contacts", {})

    # Compose initial whitelist (numbers and contact names)
    whitelist = set(saved_numbers)
    # Add contact numbers and names
    for c in contacts.values():
        if c.get("number"):
            whitelist.add(c["number"])
        if c.get("name"):
            whitelist.add(c["name"])

    # Merge any service-call provided whitelist (overrides/extends)
    call_whitelist = call.data.get(ATTR_WHITELIST, []) or []
    for w in call_whitelist:
        whitelist.add(w)
    dry_run = call.data.get(ATTR_DRY_RUN, DEFAULT_DRY_RUN)

    try:
        entry = get_netgear_lte_entry(hass, host)
        modem = ModemConnection(entry.runtime_data.modem)

        LOGGER.info("Fetching SMS inbox for cleanup from %s", entry.data.get("host"))
        sms_list = await modem.get_sms_list()

        # Normalize timestamps and sort newest -> oldest
        def parse_ts(ts: str | None) -> datetime | None:
            if not ts:
                return None
            for fmt in (
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S",
            ):
                try:
                    return datetime.strptime(ts, fmt)
                except Exception:
                    continue
            try:
                return datetime.fromisoformat(ts)
            except Exception:
                return None

        annotated = []
        for sms in sms_list:
            ts = parse_ts(getattr(sms, "timestamp", None))
            annotated.append((sms, ts))

        # Sort by timestamp desc; if missing timestamp, keep original order (assume modem returns newest first)
        annotated.sort(key=lambda x: (x[1] is not None, x[1]), reverse=True)

        # Determine messages to keep (by retain_count)
        keep_ids: set[int] = set()
        kept = 0
        for sms, ts in annotated:
            if sms.sender in whitelist:
                # Always keep whitelisted
                keep_ids.add(sms.id)
                continue
            if retain_count and kept < retain_count:
                keep_ids.add(sms.id)
                kept += 1

        # Determine by retain_days
        delete_candidates: list[int] = []
        if retain_days and retain_days > 0:
            cutoff = datetime.utcnow() - timedelta(days=retain_days)
            for sms, ts in annotated:
                if ts is None:
                    continue
                if (
                    ts < cutoff
                    and sms.id not in keep_ids
                    and sms.sender not in whitelist
                ):
                    delete_candidates.append(sms.id)

        # Also add any non-kept messages beyond retain_count
        for sms, ts in reversed(annotated):
            # reversed iterates oldest first; delete if not kept and not whitelisted
            if sms.id in keep_ids or sms.sender in whitelist:
                continue
            if sms.id not in delete_candidates and sms.id not in keep_ids:
                delete_candidates.append(sms.id)

        # Remove duplicates while preserving order
        seen = set()
        final_delete = []
        for sid in delete_candidates:
            if sid in seen:
                continue
            seen.add(sid)
            final_delete.append(sid)

        if not final_delete:
            LOGGER.info("No messages to delete after applying cleanup policy")
            hass.bus.async_fire(
                EVENT_CLEANUP_COMPLETE,
                {
                    ATTR_HOST: entry.data.get("host"),
                    ATTR_COUNT_DELETED: 0,
                    ATTR_WHITELIST: whitelist,
                    ATTR_DRY_RUN: dry_run,
                },
            )
            return

        if dry_run:
            # Report proposed deletions
            LOGGER.info("Dry run cleanup, would delete %d messages", len(final_delete))
            hass.bus.async_fire(
                EVENT_CLEANUP_COMPLETE,
                {
                    ATTR_HOST: entry.data.get("host"),
                    ATTR_COUNT_DELETED: len(final_delete),
                    ATTR_MESSAGES: final_delete,
                    ATTR_WHITELIST: whitelist,
                    ATTR_DRY_RUN: True,
                },
            )
            return

        # Perform deletion
        deleted_count = await modem.delete_sms_batch(final_delete)
        hass.bus.async_fire(
            EVENT_CLEANUP_COMPLETE,
            {
                ATTR_HOST: entry.data.get("host"),
                ATTR_COUNT_DELETED: deleted_count,
                ATTR_MESSAGES: final_delete,
                ATTR_WHITELIST: whitelist,
                ATTR_DRY_RUN: False,
            },
        )

        LOGGER.info("Cleanup deleted %d messages", deleted_count)

    except NetgearLTECoreMissingError as ex:
        LOGGER.error("Configuration error: %s", ex)
        raise ServiceValidationError(str(ex), translation_domain=DOMAIN) from ex
    except EternalEgyptVersionError as ex:
        LOGGER.error("API compatibility error: %s", ex)
        raise ServiceValidationError(
            f"API compatibility issue: {ex}",
            translation_domain=DOMAIN,
        ) from ex
    except ModemCommunicationError as ex:
        LOGGER.warning("Failed to cleanup inbox: %s", ex)
        raise ServiceValidationError(
            f"Cleanup error: {ex}",
            translation_domain=DOMAIN,
        ) from ex
    except Exception as ex:
        LOGGER.exception("Unexpected error in cleanup_inbox service")
        raise ServiceValidationError(
            f"Unexpected error: {type(ex).__name__}",
            translation_domain=DOMAIN,
        ) from ex


# The operator-specific deletion service was removed; use cleanup_inbox instead.


async def _service_get_inbox_json(call: ServiceCall) -> dict[str, Any]:
    """Get inbox as JSON (for advanced users/integrations).

    This service returns the inbox data as a dictionary instead of
    firing an event. Useful for template sensors and custom integrations.
    """
    hass = call.hass
    host = call.data.get(ATTR_HOST)

    try:
        entry = get_netgear_lte_entry(hass, host)
        modem = ModemConnection(entry.runtime_data.modem)

        LOGGER.info("Fetching SMS inbox JSON from %s", entry.data.get("host"))
        sms_list = await modem.get_sms_list()

        return {
            ATTR_HOST: entry.data.get("host"),
            ATTR_MESSAGES: [msg.to_dict() for msg in sms_list],
        }

    except NetgearLTECoreMissingError as ex:
        LOGGER.error("Configuration error: %s", ex)
        raise ServiceValidationError(str(ex), translation_domain=DOMAIN) from ex
    except EternalEgyptVersionError as ex:
        LOGGER.error("API compatibility error: %s", ex)
        raise ServiceValidationError(
            f"API compatibility issue: {ex}",
            translation_domain=DOMAIN,
        ) from ex
    except ModemCommunicationError as ex:
        LOGGER.warning("Failed to fetch inbox: %s", ex)
        raise ServiceValidationError(
            f"Modem error: {ex}",
            translation_domain=DOMAIN,
        ) from ex
    except Exception as ex:
        LOGGER.exception("Unexpected error in get_inbox_json service")
        raise ServiceValidationError(
            f"Unexpected error: {type(ex).__name__}",
            translation_domain=DOMAIN,
        ) from ex


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register all services for Netgear LTE SMS Manager."""
    service_handlers = {
        SERVICE_LIST_INBOX: (_service_list_inbox, LIST_INBOX_SCHEMA),
        SERVICE_DELETE_SMS: (_service_delete_sms, DELETE_SMS_SCHEMA),
        SERVICE_CLEANUP_INBOX: (_service_cleanup_inbox, CLEANUP_INBOX_SCHEMA),
        SERVICE_GET_INBOX_JSON: (_service_get_inbox_json, GET_INBOX_JSON_SCHEMA),
    }

    for service_name, (handler, schema) in service_handlers.items():
        hass.services.async_register(
            DOMAIN,
            service_name,
            handler,
            schema=schema,
        )
        LOGGER.info("Registered service: %s", service_name)
