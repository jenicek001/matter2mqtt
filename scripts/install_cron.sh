#!/bin/bash
# Install Matter time sync cron job

# Add daily sync at 3 AM
(crontab -l 2>/dev/null | grep -v "sync_time.py"; echo "0 3 * * * /usr/bin/python3 /home/honzik/Matter/sync_time.py >> /tmp/matter_time_sync.log 2>&1") | crontab -

echo "✓ Cron job installed - time will sync daily at 3 AM"
echo "✓ DST changes are handled automatically"
echo ""
echo "To manually sync now: python3 /home/honzik/Matter/sync_time.py"
echo "To view logs: tail -f /tmp/matter_time_sync.log"
