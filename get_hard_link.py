import os
import win32file

def get_link_count(file_path):
    """
    获取文件的链接数
    """
    return os.stat(file_path).st_nlink


def find_hard_links(file_path):
    """
    查找与指定文件相同的硬链接
    """
    hard_links = []
    base_name = os.path.basename(file_path)
    parent_dir = os.path.dirname(file_path)
    for entry in os.listdir(parent_dir):
        entry_path = os.path.join(parent_dir, entry)
        if os.path.isfile(entry_path) and os.stat(entry_path).st_ino == os.stat(file_path).st_ino:
            hard_links.append(entry_path)
    return hard_links


def get_file_physical_location(file_path):
    """
    获取文件的物理位置（磁盘簇号）
    """
    # 打开文件以获取文件句柄
    file_handle = win32file.CreateFile(
        file_path,
        win32file.GENERIC_READ,
        win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
        None,
        win32file.OPEN_EXISTING,
        win32file.FILE_ATTRIBUTE_NORMAL,
        None
    )

    # 获取文件的物理位置信息
    info = win32file.GetFileInformationByHandle(file_handle)
    file_handle.Close()

    # 返回文件的物理位置（磁盘簇号）
    return info[6]  # FILE_ALLOCATION_INFORMATION



def main():
    # 获取用户输入的文件路径
    file_path = input("请输入文件路径: ")

    # 检查文件是否存在
    if not os.path.exists(file_path):
        print("文件不存在。")
        return

    # 获取文件的链接数
    link_count = get_link_count(file_path)

    # 如果链接数大于1，则文件有硬链接
    if link_count > 1:
        print("该文件含有硬链接。")
        hard_links = find_hard_links(file_path)
        for i, link in enumerate(hard_links, start=1):
            print(f"硬链接 {i}: {link}")
        try:
            physical_location = get_file_physical_location(file_path)
            print(f"文件的物理位置（磁盘簇号）: {physical_location}")
        except Exception as e:
            print(f"无法获取文件的物理位置: {e}")
        if len(hard_links) > 1 and file_path == hard_links[0]:
            print("该文件是硬链接的本体。")
    else:
        print("该文件没有硬链接。")


if __name__ == "__main__":
    main()
