# SMS Manager - Lovelace Card Resources Configuration

To register the custom card with Home Assistant, add the following to your `configuration.yaml`:

```yaml
lovelace:
  resources:
    - url: /local/community/netgear_lte_sms_manager/www/netgear-sms-card.js
      type: module
```

Alternatively, if you're using the Browser UI to manage resources:

1. Go to **Settings → Dashboards → Lovelace → Resources**
2. Click **Create resource**
3. URL: `/local/community/netgear_lte_sms_manager/www/netgear-sms-card.js`
4. Resource type: `JavaScript Module`
5. Save

Then add the card to a Lovelace view:

```yaml
type: custom:netgear-sms-card
host: 192.168.5.1  # (Optional) IP of modem - auto-detected if only one
```

## Features

- **Inbox Display**: Shows all SMS messages with sender, content, and timestamp
- **Quick Delete**: Delete individual messages one at a time
- **Cleanup Policy**: Configure retain_count, retain_days, and preview/execute cleanup
- **Dry Run Mode**: Test cleanup policy before executing destructive operations
- **Real-time Events**: Card listens to service events and updates immediately
- **Contact Protection**: Uses configured contacts to whitelist senders during cleanup
