import cantools
import pandas as pd
import os
from pathlib import Path

"""
脚本逻辑：
1.填写TCANLINpro通过图模思录制电子油泵.csv文件 ；
2.加载dbc数据库，并填写输出文件名(.txt格式)；
3.执行脚本，等待.csv文件通过dbc转换解析后CAN报文；
"""
# ======================================================================================================================
# 必选参数
csv_path = "D:/can/test"  # 替换为你的文件夹路径
dbc_path = "D:/can/MCU_EOP CAN  Message List 1-3 20250630.dbc"   # dbc存放路径
# ======================================================================================================================
# 加载DBC数据库
db = cantools.database.load_file(dbc_path)


def file_csv():
    # 1.获取所有CSV文件夹路径
    global new_csv_file
    csv_files = [os.path.join(csv_path, f) for f in os.listdir(csv_path) if f.endswith('.csv')]

    # 2. 遍历并读取所有CSV文件
    data_frames = []
    for csv_file in csv_files:
        try:
            # 读取CSV文件(处理不同编码)
            df = pd.read_csv(csv_file, dtype=str, encoding='utf-8-sig')
            data_frames.append(df)
            new_csv_file = Path(csv_file).as_posix()
            print(f"已读取文件：{new_csv_file}")
        except Exception as e:
            print(f"读取失败{new_csv_file}:{e}")


def parse_tcanlinpro_csv(csv_path):
    # 1.获取所有CSV文件夹路径
    global new_csv_file, new_txt_file
    csv_files = [os.path.join(csv_path, f) for f in os.listdir(csv_path) if f.endswith('.csv')]

    # 2. 遍历并读取所有CSV文件,并解析
    data_frames = []
    for csv_file in csv_files:
        try:
            # 读取CSV文件(处理不同编码)
            df = pd.read_csv(csv_file, dtype=str, encoding='utf-8-sig')
            data_frames.append(df)
            new_csv_file = Path(csv_file).as_posix()
            new_txt_file = new_csv_file.replace('.csv', '.txt')
            print(f"开始解析文件：{new_csv_file}")
        except Exception as e:
            print(f"解析文件失败{new_csv_file}:{e}")

        # 读取CSV文件（自动处理编码）
        df = pd.read_csv(new_csv_file, dtype={'帧ID(Hex)': str, '数据(Hex)': str}, skiprows=1)

        # 预处理数据列
        df['can_id'] = df['帧ID(Hex)'].apply(lambda x: int(x, 16))  # 转换16进制ID
        df['data_bytes'] = df['数据(Hex)'].str.replace(' ', '').apply(bytes.fromhex)  # 处理空格分隔

        # 逐行解析
        for index, row in df.iterrows():
            try:
                msg = db.get_message_by_frame_id(row['can_id'])
                decoded = msg.decode(row['data_bytes'])

                # 构建结构化输出
                output = {
                    "timestamp": row['时间标识'],
                    "direction": row['方向'],
                    "can_id": f"0x{row['can_id']:X}",
                    "message": msg.name,
                    "signals": [
                        {
                            "name": sig.name,
                            "value": val,
                            "unit": sig.unit or "",
                            "raw_value": db.decode_message(msg.frame_id, row['data_bytes'], decode_choices=False)[
                                sig.name]
                        }
                        for sig, val in zip(msg.signals, decoded.values())
                    ]
                }
                # print(f"[{output['timestamp']:.6f}] {output['direction']} {output['can_id']} ({output['message']})")
                # for sig in output['signals']:
                #     print(f"  {sig['name']}: {sig['value']} {sig['unit']} (Raw: {sig['raw_value']})")

            except KeyError:
                print(f"[!] Unknown ID: 0x{row['can_id']:X} at {row['Time']:.6f}s")
            except Exception as e:
                print(f"[ERROR] Parse failed: {str(e)}")

            # 保存解析结果到文本文件
            with open(new_txt_file, "a", encoding="utf-8") as f:
                f.write(f"[{output['timestamp']:.6f}] {output['direction']} {output['can_id']} ({output['message']})")
                for sig in output['signals']:
                    f.write(f"  {sig['name']}: {sig['value']} {sig['unit']} (Raw: {sig['raw_value']})\n")
                f.write("\n")  # 分隔不同报文


def split_files_by_size(output_dir, base_filename, chunk_size=10 * 1024 * 1024):
    """
    按指定大小切割文件(边生成边切割)
    :param output_dir: 输出目录
    :param base_filename: 基础文件名(如data.txt)
    :param chunk_size: 分割大小(默认100MB)
    :return:
    """

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    chunk_num = 1
    current_size = 0
    current_file = None

    # 示例数据生成(替换为你的实际数据生成逻辑)
    def data_generator():
        for _ in range(1000000):
            yield b"Large data line..." * 50 + b"\n"  # 模拟大数据生成

    for data in data_generator():
        if current_file is None or current_size >= chunk_size:
            if current_file:  # 关闭上一个文件
                current_file.close()

            # 生成新文件名(如 output_001.txt)
            new_filename = f"{base_filename.rsplit('.', 1)[0]}_{chunk_num:03d}.{base_filename.split('.')[-1]}"
            file_path = os.path.join(output_dir, new_filename)
            current_file = open(file_path, 'wb')
            chunk_num += 1
            current_size = 0

        current_file.write(data)
        current_size += len(data)

        if current_file:  # 关闭最后一个文件
            current_file.close()


# 执行解析
parse_tcanlinpro_csv(csv_path)
