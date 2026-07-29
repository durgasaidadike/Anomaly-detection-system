from pathlib import Path
from watcher import WatchdogManager


def callback(event):
    print("\n========== EVENT RECEIVED ==========")
    print(event.to_dict())
    print("====================================\n")


if __name__ == "__main__":

    # Create the test directory if it doesn't exist
    test_directory = Path("test_watchdog")
    test_directory.mkdir(exist_ok=True)

    manager = WatchdogManager(callback)

    manager.add_directory(str(test_directory.resolve()))

    manager.start_monitoring()

    print("====================================")
    print("Watchdog Started")
    print(f"Monitoring: {test_directory.resolve()}")
    print("Create, modify, rename or delete files in this folder.")
    print("Press Ctrl + C to stop.")
    print("====================================")

    try:
        manager.wait()
    except KeyboardInterrupt:
        print("\nStopping Watchdog...")
        manager.shutdown()
        print("Shutdown complete.")