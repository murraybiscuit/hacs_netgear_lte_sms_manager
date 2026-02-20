# Netgear LTE SMS Manager

[![HACS Badge](https://img.shields.io/badge/HACS-Custom-41BDF5?logo=home%20assistant&logoColor=white)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Home Assistant custom component that extends the core `netgear_lte` integration with comprehensive SMS inbox management capabilities.

## Features

- **List SMS Inbox** - View all messages in the modem inbox
- **Delete SMS** - Delete specific messages by ID or in bulk
- **Auto-cleanup Operator SMS** - Automatically remove network operator notifications and balance updates
 - **Policy-based Inbox Cleanup** - Remove old or unwanted messages using retain count, age, and whitelist
- **Verbose Error Handling** - Clear feedback for API compatibility issues and modem communication problems
- **Event-based Integration** - Fires events for automations and template sensors
- **Multi-modem Support** - Manage multiple Netgear LTE modems

## Motivation

The core `netgear_lte` component provides SMS event triggers, but the modem SIM card can fill up with operator messages (balance notifications, network updates, etc.), preventing new SMS events from being received. This component fills that gap with tools to manage and clean up the inbox.

## Installation

### Via HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the "+" button and search for "Netgear LTE SMS Manager"
4. Click Install
5. Restart Home Assistant

### Manual Installation

1. Clone this repository
2. Copy the `custom_components/netgear_lte_sms_manager` folder into your `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

The component auto-detects your `netgear_lte` modem configuration from the core integration. After installation, go to **Settings → Integrations → Netgear LTE SMS Manager** to configure:

### SMS Contacts

Add trusted phone contacts that will be whitelisted during cleanup. Contacts are stored securely in Home Assistant (never in your git repo):

1. Go to integration Options
2. Select "Manage Contacts"
3. Add each contact with name and phone number
4. Contacts are auto-assigned UUIDs for future personalization

Use cases for contacts:
- Whitelist family members to protect their messages from cleanup
- Reference contact names in automation conditions (e.g., "trigger if SMS from Dad")
- Enable welcome SMS feature when new contact is added (future enhancement: "reply with HELP for menu")

### Direct Phone Numbers (Power Users)

For ad-hoc whitelisting without creating a contact, go to the "Whitelist Numbers" option and add phone numbers (one per line).

### Default Cleanup Policy

Future: Configure default `retain_count`, `retain_days`, and whether `dry_run` is on by default.

## User Interface (Lovelace Card)

A custom Lovelace card is included for visual SMS inbox management:

### Installation

1. In Home Assistant, register the custom card. Add this to `configuration.yaml`:
```yaml
lovelace:
  resources:
    - url: /local/community/netgear_lte_sms_manager/www/netgear-sms-card.js
      type: module
```

2. Add the card to a dashboard:
```yaml
type: custom:netgear-sms-card
host: 192.168.5.1  # (Optional) IP of modem
```

### Features

- **Inbox Display**: View all messages with sender, content, and timestamp
- **Quick Delete**: Delete individual messages
- **Cleanup Controls**: Set retain_count, retain_days, and toggle dry_run mode
- **Preview & Execute**: Test cleanup policy before running
- **Real-time Status**: Shows loading/success/error messages

See [Card Installation Guide](custom_components/netgear_lte_sms_manager/www/CARD_INSTALLATION.md) for detailed instructions.

## Usage

### Service: `list_inbox`

Lists all SMS messages in the modem inbox and fires an event.

```yaml
service: netgear_lte_sms_manager.list_inbox
data:
  host: "192.168.5.1"  # Optional, auto-detects if only one modem
```

**Event fired:** `netgear_lte_sms_manager_inbox_listed`

Data structure:
```json
{
  "host": "192.168.5.1",
  "messages": [
    {
      "id": 1,
      "sender": "Dad",
      "message": "Hi son, how are you?",
      "timestamp": "2025-02-17T10:00:00Z"
    }
  ]
}
```

### Service: `delete_sms`

Delete specific SMS messages by their IDs.

```yaml
service: netgear_lte_sms_manager.delete_sms
data:
  host: "192.168.5.1"
  sms_id: [1, 2, 3]  # ID or list of IDs
```

### Service: `cleanup_inbox`

Clean up the modem SMS inbox using policy options. Useful to reclaim space
from recurring operator messages while preserving messages you care about.

```yaml
service: netgear_lte_sms_manager.cleanup_inbox
data:
  host: "192.168.5.1"
  retain_count: 24    # Keep newest 24 messages
  retain_days: 0      # Ignore age-based retention
  whitelist: []       # Senders to never delete
  dry_run: true       # If true, reports what would be deleted only
```

**Event fired:** `netgear_lte_sms_manager_cleanup_complete`

**Whitelist in cleanup:**
The `cleanup_inbox` service respects saved contacts and direct phone numbers. In the `whitelist` parameter, you can specify:
- Contact names (e.g., "Dad", "Mom") - exact match on SMS sender
- Phone numbers (e.g., "+1234567890")
- The service will preserve any messages from whitelisted senders

Example:
```yaml
service: netgear_lte_sms_manager.cleanup_inbox
data:
  host: "192.168.5.1"
  retain_count: 48
  whitelist: ["Dad", "+1234567890"]  # Keep messages from these senders
  dry_run: false
```

### Service: `get_inbox_json`

Get inbox as JSON (for template sensors and integrations).

```yaml
service: netgear_lte_sms_manager.get_inbox_json
data:
  host: "192.168.5.1"
```

## Automation Examples

### Scheduled inbox cleanup

```yaml
automation:
  - alias: "Cleanup SMS inbox daily"
    trigger:
      platform: time
      at: "02:00:00"
    action:
      service: netgear_lte_sms_manager.cleanup_inbox
      data:
        host: "192.168.5.1"
        retain_count: 24
        dry_run: false
```

### Using Contacts in Automations

Currently, you provide contact names/numbers as free text in the `whitelist` parameter. In future releases, we plan to:

1. **Expose contact IDs as helper entities** - each contact gets its own entity so automations can reference them declaratively
2. **Add SMS validation** - automations can require an SMS to be from a selected contact (validation enforced at runtime)
3. **Welcome message automation** - trigger a welcome SMS when a new contact is added

For now, use contact names/numbers directly in automation whitelist parameters.

### List inbox on demand

```yaml
automation:
  - alias: "List SMS inbox"
    trigger:
      platform: template
      value_template: "{{ is_state('input_boolean.refresh_sms_inbox', 'on') }}"
    action:
      - service: netgear_lte_sms_manager.list_inbox
      - service: input_boolean.turn_off
        target:
          entity_id: input_boolean.refresh_sms_inbox
```

## Troubleshooting

### ERROR: No netgear_lte entries configured

Ensure the core `netgear_lte` integration is set up first. This component requires at least one Netgear LTE modem to be configured.

### ERROR: API compatibility issue

This error indicates a breaking change in the `eternalegypt` library. Check:
- Home Assistant version is 2025.1.0 or newer
- `netgear_lte` component is up to date
- Report the issue with the exact error message

## Architecture

This component is designed as a stateless helper that wraps the core `netgear_lte` modem connection:

```
Home Assistant
    ├─ netgear_lte (core)
    │   ├─ Modem connection
    │   ├─ SMS event listener
    │   └─ Notify service
    │
    └─ netgear_lte_sms_manager (this component)
        ├─ Models (SMS, ModemConnection wrapper)
        ├─ Helpers (config entry access)
        └─ Services (list, delete, filter)
```

**Dependency Safety:**
- All external API calls wrapped with verbose error handling
- Breaking changes detected and reported clearly
- No forking of core component code

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/yourusername/hass_netgear_lte_sms_manager
cd hass_netgear_lte_sms_manager

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=custom_components/netgear_lte_sms_manager

# Run specific test
pytest tests/test_models.py::TestModemConnection::test_get_sms_list_success
```

### Code Quality

```bash
# Format code
black custom_components tests

# Lint
ruff check custom_components tests

# Type check
mypy custom_components
```

## Roadmap

- [x] Lovelace card UI for inbox management
- [x] Persistent contact list with config flow UI
- [x] Policy-based inbox cleanup (retain count, age, whitelist)
- [ ] SMS automation trigger (keyword matching)
- [ ] Helper entities for contacts (for automation automation reference)
- [ ] SMS-triggered automation validation (require contact selection)
- [ ] Welcome SMS on new contact added
- [ ] SMS statistics and analytics
- [ ] Send SMS via automation actions
- [ ] SMS filtering and rules engine

## Contributing

Pull requests welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Run tests and linting
4. Submit a PR with a clear description

## License

MIT License - see LICENSE file for details

## Support

If you find this helpful, please consider:
- ⭐ Starring the repository
- 🐛 Reporting bugs and requesting features
- 📖 Improving the documentation
- 💬 Sharing feedback and suggestions

## Credits

Built on top of:
- [Home Assistant](https://www.home-assistant.io/)
- [eternalegypt](https://github.com/eternalegypt/eternalegypt) - Netgear modem API wrapper
- [netgear_lte core integration](https://www.home-assistant.io/integrations/netgear_lte)
