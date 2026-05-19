#!/usr/bin/env python3
"""
Windows Task Scheduler Setup for Ride Optimizer Cron Jobs.
Creates scheduled tasks equivalent to Unix cron jobs.

Usage:
    python scripts/setup_windows_tasks.py [--install|--uninstall|--list]
    
Requirements:
    - Windows 10 or later
    - Administrator privileges (for task creation)
"""

import sys
import subprocess
import argparse
from pathlib import Path
import platform


def check_windows():
    """Check if running on Windows."""
    if platform.system() != 'Windows':
        print("❌ This script is for Windows only.")
        print("On Unix systems, use: ./cron/install_cron.sh")
        return False
    return True


def get_python_path():
    """Get the full path to the Python interpreter."""
    return sys.executable


def get_project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent


def create_task(name, script_path, schedule, start_time):
    """
    Create a Windows scheduled task.
    
    Args:
        name: Task name
        script_path: Path to Python script
        schedule: DAILY, WEEKLY, MONTHLY, etc.
        start_time: Time in HH:MM format
    """
    python_exe = get_python_path()
    project_root = get_project_root()
    
    # Build schtasks command
    cmd = [
        'schtasks',
        '/Create',
        '/TN', f'RideOptimizer\\{name}',
        '/TR', f'"{python_exe}" "{script_path}"',
        '/SC', schedule,
        '/ST', start_time,
        '/F',  # Force create (overwrite if exists)
        '/RL', 'HIGHEST',  # Run with highest privileges
    ]
    
    # Add working directory
    cmd.extend(['/SD', str(project_root)])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ Created task: {name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create task {name}: {e.stderr}")
        return False


def delete_task(name):
    """Delete a Windows scheduled task."""
    cmd = ['schtasks', '/Delete', '/TN', f'RideOptimizer\\{name}', '/F']
    
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ Deleted task: {name}")
        return True
    except subprocess.CalledProcessError:
        print(f"⚠️  Task not found: {name}")
        return False


def list_tasks():
    """List all Ride Optimizer scheduled tasks."""
    cmd = ['schtasks', '/Query', '/TN', 'RideOptimizer\\*', '/FO', 'LIST', '/V']
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("📋 Ride Optimizer Scheduled Tasks:")
        print("=" * 60)
        print(result.stdout)
    except subprocess.CalledProcessError:
        print("ℹ️  No Ride Optimizer tasks found")


def install_tasks():
    """Install all scheduled tasks."""
    project_root = get_project_root()
    
    print("=" * 60)
    print("Installing Ride Optimizer Scheduled Tasks")
    print("=" * 60)
    print(f"Project root: {project_root}")
    print(f"Python: {get_python_path()}")
    print()
    
    tasks = [
        {
            'name': 'DailyAnalysis',
            'script': project_root / 'cron' / 'daily_analysis.py',
            'schedule': 'DAILY',
            'time': '02:00',
            'description': 'Daily route analysis and data refresh'
        },
        {
            'name': 'WeatherRefresh',
            'script': project_root / 'cron' / 'weather_refresh.py',
            'schedule': 'DAILY',
            'time': '06:00',
            'description': 'Weather data refresh (every 6 hours via multiple tasks)'
        },
        {
            'name': 'WeatherRefresh12',
            'script': project_root / 'cron' / 'weather_refresh.py',
            'schedule': 'DAILY',
            'time': '12:00',
            'description': 'Weather data refresh (noon)'
        },
        {
            'name': 'WeatherRefresh18',
            'script': project_root / 'cron' / 'weather_refresh.py',
            'schedule': 'DAILY',
            'time': '18:00',
            'description': 'Weather data refresh (evening)'
        },
        {
            'name': 'CacheCleanup',
            'script': project_root / 'cron' / 'cache_cleanup.py',
            'schedule': 'WEEKLY',
            'time': '03:00',
            'description': 'Weekly cache cleanup'
        },
        {
            'name': 'SystemHealth',
            'script': project_root / 'cron' / 'system_health.py',
            'schedule': 'DAILY',
            'time': '01:00',
            'description': 'Daily system health check'
        },
    ]
    
    print("Tasks to install:")
    for task in tasks:
        print(f"  • {task['name']}: {task['description']}")
    print()
    
    # Check if scripts exist
    missing_scripts = []
    for task in tasks:
        if not task['script'].exists():
            missing_scripts.append(task['script'])
    
    if missing_scripts:
        print("❌ Missing scripts:")
        for script in missing_scripts:
            print(f"  • {script}")
        print()
        print("Please ensure all cron scripts exist before installing tasks.")
        return False
    
    # Create tasks
    success_count = 0
    for task in tasks:
        if create_task(task['name'], task['script'], task['schedule'], task['time']):
            success_count += 1
    
    print()
    print("=" * 60)
    print(f"Installation complete: {success_count}/{len(tasks)} tasks created")
    print("=" * 60)
    print()
    print("To view tasks:")
    print("  python scripts/setup_windows_tasks.py --list")
    print()
    print("To view logs:")
    print(f"  type {project_root}\\logs\\cron.log")
    print()
    print("To uninstall:")
    print("  python scripts/setup_windows_tasks.py --uninstall")
    print()
    
    return success_count == len(tasks)


def uninstall_tasks():
    """Uninstall all scheduled tasks."""
    print("=" * 60)
    print("Uninstalling Ride Optimizer Scheduled Tasks")
    print("=" * 60)
    print()
    
    tasks = [
        'DailyAnalysis',
        'WeatherRefresh',
        'WeatherRefresh12',
        'WeatherRefresh18',
        'CacheCleanup',
        'SystemHealth',
    ]
    
    for task in tasks:
        delete_task(task)
    
    print()
    print("✅ Uninstallation complete")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Setup Windows Task Scheduler for Ride Optimizer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/setup_windows_tasks.py --install    # Install all tasks
  python scripts/setup_windows_tasks.py --list       # List installed tasks
  python scripts/setup_windows_tasks.py --uninstall  # Remove all tasks

Note: Requires administrator privileges to create tasks.
      Run PowerShell or Command Prompt as Administrator.
        """
    )
    
    parser.add_argument(
        '--install',
        action='store_true',
        help='Install scheduled tasks'
    )
    
    parser.add_argument(
        '--uninstall',
        action='store_true',
        help='Uninstall scheduled tasks'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List installed tasks'
    )
    
    args = parser.parse_args()
    
    # Check if running on Windows
    if not check_windows():
        return 1
    
    # If no arguments, show help
    if not (args.install or args.uninstall or args.list):
        parser.print_help()
        return 0
    
    # Execute requested action
    if args.list:
        list_tasks()
    elif args.install:
        if not install_tasks():
            return 1
    elif args.uninstall:
        uninstall_tasks()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

# Made with Bob