import requests
import time

# pin mapping
# D12 VBAT
# D13 RESET
# D14 PWK

ip = "127.0.0.1"
port = 55555
url = f"http://{ip}:{port}/set"

# vbat
requests.post(url, json={'id': 12, 'level': 1})
print(requests.get(f"http://{ip}:{port}/get_all").json())
time.sleep(3)
requests.post(url, json={'id': 12, 'level': 0})
print(requests.get(f"http://{ip}:{port}/get_all").json())

# # reset
# requests.post(url, json={'id': 14, 'level': 1})
# print(requests.get(f"http://{ip}:{port}/get_all").json())
# requests.post(url, json={'id': 13, 'level': 1})
# print(requests.get(f"http://{ip}:{port}/get_all").json())
# time.sleep(3)
# requests.post(url, json={'id': 13, 'level': 0})
# print(requests.get(f"http://{ip}:{port}/get_all").json())
# requests.post(url, json={'id': 14, 'level': 0})
# print(requests.get(f"http://{ip}:{port}/get_all").json())

# pwk
requests.post(url, json={'id': 14, 'level': 0})
print(requests.get(f"http://{ip}:{port}/get_all").json())
requests.post(url, json={'id': 14, 'level': 1})
print(requests.get(f"http://{ip}:{port}/get_all").json())
time.sleep(1)
requests.post(url, json={'id': 14, 'level': 0})
print(requests.get(f"http://{ip}:{port}/get_all").json())
