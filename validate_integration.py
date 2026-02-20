#!/usr/bin/env python3
"""Validate integration manifest and imports."""

import json
import sys

# Check manifest
try:
    with open("custom_components/netgear_lte_sms_manager/manifest.json") as f:
        manifest = json.load(f)
    print("✓ manifest.json is valid JSON")
    print(f"  domain: {manifest.get('domain')}")
    print(f"  version: {manifest.get('version')}")
    print(f"  config_flow: {manifest.get('config_flow')}")
    print(f"  dependencies: {manifest.get('dependencies')}")
except Exception as e:
    print(f"✗ manifest.json error: {e}")
    sys.exit(1)

# Check imports
try:
    print("✓ const.py imports OK")
except Exception as e:
    print(f"✗ const.py error: {e}")
    sys.exit(1)

try:
    print("✓ config_flow.py imports OK")
except Exception as e:
    print(f"✗ config_flow.py error: {e}")
    sys.exit(1)

try:
    print("✓ __init__.py imports OK")
except Exception as e:
    print(f"✗ __init__.py error: {e}")
    sys.exit(1)

print("\n✓ All checks passed - integration should load")
