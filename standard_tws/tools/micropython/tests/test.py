import requests
import time

ip = "127.0.0.1"
port = 55555

# # /get_all
# url = f"http://{ip}:{port}/get_all"
# r = requests.get(url)
# print(r.status_code)
# print(r.json())

# # /get
#
# url = f"http:/{ip}:{port}/get"
# start = time.time()
# r = requests.post(url, json={'id': 2})
# print(r.json())
# print(r.status_code)
# print(time.time() - start)


# /set
print("set===========================")
url = f"http://{ip}:{port}/set"
start = time.time()
r = requests.post(url, json={'id': 2, 'level': 1})
# r = requests.post(url, json={'id': 2, 'level': 0})
print(r.status_code)
print(r.json())
print(time.time() - start)

# /get

print("get===========================")
url = f"http://{ip}:{port}/get"
start = time.time()
r = requests.post(url, json={'id': 2})
print(r.json())
print(r.status_code)
print(time.time() - start)


# /get_all
print("get_all===========================")
url = f"http://{ip}:{port}/get_all"
r = requests.get(url)
print(r.status_code)
print(r.json())

# /set_pwm
print("set_pwm===========================")
url = f"http://{ip}:{port}/set_pwm"
start = time.time()
r = requests.post(url, json={'id': 20, 'level': 1})
print(r.status_code)
print(r.content)
print(time.time() - start)
