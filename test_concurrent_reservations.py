"""
Test Script for Concurrent Report Number Reservations
Validates the thread-safe reservation system with multiple simultaneous users.
"""

import threading
import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database.db_manager import DatabaseManager
from services.logging_service import LoggingService
from services.report_number_service import ReportNumberService
from config import Config


def test_single_reservation():
    """Test 1: Single user reservation."""
    print("\n" + "="*70)
    print("TEST 1: Single User Reservation")
    print("="*70)

    Config.load()
    db = DatabaseManager(Config.DATABASE_PATH)
    logger = LoggingService(db)
    service = ReportNumberService(db, logger)

    success, reservation, message = service.reserve_next_numbers("test_user1")

    if success:
        print(f"✅ SUCCESS: {message}")
        print(f"   Report Number: {reservation['report_number']}")
        print(f"   Serial Number: {reservation['serial_number']}")
        print(f"   Expires At: {reservation['expires_at']}")
        print(f"   Has Gap: {reservation['has_gap']}")

        # Cancel the reservation
        service.cancel_reservation(reservation['report_number'], "test_user1")
        print(f"   Reservation cancelled")
    else:
        print(f"❌ FAILED: {message}")

    return success


def test_concurrent_reservations():
    """Test 2: Multiple concurrent users."""
    print("\n" + "="*70)
    print("TEST 2: Concurrent Users (5 simultaneous reservations)")
    print("="*70)

    Config.load()
    db = DatabaseManager(Config.DATABASE_PATH)
    logger = LoggingService(db)
    service = ReportNumberService(db, logger)

    results = []
    lock = threading.Lock()

    def reserve_number(username):
        success, reservation, message = service.reserve_next_numbers(username)
        with lock:
            if success:
                results.append({
                    'username': username,
                    'report_number': reservation['report_number'],
                    'serial_number': reservation['serial_number'],
                    'success': True
                })
                print(f"✅ {username}: {reservation['report_number']} (SN: {reservation['serial_number']})")
            else:
                results.append({
                    'username': username,
                    'error': message,
                    'success': False
                })
                print(f"❌ {username}: {message}")

    # Create and start threads
    threads = []
    for i in range(5):
        t = threading.Thread(target=reserve_number, args=(f"user{i+1}",))
        threads.append(t)

    # Start all threads simultaneously
    print("\nStarting 5 concurrent reservation requests...")
    for t in threads:
        t.start()

    # Wait for all to complete
    for t in threads:
        t.join()

    # Verify all got unique numbers
    print("\n" + "-"*70)
    print("VERIFICATION:")
    report_numbers = [r['report_number'] for r in results if r['success']]
    serial_numbers = [r['serial_number'] for r in results if r['success']]

    if len(report_numbers) == len(set(report_numbers)):
        print(f"✅ All {len(report_numbers)} report numbers are unique")
    else:
        print(f"❌ COLLISION DETECTED! Duplicate report numbers found")

    if len(serial_numbers) == len(set(serial_numbers)):
        print(f"✅ All {len(serial_numbers)} serial numbers are unique")
    else:
        print(f"❌ COLLISION DETECTED! Duplicate serial numbers found")

    # Clean up reservations
    print("\nCleaning up reservations...")
    for result in results:
        if result['success']:
            service.cancel_reservation(result['report_number'], result['username'])

    return len(report_numbers) == len(set(report_numbers)) and len(serial_numbers) == len(set(serial_numbers))


def test_reservation_expiry():
    """Test 3: Reservation expiry after 5 minutes."""
    print("\n" + "="*70)
    print("TEST 3: Reservation Expiry (simulated)")
    print("="*70)

    Config.load()
    db = DatabaseManager(Config.DATABASE_PATH)
    logger = LoggingService(db)
    service = ReportNumberService(db, logger)

    # Reserve a number
    success, reservation, message = service.reserve_next_numbers("expiry_test_user")

    if success:
        print(f"✅ Reserved: {reservation['report_number']}")
        print(f"   Expires at: {reservation['expires_at']}")

        # Check active reservations
        stats = service.get_reservation_stats()
        print(f"   Active reservations: {stats['active_reservations']}")

        # Simulate manual expiry by cleaning up
        print("\n   Manually triggering cleanup...")
        service.cleanup_expired_reservations_public()

        # Note: Won't actually expire immediately in test
        # In real scenario, wait 5+ minutes or manually delete from database

        print(f"✅ Test completed (actual expiry happens after 5 minutes)")

        # Clean up
        service.cancel_reservation(reservation['report_number'], "expiry_test_user")
    else:
        print(f"❌ FAILED: {message}")

    return success


def test_gap_detection():
    """Test 4: Gap detection and reuse."""
    print("\n" + "="*70)
    print("TEST 4: Gap Detection & Reuse")
    print("="*70)

    Config.load()
    db = DatabaseManager(Config.DATABASE_PATH)
    logger = LoggingService(db)
    service = ReportNumberService(db, logger)

    # Check for existing gaps
    notification = service.get_gap_notification("gap_test_user")

    if notification:
        print(f"📋 {notification}")
        print("\n   This indicates there are deleted reports that can be reused.")
    else:
        print("ℹ️  No gaps detected in current month.")
        print("   (This is normal if no reports have been deleted)")

    # Get stats
    stats = service.get_reservation_stats()
    print(f"\nGaps in current month: {stats['current_month_gaps']}")

    return True  # This test is informational


def test_statistics():
    """Test 5: Get reservation statistics."""
    print("\n" + "="*70)
    print("TEST 5: Reservation Statistics")
    print("="*70)

    Config.load()
    db = DatabaseManager(Config.DATABASE_PATH)
    logger = LoggingService(db)
    service = ReportNumberService(db, logger)

    stats = service.get_reservation_stats()

    print(f"Active Reservations: {stats['active_reservations']}")
    print(f"Expired Reservations (need cleanup): {stats['expired_reservations']}")
    print(f"Used Reservations (historical): {stats['used_reservations']}")
    print(f"Gaps in Current Month: {stats['current_month_gaps']}")

    # Get active reservations
    active = service.get_active_reservations()
    if active:
        print(f"\nActive Reservations Details:")
        for res in active:
            print(f"  - {res['report_number']} reserved by {res['reserved_by']} until {res['expires_at']}")
    else:
        print(f"\nNo active reservations at the moment.")

    return True


def test_stress_test():
    """Test 6: Stress test with 50 concurrent users."""
    print("\n" + "="*70)
    print("TEST 6: Stress Test (50 concurrent users)")
    print("="*70)

    Config.load()
    db = DatabaseManager(Config.DATABASE_PATH)
    logger = LoggingService(db)
    service = ReportNumberService(db, logger)

    results = []
    lock = threading.Lock()
    start_time = time.time()

    def reserve_number(username):
        success, reservation, message = service.reserve_next_numbers(username)
        with lock:
            if success:
                results.append({
                    'username': username,
                    'report_number': reservation['report_number'],
                    'serial_number': reservation['serial_number'],
                    'success': True
                })
            else:
                results.append({
                    'username': username,
                    'error': message,
                    'success': False
                })

    # Create 50 threads
    threads = []
    for i in range(50):
        t = threading.Thread(target=reserve_number, args=(f"stress_user{i+1}",))
        threads.append(t)

    # Start all threads
    print("Starting 50 concurrent reservation requests...")
    for t in threads:
        t.start()

    # Wait for completion
    for t in threads:
        t.join()

    end_time = time.time()
    duration = end_time - start_time

    # Analyze results
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    print(f"\nCompleted in {duration:.2f} seconds")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")

    # Verify uniqueness
    report_numbers = [r['report_number'] for r in successful]
    serial_numbers = [r['serial_number'] for r in successful]

    all_unique = (len(report_numbers) == len(set(report_numbers)) and
                  len(serial_numbers) == len(set(serial_numbers)))

    if all_unique:
        print(f"✅ All numbers are unique - NO COLLISIONS!")
    else:
        print(f"❌ COLLISION DETECTED!")

    # Clean up
    print("\nCleaning up 50 reservations...")
    for result in successful:
        service.cancel_reservation(result['report_number'], result['username'])

    print(f"✅ Cleanup complete")

    return all_unique


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("CONCURRENT REPORT NUMBER RESERVATION TEST SUITE")
    print("="*70)
    print("\nThis test suite validates the thread-safe reservation system.")
    print("It ensures no number collisions occur with multiple simultaneous users.")

    try:
        # Check if config is loaded
        if not Config.load():
            print("\n❌ ERROR: Configuration not loaded. Please run the application first.")
            return False

        print(f"\nDatabase: {Config.DATABASE_PATH}")

        # Run tests
        tests = [
            ("Single Reservation", test_single_reservation),
            ("Concurrent Reservations (5 users)", test_concurrent_reservations),
            ("Reservation Expiry", test_reservation_expiry),
            ("Gap Detection", test_gap_detection),
            ("Statistics", test_statistics),
            ("Stress Test (50 users)", test_stress_test),
        ]

        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"\n❌ ERROR in {test_name}: {str(e)}")
                import traceback
                traceback.print_exc()
                results.append((test_name, False))

        # Print summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status}: {test_name}")

        passed = sum(1 for _, r in results if r)
        total = len(results)

        print(f"\nTotal: {passed}/{total} tests passed")

        if passed == total:
            print("\n🎉 ALL TESTS PASSED! Reservation system is working correctly.")
            return True
        else:
            print("\n⚠️  Some tests failed. Please review the output above.")
            return False

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
