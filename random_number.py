import random


list = ['a', 'b', 'c', 'BC', 'BG', 'UC', 12, 15, 17, 30, 25]
print("三个随机元素：")
Q = ''
for i in range(0, 3):
    t = random.randint(0, 10)
    print(list[t])
    Q += str(list[t])
print("三个字符串拼接字符为：", Q)
