import requests
import time

ip = "127.0.0.1"
port = 55555
url = f"http://{ip}:{port}/led_set_status"

# free
# requests.post(url, json={'free': True, 'testing': False, 'breakdown': False})
# print(requests.get(f"http://{ip}:{port}/get_all").json())  # debug
# time.sleep(1)

# test
requests.post(url, json={'free': False, 'testing': True, 'breakdown': False})
print(requests.get(f"http://{ip}:{port}/get_all").json())  # debug

# free with breakdown
# requests.post(url, json={'free': True, 'testing': False, 'breakdown': True})
# print(requests.get(f"http://{ip}:{port}/get_all").json())  # debug
