"""Helper functions for accessing the netgear_lte core component."""

from __future__ import annotations

import json
import uuid

from .const import DOMAIN, DOMAIN_NETGEAR_CORE, LOGGER
from .models import NetgearLTECoreMissingError

# Avoid importing constants from homeassistant to keep type stubs happy
HOST_KEY = "host"


def get_netgear_lte_entry(hass, host: str | None = None):
    """Get a netgear_lte config entry by host or return the first loaded entry.

    Args:
        hass: Home Assistant instance.
        host: Optional IP address of the modem. If not provided and only one
              modem is configured, returns that one.

    Returns:
        The netgear_lte ConfigEntry.

    Raises:
        NetgearLTECoreMissingError: If no entries are found or host doesn't match.
    """
    entries = hass.config_entries.async_loaded_entries(DOMAIN_NETGEAR_CORE)

    if not entries:
        raise NetgearLTECoreMissingError(
            "netgear_lte component is not configured. Please set up at least one Netgear LTE modem."
        )

    if host is None:
        # Return first entry if only one, otherwise require host parameter
        if len(entries) == 1:
            LOGGER.debug("Using single configured Netgear LTE modem")
            return entries[0]
        raise NetgearLTECoreMissingError(
            f"Multiple Netgear LTE modems configured, host parameter is required. "
            f"Available hosts: {[e.data.get(HOST_KEY) for e in entries]}"
        )

    for entry in entries:
        if entry.data.get(HOST_KEY) == host:
            LOGGER.debug("Found netgear_lte entry for host %s", host)
            return entry

    raise NetgearLTECoreMissingError(
        f"No Netgear LTE modem found at {host}. "
        f"Available hosts: {[e.data.get(HOST_KEY) for e in entries]}"
    )


def get_all_netgear_modems(hass) -> dict[str, dict]:
    """Get all configured Netgear LTE modems and their info.

    Useful for discovery and multi-modem setups.

    Args:
        hass: Home Assistant instance.

    Returns:
        Dictionary with host as key and modem info dict as value.
        Structure: {
            "192.168.5.1": {
                "title": "Netgear LM1200",
                "host": "192.168.5.1",
                "modem": Modem instance,
                "entry": ConfigEntry instance,
            }
        }
    """
    modems = {}
    for entry in hass.config_entries.async_loaded_entries(DOMAIN_NETGEAR_CORE):
        host = entry.data.get(HOST_KEY)
        if host and entry.runtime_data:
            modems[host] = {
                "title": entry.title,
                "host": host,
                "modem": entry.runtime_data.modem,
                "entry": entry,
            }

    LOGGER.debug("Found %d Netgear LTE modems", len(modems))
    return modems


def get_saved_options(hass) -> dict:
    """Return stored integration options (first config entry) or empty dict.

    Options are stored as raw multiline strings and parsed by helpers.
    """
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        return {}
    # Use first entry for global options
    return dict(entries[0].options or {})


def parse_whitelist_options(options: dict) -> dict:
    """Parse options into structured whitelist data.

    Returns dict with keys:
      - 'phone_numbers': set of direct phone number strings
      - 'contacts': dict mapping contact uuid -> {"name": str, "number": str}
    """
    phone_numbers = set()
    contacts: dict[str, dict] = {}

    # Direct phone numbers: newline-separated (for power users)
    raw_nums = options.get("whitelist_numbers") or ""
    for line in (l.strip() for l in raw_nums.splitlines() if l.strip()):
        phone_numbers.add(line)

    # Contacts: JSON array of {uuid, name, number}
    # For backward compat, also parse csv format "name,number" (auto-generate uuid)
    raw_contacts = options.get("contacts") or ""
    if raw_contacts.strip().startswith("["):
        # JSON format
        try:
            contacts_list = json.loads(raw_contacts)
            for c in contacts_list:
                cid = c.get("uuid") or str(uuid.uuid4())
                if c.get("name") and c.get("number"):
                    contacts[cid] = {"name": c["name"], "number": c["number"]}
        except (json.JSONDecodeError, TypeError):
            pass  # Ignore JSON parsing errors
    else:
        # CSV backward compat: "name,number" lines (auto-generate uuid)
        for line in (l.strip() for l in raw_contacts.splitlines() if l.strip()):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2:
                name, number = parts[0], parts[1]
                if name and number:
                    cid = str(uuid.uuid4())
                    contacts[cid] = {"name": name, "number": number}

    return {"phone_numbers": phone_numbers, "contacts": contacts}
