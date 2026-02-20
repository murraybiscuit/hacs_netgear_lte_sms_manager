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
        """Initial step: display contact list with action menu."""
        contacts = self._load_contacts()
        
        if user_input is None:
            # Build contact list display
            contact_lines = []
            if contacts:
                for contact in contacts:
                    contact_lines.append(f"  • {contact['name']} ({contact['number']})")
            else:
                contact_lines.append("  (no contacts yet)")
            
            contact_list_display = "\n".join(contact_lines)
            
            # Show menu with actions
            menu_options = ["add_contact"]
            if contacts:
                menu_options.extend(["edit_contact", "delete_contact"])
            
            return self.async_show_menu(
                step_id="init",
                menu_options=menu_options,
                description_placeholders={
                    "contact_list": contact_list_display,
                },
            )
        
        # This shouldn't be reached with async_show_menu
        return await self.async_step_init()

    async def async_step_add_contact(self, user_input: dict[str, Any] | None = None):
        """Form to add a new contact."""
        if user_input is None:
            return self.async_show_form(
                step_id="add_contact",
                data_schema=vol.Schema({
                    vol.Required("name"): str,
                    vol.Required("number"): str,
                }),
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

        # Save and return to init
        return self.async_create_entry(
            title="",
            data={"contacts": self._save_contacts(contacts)},
        )

    async def async_step_edit_contact(self, user_input: dict[str, Any] | None = None):
        """Select and edit a contact."""
        contacts = self._load_contacts()
        
        if user_input is None:
            # Show dropdown to select contact to edit
            contact_options = {c["uuid"]: f"{c['name']} ({c['number']})" for c in contacts}
            if not contact_options:
                return await self.async_step_init()
            
            return self.async_show_form(
                step_id="edit_contact",
                data_schema=vol.Schema({
                    vol.Required("contact_uuid"): vol.In(contact_options),
                }),
            )
        
        # Get selected contact
        contact_uuid = user_input.get("contact_uuid")
        contact = next((c for c in contacts if c["uuid"] == contact_uuid), None)
        
        if not contact:
            return await self.async_step_init()
        
        # Store UUID for next step
        self._editing_contact_uuid = contact_uuid
        return await self.async_step_edit_contact_form()

    async def async_step_edit_contact_form(self, user_input: dict[str, Any] | None = None):
        """Form to edit the selected contact."""
        contacts = self._load_contacts()
        contact = next(
            (c for c in contacts if c["uuid"] == getattr(self, "_editing_contact_uuid", None)),
            None,
        )
        
        if not contact:
            return await self.async_step_init()
        
        if user_input is None:
            return self.async_show_form(
                step_id="edit_contact_form",
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

    async def async_step_delete_contact(self, user_input: dict[str, Any] | None = None):
        """Select and delete a contact."""
        contacts = self._load_contacts()
        
        if user_input is None:
            # Show dropdown to select contact to delete
            contact_options = {c["uuid"]: f"{c['name']} ({c['number']})" for c in contacts}
            if not contact_options:
                return await self.async_step_init()
            
            return self.async_show_form(
                step_id="delete_contact",
                data_schema=vol.Schema({
                    vol.Required("contact_uuid"): vol.In(contact_options),
                }),
            )
        
        # Delete selected contact
        contact_uuid = user_input.get("contact_uuid")
        contacts = [c for c in contacts if c["uuid"] != contact_uuid]
        
        return self.async_create_entry(
            title="",
            data={"contacts": self._save_contacts(contacts)},
        )
