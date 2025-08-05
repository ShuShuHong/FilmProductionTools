import os


def get_inode(filepath):
    """
    获取文件的inode号（在Windows上是文件索引号）
    """
    return os.stat(filepath).st_ino


def find_hard_links(directory):
    """
    在指定目录中查找硬链接文件
    """
    # 存储inode到文件路径的映射
    inode_map = {}

    # 遍历目录中的所有文件
    for root, dirs, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)
            try:
                # 获取文件的inode号
                inode = get_inode(filepath)
                # 将文件路径添加到对应的inode列表中
                if inode not in inode_map:
                    inode_map[inode] = []
                inode_map[inode].append(filepath)
            except OSError as e:
                print(f"无法访问文件: {filepath}, 错误: {e}")

    # 找出硬链接组
    hard_links = {inode: paths for inode, paths in inode_map.items() if len(paths) > 1}

    return hard_links


def main():
    directory = input("请输入要检查的文件夹路径: ")
    hard_links = find_hard_links(directory)

    if not hard_links:
        print("在指定文件夹中没有找到硬链接文件。")
    else:
        print("以下文件是硬链接关系：")
        for inode, paths in hard_links.items():
            print(f"Inode {inode}:")
            for path in paths:
                print(f"  {path}")


if __name__ == "__main__":
    main()
