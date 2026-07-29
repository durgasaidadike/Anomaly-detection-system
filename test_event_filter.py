from datetime import datetime

from event_filter import EventFilter
from watcher import RawEvent


event_filter = EventFilter()

test_events = [
    RawEvent(
        timestamp=datetime.now(),
        event_type="MODIFIED",
        source_path="hello.txt",
        destination_path=None,
        file_name="hello.txt",
        extension=".txt",
        directory=".",
        is_directory=False,
        file_size=100,
    ),
    RawEvent(
        timestamp=datetime.now(),
        event_type="MODIFIED",
        source_path="~$report.docx",
        destination_path=None,
        file_name="~$report.docx",
        extension=".docx",
        directory=".",
        is_directory=False,
        file_size=100,
    ),
    RawEvent(
        timestamp=datetime.now(),
        event_type="MODIFIED",
        source_path="desktop.ini",
        destination_path=None,
        file_name="desktop.ini",
        extension=".ini",
        directory=".",
        is_directory=False,
        file_size=100,
    ),
]

for event in test_events:
    print("\n------------------------")
    print("Input :", event.file_name)

    result = event_filter.process(event)

    if result is None:
        print("Status : FILTERED")
    else:
        print("Status : ACCEPTED")
        print(result)