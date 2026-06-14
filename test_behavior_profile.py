from behavior_profile_builder import (
    build_behavior_profile
)

profile = build_behavior_profile()

print("\n===== BEHAVIOR PROFILE =====\n")

for key, value in profile.items():

    print(f"{key}: {value}")