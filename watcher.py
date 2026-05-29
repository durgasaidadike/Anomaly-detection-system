import os
import time
import requests
from collections import deque
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

WATCHED_FOLDER = r"C:\projects\watched-folder"
API_URL = "http://127.0.0.1:5000/analyze-event"
TIME_WINDOW_SECONDS = 10

recent_events = deque()


class WatchHandler(FileSystemEventHandler):
    def cleanup_old_events(self):
        now = time.time()
        while recent_events and now - recent_events[0]["timestamp"] > TIME_WINDOW_SECONDS:
            recent_events.popleft()

    def build_payload(self):
        self.cleanup_old_events()

        unique_files = set()
        total_change_size = 0
        created_count = 0
        modified_count = 0
        deleted_count = 0
        moved_count = 0

        for item in recent_events:
            unique_files.add(item["file_path"])
            total_change_size += item["change_size"]

            if item["event_type"] == "CREATED":
                created_count += 1
            elif item["event_type"] == "MODIFIED":
                modified_count += 1
            elif item["event_type"] == "DELETED":
                deleted_count += 1
            elif item["event_type"] == "MOVED":
                moved_count += 1

        current_hour = time.localtime().tm_hour
        unusual_time_access = 1 if current_hour < 6 or current_hour > 22 else 0

        payload = {
            "file_count": len(unique_files),
            "operation_frequency": len(recent_events),
            "unusual_time_access": unusual_time_access,
            "change_size": total_change_size
        }

        extra_info = {
            "created_count": created_count,
            "modified_count": modified_count,
            "deleted_count": deleted_count,
            "moved_count": moved_count
        }

        return payload, extra_info

    def record_event(self, event_type, file_path):
        try:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                change_size = os.path.getsize(file_path)
            else:
                change_size = 0

            event_info = {
                "timestamp": time.time(),
                "event_type": event_type,
                "file_path": file_path,
                "change_size": change_size
            }

            recent_events.append(event_info)

            payload, extra_info = self.build_payload()

            response = requests.post(API_URL, json=payload, timeout=5)

            print(f"\n[{event_type}] {file_path}")
            print("Behavior Counters:", extra_info)
            print("Sent Data:", payload)
            print("Status Code:", response.status_code)

            try:
                print("Response JSON:", response.json())
            except Exception:
                print("Raw Response:", response.text)

        except requests.exceptions.ConnectionError:
            print(f"\n[{event_type}] {file_path}")
            print("Error: Flask API is not running.")

        except Exception as e:
            print(f"\n[{event_type}] {file_path}")
            print("Error:", str(e))

    def on_created(self, event):
        if not event.is_directory:
            self.record_event("CREATED", event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self.record_event("MODIFIED", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self.record_event("DELETED", event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self.record_event("MOVED", event.dest_path)


if __name__ == "__main__":
    if not os.path.exists(WATCHED_FOLDER):
        print(f"Folder does not exist: {WATCHED_FOLDER}")
        exit()

    event_handler = WatchHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCHED_FOLDER, recursive=True)

    print(f"Watching folder: {WATCHED_FOLDER}")
    print(f"Tracking behavior for last {TIME_WINDOW_SECONDS} seconds...")
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping watcher...")
        observer.stop()

    observer.join()