
import requests
import json

url = "https://0.0.0.0:8080/printer/status-usb"
import urllib3

# Suppress only the InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

payload = json.dumps({
  "vendor_id": "0fe6",
  "product_id": "811e"
})
headers = {
  'Content-Type': 'application/json'
}

for i in range(100):
    response = requests.request("POST", url, headers=headers, data=payload, verify=False)

    print(response.text)

print("100 req done")