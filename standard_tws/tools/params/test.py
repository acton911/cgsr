import requests
import time

ip = "127.0.0.1"
port = 55556
url = f"http://{ip}:{port}/query"

# vbat
r = requests.post(url, json={'sql': "select * from 5G_Project;"})
print(r.json())
