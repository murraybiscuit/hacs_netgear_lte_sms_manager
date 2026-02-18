"""Helper functions for accessing the netgear_lte core component."""

from __future__ import annotations

from .const import DOMAIN_NETGEAR_CORE, LOGGER
from .models import NetgearLTECoreMissingError

# Avoid importing constants from homeassistant to keep type stubs happy
HOST_KEY = "host"


def get_netgear_lte_entry(
    hass: "object", host: str | None = None
) -> "ConfigEntry":
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


def get_all_netgear_modems(hass: "object") -> dict[str, dict]:
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
