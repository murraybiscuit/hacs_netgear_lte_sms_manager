"""Unit tests for models.py - SMS message and modem wrapper."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.netgear_lte_sms_manager.models import (
    DependencyError,
    EternalEgyptVersionError,
    ModemCommunicationError,
    ModemConnection,
    NetgearLTECoreMissingError,
    SMSMessage,
)


class TestSMSMessage:
    """Tests for SMSMessage dataclass."""

    def test_sms_message_creation(self) -> None:
        """Test creating an SMS message."""
        msg = SMSMessage(
            id=1,
            sender="Dad",
            message="Hello",
            timestamp="2025-02-17T10:00:00Z",
        )
        assert msg.id == 1
        assert msg.sender == "Dad"
        assert msg.message == "Hello"
        assert msg.timestamp == "2025-02-17T10:00:00Z"

    def test_sms_message_to_dict(self) -> None:
        """Test converting SMS message to dictionary."""
        msg = SMSMessage(id=1, sender="Test", message="Hi")
        data = msg.to_dict()
        assert data["id"] == 1
        assert data["sender"] == "Test"
        assert data["message"] == "Hi"
        assert data["timestamp"] is None


class TestModemConnection:
    """Tests for ModemConnection wrapper."""

    def test_modem_connection_init_with_none(self) -> None:
        """Test that ModemConnection raises on None modem."""
        with pytest.raises(ValueError, match="modem cannot be None"):
            ModemConnection(None)

    @pytest.mark.asyncio
    async def test_get_sms_list_success(self, mock_modem: MagicMock) -> None:
        """Test successful SMS list retrieval."""
        conn = ModemConnection(mock_modem)
        sms_list = await conn.get_sms_list()

        assert len(sms_list) == 3
        assert sms_list[0].id == 1
        assert sms_list[0].sender == "Dad"
        assert sms_list[1].sender == "Orange"

    @pytest.mark.asyncio
    async def test_get_sms_list_missing_method(
        self, mock_modem: MagicMock
    ) -> None:
        """Test error when eternalegypt API changes (missing method)."""
        # Simulate modem without sms_list method
        delattr(mock_modem, "sms_list")

        conn = ModemConnection(mock_modem)
        with pytest.raises(EternalEgyptVersionError, match="sms_list"):
            await conn.get_sms_list()

    @pytest.mark.asyncio
    async def test_get_sms_list_attribute_error(
        self, mock_modem: MagicMock
    ) -> None:
        """Test handling of AttributeError from modem."""
        mock_modem.sms_list = AsyncMock(side_effect=AttributeError("Missing field"))

        conn = ModemConnection(mock_modem)
        with pytest.raises(EternalEgyptVersionError, match="API mismatch"):
            await conn.get_sms_list()

    @pytest.mark.asyncio
    async def test_get_sms_list_timeout_error(
        self, mock_modem: MagicMock
    ) -> None:
        """Test handling of timeout from modem."""
        mock_modem.sms_list = AsyncMock(side_effect=TimeoutError("Modem offline"))

        conn = ModemConnection(mock_modem)
        with pytest.raises(ModemCommunicationError, match="Timeout"):
            await conn.get_sms_list()

    @pytest.mark.asyncio
    async def test_delete_sms_success(self, mock_modem: MagicMock) -> None:
        """Test successful SMS deletion."""
        conn = ModemConnection(mock_modem)
        await conn.delete_sms(1)

        mock_modem.delete_sms.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_sms_missing_method(
        self, mock_modem: MagicMock
    ) -> None:
        """Test error when delete_sms method doesn't exist."""
        delattr(mock_modem, "delete_sms")

        conn = ModemConnection(mock_modem)
        with pytest.raises(EternalEgyptVersionError, match="delete_sms"):
            await conn.delete_sms(1)

    @pytest.mark.asyncio
    async def test_delete_sms_communication_error(
        self, mock_modem: MagicMock
    ) -> None:
        """Test handling of communication error during deletion."""
        mock_modem.delete_sms = AsyncMock(
            side_effect=TimeoutError("Modem not responding")
        )

        conn = ModemConnection(mock_modem)
        with pytest.raises(ModemCommunicationError, match="Failed to delete"):
            await conn.delete_sms(1)

    @pytest.mark.asyncio
    async def test_delete_sms_batch_success(
        self, mock_modem: MagicMock
    ) -> None:
        """Test successful batch SMS deletion."""
        conn = ModemConnection(mock_modem)
        deleted = await conn.delete_sms_batch([1, 2, 3])

        assert deleted == 3
        assert mock_modem.delete_sms.call_count == 3

    @pytest.mark.asyncio
    async def test_delete_sms_batch_partial_failure(
        self, mock_modem: MagicMock
    ) -> None:
        """Test batch deletion with some failures."""
        # First call succeeds, second fails, third succeeds
        mock_modem.delete_sms = AsyncMock(
            side_effect=[
                None,  # Success
                TimeoutError("Modem offline"),  # Failure
                None,  # Success
            ]
        )

        conn = ModemConnection(mock_modem)
        deleted = await conn.delete_sms_batch([1, 2, 3])

        assert deleted == 2
        assert mock_modem.delete_sms.call_count == 3

    @pytest.mark.asyncio
    async def test_delete_sms_batch_all_failures(
        self, mock_modem: MagicMock
    ) -> None:
        """Test batch deletion where all fail."""
        mock_modem.delete_sms = AsyncMock(
            side_effect=TimeoutError("Modem offline")
        )

        conn = ModemConnection(mock_modem)
        with pytest.raises(ModemCommunicationError, match="Failed to delete any"):
            await conn.delete_sms_batch([1, 2])
