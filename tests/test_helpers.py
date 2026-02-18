"""Unit tests for helpers.py - netgear_lte core integration."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.netgear_lte_sms_manager.helpers import (
    get_all_netgear_modems,
    get_netgear_lte_entry,
)
from custom_components.netgear_lte_sms_manager.models import (
    NetgearLTECoreMissingError,
)


class TestGetNetgearLTEEntry:
    """Tests for get_netgear_lte_entry helper."""

    def test_no_entries_configured(self, mock_hass: MagicMock) -> None:
        """Test error when no netgear_lte entries are configured."""
        mock_hass.config_entries.async_loaded_entries.return_value = []

        with pytest.raises(NetgearLTECoreMissingError, match="not configured"):
            get_netgear_lte_entry(mock_hass)

    def test_single_entry_auto_select(self, mock_hass: MagicMock) -> None:
        """Test auto-selection of single entry when host not specified."""
        entry = MagicMock()
        entry.data = {"host": "192.168.5.1"}
        mock_hass.config_entries.async_loaded_entries.return_value = [entry]

        result = get_netgear_lte_entry(mock_hass)
        assert result == entry

    def test_multiple_entries_host_required(self, mock_hass: MagicMock) -> None:
        """Test that host is required when multiple modems are configured."""
        entry1 = MagicMock()
        entry1.data = {"host": "192.168.5.1"}
        entry2 = MagicMock()
        entry2.data = {"host": "192.168.6.1"}
        mock_hass.config_entries.async_loaded_entries.return_value = [
            entry1,
            entry2,
        ]

        with pytest.raises(NetgearLTECoreMissingError, match="host parameter"):
            get_netgear_lte_entry(mock_hass, host=None)

    def test_matching_host_found(self, mock_hass: MagicMock) -> None:
        """Test finding entry by host address."""
        entry1 = MagicMock()
        entry1.data = {"host": "192.168.5.1"}
        entry2 = MagicMock()
        entry2.data = {"host": "192.168.6.1"}
        mock_hass.config_entries.async_loaded_entries.return_value = [
            entry1,
            entry2,
        ]

        result = get_netgear_lte_entry(mock_hass, host="192.168.6.1")
        assert result == entry2

    def test_host_not_found(self, mock_hass: MagicMock) -> None:
        """Test error when specified host is not found."""
        entry = MagicMock()
        entry.data = {"host": "192.168.5.1"}
        mock_hass.config_entries.async_loaded_entries.return_value = [entry]

        with pytest.raises(NetgearLTECoreMissingError, match="No Netgear LTE modem found"):
            get_netgear_lte_entry(mock_hass, host="192.168.99.1")


class TestGetAllNetgearModems:
    """Tests for get_all_netgear_modems helper."""

    def test_no_modems(self, mock_hass: MagicMock) -> None:
        """Test when no modems are configured."""
        mock_hass.config_entries.async_loaded_entries.return_value = []

        result = get_all_netgear_modems(mock_hass)
        assert result == {}

    def test_single_modem(self, mock_hass: MagicMock, mock_modem: MagicMock) -> None:
        """Test discovering single modem."""
        entry = MagicMock()
        entry.data = {"host": "192.168.5.1"}
        entry.title = "Netgear LM1200"
        entry.runtime_data = MagicMock()
        entry.runtime_data.modem = mock_modem
        mock_hass.config_entries.async_loaded_entries.return_value = [entry]

        result = get_all_netgear_modems(mock_hass)

        assert "192.168.5.1" in result
        assert result["192.168.5.1"]["title"] == "Netgear LM1200"
        assert result["192.168.5.1"]["host"] == "192.168.5.1"
        assert result["192.168.5.1"]["modem"] == mock_modem

    def test_multiple_modems(
        self, mock_hass: MagicMock, mock_modem: MagicMock
    ) -> None:
        """Test discovering multiple modems."""
        modem2 = MagicMock()

        entry1 = MagicMock()
        entry1.data = {"host": "192.168.5.1"}
        entry1.title = "Modem 1"
        entry1.runtime_data = MagicMock()
        entry1.runtime_data.modem = mock_modem

        entry2 = MagicMock()
        entry2.data = {"host": "192.168.6.1"}
        entry2.title = "Modem 2"
        entry2.runtime_data = MagicMock()
        entry2.runtime_data.modem = modem2

        mock_hass.config_entries.async_loaded_entries.return_value = [
            entry1,
            entry2,
        ]

        result = get_all_netgear_modems(mock_hass)

        assert len(result) == 2
        assert "192.168.5.1" in result
        assert "192.168.6.1" in result

    def test_entry_without_runtime_data(self, mock_hass: MagicMock) -> None:
        """Test handling entry with no runtime data (loading state)."""
        entry = MagicMock()
        entry.data = {"host": "192.168.5.1"}
        entry.title = "Netgear LM1200"
        entry.runtime_data = None
        mock_hass.config_entries.async_loaded_entries.return_value = [entry]

        result = get_all_netgear_modems(mock_hass)
        assert result == {}
