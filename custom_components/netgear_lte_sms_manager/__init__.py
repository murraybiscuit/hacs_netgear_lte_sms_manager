"""Netgear LTE SMS Manager integration for Home Assistant.

This integration extends the core netgear_lte component with SMS inbox
management capabilities, providing services to list, delete, and filter
SMS messages from the modem.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, LOGGER
from .services import async_setup_services


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Netgear LTE SMS Manager integration."""
    LOGGER.info("Setting up Netgear LTE SMS Manager")
    async_setup_services(hass)
    return True
