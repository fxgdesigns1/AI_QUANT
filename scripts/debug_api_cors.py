import requests

try:
    response = requests.get('http://127.0.0.1:5001/api/stats', headers={'Origin': 'http://127.0.0.1:5173'})
    print("Status:", response.status_code)
    print("Headers:", response.headers)
    print("Content:", response.text[:100])
except Exception as e:
    print("Error:", e)
