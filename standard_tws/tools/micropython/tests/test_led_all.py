import requests
import time

ip = "127.0.0.1"
port = 55555
url = f"http://{ip}:{port}/led_set"

# free
requests.post(url, json={'free': True, 'testing': False, 'breakdown': False})
time.sleep(5)
# testing
requests.post(url, json={'free': False, 'testing': True})
time.sleep(5)
# breakdown
requests.post(url, json={'free': True, 'testing': False, 'breakdown': True})
time.sleep(5)
# free
requests.post(url, json={'breakdown': False})
time.sleep(5)
# testing
requests.post(url, json={'free': False, 'testing': True})
time.sleep(5)
# breakdown
requests.post(url, json={'free': True, 'testing': False, 'breakdown': True})
time.sleep(5)
