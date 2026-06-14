from behavior_analyzer import analyze_behavior

sample_event = {
    "event_type": "DELETED",
    "file_extension": ".exe",
    "directory": "D:\\SecretFolder",
    "event_hour": 3,
    "file_size": 5000
}

result = analyze_behavior(
    sample_event,
    operation_frequency=50
)

print("\n===== ANALYSIS RESULT =====\n")

for key, value in result.items():
    print(f"{key}: {value}")
    # TODO:
# Replace lifetime counts with
# window-based behavioral baselines
# in V3