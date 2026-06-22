#!/usr/bin/env python3
"""Send weekly maintenance summary notification via ntfy."""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import Config
from src.ntfy_notifier import NtfyNotifier


def main():
    summary = {
        'security_vulnerabilities': int(sys.argv[1]) if len(sys.argv) > 1 else 0,
        'issues_closed': int(sys.argv[2]) if len(sys.argv) > 2 else 0,
        'cache_size_mb': int(sys.argv[3]) if len(sys.argv) > 3 else 0,
    }

    try:
        config = Config()
        notifier = NtfyNotifier(config.get('notifications.ntfy'))
    except Exception as e:
        print(f"Failed to initialize notifier: {e}")
        return 1

    if notifier.enabled:
        notifier.send_maintenance_summary(summary)
        print("Maintenance summary notification sent")
    else:
        print("Notifications disabled, skipping summary")

    return 0


if __name__ == '__main__':
    sys.exit(main())
