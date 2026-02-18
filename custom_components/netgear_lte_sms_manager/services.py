"""Services for the Netgear LTE SMS Manager integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_COUNT_DELETED,
    ATTR_HOST,
    ATTR_MESSAGES,
    ATTR_OPERATORS,
    ATTR_SMS_ID,
    ATTR_TIMESTAMP,
    DEFAULT_OPERATOR_PATTERNS,
    DOMAIN,
    EVENT_DELETE_OPERATOR_SMS_COMPLETE,
    EVENT_SMS_INBOX_LISTED,
    LOGGER,
    SERVICE_DELETE_OPERATOR_SMS,
    SERVICE_DELETE_SMS,
    SERVICE_GET_INBOX_JSON,
    SERVICE_LIST_INBOX,
)
from .helpers import get_all_netgear_modems, get_netgear_lte_entry
from .models import (
    DependencyError,
    EternalEgyptVersionError,
    ModemConnection,
    ModemCommunicationError,
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

DELETE_OPERATOR_SMS_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_HOST): cv.string,
        vol.Optional(ATTR_OPERATORS): vol.All(cv.ensure_list, [cv.string]),
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

        LOGGER.info("Fetching SMS inbox from %s", entry.data[CONF_HOST])
        sms_list = await modem.get_sms_list()

        event_data = {
            ATTR_HOST: entry.data[CONF_HOST],
            ATTR_MESSAGES: [msg.to_dict() for msg in sms_list],
        }

        LOGGER.info(
            "Found %d SMS messages in inbox, firing event", len(sms_list)
        )
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

        LOGGER.info("Deleting %d SMS from %s", len(sms_ids), entry.data[CONF_HOST])
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


async def _service_delete_operator_sms(call: ServiceCall) -> None:
    """Delete SMS from known operators (auto-cleanup).

    This service automatically deletes SMS messages from common
    network operators (e.g., balance notifications, network updates).
    """
    hass = call.hass
    host = call.data.get(ATTR_HOST)
    operators = call.data.get(ATTR_OPERATORS, DEFAULT_OPERATOR_PATTERNS)

    try:
        entry = get_netgear_lte_entry(hass, host)
        modem = ModemConnection(entry.runtime_data.modem)

        LOGGER.info(
            "Fetching SMS inbox to filter operator messages from %s",
            entry.data[CONF_HOST],
        )
        sms_list = await modem.get_sms_list()

        # Find SMS from operators
        sms_to_delete = []
        for sms in sms_list:
            for operator in operators:
                if operator.lower() in sms.sender.lower():
                    sms_to_delete.append(sms.id)
                    LOGGER.debug(
                        "Marking SMS %d from %s for deletion",
                        sms.id,
                        sms.sender,
                    )
                    break

        if not sms_to_delete:
            LOGGER.info(
                "No operator SMS found matching patterns: %s",
                operators,
            )
            deleted_count = 0
        else:
            LOGGER.info(
                "Deleting %d operator SMS from %s",
                len(sms_to_delete),
                entry.data[CONF_HOST],
            )
            deleted_count = await modem.delete_sms_batch(sms_to_delete)

        event_data = {
            ATTR_HOST: entry.data[CONF_HOST],
            ATTR_COUNT_DELETED: deleted_count,
            ATTR_OPERATORS: operators,
        }
        hass.bus.async_fire(EVENT_DELETE_OPERATOR_SMS_COMPLETE, event_data)

        LOGGER.info("Deleted %d operator SMS", deleted_count)

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
        LOGGER.warning("Failed to delete operator SMS: %s", ex)
        raise ServiceValidationError(
            f"Deletion error: {ex}",
            translation_domain=DOMAIN,
        ) from ex
    except Exception as ex:
        LOGGER.exception("Unexpected error in delete_operator_sms service")
        raise ServiceValidationError(
            f"Unexpected error: {type(ex).__name__}",
            translation_domain=DOMAIN,
        ) from ex


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

        LOGGER.info("Fetching SMS inbox JSON from %s", entry.data[CONF_HOST])
        sms_list = await modem.get_sms_list()

        return {
            ATTR_HOST: entry.data[CONF_HOST],
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
        SERVICE_DELETE_OPERATOR_SMS: (
            _service_delete_operator_sms,
            DELETE_OPERATOR_SMS_SCHEMA,
        ),
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
