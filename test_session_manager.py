from datetime import datetime, timedelta, timezone

from session_manager import SessionManager


class TestEvent:
    def __init__(self, event_type, timestamp):
        self.event_type = event_type
        self.timestamp = timestamp


received_sessions = []


def session_receiver(session):
    received_sessions.append(session)


now = datetime.now(timezone.utc)

manager = SessionManager(
    idle_timeout_seconds=60,
    session_sink=session_receiver
)

event1 = TestEvent(
    "CREATED",
    now
)

session = manager.process_event(event1)

print("\n========== SESSION TEST ==========")
print("Session ID:", session.metadata.session_id)
print("Status:", session.metadata.status)
print("Event Count:", session.metadata.event_count)

event2 = TestEvent(
    "MODIFIED",
    now + timedelta(seconds=10)
)

updated = manager.process_event(
    event2,
    session.metadata.session_id
)

print("\nAfter second event:")
print("Event Count:", updated.metadata.event_count)
print("Last Activity:", updated.metadata.last_activity)

print(
    "Forwarded Sessions After Update:",
    len(received_sessions)
)

expired = manager.check_expired_sessions(
    now + timedelta(seconds=100)
)

print("\nExpired Sessions:", len(expired))
print("Active Sessions:", len(manager.active_sessions))

print(
    "\nForwarded Sessions:",
    len(received_sessions)
)

if received_sessions:
    print(
        "Last Forwarded Status:",
        received_sessions[-1].metadata.status
    )

print("\n==================================")

print("\n========== MULTI SESSION TEST ==========")

manager_multi = SessionManager()

event_a = TestEvent(
    "CREATED",
    now
)

event_b = TestEvent(
    "MODIFIED",
    now
)

session_a = manager_multi.process_event(event_a)
session_b = manager_multi.process_event(event_b)

print("Session A:", session_a.metadata.session_id)
print("Session B:", session_b.metadata.session_id)
print(
    "Active Sessions:",
    len(manager_multi.active_sessions)
)

print(
    "Sessions Are Independent:",
    session_a.metadata.session_id != session_b.metadata.session_id
)

print("========================================")

print("\n========== INTERRUPTED SESSION TEST ==========")

manager_interrupted = SessionManager()

event_1 = TestEvent(
    "CREATED",
    now
)

event_2 = TestEvent(
    "MODIFIED",
    now
)

session_1 = manager_interrupted.process_event(event_1)
session_2 = manager_interrupted.process_event(event_2)

print(
    "Initial Active Sessions:",
    len(manager_interrupted.active_sessions)
)

# Complete only the first session.
completed_session = manager_interrupted.close_session(
    session_1.metadata.session_id,
    now
)

print(
    "Completed Session:",
    completed_session.metadata.session_id
    if completed_session
    else None
)

print(
    "Remaining Active Sessions:",
    len(manager_interrupted.active_sessions)
)

print(
    "Second Session Preserved:",
    session_2.metadata.session_id
    in manager_interrupted.active_sessions
)

print("=============================================")

print("\n========== EMPTY SESSION TEST ==========")

manager_empty = SessionManager()

print(
    "Initial Active Sessions:",
    len(manager_empty.active_sessions)
)

print(
    "No Phantom Sessions:",
    len(manager_empty.active_sessions) == 0
)

print(
    "Empty Event List Prevented:",
    all(
        len(session.events) > 0
        for session in manager_empty.active_sessions.values()
    )
)

print("========================================")

print("\n========== CORRUPTED SESSION TEST ==========")

manager_corrupted = SessionManager()

corrupted_event = TestEvent(
    "MODIFIED",
    now
)

corrupted_session = manager_corrupted.process_event(
    corrupted_event
)

corrupted_session_id = (
    corrupted_session.metadata.session_id
)

print(
    "Initial Active Sessions:",
    len(manager_corrupted.active_sessions)
)

closed_corrupted = manager_corrupted.close_corrupted_session(
    corrupted_session_id
)

print(
    "Corrupted Session Closed:",
    closed_corrupted is not None
)

print(
    "Closed Session Status:",
    closed_corrupted.metadata.status
    if closed_corrupted
    else None
)

print(
    "Active Sessions After Close:",
    len(manager_corrupted.active_sessions)
)

print(
    "Session Removed:",
    corrupted_session_id
    not in manager_corrupted.active_sessions
)

print("============================================")

print("\n========== UPDATE FAILURE TEST ==========")

manager_failure = SessionManager()

failure_event = TestEvent(
    "MODIFIED",
    now
)

failure_session = manager_failure.process_event(
    failure_event
)

failure_session_id = failure_session.metadata.session_id


def failing_append(*args, **kwargs):
    raise RuntimeError("Simulated session update failure")


failure_session.append_event = failing_append

result = manager_failure.update_session(
    failure_session_id,
    TestEvent("MODIFIED", now)
)

print(
    "Update Result:",
    result
)

print(
    "Active Sessions After Failure:",
    len(manager_failure.active_sessions)
)

print(
    "Session Preserved:",
    failure_session_id
    in manager_failure.active_sessions
)

print("=========================================")
