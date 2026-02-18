"""Constants for the Netgear LTE SMS Manager integration."""

import logging
from typing import Final

DOMAIN: Final = "netgear_lte_sms_manager"
DOMAIN_NETGEAR_CORE: Final = "netgear_lte"

LOGGER = logging.getLogger(__package__)

# Service names
SERVICE_LIST_INBOX: Final = "list_inbox"
SERVICE_DELETE_SMS: Final = "delete_sms"
SERVICE_DELETE_OPERATOR_SMS: Final = "delete_operator_sms"
SERVICE_GET_INBOX_JSON: Final = "get_inbox_json"

# Event names
EVENT_SMS_INBOX_LISTED: Final = "netgear_lte_sms_manager_inbox_listed"
EVENT_DELETE_OPERATOR_SMS_COMPLETE: Final = "netgear_lte_sms_manager_delete_operator_sms_complete"

# Attributes
ATTR_HOST: Final = "host"
ATTR_SMS_ID: Final = "sms_id"
ATTR_MESSAGES: Final = "messages"
ATTR_OPERATORS: Final = "operators"
ATTR_COUNT_DELETED: Final = "count_deleted"
ATTR_TIMESTAMP: Final = "timestamp"

# Default operator patterns to filter (common network operators)
DEFAULT_OPERATOR_PATTERNS: Final = [
    "Orange",
    "Vodafone",
    "T-Mobile",
    "AT&T",
    "Verizon",
    "Sprint",
    "Rogers",
    "Bell",
    "Telus",
    "Telstra",
    "Optus",
    "ntn",
    "o2",
]
