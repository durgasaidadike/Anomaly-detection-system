from event_filter import should_ignore
from event_filter import build_event


test_files = [

    "hello.txt",

    "~$report.docx",

    "~WRD0001.tmp",

    "salary.xlsx",

    "desktop.ini",

    "thumbs.db"

]


for file in test_files:

    print("\n--------------------")

    print("File:", file)

    if should_ignore(file):

        print("Status: IGNORED")

    else:

        print("Status: ACCEPTED")

        event = build_event(
            "MODIFIED",
            file
        )

        print(event)
        