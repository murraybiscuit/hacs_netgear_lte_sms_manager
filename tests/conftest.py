"""Pytest configuration and shared fixtures."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_modem() -> MagicMock:
    """Mock eternalegypt.Modem instance."""
    modem = AsyncMock()
    modem.token = "fake-test-token"
    modem.hostname = "192.168.5.1"

    # Mock sms_list to return test data
    modem.sms_list = AsyncMock(
        return_value=[
            MagicMock(
                id=1,
                sender="Dad",
                message="Hi son, how are you?",
                timestamp="2025-02-17T10:00:00Z",
            ),
            MagicMock(
                id=2,
                sender="Orange",
                message="Your balance is $10.50",
                timestamp="2025-02-17T09:30:00Z",
            ),
            MagicMock(
                id=3,
                sender="Work",
                message="Meeting moved to 3pm",
                timestamp="2025-02-17T09:00:00Z",
            ),
        ]
    )

    modem.delete_sms = AsyncMock()
    return modem


@pytest.fixture
def mock_config_entry() -> MagicMock:
    """Mock Home Assistant ConfigEntry with netgear_lte data."""
    entry = MagicMock()
    entry.data = {"host": "192.168.5.1"}
    entry.title = "Netgear LM1200"
    entry.runtime_data = MagicMock()
    entry.runtime_data.modem = None  # Will be set with mock_modem when needed
    return entry


@pytest.fixture
def mock_hass() -> AsyncMock:
    """Mock Home Assistant instance."""
    hass = AsyncMock()
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_loaded_entries = MagicMock(return_value=[])
    hass.bus = MagicMock()
    hass.bus.async_fire = MagicMock()
    hass.services = MagicMock()
    hass.services.async_register = MagicMock()
    return hass
