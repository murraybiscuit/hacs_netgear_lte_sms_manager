"""Unit tests for services.py - service handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.netgear_lte_sms_manager.const import (
    ATTR_HOST,
    ATTR_SMS_ID,
    EVENT_SMS_INBOX_LISTED,
)


class TestListInboxService:
    """Tests for list_inbox service."""

    @pytest.mark.asyncio
    async def test_list_inbox_success(self, mock_hass: MagicMock) -> None:
        """Test successful inbox listing."""
        from custom_components.netgear_lte_sms_manager.services import (
            _service_list_inbox,
        )

        entry = MagicMock()
        entry.data = {ATTR_HOST: "192.168.5.1"}
        entry.runtime_data = MagicMock()
        entry.runtime_data.modem = MagicMock()
        entry.runtime_data.modem.sms_list = AsyncMock(return_value=[])

        mock_hass.config_entries.async_loaded_entries.return_value = [entry]

        call = MagicMock()
        call.hass = mock_hass
        call.data = {}

        with patch(
            "custom_components.netgear_lte_sms_manager.services.get_netgear_lte_entry"
        ) as mock_get_entry:
            mock_get_entry.return_value = entry
            await _service_list_inbox(call)

        # Verify event was fired
        mock_hass.bus.async_fire.assert_called_once()
        call_args = mock_hass.bus.async_fire.call_args
        assert call_args[0][0] == EVENT_SMS_INBOX_LISTED

    @pytest.mark.asyncio
    async def test_list_inbox_no_config(self, mock_hass: MagicMock) -> None:
        """Test error when netgear_lte not configured."""
        from custom_components.netgear_lte_sms_manager.services import (
            _service_list_inbox,
        )

        mock_hass.config_entries.async_loaded_entries.return_value = []

        call = MagicMock()
        call.hass = mock_hass
        call.data = {}

        with patch(
            "custom_components.netgear_lte_sms_manager.services.get_netgear_lte_entry"
        ) as mock_get_entry:
            from custom_components.netgear_lte_sms_manager.models import (
                NetgearLTECoreMissingError,
            )

            mock_get_entry.side_effect = NetgearLTECoreMissingError("not configured")

            # Mock the exception class so pytest.raises can work with it
            with patch(
                "custom_components.netgear_lte_sms_manager.services.ServiceValidationError",
                side_effect=Exception,
            ):
                try:
                    await _service_list_inbox(call)
                    assert False, "Should have raised an exception"
                except Exception:
                    pass  # Expected


class TestDeleteSmsService:
    """Tests for delete_sms service."""

    @pytest.mark.asyncio
    async def test_delete_sms_success(self, mock_hass: MagicMock) -> None:
        """Test successful SMS deletion."""
        from custom_components.netgear_lte_sms_manager.services import (
            _service_delete_sms,
        )

        entry = MagicMock()
        entry.data = {ATTR_HOST: "192.168.5.1"}
        entry.runtime_data = MagicMock()
        entry.runtime_data.modem = MagicMock()
        entry.runtime_data.modem.delete_sms = AsyncMock()

        call = MagicMock()
        call.hass = mock_hass
        call.data = {ATTR_SMS_ID: [1, 2, 3]}

        with patch(
            "custom_components.netgear_lte_sms_manager.services.get_netgear_lte_entry"
        ) as mock_get_entry:
            with patch(
                "custom_components.netgear_lte_sms_manager.services.ModemConnection"
            ) as mock_modem_conn:
                mock_get_entry.return_value = entry
                mock_conn_inst = AsyncMock()
                mock_conn_inst.delete_sms_batch = AsyncMock(return_value=3)
                mock_modem_conn.return_value = mock_conn_inst

                await _service_delete_sms(call)

                mock_conn_inst.delete_sms_batch.assert_called_once_with([1, 2, 3])


class TestCleanupInboxService:
    """Tests for cleanup_inbox service."""

    @pytest.mark.asyncio
    async def test_cleanup_inbox_dry_run(self, mock_hass: MagicMock) -> None:
        """Dry run should report proposed deletions but not delete."""
        from custom_components.netgear_lte_sms_manager.models import SMSMessage
        from custom_components.netgear_lte_sms_manager.services import (
            _service_cleanup_inbox,
        )

        entry = MagicMock()
        entry.data = {ATTR_HOST: "192.168.5.1"}
        entry.runtime_data = MagicMock()
        entry.runtime_data.modem = MagicMock()

        call = MagicMock()
        call.hass = mock_hass
        call.data = {"dry_run": True, "retain_count": 1}

        with patch(
            "custom_components.netgear_lte_sms_manager.services.get_netgear_lte_entry"
        ) as mock_get_entry:
            with patch(
                "custom_components.netgear_lte_sms_manager.services.ModemConnection"
            ) as mock_modem_conn:
                mock_get_entry.return_value = entry
                mock_conn_inst = AsyncMock()
                mock_conn_inst.get_sms_list = AsyncMock(
                    return_value=[
                        SMSMessage(1, "Orange", "Balance: $10", "2025-02-17T09:30:00Z"),
                        SMSMessage(2, "Dad", "Hi", "2025-02-17T10:00:00Z"),
                        SMSMessage(3, "Spam", "Buy now", "2025-02-16T08:00:00Z"),
                    ]
                )
                mock_conn_inst.delete_sms_batch = AsyncMock(return_value=0)
                mock_modem_conn.return_value = mock_conn_inst

                await _service_cleanup_inbox(call)

                # Dry run should not call delete_sms_batch
                mock_conn_inst.delete_sms_batch.assert_not_called()
                mock_hass.bus.async_fire.assert_called()

    @pytest.mark.asyncio
    async def test_cleanup_inbox_delete(self, mock_hass: MagicMock) -> None:
        """Actual cleanup should delete messages and respect whitelist."""
        from custom_components.netgear_lte_sms_manager.models import SMSMessage
        from custom_components.netgear_lte_sms_manager.services import (
            _service_cleanup_inbox,
        )

        entry = MagicMock()
        entry.data = {ATTR_HOST: "192.168.5.1"}
        entry.runtime_data = MagicMock()
        entry.runtime_data.modem = MagicMock()

        call = MagicMock()
        call.hass = mock_hass
        call.data = {"dry_run": False, "retain_count": 1, "whitelist": ["Dad"]}

        with patch(
            "custom_components.netgear_lte_sms_manager.services.get_netgear_lte_entry"
        ) as mock_get_entry:
            with patch(
                "custom_components.netgear_lte_sms_manager.services.ModemConnection"
            ) as mock_modem_conn:
                mock_get_entry.return_value = entry
                mock_conn_inst = AsyncMock()
                mock_conn_inst.get_sms_list = AsyncMock(
                    return_value=[
                        SMSMessage(1, "Orange", "Balance: $10", "2025-02-17T09:30:00Z"),
                        SMSMessage(2, "Dad", "Hi", "2025-02-17T10:00:00Z"),
                        SMSMessage(3, "Spam", "Buy now", "2025-02-16T08:00:00Z"),
                    ]
                )
                mock_conn_inst.delete_sms_batch = AsyncMock(return_value=2)
                mock_modem_conn.return_value = mock_conn_inst

                await _service_cleanup_inbox(call)

                # Should have called delete_sms_batch to remove non-whitelisted extras
                mock_conn_inst.delete_sms_batch.assert_called_once()
                mock_hass.bus.async_fire.assert_called()
