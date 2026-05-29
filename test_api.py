import requests

url = "http://127.0.0.1:5000/analyze-event"
# Test 3: High activity
data = {
    "file_count": 90,
    "operation_frequency": 95,
    "unusual_time_access": 85,
    "change_size": 100
}

response = requests.post(url, json=data)

print("Status Code:", response.status_code)
print("Response JSON:", response.json())