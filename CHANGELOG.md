# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0-beta.1] - 2026-02-19

### Added

- **SMS Inbox Management**
  - `list_inbox` service: List all SMS in modem inbox
  - `delete_sms` service: Delete specific messages by ID
  - `cleanup_inbox` service: Policy-based cleanup with retain_count, retain_days, whitelist, and dry_run
  - `get_inbox_json` service: Return inbox as JSON for template sensors

- **Contact Management**
  - Config flow UI for adding/managing SMS contacts
  - Contacts stored in integration options (never in repo)
  - UUID-based contact IDs for future extensibility
  - Whitelist support for protecting contact messages during cleanup

- **Lovelace Card**
  - Custom card for visual SMS inbox management
  - Inbox display with sender, message, and timestamp
  - Quick delete buttons for individual messages
  - Cleanup controls with dry-run preview
  - Real-time event listening for service feedback

- **Configuration**
  - Integration options flow with two sections:
    - Manage Contacts: structured UI for adding/editing contacts
    - Whitelist Numbers: power-user direct phone number list
  - Multi-modem support (auto-detect single modem, explicit host parameter for multiple)
  - Full error handling with clear feedback for API issues

- **Development & Testing**
  - Unit test suite (27 tests covering models, helpers, services)
  - pytest with asyncio support for async service testing
  - Mock-based testing to avoid heavy Home Assistant installation in dev
  - Comprehensive error classes (NetgearLTECoreMissingError, EternalEgyptVersionError, ModemCommunicationError)
  - Pre-commit hooks with black, ruff, mypy for code quality

### Security

- Phone numbers stored in Home Assistant `.storage`, not in version control
- No hardcoded credentials or sensitive defaults
- Contact list persisted securely per Home Assistant installation

### Known Limitations

- Contact resolution in automations requires specifying name/number (future: helper entities for declarative reference)
- Automation validation of SMS source (future: built-in trigger condition)
- Welcome SMS on new contact (future: automation template)

### Future Roadmap

- Helper entities for contacts (allow automation automation reference by ID)
- SMS automation trigger platform (keyword matching, contact validation)
- Welcome SMS feature for new contacts
- SMS statistics and analytics

---

## [0.1.0-beta.1] Release Notes

This is the first beta release of **Netgear LTE SMS Manager** for Home Assistant.

### Getting Started

1. Install via HACS (when available) or manually clone to `custom_components/`
2. Restart Home Assistant
3. Configure contacts via Settings → Integrations → Netgear LTE SMS Manager
4. Add Lovelace card to dashboard with `type: custom:netgear-sms-card`
5. Use services in automations or call from card UI

### Stable Beta Status

This release is feature-complete for SMS inbox management. Core functionality is tested and production-ready:
- ✅ Service-based API for inbox operations
- ✅ Persistent contact configuration
- ✅ Policy-based cleanup with dry-run safety
- ✅ Multi-modem support
- ✅ Comprehensive error handling
- ✅ Unit test suite (27 tests)
- ✅ Lovelace card UI

Please report issues with [GitHub Issues](https://github.com/murraybiscuit/hass_netgear_lte_sms_manager/issues).
