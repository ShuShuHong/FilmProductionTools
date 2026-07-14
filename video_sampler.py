import os
import subprocess
import shutil
from datetime import datetime
import chardet

# 读取跳过列表
def get_skip_list():
    """
    从skip.txt文件中读取跳过列表
    """
    skip_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'skip.txt')
    skip_list = []
    try:
        with open(skip_file, 'r', encoding='utf-8') as f:
            skip_list = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"警告: 跳过列表文件 {skip_file} 未找到")
    except Exception as e:
        print(f"读取跳过列表时出错: {str(e)}")
    return skip_list

# 初始化跳过列表
skip_list = get_skip_list()

# 常见的非视频文件扩展名列表，用于快速过滤
non_video_extensions = {
    # 图片文件
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.svg', '.heic',
    # 文档文件
    '.txt', '.doc', '.docx', '.pdf', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods', '.odp',
    # 音频文件
    '.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a', '.wma', '.opus',
    # 压缩文件
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
    # 代码文件
    '.py', '.java', '.cpp', '.c', '.h', '.cs', '.js', '.html', '.css', '.php', '.go', '.rust',
    # 配置文件
    '.ini', '.conf', '.cfg', '.json', '.yaml', '.yml', '.xml', '.toml',
    # 系统文件
    '.exe', '.dll', '.sys', '.bat', '.cmd', '.sh', '.lnk', '.iso', '.img',
    # 其他常见非视频文件
    '.log', '.tmp', '.temp', '.bak', '.backup', '.swp', '.swo',
}


def get_ffmpeg_executable():
    """
    从bin目录获取ffmpeg和ffprobe可执行文件路径
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bin_dir = os.path.join(script_dir, 'bin')
    ffmpeg_exe = os.path.join(bin_dir, 'ffmpeg.exe')
    ffprobe_exe = os.path.join(bin_dir, 'ffprobe.exe')

    if not os.path.isfile(ffmpeg_exe):
        print(f"警告: ffmpeg.exe 未找到于 {bin_dir}，部分功能可能无法使用")
    
    if not os.path.isfile(ffprobe_exe):
        raise FileNotFoundError(f"ffprobe.exe 未找到于 {bin_dir}，请检查bin文件夹")

    return ffmpeg_exe, ffprobe_exe


def is_video_file(file_path):
    """
    使用ffprobe检测文件是否为视频文件
    """
    try:
        _, ffprobe_exe = get_ffmpeg_executable()
        cmd = [
            ffprobe_exe, '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=codec_type', '-of', 'default=noprint_wrappers=1:nokey=1',
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=False, check=False)
        
        # 自动检测输出编码
        if result.stdout:
            detected_encoding = chardet.detect(result.stdout)['encoding']
            stdout_text = result.stdout.decode(detected_encoding, errors='replace').strip()
        else:
            stdout_text = ''
        
        # 如果包含视频流，返回True
        return result.returncode == 0 and stdout_text == 'video'
    except Exception:
        # 其他错误，如文件不存在、权限问题等
        return False

def get_video_info(file_path):
    """
    使用ffprobe获取视频文件的详细信息
    """
    try:
        # 获取ffprobe可执行文件路径
        _, ffprobe_exe = get_ffmpeg_executable()
        
        # 获取视频流信息
        cmd = [
            ffprobe_exe, '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=codec_name,profile,pix_fmt',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=False, check=True)
        
        # 自动检测输出编码
        if result.stdout:
            detected_encoding = chardet.detect(result.stdout)['encoding']
            stdout_text = result.stdout.decode(detected_encoding, errors='replace').strip()
            output = stdout_text.split('\n')
        else:
            output = []
        
        if len(output) >= 3:
            codec_name = output[0].strip('\n\r')
            profile = output[1].strip('\n\r')
            pix_fmt = output[2].strip('\n\r')
        elif len(output) == 2:
            codec_name = output[0].strip('\n\r')
            profile = 'unknown'
            pix_fmt = output[1].strip('\n\r')
        else:
            return None
        
        # 检查是否有alpha通道
        has_alpha = 'alpha' in pix_fmt.lower() or 'a' in pix_fmt.lower() or 'yuva' in pix_fmt.lower()
        
        # 获取视频时长
        duration_cmd = [
            ffprobe_exe, '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            file_path
        ]
        duration_result = subprocess.run(duration_cmd, capture_output=True, text=False, check=True)
        
        # 自动检测输出编码
        if duration_result.stdout:
            duration_encoding = chardet.detect(duration_result.stdout)['encoding']
            duration_text = duration_result.stdout.decode(duration_encoding, errors='replace').strip()
            duration = float(duration_text)
        else:
            duration = 0.0
        
        return {
            'codec_name': codec_name,
            'profile': profile,
            'pix_fmt': pix_fmt,
            'has_alpha': has_alpha,
            'duration': duration
        }
    except subprocess.CalledProcessError as e:
        # 自动检测错误输出的编码
        if e.stderr:
            detected_encoding = chardet.detect(e.stderr)['encoding']
            stderr_text = e.stderr.decode(detected_encoding, errors='replace')
            print(f"获取视频信息失败 {file_path}: {stderr_text}")
        else:
            print(f"获取视频信息失败 {file_path}: 命令执行失败")
        return None
    except Exception as e:
        print(f"处理视频文件时出错 {file_path}: {str(e)}")
        return None

def classify_videos(folder_path):
    """
    遍历文件夹及其子文件夹，根据视频属性分类视频文件
    """
    video_types = {}
    total_files = 0
    video_files = 0
    processed_files = 0
    
    print(f"开始遍历文件夹: {folder_path}")
    
    # 遍历文件夹及其子文件夹
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            total_files += 1
            
            # 获取文件扩展名（转换为小写）
            _, ext = os.path.splitext(file)
            ext = ext.lower()
            
            # 快速过滤常见非视频文件
            if ext in non_video_extensions:
                continue
            
            file_path = os.path.join(root, file)
            
            # 检查路径是否包含跳过列表中的任何文本
            if any(skip_text in file_path for skip_text in skip_list):
                continue
            
            # 使用ffprobe检测文件是否为视频文件
            if is_video_file(file_path):
                video_files += 1
                
                # 获取视频信息
                video_info = get_video_info(file_path)
                if video_info:
                    processed_files += 1
                    
                    # 获取文件大小
                    try:
                        file_size = os.path.getsize(file_path)
                    except Exception as e:
                        print(f"获取文件大小失败 {file_path}: {str(e)}")
                        file_size = 0
                    
                    # 构建视频类型标识符，包含文件扩展名
                    video_type = (
                        video_info['codec_name'],
                        video_info['profile'],
                        video_info['pix_fmt'],
                        video_info['has_alpha'],
                        ext
                    )
                    
                    # 如果是新类型，添加到字典中
                    if video_type not in video_types:
                        video_types[video_type] = {
                            'sample_file_path': file_path,
                            'sample_info': video_info,
                            'count': 0,
                            'total_size': 0,
                            'total_duration': 0,
                            'files': []
                        }
                    
                    # 更新视频类型的统计信息
                    video_types[video_type]['count'] += 1
                    video_types[video_type]['total_size'] += file_size
                    video_types[video_type]['total_duration'] += video_info['duration']
                    video_types[video_type]['files'].append({
                        'file_path': file_path,
                        'file_size': file_size,
                        'duration': video_info['duration']
                    })
                    
                    # 打印进度信息
                    if processed_files % 10 == 0:
                        print(f"已处理 {processed_files}/{video_files} 个视频文件，找到 {len(video_types)} 种不同类型")
    
    print(f"遍历完成！总共扫描了 {total_files} 个文件，其中 {video_files} 个是视频文件，成功处理了 {processed_files} 个视频文件，找到 {len(video_types)} 种不同类型")
    return video_types

def format_file_size(size_bytes):
    """
    将字节大小格式化为人类可读的格式
    """
    if size_bytes == 0:
        return "0 B"
    size_name = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_name) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {size_name[i]}"


def sanitize_filename(filename):
    """
    清理文件名中的非法字符，确保文件名符合操作系统命名规则
    """
    # Windows 系统中不允许的字符
    illegal_chars = '<>:/\\|?*"' + '\x00' + '\r\n' + '\t'
    # 替换非法字符为下划线
    for char in illegal_chars:
        filename = filename.replace(char, '_')
    # 替换连续的下划线为单个下划线
    while '__' in filename:
        filename = filename.replace('__', '_')
    # 移除文件名开头和结尾的下划线
    filename = filename.strip('_')
    # 确保文件名不为空
    if not filename:
        filename = "unknown"
    return filename

def format_duration(seconds):
    """
    将秒数格式化为人类可读的格式（HH:MM:SS）
    """
    if seconds < 0:
        return "00:00:00"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def save_samples(video_types, output_folder):
    """
    将每种类型的视频样本保存到新的文件夹
    """
    # 创建输出文件夹
    os.makedirs(output_folder, exist_ok=True)
    
    # 计算总大小和总时长
    total_size = sum(video_data['total_size'] for _, video_data in video_types.items())
    total_duration = sum(video_data['total_duration'] for _, video_data in video_types.items())
    total_files = sum(video_data['count'] for _, video_data in video_types.items())
    
    # 创建记录文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(output_folder, f'video_samples_report_{timestamp}.md')
    
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"# 视频样本收集报告\n\n")
        f.write(f"## 报告概况\n")
        f.write(f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- 视频类型总数: {len(video_types)}\n")
        f.write(f"- 样本总数量: {total_files}\n")
        f.write(f"- 样本总大小: {format_file_size(total_size)}\n")
        f.write(f"- 样本总时长: {format_duration(total_duration)}\n\n")
        
        # 写入视频类型统计信息
        f.write("## 视频类型统计信息\n\n")
        f.write("| 序号 | 编码格式 | 编码级别 | 像素格式 | 透明通道 | 文件数 | 总大小 | 总时长 | 样本文件名 |\n")
        f.write("| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
        
        # 复制样本文件并记录信息
        for i, (video_type, video_data) in enumerate(video_types.items(), 1):
            codec, profile, pix_fmt, has_alpha, ext = video_type
            file_path = video_data['sample_file_path']
            file_name = os.path.basename(file_path)
            sample_file_size = os.path.getsize(file_path)
            
            # 构建目标文件名和路径
            alpha_str = "_alpha" if has_alpha else ""
            # 清理codec、profile和pix_fmt中的非法字符
            sanitized_codec = sanitize_filename(codec)
            sanitized_profile = sanitize_filename(profile)
            sanitized_pix_fmt = sanitize_filename(pix_fmt)
            # 构建基础文件名
            base_name = f"sample_{i:03d}_{sanitized_codec}_{sanitized_profile}_{sanitized_pix_fmt}{alpha_str}"
            file_ext = os.path.splitext(file_name)[1]
            # 清理最终文件名中的非法字符
            final_base_name = sanitize_filename(base_name)
            target_file_name = f"{final_base_name}{file_ext}"
            target_file_path = os.path.join(output_folder, target_file_name)
            
            try:
                # 复制文件
                shutil.copy2(file_path, target_file_path)
                
                # 记录信息，确保一行完整显示，清理可能包含的换行符
                alpha_channel = '有Alpha通道' if has_alpha else '无Alpha通道'
                # 移除所有可能导致换行的字符
                clean_codec = codec.replace('\n', '').replace('\r', '')
                clean_profile = profile.replace('\n', '').replace('\r', '')
                clean_pix_fmt = pix_fmt.replace('\n', '').replace('\r', '')
                clean_file_name = file_name.replace('\n', '').replace('\r', '')
                f.write(f"| {i} | {clean_codec} | {clean_profile} | {clean_pix_fmt} | {alpha_channel} | {video_data['count']} | {format_file_size(video_data['total_size'])} | {format_duration(video_data['total_duration'])} | {clean_file_name} |\n")
                print(f"已保存样本 {i}: {file_name} ({format_file_size(sample_file_size)}) -> {target_file_name}")
            except Exception as e:
                print(f"保存样本失败 {file_path}: {str(e)}")
    
    # 更新日志文件路径显示
    log_file_name = os.path.basename(log_file)
    
    print(f"\n所有样本已保存到: {output_folder}")
    print(f"样本总数量: {total_files}")
    print(f"样本总大小: {format_file_size(total_size)}")
    print(f"样本总时长: {format_duration(total_duration)}")
    print(f"详细记录已保存到: {log_file}")
    return log_file

import sys

def main():
    print("=" * 60)
    print("视频样本收集工具")
    print("用于收集不同编码格式、色彩格式的视频样本")
    print("=" * 60)
    print()
    
    # 获取文件夹路径，可以通过命令行参数传入
    folder_path = None
    if len(sys.argv) > 1:
        folder_path = sys.argv[1]
    else:
        # 获取用户输入的文件夹路径
        folder_path = input("请输入要扫描的文件夹路径: ").strip()
    
    # 验证文件夹路径
    if not os.path.isdir(folder_path):
        print(f"错误: {folder_path} 不是有效的文件夹路径")
        return
    
    # 分类视频文件
    video_types = classify_videos(folder_path)
    
    if not video_types:
        print("没有找到有效的视频文件")
        return
    
    # 计算统计信息
    total_size = sum(video_data['total_size'] for _, video_data in video_types.items())
    total_files = sum(video_data['count'] for _, video_data in video_types.items())
    total_duration = sum(video_data['total_duration'] for _, video_data in video_types.items())
    
    # 计算样本总大小（仅遴选的样本文件）
    samples_total_size = 0
    for _, video_data in video_types.items():
        sample_path = video_data['sample_file_path']
        samples_total_size += os.path.getsize(sample_path)
    
    # 显示分类结果
    print("\n" + "=" * 100)
    print("视频类型分类结果")
    print("=" * 100)
    print(f"{'序号':<5} {'编码格式':<15} {'Profile':<15} {'色彩格式':<15} {'Alpha通道':<10} {'文件数':<8} {'总大小':<12} {'总时长':<12}")
    print("-" * 100)
    
    for i, (video_type, video_data) in enumerate(video_types.items(), 1):
        codec, profile, pix_fmt, has_alpha, ext = video_type
        print(f"{i:<5} {codec:<15} {profile:<15} {pix_fmt:<15} {'是' if has_alpha else '否':<10} {video_data['count']:<8} {format_file_size(video_data['total_size']):<12} {format_duration(video_data['total_duration']):<12}")
    
    print(f"\n{'视频类型总数':<55} {len(video_types):<5}")
    print(f"{'总文件数':<55} {total_files:<5}")
    print(f"{'总大小':<55} {format_file_size(total_size):<12}")
    print(f"{'总时长':<55} {format_duration(total_duration):<12}")
    print(f"{'所有样本总大小':<55} {format_file_size(samples_total_size):<12}")
    
    # 询问用户是否保存样本
    print("\n" + "=" * 75)
    save_choice = input(f"是否要将这 {len(video_types)} 种不同类型的视频样本保存到新的文件夹？(y/n): ").strip().lower()
    
    if save_choice == 'y' or save_choice == 'yes':
        # 获取输出文件夹路径
        default_output = os.path.join(os.getcwd(), f"video_samples_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        output_folder = input(f"请输入保存样本的文件夹路径 (默认: {default_output}): ").strip()
        
        if not output_folder:
            output_folder = default_output
        
        # 保存样本
        save_samples(video_types, output_folder)
    else:
        print("已取消保存样本操作")
    
    print("\n程序执行完毕！")

if __name__ == "__main__":
    main()
