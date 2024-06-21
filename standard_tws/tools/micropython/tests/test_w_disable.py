import requests


pin_w_disable = "20"

# 请求ESP32线程
requests_data = {"id": pin_w_disable, "level": 1}
r = requests.post('http://127.0.0.1:55555/set_pwm', json=requests_data)

print(r.status_code)
