import pyboard
import time

start_time = time.time()
pyb = pyboard.Pyboard('COM22', 115200)
print(f"Open Serial Used: {time.time() - start_time} seconds")


start_time = time.time()
pyb.enter_raw_repl()
print(f"Enter RAW REPL Used: {time.time() - start_time} seconds")

start_time = time.time()
ret = pyb.exec('from machine import Pin\np12 = Pin(12, Pin.OUT)\np12.value(0)\nprint(p12.value())')
print(f"Exec Command Used: {time.time() - start_time} seconds")
print(ret)

start_time = time.time()
ret = pyb.exec('from machine import Pin\np12 = Pin(12, Pin.OUT)\np12.value(1)\nprint(p12.value())')
print(f"Exec Command Used: {time.time() - start_time} seconds")
print(ret)

start_time = time.time()
ret = pyb.exec('from machine import Pin\np12 = Pin(12, Pin.OUT)\np12.value(1)\nprint(p12.value())')
print(f"Exec Command Used: {time.time() - start_time} seconds")
print(ret)

start_time = time.time()
ret = pyb.exec('print(repr(p12))')
print(f"repr(p12) Command Used: {time.time() - start_time} seconds")
print(ret)


start_time = time.time()
pyb.exit_raw_repl()
print(f"Exit RAW REPL Used: {time.time() - start_time} seconds")
