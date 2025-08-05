import os

def batch_rename_extension(folder_path, old_extension, new_extension):
    # 确保文件夹路径存在
    if not os.path.isdir(folder_path):
        print(f"文件夹路径 {folder_path} 不存在。")
        return

    # 遍历文件夹中的所有文件
    for filename in os.listdir(folder_path):
        # 检查文件后缀名是否匹配旧后缀名
        if filename.endswith(old_extension):
            # 构建新的文件名
            new_filename = filename.replace(old_extension, new_extension)
            # 构建完整的旧文件路径和新文件路径
            old_file_path = os.path.join(folder_path, filename)
            new_file_path = os.path.join(folder_path, new_filename)
            # 重命名文件
            os.rename(old_file_path, new_file_path)
            print(f"已将 {old_file_path} 重命名为 {new_file_path}")

# 获取用户输入
folder_path = input("请输入文件夹地址: ")
old_extension = input("请输入需要修改的文件后缀名（例如 .txt）: ")
new_extension = input("请输入目标后缀名（例如 .csv）: ")

# 调用函数进行批量修改
batch_rename_extension(folder_path, old_extension, new_extension)