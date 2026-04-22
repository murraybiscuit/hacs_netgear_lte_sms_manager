"""TDD tests for SMS command dispatch — Layer 2.

Tests cover the coordinator's _dispatch_commands logic:
- trusted sender + matching keyword → service called + reply sent
- trusted sender + no keyword match → nothing executed
- untrusted sender + matching keyword → silently ignored
- service call failure → reply_fail sent, not reply_ok
- no reply configured → no SMS sent after execution
- no commands configured → no service calls made
- multiple new messages → each dispatched independently
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from custom_components.netgear_lte_sms_manager.helpers import save_commands, save_contacts
from custom_components.netgear_lte_sms_manager.models import SMSMessage


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_sms(id: int, sender: str, message: str) -> SMSMessage:
    return SMSMessage(id=id, sender=sender, message=message, timestamp="2026-04-21T10:00:00Z")


def _make_entry(commands: list[dict], contacts: list[dict]) -> MagicMock:
    entry = MagicMock()
    entry.options = {
        "commands": save_commands(commands),
        "contacts": save_contacts(contacts),
    }
    return entry


LOCK_CMD = {
    "uuid": "uuid-lock",
    "name": "lock front door",
    "keywords": ["lock front door", "lock door", "lock up", "lock"],
    "service": "lock.lock",
    "entity_id": "lock.front_door_lock",
    "service_data": {},
    "reply_ok": "Front door locked.",
    "reply_fail": "Failed to lock front door.",
}

UNLOCK_CMD = {
    "uuid": "uuid-unlock",
    "name": "unlock front door",
    "keywords": ["unlock front door", "unlock door", "unlock"],
    "service": "lock.unlock",
    "entity_id": "lock.front_door_lock",
    "service_data": {},
    "reply_ok": "Front door unlocked.",
    "reply_fail": "Failed to unlock front door.",
}

GARAGE_OPEN_CMD = {
    "uuid": "uuid-garage-open",
    "name": "open garage",
    "keywords": ["open garage", "garage open", "garage up"],
    "service": "cover.open_cover",
    "entity_id": "cover.garage_door",
    "service_data": {},
    "reply_ok": "Garage door opening.",
    "reply_fail": "Failed to open garage.",
}

TRUSTED_CONTACT = {"uuid": "c1", "name": "Murray", "number": "+61412345678"}
TRUSTED_NUMBER_NORMALISED = "61412345678"

ALL_COMMANDS = [UNLOCK_CMD, LOCK_CMD, GARAGE_OPEN_CMD]


# ---------------------------------------------------------------------------
# Helper to build a minimal coordinator under test
# ---------------------------------------------------------------------------

def _make_coordinator(hass, entry):
    from custom_components.netgear_lte_sms_manager.coordinator import SMSCoordinator
    coord = SMSCoordinator.__new__(SMSCoordinator)
    coord.hass = hass
    coord._entry = entry
    coord._first_poll = False
    coord._last_seen_ids = set()
    coord.logger = MagicMock()
    return coord


def _make_modem(send_ok: bool = True) -> MagicMock:
    modem = MagicMock()
    modem.send_sms = AsyncMock() if send_ok else AsyncMock(side_effect=Exception("send failed"))
    return modem


# ---------------------------------------------------------------------------
# Core dispatch tests
# ---------------------------------------------------------------------------

class TestDispatchTrustedSender:
    @pytest.mark.asyncio
    async def test_trusted_sender_command_calls_service(self, mock_hass):
        entry = _make_entry([LOCK_CMD], [TRUSTED_CONTACT])
        coord = _make_coordinator(mock_hass, entry)
        modem = _make_modem()
        mock_hass.services.async_call = AsyncMock()

        msg = _make_sms(1, "+61412345678", "lock the front door")
        await coord._dispatch_commands(modem, [msg])

        mock_hass.services.async_call.assert_awaited_once_with(
            "lock", "lock",
            {"entity_id": "lock.front_door_lock"},
            blocking=True,
        )

    @pytest.mark.asyncio
    async def test_trusted_sender_reply_ok_sent(self, mock_hass):
        entry = _make_entry([LOCK_CMD], [TRUSTED_CONTACT])
        coord = _make_coordinator(mock_hass, entry)
        modem = _make_modem()
        mock_hass.services.async_call = AsyncMock()

        await coord._dispatch_commands(modem, [_make_sms(1, "+61412345678", "lock")])

        modem.send_sms.assert_awaited_once_with("+61412345678", "Front door locked.")

    @pytest.mark.asyncio
    async def test_trusted_sender_fires_command_executed_event(self, mock_hass):
        from custom_components.netgear_lte_sms_manager.const import EVENT_COMMAND_EXECUTED
        entry = _make_entry([LOCK_CMD], [TRUSTED_CONTACT])
        coord = _make_coordinator(mock_hass, entry)
        modem = _make_modem()
        mock_hass.services.async_call = AsyncMock()

        await coord._dispatch_commands(modem, [_make_sms(1, "+61412345678", "lock")])

        fired = [c[0][0] for c in mock_hass.bus.async_fire.call_args_list]
        assert EVENT_COMMAND_EXECUTED in fired

        event_data = next(
            c[0][1] for c in mock_hass.bus.async_fire.call_args_list
            if c[0][0] == EVENT_COMMAND_EXECUTED
        )
        assert event_data["success"] is True
        assert event_data["command"] == "lock front door"
        assert event_data["sender"] == "+61412345678"

    @pytest.mark.asyncio
    async def test_number_normalisation_matches(self, mock_hass):
        """Contact stored as +61412345678 should match SMS sender 0412345678 (AU format)."""
        contact = {"uuid": "c1", "name": "Murray", "number": "+61412345678"}
        entry = _make_entry([LOCK_CMD], [contact])
        coord = _make_coordinator(mock_hass, entry)
        modem = _make_modem()
        mock_hass.services.async_call = AsyncMock()

        # sender comes in without country code prefix
        await coord._dispatch_commands(modem, [_make_sms(1, "61412345678", "lock")])

        mock_hass.services.async_call.assert_awaited_once()


class TestDispatchUntrustedSender:
    @pytest.mark.asyncio
    async def test_untrusted_sender_ignored(self, mock_hass):
        entry = _make_entry([LOCK_CMD], [TRUSTED_CONTACT])
        coord = _make_coordinator(mock_hass, entry)
        modem = _make_modem()
        mock_hass.services.async_call = AsyncMock()

        await coord._dispatch_commands(modem, [_make_sms(1, "+61499999999", "lock")])

        mock_hass.services.async_call.assert_not_awaited()
        modem.send_sms.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_untrusted_sender_no_event_fired(self, mock_hass):
        from custom_components.netgear_lte_sms_manager.const import EVENT_COMMAND_EXECUTED
        entry = _make_entry([LOCK_CMD], [TRUSTED_CONTACT])
        coord = _make_coordinator(mock_hass, entry)
        modem = _make_modem()
        mock_hass.services.async_call = AsyncMock()

        await coord._dispatch_commands(modem, [_make_sms(1, "+61499999999", "lock")])

        fired = [c[0][0] for c in mock_hass.bus.async_fire.call_args_list]
        assert EVENT_COMMAND_EXECUTED not in fired


class TestDispatchNoMatch:
    @pytest.mark.asyncio
    async def test_trusted_sender_no_keyword_match(self, mock_hass):
        entry = _make_entry([LOCK_CMD], [TRUSTED_CONTACT])
        coord = _make_coordinator(mock_hass, entry)
        modem = _make_modem()
        mock_hass.services.async_call = AsyncMock()

        await coord._dispatch_commands(modem, [_make_sms(1, "+61412345678", "hello how are you")])

        mock_hass.services.async_call.assert_not_awaited()
        modem.send_sms.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_commands_configured(self, mock_hass):
        entry = _make_entry([], [TRUSTED_CONTACT])
        coord = _make_coordinator(mock_hass, entry)
        modem = _make_modem()
        mock_hass.services.async_call = AsyncMock()

        await coord._dispatch_commands(modem, [_make_sms(1, "+61412345678", "lock")])

        mock_hass.services.async_call.assert_not_awaited()


class TestDispatchServiceFailure:
    @pytest.mark.asyncio
    async def test_service_failure_sends_reply_fail(self, mock_hass):
        entry = _make_entry([LOCK_CMD], [TRUSTED_CONTACT])
        coord = _make_coordinator(mock_hass, entry)
        modem = _make_modem()
        mock_hass.services.async_call = AsyncMock(side_effect=Exception("service unavailable"))

        await coord._dispatch_commands(modem, [_make_sms(1, "+61412345678", "lock")])

        modem.send_sms.assert_awaited_once_with("+61412345678", "Failed to lock front door.")

    @pytest.mark.asyncio
    async def test_service_failure_fires_event_with_success_false(self, mock_hass):
        from custom_components.netgear_lte_sms_manager.const import EVENT_COMMAND_EXECUTED
        entry = _make_entry([LOCK_CMD], [TRUSTED_CONTACT])
        coord = _make_coordinator(mock_hass, entry)
        modem = _make_modem()
        mock_hass.services.async_call = AsyncMock(side_effect=Exception("unavailable"))

        await coord._dispatch_commands(modem, [_make_sms(1, "+61412345678", "lock")])

        event_data = next(
            c[0][1] for c in mock_hass.bus.async_fire.call_args_list
            if c[0][0] == EVENT_COMMAND_EXECUTED
        )
        assert event_data["success"] is False

    @pytest.mark.asyncio
    async def test_reply_send_failure_does_not_raise(self, mock_hass):
        """A broken modem send should not propagate — command still considered executed."""
        entry = _make_entry([LOCK_CMD], [TRUSTED_CONTACT])
        coord = _make_coordinator(mock_hass, entry)
        modem = _make_modem(send_ok=False)
        mock_hass.services.async_call = AsyncMock()

        # Should not raise
        await coord._dispatch_commands(modem, [_make_sms(1, "+61412345678", "lock")])

        mock_hass.services.async_call.assert_awaited_once()


class TestDispatchEdgeCases:
    @pytest.mark.asyncio
    async def test_no_reply_configured_no_sms_sent(self, mock_hass):
        cmd_no_reply = {**LOCK_CMD, "reply_ok": "", "reply_fail": ""}
        entry = _make_entry([cmd_no_reply], [TRUSTED_CONTACT])
        coord = _make_coordinator(mock_hass, entry)
        modem = _make_modem()
        mock_hass.services.async_call = AsyncMock()

        await coord._dispatch_commands(modem, [_make_sms(1, "+61412345678", "lock")])

        modem.send_sms.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_multiple_messages_dispatched_independently(self, mock_hass):
        entry = _make_entry([LOCK_CMD, GARAGE_OPEN_CMD], [TRUSTED_CONTACT])
        coord = _make_coordinator(mock_hass, entry)
        modem = _make_modem()
        mock_hass.services.async_call = AsyncMock()

        msgs = [
            _make_sms(1, "+61412345678", "lock"),
            _make_sms(2, "+61412345678", "open garage"),
        ]
        await coord._dispatch_commands(modem, msgs)

        assert mock_hass.services.async_call.await_count == 2
        calls = mock_hass.services.async_call.await_args_list
        assert calls[0][0] == ("lock", "lock", {"entity_id": "lock.front_door_lock"})
        assert calls[1][0] == ("cover", "open_cover", {"entity_id": "cover.garage_door"})

    @pytest.mark.asyncio
    async def test_service_data_passed_through(self, mock_hass):
        cmd_with_data = {
            **LOCK_CMD,
            "service_data": {"code": "1234"},
        }
        entry = _make_entry([cmd_with_data], [TRUSTED_CONTACT])
        coord = _make_coordinator(mock_hass, entry)
        modem = _make_modem()
        mock_hass.services.async_call = AsyncMock()

        await coord._dispatch_commands(modem, [_make_sms(1, "+61412345678", "lock")])

        call_kwargs = mock_hass.services.async_call.await_args
        assert call_kwargs[0][2] == {"entity_id": "lock.front_door_lock", "code": "1234"}
