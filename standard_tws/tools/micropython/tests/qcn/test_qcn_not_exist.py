import requests
import time

url = f"http://localhost:55555/restore_qcn"


start = time.time()
print(start)
r = requests.post(url, json={'SN': "AAA1"})
print(r.content)
print(time.time())
print('time used: ', time.time() - start)
