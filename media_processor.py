import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime, timezone, timedelta  # 添加这行导入

class MediaProcessor:
    def __init__(self, root):
        self.root = root
        self.root.title("媒体文件处理器")
        
        # 设置FFmpeg路径
        self.bin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")
        self.ffprobe_path = os.path.join(self.bin_dir, "ffprobe.exe")
        
        # 创建UI组件
        self.create_widgets()
    
    def create_widgets(self):
        # 文件夹路径输入框
        tk.Label(self.root, text="文件夹路径:").pack(pady=(10, 0))
        
        self.path_var = tk.StringVar()
        self.path_entry = tk.Entry(self.root, textvariable=self.path_var, width=50)
        self.path_entry.pack(pady=(0, 10))
        
        # 浏览按钮
        tk.Button(self.root, text="浏览...", command=self.browse_folder).pack(pady=(0, 10))
        
        # 执行按钮
        tk.Button(self.root, text="开始处理", command=self.process_files).pack(pady=(0, 10))
        
        # 消息预览框和滚动条布局
        msg_frame = tk.Frame(self.root)
        msg_frame.pack(pady=(10, 0), fill=tk.BOTH, expand=True)
        
        tk.Label(msg_frame, text="处理消息:").pack(anchor=tk.W)
        
        self.message_text = tk.Text(msg_frame, height=15, width=70)
        self.message_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(msg_frame, command=self.message_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.message_text.config(yscrollcommand=scrollbar.set)

        # 时间校准区域
        self.time_adjust_frame = tk.LabelFrame(self.root, text="时间校准设置")
        self.time_adjust_frame.pack(pady=(10, 0), fill=tk.X)
        
        self.enable_adjust = tk.BooleanVar()
        tk.Checkbutton(
            self.time_adjust_frame, 
            text="启用时间校准",
            variable=self.enable_adjust
        ).pack(anchor=tk.W)

        # 原时间输入组件
        tk.Label(self.time_adjust_frame, text="原时间:").pack(anchor=tk.W)
        original_frame = tk.Frame(self.time_adjust_frame)
        original_frame.pack(anchor=tk.W)
        
        tk.Label(original_frame, text="年").grid(row=0, column=0)
        self.original_year = tk.Entry(original_frame, width=5)
        self.original_year.grid(row=0, column=1)
        self.original_year.insert(0, "2025")  # 默认年
        
        tk.Label(original_frame, text="月").grid(row=0, column=2)
        self.original_month = tk.Entry(original_frame, width=3)
        self.original_month.grid(row=0, column=3)
        self.original_month.insert(0, "01")  # 默认月
        
        tk.Label(original_frame, text="日").grid(row=0, column=4)
        self.original_day = tk.Entry(original_frame, width=3)
        self.original_day.grid(row=0, column=5)
        self.original_day.insert(0, "01")  # 默认日
        
        tk.Label(original_frame, text="时").grid(row=0, column=6)
        self.original_hour = tk.Entry(original_frame, width=3)
        self.original_hour.grid(row=0, column=7)
        self.original_hour.insert(0, "00")  # 默认时
        
        tk.Label(original_frame, text="分").grid(row=0, column=8)
        self.original_minute = tk.Entry(original_frame, width=3)
        self.original_minute.grid(row=0, column=9)
        self.original_minute.insert(0, "00")  # 默认分
        
        tk.Label(original_frame, text="秒").grid(row=0, column=10)
        self.original_second = tk.Entry(original_frame, width=3)
        self.original_second.grid(row=0, column=11)
        self.original_second.insert(0, "00")  # 默认秒

        # 修改到时间输入组件
        tk.Label(self.time_adjust_frame, text="修改到:").pack(anchor=tk.W, pady=(5,0))
        adjusted_frame = tk.Frame(self.time_adjust_frame)
        adjusted_frame.pack(anchor=tk.W)
        
        tk.Label(adjusted_frame, text="年").grid(row=0, column=0)
        self.adjusted_year = tk.Entry(adjusted_frame, width=5)
        self.adjusted_year.grid(row=0, column=1)
        self.adjusted_year.insert(0, "2025")  # 默认年
        
        tk.Label(adjusted_frame, text="月").grid(row=0, column=2)
        self.adjusted_month = tk.Entry(adjusted_frame, width=3)
        self.adjusted_month.grid(row=0, column=3)
        self.adjusted_month.insert(0, "01")  # 默认月
        
        tk.Label(adjusted_frame, text="日").grid(row=0, column=4)
        self.adjusted_day = tk.Entry(adjusted_frame, width=3)
        self.adjusted_day.grid(row=0, column=5)
        self.adjusted_day.insert(0, "01")  # 默认日
        
        tk.Label(adjusted_frame, text="时").grid(row=0, column=6)
        self.adjusted_hour = tk.Entry(adjusted_frame, width=3)
        self.adjusted_hour.grid(row=0, column=7)
        self.adjusted_hour.insert(0, "00")  # 默认时
        
        tk.Label(adjusted_frame, text="分").grid(row=0, column=8)
        self.adjusted_minute = tk.Entry(adjusted_frame, width=3)
        self.adjusted_minute.grid(row=0, column=9)
        self.adjusted_minute.insert(0, "00")  # 默认分
        
        tk.Label(adjusted_frame, text="秒").grid(row=0, column=10)
        self.adjusted_second = tk.Entry(adjusted_frame, width=3)
        self.adjusted_second.grid(row=0, column=11)
        self.adjusted_second.insert(0, "00")  # 默认秒

    def browse_folder(self):
        """打开文件夹选择对话框"""
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.path_var.set(folder_path)

    def process_files(self):
        folder_path = self.path_var.get()
        if not folder_path:
            messagebox.showerror("错误", "请选择文件夹路径")
            return
        
        # 校验时间格式
        if self.enable_adjust.get():
            try:
                original_time = self.validate_time_input(
                    self.original_year.get(),
                    self.original_month.get(),
                    self.original_day.get(),
                    self.original_hour.get(),
                    self.original_minute.get(),
                    self.original_second.get()
                )
                adjusted_time = self.validate_time_input(
                    self.adjusted_year.get(),
                    self.adjusted_month.get(),
                    self.adjusted_day.get(),
                    self.adjusted_hour.get(),
                    self.adjusted_minute.get(),
                    self.adjusted_second.get()
                )
            except ValueError as e:
                messagebox.showerror("错误", f"时间格式错误: {str(e)}")
                return
        
        self.message_text.delete(1.0, tk.END)
        self.message_text.insert(tk.END, f"开始处理文件夹: {folder_path}\n")
        self.message_text.see(tk.END)  # 自动滚动到底部
        self.root.update()
        
        # 遍历文件夹
        file_count = 0
        for root_dir, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root_dir, file)
                self.process_single_file(file_path)
                file_count += 1
        
        # 处理完成后显示提示
        self.message_text.insert(tk.END, f"\n处理完成，共处理 {file_count} 个文件\n")
        self.message_text.see(tk.END)  # 自动滚动到底部
        self.root.update()

    def process_single_file(self, file_path):
        try:
            # 获取当前系统时区偏移量
            utc_offset = datetime.now().astimezone().utcoffset()
            utc_hours = utc_offset.total_seconds() / 3600 if utc_offset else 0
            
            # 使用ffprobe获取创建时间
            cmd = [
                self.ffprobe_path,
                "-v", "error",
                "-show_entries", "format_tags=creation_time",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            creation_time_str = result.stdout.strip()
            
            if creation_time_str:
                try:
                    # 解析UTC时间字符串并转换为本地时区
                    utc_dt = datetime.strptime(creation_time_str.split('.')[0], "%Y-%m-%dT%H:%M:%S")
                    local_dt = utc_dt + timedelta(hours=utc_hours)  # 根据系统时区调整
                    message = f"{file_path} - 使用媒体文件创建时间: {local_dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
                except ValueError as e:
                    # 如果解析失败，使用文件修改时间
                    mtime = os.path.getmtime(file_path)
                    local_dt = datetime.fromtimestamp(mtime)
                    message = f"{file_path} - 媒体时间解析失败，使用文件修改时间: {local_dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
            else:
                # 获取不到创建时间，使用文件修改时间
                mtime = os.path.getmtime(file_path)
                local_dt = datetime.fromtimestamp(mtime)
                message = f"{file_path} - 未找到媒体创建时间，使用文件修改时间: {local_dt.strftime('%Y-%m-%d %H:%M:%S')}\n"

            # 如果启用了时间校准
            if self.enable_adjust.get():
                try:
                    original_time = self.validate_time_input(
                        self.original_year.get(),
                        self.original_month.get(),
                        self.original_day.get(),
                        self.original_hour.get(),
                        self.original_minute.get(),
                        self.original_second.get()
                    )
                    adjusted_time = self.validate_time_input(
                        self.adjusted_year.get(),
                        self.adjusted_month.get(),
                        self.adjusted_day.get(),
                        self.adjusted_hour.get(),
                        self.adjusted_minute.get(),
                        self.adjusted_second.get()
                    )
                    time_diff = adjusted_time - original_time
                    local_dt += time_diff
                except ValueError:
                    pass  # 如果时间格式错误，跳过校准

            timestamp = local_dt.timestamp()
            os.utime(file_path, (timestamp, timestamp))
            
            self.message_text.insert(tk.END, message)
            self.message_text.see(tk.END)  # 每次插入消息后自动滚动
            self.root.update()
            
        except Exception as e:
            self.message_text.insert(tk.END, f"处理 {file_path} 时出错: {str(e)}\n")
            self.message_text.see(tk.END)  # 自动滚动到底部
            self.root.update()

    def validate_time_input(self, year, month, day, hour, minute, second):
        try:
            return datetime(  # 这里已经可以正确使用datetime了
                int(year), int(month), int(day),
                int(hour), int(minute), int(second)
            )
        except ValueError as e:
            raise ValueError(f"无效的时间格式: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MediaProcessor(root)
    root.mainloop()