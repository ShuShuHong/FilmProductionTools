from tqdm import tqdm
import time

def process_files(file_count):
    # 使用 tqdm 创建一个进度条，total 是任务总数，desc 是描述
    for i in tqdm(range(file_count), desc="Processing files", unit="file"):
        # 模拟文件处理的延迟
        time.sleep(0.1)  # 这里模拟每个文件处理 0.1 秒

# 测试：假设我们有 50 个文件需要处理
process_files(50)
