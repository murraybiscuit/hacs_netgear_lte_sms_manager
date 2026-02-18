"""Type stubs and data models for netgear_lte_sms_manager.

This module provides abstraction and type safety for the dependency on
the netgear_lte core component and eternalegypt library. All external
API calls are wrapped with verbose error handling to catch breaking
changes early.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from eternalegypt.eternalegypt import Modem

from .const import LOGGER


@dataclass
class SMSMessage:
    """Represents an SMS message in the modem inbox."""

    id: int
    sender: str
    message: str
    timestamp: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class DependencyError(Exception):
    """Base exception for dependency API compatibility issues."""

    pass


class EternalEgyptVersionError(DependencyError):
    """eternalegypt library API has changed or is incompatible."""

    pass


class ModemCommunicationError(DependencyError):
    """Failed to communicate with the Netgear modem."""

    pass


class NetgearLTECoreMissingError(DependencyError):
    """netgear_lte core component is not configured or loaded."""

    pass


class ModemConnection:
    """Wrapper around eternalegypt.Modem for safe access with error handling.

    This wrapper provides a stable interface and catches version mismatches
    in the eternalegypt library.
    """

    def __init__(self, modem: Modem) -> None:
        """Initialize the modem connection wrapper.

        Args:
            modem: The eternalegypt.Modem instance from netgear_lte core.

        Raises:
            ValueError: If modem is None.
        """
        if modem is None:
            raise ValueError("modem cannot be None")
        self._modem = modem

    async def get_sms_list(self) -> list[SMSMessage]:
        """Get all SMS from modem inbox with error handling.

        Returns:
            List of SMSMessage objects from the inbox.

        Raises:
            EternalEgyptVersionError: If the modem library API has changed.
            ModemCommunicationError: If communication with modem fails.
        """
        try:
            if not hasattr(self._modem, "sms_list"):
                raise EternalEgyptVersionError(
                    "Modem.sms_list method not found. eternalegypt version may be incompatible. "
                    "Expected eternalegypt>=0.0.18"
                )

            raw_list = await self._modem.sms_list()

            sms_messages = []
            for sms in raw_list:
                try:
                    # Safely extract SMS properties with defaults
                    msg = SMSMessage(
                        id=int(sms.id),
                        sender=str(sms.sender) if hasattr(sms, "sender") else "Unknown",
                        message=str(sms.message) if hasattr(sms, "message") else "",
                        timestamp=str(sms.timestamp)
                        if hasattr(sms, "timestamp") and sms.timestamp
                        else None,
                    )
                    sms_messages.append(msg)
                except (AttributeError, ValueError, TypeError) as e:
                    LOGGER.warning(
                        "Failed to parse SMS message, skipping: %s. Error: %s", sms, e
                    )
                    continue

            return sms_messages

        except EternalEgyptVersionError:
            raise
        except AttributeError as ex:
            raise EternalEgyptVersionError(
                f"Modem API mismatch detected: {ex}. "
                "This likely means eternalegypt has a breaking change. "
                "See https://github.com/yourusername/hass_netgear_lte_sms_manager/issues"
            ) from ex
        except TimeoutError as ex:
            raise ModemCommunicationError(
                f"Timeout communicating with modem at {self._modem.hostname}: {ex}"
            ) from ex
        except Exception as ex:
            raise ModemCommunicationError(
                f"Failed to fetch SMS list from {self._modem.hostname}: {type(ex).__name__}: {ex}"
            ) from ex

    async def delete_sms(self, sms_id: int) -> None:
        """Delete a single SMS by ID.

        Args:
            sms_id: The ID of the SMS to delete.

        Raises:
            EternalEgyptVersionError: If the modem library API has changed.
            ModemCommunicationError: If communication with modem fails.
        """
        try:
            if not hasattr(self._modem, "delete_sms"):
                raise EternalEgyptVersionError(
                    "Modem.delete_sms method not found. eternalegypt version may be incompatible."
                )

            await self._modem.delete_sms(sms_id)

        except EternalEgyptVersionError:
            raise
        except AttributeError as ex:
            raise EternalEgyptVersionError(
                f"Modem API mismatch in delete_sms: {ex}"
            ) from ex
        except Exception as ex:
            raise ModemCommunicationError(
                f"Failed to delete SMS {sms_id}: {type(ex).__name__}: {ex}"
            ) from ex

    async def delete_sms_batch(self, sms_ids: list[int]) -> int:
        """Delete multiple SMS by IDs.

        Args:
            sms_ids: List of SMS IDs to delete.

        Returns:
            Number of SMS successfully deleted.

        Raises:
            ModemCommunicationError: If any deletion fails.
        """
        deleted_count = 0
        errors = []

        for sms_id in sms_ids:
            try:
                await self.delete_sms(sms_id)
                deleted_count += 1
            except Exception as ex:
                errors.append((sms_id, str(ex)))
                LOGGER.warning("Failed to delete SMS %d: %s", sms_id, ex)

        if errors and deleted_count == 0:
            # All deletions failed
            raise ModemCommunicationError(
                f"Failed to delete any SMS. Errors: {errors}"
            )

        if errors:
            # Some deletions failed, log but continue
            LOGGER.warning(
                "Partial deletion: %d succeeded, %d failed. Errors: %s",
                deleted_count,
                len(errors),
                errors,
            )

        return deleted_count
