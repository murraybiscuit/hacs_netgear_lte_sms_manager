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
        return OptionsFlowHandler()


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
        """Initial step: display contact list UI."""
        if user_input is None:
            # Load contacts for display
            contacts = self._load_contacts()
            contact_list_display = "\n".join(
                [f"{c['name']} ({c['number']})" for c in contacts]
            ) if contacts else "(no contacts yet)"
            
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema({
                    vol.Optional("action"): vol.In(["add_contact", "edit_contact", "delete_contact"]),
                }),
                description_placeholders={
                    "current_contacts": contact_list_display
                },
            )
        
        action = user_input.get("action")
        if action == "add_contact":
            return await self.async_step_add_contact()
        elif action == "edit_contact":
            return await self.async_step_select_contact_to_edit()
        elif action == "delete_contact":
            return await self.async_step_select_contact_to_delete()
        
        # Return to init if no action
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
            data={"contacts": self._save_contacts(contacts)},
        )

    async def async_step_select_contact_to_edit(self, user_input: dict[str, Any] | None = None):
        """Select a contact to edit."""
        contacts = self._load_contacts()
        
        if user_input is None:
            contact_options = {c["uuid"]: f"{c['name']} ({c['number']})" for c in contacts}
            if not contact_options:
                return await self.async_step_init()
            
            return self.async_show_form(
                step_id="select_contact_to_edit",
                data_schema=vol.Schema({
                    vol.Required("contact_uuid"): vol.In(contact_options),
                }),
            )
        
        contact_uuid = user_input.get("contact_uuid")
        return await self.async_step_edit_contact(contact_uuid=contact_uuid)

    async def async_step_edit_contact(self, user_input: dict[str, Any] | None = None, contact_uuid: str | None = None):
        """Form to edit an existing contact."""
        contacts = self._load_contacts()
        contact = next((c for c in contacts if c["uuid"] == contact_uuid), None)
        
        if not contact:
            return await self.async_step_init()
        
        if user_input is None:
            return self.async_show_form(
                step_id="edit_contact",
                data_schema=vol.Schema({
                    vol.Required("name", default=contact["name"]): str,
                    vol.Required("number", default=contact["number"]): str,
                }),
            )
        
        # Update contact
        contact["name"] = user_input["name"]
        contact["number"] = user_input["number"]
        
        return self.async_create_entry(
            title="",
            data={"contacts": self._save_contacts(contacts)},
        )

    async def async_step_select_contact_to_delete(self, user_input: dict[str, Any] | None = None):
        """Select a contact to delete."""
        contacts = self._load_contacts()
        
        if user_input is None:
            contact_options = {c["uuid"]: f"{c['name']} ({c['number']})" for c in contacts}
            if not contact_options:
                return await self.async_step_init()
            
            return self.async_show_form(
                step_id="select_contact_to_delete",
                data_schema=vol.Schema({
                    vol.Required("contact_uuid"): vol.In(contact_options),
                }),
            )
        
        contact_uuid = user_input.get("contact_uuid")
        contacts = [c for c in contacts if c["uuid"] != contact_uuid]
        
        return self.async_create_entry(
            title="",
            data={"contacts": self._save_contacts(contacts)},
        )
