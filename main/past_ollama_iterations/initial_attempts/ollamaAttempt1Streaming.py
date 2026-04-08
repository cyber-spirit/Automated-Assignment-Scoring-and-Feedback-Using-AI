#New attempy by using Ollama
#This generates a response that also shows the streaming of the model 'thinking'.
import requests
import json

url = "http://localhost:11434/api/generate"

payload = json.dumps({
   "model": "deepseek-r1:8b",
   "prompt": "hello"
})
headers = {
   'Content-Type': 'application/json'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)