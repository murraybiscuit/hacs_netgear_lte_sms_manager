"""Constants for the Netgear LTE SMS Manager integration."""

import logging
from typing import Final

DOMAIN: Final = "netgear_lte_sms_manager"
DOMAIN_NETGEAR_CORE: Final = "netgear_lte"

LOGGER = logging.getLogger(__package__)

# Service names
SERVICE_LIST_INBOX: Final = "list_inbox"
SERVICE_DELETE_SMS: Final = "delete_sms"
SERVICE_CLEANUP_INBOX: Final = "cleanup_inbox"
SERVICE_GET_INBOX_JSON: Final = "get_inbox_json"

# Event names
EVENT_SMS_INBOX_LISTED: Final = "netgear_lte_sms_manager_inbox_listed"
EVENT_CLEANUP_COMPLETE: Final = "netgear_lte_sms_manager_cleanup_complete"

# Attributes
ATTR_HOST: Final = "host"
ATTR_SMS_ID: Final = "sms_id"
ATTR_MESSAGES: Final = "messages"
ATTR_WHITELIST: Final = "whitelist"
ATTR_RETAIN_COUNT: Final = "retain_count"
ATTR_RETAIN_DAYS: Final = "retain_days"
ATTR_DRY_RUN: Final = "dry_run"
ATTR_COUNT_DELETED: Final = "count_deleted"
ATTR_TIMESTAMP: Final = "timestamp"

# Defaults for cleanup behaviour
DEFAULT_RETAIN_COUNT: Final = 24
DEFAULT_RETAIN_DAYS: Final = 0  # 0 means ignore age
DEFAULT_DRY_RUN: Final = True
