"""Sensor platform for Netgear LTE SMS Manager."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LOGGER
from .coordinator import SMSCoordinator
from .helpers import get_netgear_lte_entry, load_contacts
from .models import NetgearLTECoreMissingError

_DEVICE_INFO_KWARGS = {
    "manufacturer": "Netgear",
    "model": "LTE SMS Manager",
    "entry_type": DeviceEntryType.SERVICE,
}


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Netgear LTE SMS Manager",
        **_DEVICE_INFO_KWARGS,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SMSCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        SMSInboxSensor(coordinator, entry),
        SIMNumberSensor(coordinator, entry),
    ])


class SMSInboxSensor(CoordinatorEntity[SMSCoordinator], SensorEntity):
    """Sensor exposing SMS inbox count and message list."""

    _attr_icon = "mdi:message-text-outline"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "messages"
    _attr_has_entity_name = True
    _attr_translation_key = "sms_inbox"

    def __init__(self, coordinator: SMSCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_sms_inbox_v2"
        self._attr_name = "Inbox"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> int | None:
        if self.coordinator.data is None:
            return None
        return len(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict:
        messages = [msg.to_dict() for msg in self.coordinator.data] if self.coordinator.data else []
        contacts = load_contacts(self._entry.options)
        sim_number = _get_sim_number(self.hass)
        return {"messages": messages, "contacts": contacts, "sim_number": sim_number}


class SIMNumberSensor(CoordinatorEntity[SMSCoordinator], SensorEntity):
    """Diagnostic sensor showing the modem SIM phone number."""

    _attr_icon = "mdi:sim"
    _attr_has_entity_name = True
    _attr_translation_key = "sim_number"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: SMSCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_sim_number"
        self._attr_name = "SIM number"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> str | None:
        return _get_sim_number(self.hass) or None


def _get_sim_number(hass: HomeAssistant) -> str:
    try:
        lte_entry = get_netgear_lte_entry(hass)
        info = lte_entry.runtime_data.data
        if info is None:
            return ""
        sim_number = info.items.get("sim.phonenumber", "")
        LOGGER.debug("sim_number from coordinator: %r", sim_number)
        return sim_number
    except NetgearLTECoreMissingError as err:
        LOGGER.debug("netgear_lte entry not available: %s", err)
        return ""
    except Exception:
        LOGGER.exception("Unexpected error reading sim_number")
        return ""
