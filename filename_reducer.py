import os
import tkinter as tk
from tkinter import filedialog, scrolledtext

class FilenameReducer:
    def __init__(self, root):
        self.root = root
        root.title("文件名精简工具")
        
        # 文件夹路径输入框
        tk.Label(root, text="文件夹路径:").pack()
        self.folder_path = tk.Entry(root, width=50)
        self.folder_path.pack()
        tk.Button(root, text="浏览...", command=self.browse_folder).pack()
        
        # 要删除的字符串输入框
        tk.Label(root, text="要从文件名中删除的字符串:").pack()
        self.string_to_remove = tk.Entry(root, width=50)
        self.string_to_remove.pack()
        
        # 运行按钮
        tk.Button(root, text="执行删除", command=self.process_files).pack()
        
        # 运行信息窗口
        tk.Label(root, text="运行日志:").pack()
        self.log = scrolledtext.ScrolledText(root, width=60, height=15)
        self.log.pack()
    
    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path.delete(0, tk.END)
            self.folder_path.insert(0, folder_selected)
    
    def process_files(self):
        folder = self.folder_path.get()
        remove_str = self.string_to_remove.get()
        
        if not folder or not remove_str:
            self.log_message("错误: 请先选择文件夹并输入要删除的字符串")
            return
        
        try:
            for root_dir, _, files in os.walk(folder):
                for filename in files:
                    if remove_str in filename:
                        old_path = os.path.join(root_dir, filename)
                        new_filename = filename.replace(remove_str, "")
                        new_path = os.path.join(root_dir, new_filename)
                        
                        os.rename(old_path, new_path)
                        self.log_message(f"已重命名: {filename} -> {new_filename}")
            
            self.log_message("操作完成!")
        except Exception as e:
            self.log_message(f"发生错误: {str(e)}")
    
    def log_message(self, message):
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)
        self.root.update()

if __name__ == "__main__":
    root = tk.Tk()
    app = FilenameReducer(root)
    root.mainloop()