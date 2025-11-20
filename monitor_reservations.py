"""
Real-Time Reservation Monitor
Displays active report number reservations and system statistics.

Usage:
  python monitor_reservations.py              # One-time display
  python monitor_reservations.py --watch      # Continuous monitoring (updates every 5 seconds)
  python monitor_reservations.py --stats      # Show statistics only
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database.db_manager import DatabaseManager
from services.logging_service import LoggingService
from services.report_number_service import ReportNumberService
from config import Config


def clear_screen():
    """Clear the terminal screen."""
    import os
    os.system('cls' if os.name == 'nt' else 'clear')


def format_time_remaining(expires_at):
    """Calculate and format time remaining until expiry."""
    try:
        # Parse ISO format datetime
        from dateutil import parser
        expiry = parser.parse(expires_at)
        now = datetime.now(expiry.tzinfo) if expiry.tzinfo else datetime.now()

        delta = expiry - now
        total_seconds = int(delta.total_seconds())

        if total_seconds < 0:
            return "EXPIRED"

        minutes = total_seconds // 60
        seconds = total_seconds % 60

        return f"{minutes}m {seconds}s"

    except:
        return "Unknown"


def display_active_reservations(service):
    """Display all active reservations."""
    reservations = service.get_active_reservations()

    print("\n" + "="*80)
    print("  ACTIVE RESERVATIONS")
    print("="*80)

    if not reservations:
        print("\n  No active reservations at the moment.")
        print("  (All users have either saved or cancelled their reports)")
    else:
        print(f"\n  Total Active: {len(reservations)}")
        print("\n  " + "-"*76)
        print(f"  {'Report Number':<15} {'SN':<8} {'Reserved By':<15} {'Time Left':<12} {'Reserved At':<20}")
        print(f"  " + "-"*76)

        for res in reservations:
            time_left = format_time_remaining(res['expires_at'])
            reserved_at = res['reserved_at'][:16].replace('T', ' ')  # Trim to fit

            print(f"  {res['report_number']:<15} {res['serial_number']:<8} "
                  f"{res['reserved_by']:<15} {time_left:<12} {reserved_at:<20}")

        print("  " + "-"*76)


def display_statistics(service):
    """Display reservation statistics."""
    stats = service.get_reservation_stats()

    print("\n" + "="*80)
    print("  SYSTEM STATISTICS")
    print("="*80)

    print(f"\n  Active Reservations:           {stats['active_reservations']}")
    print(f"  Expired (need cleanup):        {stats['expired_reservations']}")
    print(f"  Used (historical):             {stats['used_reservations']}")
    print(f"  Gaps in Current Month:         {stats['current_month_gaps']}")

    # Additional info
    gap_notification = service.get_gap_notification("monitor")
    if gap_notification:
        print(f"\n  📋 {gap_notification}")


def display_header():
    """Display monitor header."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "="*80)
    print(f"  REPORT NUMBER RESERVATION MONITOR")
    print(f"  Last Updated: {now}")
    print("="*80)


def monitor_once():
    """Display reservations and statistics once."""
    Config.load()
    db = DatabaseManager(Config.DATABASE_PATH)
    logger = LoggingService(db)
    service = ReportNumberService(db, logger)

    display_header()
    display_active_reservations(service)
    display_statistics(service)

    print("\n" + "="*80)
    print()


def monitor_continuously(interval=5):
    """Monitor reservations continuously with auto-refresh."""
    print("\nStarting continuous monitoring...")
    print(f"Refresh interval: {interval} seconds")
    print("Press Ctrl+C to stop\n")

    try:
        Config.load()
        db = DatabaseManager(Config.DATABASE_PATH)
        logger = LoggingService(db)
        service = ReportNumberService(db, logger)

        while True:
            clear_screen()
            display_header()
            display_active_reservations(service)
            display_statistics(service)

            print(f"\n  [Auto-refresh in {interval}s... Press Ctrl+C to exit]")

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\n  Monitoring stopped by user")
        print()


def show_stats_only():
    """Show only statistics."""
    Config.load()
    db = DatabaseManager(Config.DATABASE_PATH)
    logger = LoggingService(db)
    service = ReportNumberService(db, logger)

    display_header()
    display_statistics(service)

    print("\n" + "="*80)
    print()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Monitor report number reservations in real-time",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python monitor_reservations.py              # Display once
  python monitor_reservations.py --watch      # Continuous monitoring
  python monitor_reservations.py --stats      # Statistics only
  python monitor_reservations.py -w -i 10     # Watch with 10-second interval
        """
    )

    parser.add_argument('-w', '--watch', action='store_true',
                        help='Continuous monitoring mode (auto-refresh)')
    parser.add_argument('-i', '--interval', type=int, default=5,
                        help='Refresh interval in seconds (default: 5)')
    parser.add_argument('-s', '--stats', action='store_true',
                        help='Show statistics only')

    args = parser.parse_args()

    try:
        if not Config.load():
            print("\n❌ ERROR: Configuration not loaded. Please run the application first.")
            return 1

        if args.stats:
            show_stats_only()
        elif args.watch:
            monitor_continuously(args.interval)
        else:
            monitor_once()

        return 0

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
