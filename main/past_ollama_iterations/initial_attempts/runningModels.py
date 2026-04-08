import requests

url = "http://localhost:11434/api/ps"

payload={}
headers = {}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)
