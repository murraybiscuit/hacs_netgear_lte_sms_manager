"""Config and options flow for Netgear LTE SMS Manager."""

from __future__ import annotations

import json
import uuid
from typing import Any

import voluptuous as vol
from homeassistant import config_entries

from .const import DOMAIN


class NetgearLTESMSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the integration (creates a single entry)."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Create the integration entry with default options."""
        if user_input is None:
            return self.async_show_form(step_id="user")

        # Create config entry with no special data; options editable via OptionsFlow
        return self.async_create_entry(title="Netgear LTE SMS Manager", data={})

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get options flow handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for the integration."""

    def _load_contacts(self) -> list[dict]:
        """Load contacts from stored options."""
        raw = self.config_entry.options.get("contacts", "")
        if not raw:
            return []
        # Try to load as JSON
        if raw.startswith("["):
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return []
        else:
            # Backward compat: parse csv "name,number" lines
            contacts = []
            for line in (l.strip() for l in raw.splitlines() if l.strip()):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2:
                    contacts.append(
                        {
                            "uuid": str(uuid.uuid4()),
                            "name": parts[0],
                            "number": parts[1],
                        }
                    )
            return contacts

    def _save_contacts(self, contacts: list[dict]) -> str:
        """Serialize contacts to JSON string."""
        return json.dumps(contacts, indent=2)

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Initial step: show menu for configuration sections."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["manage_contacts", "whitelist_numbers"],
        )

    async def async_step_manage_contacts(
        self, user_input: dict[str, Any] | None = None
    ):
        """Manage SMS contacts (add, edit, delete)."""
        if user_input is None:
            # Load contacts for display
            contacts = self._load_contacts()
            contact_list = "\n".join(
                [
                    f"{i + 1}. {c['name']} ({c['number']})"
                    for i, c in enumerate(contacts)
                ]
            )
            return self.async_show_form(
                step_id="manage_contacts",
                data_schema=vol.Schema(
                    {
                        vol.Optional("contact_list", default=contact_list): str,
                        vol.Optional("action"): vol.In(["add_contact", "back"]),
                    }
                ),
                description_placeholders={
                    "current_contacts": contact_list or "(no contacts yet)"
                },
            )

        action = user_input.get("action")
        if action == "add_contact":
            return await self.async_step_add_contact()
        else:
            return await self.async_step_init()

    async def async_step_add_contact(self, user_input: dict[str, Any] | None = None):
        """Form to add a new contact."""
        if user_input is None:
            return self.async_show_form(
                step_id="add_contact",
                data_schema=vol.Schema(
                    {
                        vol.Required("name"): str,
                        vol.Required("number"): str,
                    }
                ),
            )

        # Load existing contacts
        contacts = self._load_contacts()
        
        # Add new contact with auto-generated UUID
        new_contact = {
            "uuid": str(uuid.uuid4()),
            "name": user_input["name"],
            "number": user_input["number"],
        }
        contacts.append(new_contact)

        # Save updated contacts via options
        return self.async_create_entry(
            title="",
            data={
                "whitelist_numbers": self.config_entry.options.get(
                    "whitelist_numbers", ""
                ),
                "contacts": self._save_contacts(contacts),
            },
        )

    async def async_step_whitelist_numbers(
        self, user_input: dict[str, Any] | None = None
    ):
        """Allow direct phone number whitelist (power users)."""
        if user_input is None:
            return self.async_show_form(
                step_id="whitelist_numbers",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            "whitelist_numbers",
                            default=self.config_entry.options.get(
                                "whitelist_numbers", ""
                            ),
                        ): str,
                    }
                ),
                description_placeholders={
                    "help": "One phone number per line. Contacts are preferred; use this for numbers not in your contact list."
                },
            )

        # Load current contacts to preserve them
        contacts = self._load_contacts()
        
        # Save options
        return self.async_create_entry(
            title="",
            data={
                "whitelist_numbers": user_input.get("whitelist_numbers", ""),
                "contacts": self._save_contacts(contacts),
            },
        )
