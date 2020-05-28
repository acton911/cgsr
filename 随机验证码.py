import random


def make_code(n):
    res = ''
    for i in range(n):
        num = str(random.randint(1, 9))  # 生成随机1-9，并强转成字符串格式
        char = chr(random.randint(65, 99))  # 生成随机a-z字母
        get_str = random.choice([num, char]) # 从生成的数字和字母选择一个进行字符串拼接
        res += get_str
    return res


verti_code = make_code(5)


print(verti_code)