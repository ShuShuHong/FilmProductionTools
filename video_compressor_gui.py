import os
import subprocess
from tkinter import *
from tkinter import filedialog, messagebox, scrolledtext, ttk
import threading
import ffmpeg
from datetime import datetime
import shutil
import cv2
import sys
import webbrowser
from PIL import Image, ImageTk  # 导入Pillow库
import calculate_sb_coefficient

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

def run_hidden(command, **kwargs):
    if sys.platform == 'win32':
        CREATE_NO_WINDOW = 0x08000000
        kwargs['creationflags'] = CREATE_NO_WINDOW
    result = subprocess.run(command, **kwargs)
    return result

def get_ffmpeg_executable():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bin_dir = os.path.join(script_dir, 'bin')
    ffmpeg_exe = os.path.join(bin_dir, 'ffmpeg.exe')
    ffprobe_exe = os.path.join(bin_dir, 'ffprobe.exe')

    if not os.path.isfile(ffmpeg_exe) or not os.path.isfile(ffprobe_exe):
        raise FileNotFoundError("ffmpeg.exe 或 ffprobe.exe 未找到，请检查 /bin 文件夹。")

    return ffmpeg_exe, ffprobe_exe


def is_video_file(file_path):
    """
    使用ffprobe检测文件是否为视频文件
    """
    try:
        ffmpeg_exe, ffprobe_exe = get_ffmpeg_executable()
        cmd = [
            ffprobe_exe, '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=codec_type', '-of', 'default=noprint_wrappers=1:nokey=1',
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        # 如果包含视频流，返回True
        return result.returncode == 0 and result.stdout.strip() == 'video'
    except Exception:
        # 其他错误，如文件不存在、权限问题等
        return False


def get_folder_size(folder_path):
    total_size = 0
    for dirpath, _, filenames in os.walk(folder_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size


def get_video_info(file_path):
    try:
        ffmpeg_exe, ffprobe_exe = get_ffmpeg_executable()
        probe = ffmpeg.probe(file_path, cmd=ffprobe_exe)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        audio_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)
        if not video_stream:
            raise ValueError("No video stream found")

        width = int(video_stream.get('width', 0))
        height = int(video_stream.get('height', 0))
        pix_fmt = video_stream.get('pix_fmt', 'unknown')
        bit_rate = int(video_stream.get('bit_rate', 0))
        codec_name = video_stream.get('codec_name', 'unknown')
        profile = video_stream.get('profile', 'unknown')
        fps = float(video_stream.get('avg_frame_rate', '0').split('/')[0]) / float(
            video_stream.get('avg_frame_rate', '1').split('/')[1])

        duration_seconds = float(probe.get('format', {}).get('duration', 0))
        file_size = os.path.getsize(file_path)

        # Calculate overall bitrate including audio
        if audio_stream:
            audio_bit_rate = int(audio_stream.get('bit_rate', 0))
            overall_bit_rate = (file_size * 8) / (duration_seconds * 1_000_000)
        else:
            overall_bit_rate = (file_size * 8) / (duration_seconds * 1_000_000)
            audio_bit_rate = 0

        log_text.insert(END, f"获取到的时长: {duration_seconds:.2f}秒, 文件大小: {file_size / (1024 * 1024):.2f}MB\n")
        log_text.see(END)

        return width, height, pix_fmt, bit_rate, codec_name, profile, fps, overall_bit_rate, audio_bit_rate
    except ffmpeg.Error as e:
        log_text.insert(END, f"FFmpeg Error: {e.stderr.decode()}\n")
        raise ValueError(f"无法解析视频信息: {e.stderr.decode()}") from e
    except Exception as e:
        log_text.insert(END, f"General Error: {str(e)}\n")
        raise ValueError(f"无法获取视频信息: {str(e)}") from e


def has_alpha_channel(pix_fmt, codec_name, profile):
    alpha_keywords = ['rgba', 'argb', 'abgr', 'bgra', 'gbrap', 'gbrap10le', 'gbrap12le', 'yuva']
    prores_4444_profiles = ['4444']

    if any(alpha_keyword in pix_fmt for alpha_keyword in alpha_keywords):
        return True
    if codec_name == 'prores' and profile in prores_4444_profiles:
        return True
    return False


def calculate_standard_bitrate(width, height, fps, coefficient, pix_fmt):
    pixels_per_second = width * height * fps
    if compress_color.get():
       sb_coefficient = 1
       log_text.insert(END, f"选择了压缩色彩位深码率1倍")
    else:
        # 获取像素格式的位深
        pix_fmt_bits_dict = calculate_sb_coefficient.get_pix_fmt_bits()
        bits = pix_fmt_bits_dict.get(pix_fmt, 0)
        # 计算与 "yuv420p" 的位深的倍数
        yuv420p_bits = calculate_sb_coefficient.get_pix_fmt_bits().get("yuv420p", 0)
        sb_coefficient = bits / yuv420p_bits
        log_text.insert(END, f"维持原始像素格式：{pix_fmt}；码率倍增：{sb_coefficient}\n")
    standard_bitrate = pixels_per_second / (coefficient * 1000000) * sb_coefficient
    return standard_bitrate

def check_nvenc():
    """Check if NVENC is supported on the host system."""
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, check=True)
        if "NVIDIA" in result.stdout and "Driver Version" in result.stdout:
            return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return False


def check_qsv():
    """Check if the system supports hevc_qsv encoder via FFmpeg."""
    try:
        # Define the path to ffmpeg.exe, adjust as necessary
        ffmpeg_bin = os.path.join(os.getcwd(), 'bin', 'ffmpeg.exe')

        # Run FFmpeg with -encoders flag to list all available encoders
        result = subprocess.run([ffmpeg_bin, '-encoders'], capture_output=True, text=True, check=True)

        # Check if hevc_qsv is in the list of encoders
        if "hevc_qsv" in result.stdout:
            return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return False

def check_amf():
    """Check if AMF is supported on the host system."""
    try:
        result = subprocess.run(['wmic', 'path', 'win32_VideoController', 'get', 'name'],
                                capture_output=True, text=True, check=True)
        if "AMD" in result.stdout:
            return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return False

def compress_video(input_file, output_file, target_bitrate, use_cpu, pix_fmt):
    ffmpeg_exe, _ = get_ffmpeg_executable()
    log_text.insert(END, f"开始压缩 {input_file} 到 {output_file}，目标码率: {target_bitrate}Mbps\n")
    if not use_cpu:
        if hardware_accelerator == 'nvenc':
            command = [
                ffmpeg_exe,
                '-i', input_file,
                '-c:v', 'hevc_nvenc',
                '-preset', 'fast', '-crf', '28',
                '-b:v', f'{target_bitrate}M', '-c:a', 'aac', '-b:a', '128k',
            ]
        elif hardware_accelerator == 'amf':
            command = [
                ffmpeg_exe,
                '-i', input_file,
                '-c:v', 'hevc_amf',
                '-usage', 'transcoding',  # 设置编码用途为转码
                '-rc', 'vbr_peak',  # 使用可变比特率（VBR），以适应视频内容的变化
                '-b:v', f'{target_bitrate}M',  # 设置目标视频比特率
                '-quality', 'speed',  # 优先考虑编码速度
                '-bf', '3',  # 设置B帧数量，通常3到4是合理的值
                '-coder', '1',  # 使用CABAC熵编码，通常提供更好的压缩效率
                '-color_range', 'tv',  # 设置颜色范围为电视标准 (0-255)
                '-c:a', 'aac',  # 使用AAC编码音频
                '-b:a', '128k',  # 设置音频比特率为128k
            ]
        elif hardware_accelerator == 'qsv':
            command = [
                ffmpeg_exe,
                '-i', input_file,
                '-c:v', 'hevc_qsv',
                '-preset', 'fast', '-crf', '28',
                '-b:v', f'{target_bitrate}M', '-c:a', 'aac', '-b:a', '128k',
            ]
        else:
            command = [
                ffmpeg_exe,
                '-i', input_file,
                '-c:v', 'libx265',
                '-preset', 'fast', '-crf', '28',
                '-b:v', f'{target_bitrate}M', '-c:a', 'aac', '-b:a', '128k',
            ]
    else:
        command = [
            ffmpeg_exe,
            '-i', input_file,
            '-c:v', 'libx265',
            '-preset', 'fast', '-crf', '28',
            '-b:v', f'{target_bitrate}M', '-c:a', 'aac', '-b:a', '128k',
        ]
        # 根据 compress_color 决定是否添加 -pix_fmt yuv420p
    if compress_color.get():
        command.append('-pix_fmt')
        command.append('yuv420p')
    else:
        command.append('-pix_fmt')
        command.append(pix_fmt)  # pix_fmt 是从 get_video_info 中获取的原始像素格式

    command.append(output_file)
    log_text.insert(END, f"压缩参数： {command} \n")

    with open(os.devnull, 'w') as devnull:
        result = run_hidden(command, stdout=devnull, stderr=subprocess.PIPE)

    if result.returncode != 0:
        log_text.insert(END, f"压缩失败: {result.stderr.decode()}\n")
        return False
    if os.path.getsize(output_file) == 0:
        log_text.insert(END, f"生成的文件大小为 0KB，跳过替换\n")
        return False

    # Check if the compressed file has a valid video stream
    try:
        _, ffprobe_exe = get_ffmpeg_executable()
        probe = ffmpeg.probe(output_file, cmd=ffprobe_exe)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        if not video_stream:
            log_text.insert(END, f"压缩后的文件没有有效的视频轨道，跳过替换\n")
            return False

        # Check for black screen by analyzing all frames
        if is_black_screen_all_frames(output_file):
            log_text.insert(END, f"压缩后的文件包含纯黑帧，检查原视频是否也为纯黑\n")
            if is_black_screen_all_frames(input_file):
                log_text.insert(END, f"原视频也是纯黑视频，不认为是转码失败\n")
                return True
            else:
                log_text.insert(END, f"原视频不是纯黑视频，认为是转码失败\n")
                return False
    except ffmpeg.Error as e:
        log_text.insert(END, f"无法解析压缩后的视频信息: {e.stderr.decode()}\n")
        return False

    log_text.insert(END, f"完成压缩 {input_file} 到 {output_file}\n\n")
    return True


def replace_with_compressed(input_file, compressed_file):
    global replace_hard_links_var
    if replace_hard_links_var.get():
        # Use shutil.copyfileobj to replace hard links
        with open(compressed_file, 'rb') as src:
            with open(input_file, 'wb') as dst:
                shutil.copyfileobj(src, dst)
        # Update the modification time to match the compressed file
        stat = os.stat(compressed_file)
        os.utime(input_file, (stat.st_atime, stat.st_mtime))
        log_text.insert(END, f"已压缩并更新所有副本\n")
    else:
        # Create a copy of the compressed file before replacing the original file
        temp_copy_file = os.path.join(os.path.dirname(compressed_file), f'temp_copy_{os.path.basename(compressed_file)}')
        shutil.copy2(compressed_file, temp_copy_file)
        # Replace the original file with the copied file
        os.replace(temp_copy_file, input_file)
        log_text.insert(END, f"已压缩并替换当前文件\n")



def is_black_screen_all_frames(video_file):
    try:
        cap = cv2.VideoCapture(video_file)
        if not cap.isOpened():
            log_text.insert(END, f"无法打开视频文件: {video_file}\n")
            return True

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count == 0:
            log_text.insert(END, f"视频文件帧数为 0: {video_file}\n")
            return True

        all_black = True
        frame_index = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if not is_frame_black(frame):
                all_black = False
                break
            frame_index += 1
            if frame_index % 100 == 0:  # 每处理100帧打印一次进度
                log_text.insert(END, f"已检查 {frame_index}/{frame_count} 帧\n")
                log_text.see(END)

        cap.release()
        log_text.insert(END, f"已检查所有 {frame_count} 帧\n")
        return all_black
    except AttributeError as ae:
        log_text.insert(END, f"OpenCV 错误: {ae}\n")
        return True
    except Exception as e:
        log_text.insert(END, f"通用错误: {str(e)}\n")
        return True


def is_frame_black(frame):
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mean_intensity = cv2.mean(gray_frame)[0]
    return mean_intensity < 10  # Adjust threshold as needed


def are_frames_identical(frame1, frame2):
    return cv2.norm(frame1, frame2, cv2.NORM_L2) == 0


def secondary_compress_video(input_file, output_file, target_bitrate, pix_fmt):
    ffmpeg_exe, _ = get_ffmpeg_executable()
    log_text.insert(END, f"尝试使用 CPU 进行二次压缩 {input_file} 到 {output_file}，目标码率: {target_bitrate}Mbps\n")
    cmd = [
            ffmpeg_exe,
            '-i', input_file,
            '-c:v', 'libx265',
            '-preset', 'fast', '-crf', '28',
            '-b:v', f'{target_bitrate}M', '-c:a', 'aac', '-b:a', '128k',
            output_file
        ]
    if compress_color.get():
        cmd.append('-pix_fmt')
        cmd.append('yuv420p')
    else:
        cmd.append('-pix_fmt')
        cmd.append(pix_fmt)  # pix_fmt 是从 get_video_info 中获取的原始像素格式
    cmd.append(output_file)
    log_text.insert(END, f"压缩参数： {cmd} \n")
    try:
        run_hidden(cmd, check=True)
        log_text.insert(END, f"二次压缩完成. 输出保存到 {output_file}\n")
        return True
    except subprocess.CalledProcessError as e:
        log_text.insert(END, f"二次压缩时出错: {e}\n")
        return False


def compare_videos(video1, video2):
    try:
        cap1 = cv2.VideoCapture(video1)
        cap2 = cv2.VideoCapture(video2)

        if not cap1.isOpened() or not cap2.isOpened():
            log_text.insert(END, "无法打开其中一个视频文件\n")
            return False

        fps1 = cap1.get(cv2.CAP_PROP_FPS)
        fps2 = cap2.get(cv2.CAP_PROP_FPS)
        if fps1 != fps2:
            log_text.insert(END, "两个视频的帧率不同\n")
            return False

        frame_count1 = int(cap1.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_count2 = int(cap2.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count1 != frame_count2:
            log_text.insert(END, "两个视频的帧数不同\n")
            return False

        frame_index = 0
        while True:
            ret1, frame1 = cap1.read()
            ret2, frame2 = cap2.read()

            if not ret1 or not ret2:
                break

            if not are_frames_identical(frame1, frame2):
                log_text.insert(END, f"帧 {frame_index} 不相同\n")
                return False

            frame_index += 1
            if frame_index % 100 == 0:  # 每处理100帧打印一次进度
                log_text.insert(END, f"已比较 {frame_index}/{frame_count1} 帧\n")
                log_text.see(END)

        cap1.release()
        cap2.release()
        log_text.insert(END, f"已比较所有 {frame_count1} 帧\n")
        return True
    except AttributeError as ae:
        log_text.insert(END, f"OpenCV 错误: {ae}\n")
        return False
    except Exception as e:
        log_text.insert(END, f"通用错误: {str(e)}\n")
        return False

def process_folder_with_output(folder_path, output_folder_path, coefficient, use_cpu):
    initial_size = get_folder_size(folder_path)
    video_files = []
    skipped_files = []
    failed_files = []
    secondary_success_files = []
    total_files = 0
    checked_files = 0

    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            total_files += 1
            
            # 获取文件扩展名（转换为小写）
            _, ext = os.path.splitext(filename)
            ext = ext.lower()
            
            # 快速过滤常见非视频文件
            if ext in non_video_extensions:
                continue
            
            file_path = os.path.join(root, filename)
            
            # 检查路径是否包含跳过列表中的任何文本
            if any(skip_text in file_path for skip_text in skip_list):
                continue
            
            checked_files += 1
            
            # 使用ffprobe检测文件是否为视频文件
            if is_video_file(file_path):
                video_files.append(file_path)

    total_files = len(video_files)
    log_text.insert(END, f"找到 {total_files} 个视频文件。\n")

    for i, file_path in enumerate(video_files):
        if stop_processing:
            log_text.insert(END, "处理被用户终止\n")
            break

        relative_path = os.path.relpath(file_path, folder_path)
        output_file_path = os.path.join(output_folder_path, relative_path)
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

        temp_output_file = ''
        secondary_temp_output_file = ''
        try:
            width, height, pix_fmt, bit_rate, codec_name, profile, fps, overall_bit_rate, audio_bit_rate = get_video_info(
                file_path)
            video_bit_rate = overall_bit_rate - audio_bit_rate / 1_000_000  # Convert to Mbps

            standard_bitrate = calculate_standard_bitrate(width, height, fps, coefficient, pix_fmt)
            full_file_bitrate = standard_bitrate + 0.128  # Add 128kbps for AAC audio
            max_allowed_bitrate = full_file_bitrate * 1.2

            log_text.insert(END,
                            f"\n处理文件: {file_path}, 宽度: {width}p, 高度: {height}p, 帧率: {fps}fps, 视频码率: {video_bit_rate:.2f}Mbps, 全文件码率: {full_file_bitrate:.2f}Mbps, 最大允许码率: {max_allowed_bitrate:.2f}Mbps, 像素格式: {pix_fmt}, 编码器: {codec_name}, Profile: {profile}\n")
            log_text.see(END)

            # Check if the pixel format contains an alpha channel or if it's ProRes 4444
            if has_alpha_channel(pix_fmt, codec_name, profile):
                log_text.insert(END, f"{os.path.basename(file_path)} 包含 alpha 通道或使用 ProRes 4444 编码，跳过处理\n")
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # Convert to MB
                skipped_files.append((file_path, pix_fmt, codec_name, profile, file_size))
                continue

            if video_bit_rate > max_allowed_bitrate:
                target_bitrate = standard_bitrate
                temp_output_file = os.path.join(os.path.dirname(output_file_path), f'temp_{os.path.basename(output_file_path)}.mp4')
                compression_successful = compress_video(file_path, temp_output_file, target_bitrate, use_cpu, pix_fmt)

                if compression_successful:
                    shutil.move(temp_output_file, output_file_path)
                    secondary_success_files.append((output_file_path, "首次成功"))
                else:
                    failed_files.append((file_path, "首次压缩失败"))

                    # Try secondary compression
                    secondary_temp_output_file = os.path.join(os.path.dirname(output_file_path),
                                                              f'secondary_temp_{os.path.basename(output_file_path)}.mp4')
                    secondary_compression_successful = secondary_compress_video(file_path, secondary_temp_output_file, pix_fmt,
                                                                                bitrate=str(target_bitrate) + 'M',
                                                                                use_cpu=use_cpu)

                    if secondary_compression_successful:
                        if is_black_screen_all_frames(secondary_temp_output_file):
                            log_text.insert(END, f"二次压缩后的文件仍然为纯黑，认为是转码失败\n")
                            failed_files.append((file_path, "二次压缩后仍为纯黑"))
                        elif compare_videos(file_path, secondary_temp_output_file):
                            log_text.insert(END, f"二次压缩后的文件与原视频完全一致，认为是转码成功\n")
                            shutil.move(secondary_temp_output_file, output_file_path)
                            secondary_success_files.append((output_file_path, "二次成功"))
                        else:
                            log_text.insert(END, f"二次压缩后的文件与原视频不一致，认为是转码失败\n")
                            failed_files.append((file_path, "二次压缩后不一致"))
                    else:
                        failed_files.append((file_path, "二次压缩失败"))

                    # If secondary compression fails or secondary compressed file does not match original, keep temporary files for analysis
                    if not secondary_compression_successful or not compare_videos(file_path,
                                                                                  secondary_temp_output_file):
                        log_text.insert(END,
                                        f"保留临时文件: {temp_output_file} 和 {secondary_temp_output_file} 以供分析\n")
                    else:
                        os.remove(temp_output_file)  # 删除临时文件
                        os.remove(secondary_temp_output_file)  # 删除临时文件
            else:
                log_text.insert(END, f"{os.path.basename(file_path)} 符合标准码率要求，无需压缩\n")
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # Convert to MB
                skipped_files.append((file_path, pix_fmt, codec_name, profile, file_size))
                #shutil.copy2(file_path, output_file_path)
        except ValueError as ve:
            log_text.insert(END, f"处理文件 {file_path} 时出错: {ve}\n")
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # Convert to MB
            skipped_files.append((file_path, "未知", "未知", "未知", file_size))
            if os.path.exists(temp_output_file):
                log_text.insert(END, f"保留临时文件: {temp_output_file} 以供分析\n")
            if os.path.exists(secondary_temp_output_file):
                log_text.insert(END, f"保留临时文件: {secondary_temp_output_file} 以供分析\n")
        except Exception as e:
            log_text.insert(END, f"处理文件 {file_path} 时出错: {e}\n")
            failed_files.append((file_path, str(e)))
            if os.path.exists(temp_output_file):
                log_text.insert(END, f"保留临时文件: {temp_output_file} 以供分析\n")
            if os.path.exists(secondary_temp_output_file):
                log_text.insert(END, f"保留临时文件: {secondary_temp_output_file} 以供分析\n")
        finally:
            progress_var.set((i + 1) / total_files * 100)
            window.update_idletasks()

    final_size = get_folder_size(output_folder_path)
    size_difference = final_size - initial_size

    report_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file_path = os.path.join(output_folder_path, f'compression_report_{report_timestamp}.txt')
    with open(report_file_path, 'w', encoding='utf-8') as report_file:
        report_file.write(f"压缩报告 - 时间戳: {report_timestamp}\n")
        report_file.write(f"初始文件夹大小: {initial_size / (1024 * 1024):.2f}MB\n")
        report_file.write(f"最终文件夹大小: {final_size / (1024 * 1024):.2f}MB\n")
        report_file.write(f"节省的空间: {size_difference / (1024 * 1024):.2f}MB\n")
        report_file.write(f"使用的压缩系数: {coefficient}\n")
        report_file.write(f"压缩成功的视频文件数量: {len(secondary_success_files)}\n")
        report_file.write(f"跳过的视频文件数量: {len(skipped_files)}\n")
        report_file.write(f"压缩失败的视频文件数量: {len(failed_files)}\n\n")

        if skipped_files:
            report_file.write("跳过的文件列表:\n")
            for file_path, pix_fmt, codec_name, profile, file_size in skipped_files:
                report_file.write(
                    f"文件名: {os.path.basename(file_path)}, 路径: {file_path}, 像素格式: {pix_fmt}, 编码器: {codec_name}, Profile: {profile}, 文件大小: {file_size:.2f}MB\n")
            report_file.write("\n")

        if failed_files:
            report_file.write("压缩失败的文件列表:\n")
            for file_path, reason in failed_files:
                report_file.write(f"文件名: {os.path.basename(file_path)}, 路径: {file_path}, 原因: {reason}\n")
            report_file.write("\n")

        if secondary_success_files:
            report_file.write("成功的文件列表:\n")
            for file_path, status in secondary_success_files:
                report_file.write(f"文件名: {os.path.basename(file_path)}, 路径: {file_path}, 状态: {status}\n")

    log_text.insert(END, f"已完成所有视频处理任务。\n\n")
    log_text.insert(END, f"详细报告已保存到 {report_file_path}\n\n")
    log_text.see(END)

def process_folder(folder_path, coefficient, use_cpu):
    global stop_processing
    initial_size = get_folder_size(folder_path)
    video_files = []
    skipped_files = []
    failed_files = []
    secondary_success_files = []
    total_files = 0
    checked_files = 0

    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            total_files += 1
            
            # 获取文件扩展名（转换为小写）
            _, ext = os.path.splitext(filename)
            ext = ext.lower()
            
            # 快速过滤常见非视频文件
            if ext in non_video_extensions:
                continue
            
            file_path = os.path.join(root, filename)
            
            # 检查路径是否包含跳过列表中的任何文本
            if any(skip_text in file_path for skip_text in skip_list):
                continue
            
            checked_files += 1
            
            # 使用ffprobe检测文件是否为视频文件
            if is_video_file(file_path):
                video_files.append(file_path)

    total_files = len(video_files)
    log_text.insert(END, f"找到 {total_files} 个视频文件。\n")

    for i, file_path in enumerate(video_files):
        if stop_processing:
            log_text.insert(END, "处理被用户终止\n")
            break

        temp_output_file = ''
        secondary_temp_output_file = ''
        try:
            width, height, pix_fmt, bit_rate, codec_name, profile, fps, overall_bit_rate, audio_bit_rate = get_video_info(
                file_path)
            video_bit_rate = overall_bit_rate - audio_bit_rate / 1_000_000  # Convert to Mbps

            standard_bitrate = calculate_standard_bitrate(width, height, fps, coefficient, pix_fmt)
            full_file_bitrate = standard_bitrate + 0.128  # Add 128kbps for AAC audio
            max_allowed_bitrate = full_file_bitrate * 1.2

            log_text.insert(END,
                            f"\n处理文件: {file_path}, 宽度: {width}p, 高度: {height}p, 帧率: {fps}fps, 视频码率: {video_bit_rate:.2f}Mbps, 全文件码率: {full_file_bitrate:.2f}Mbps, 最大允许码率: {max_allowed_bitrate:.2f}Mbps, 像素格式: {pix_fmt}, 编码器: {codec_name}, Profile: {profile}\n")
            log_text.see(END)

            # Check if the pixel format contains an alpha channel or if it's ProRes 4444
            if has_alpha_channel(pix_fmt, codec_name, profile):
                log_text.insert(END, f"{os.path.basename(file_path)} 包含 alpha 通道或使用 ProRes 4444 编码，跳过处理\n")
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # Convert to MB
                skipped_files.append((file_path, pix_fmt, codec_name, profile, file_size))
                continue

            if video_bit_rate > max_allowed_bitrate:
                target_bitrate = standard_bitrate
                temp_output_file = os.path.join(os.path.dirname(file_path), f'temp_{os.path.basename(file_path)}.mp4')
                compression_successful = compress_video(file_path, temp_output_file, target_bitrate, use_cpu, pix_fmt)

                if compression_successful:
                    replace_with_compressed(file_path, temp_output_file)
                    #log_text.insert(END,
                                    #f"{os.path.basename(file_path)} 已压缩到 {target_bitrate}Mbps 并更新所有副本\n")
                    os.remove(temp_output_file)  # 删除临时文件
                    secondary_success_files.append((file_path, "首次成功"))
                else:
                    failed_files.append((file_path, "首次压缩失败"))

                    # Try secondary compression
                    secondary_temp_output_file = os.path.join(os.path.dirname(file_path),
                                                              f'secondary_temp_{os.path.basename(file_path)}.mp4')
                    secondary_compression_successful = secondary_compress_video(file_path, secondary_temp_output_file, pix_fmt,
                                                                                bitrate=str(target_bitrate) + 'M',
                                                                                use_cpu=use_cpu)

                    if secondary_compression_successful:
                        if is_black_screen_all_frames(secondary_temp_output_file):
                            log_text.insert(END, f"二次压缩后的文件仍然为纯黑，认为是转码失败\n")
                            failed_files.append((file_path, "二次压缩后仍为纯黑"))
                        elif compare_videos(file_path, secondary_temp_output_file):
                            log_text.insert(END, f"二次压缩后的文件与原视频完全一致，认为是转码成功\n\n")
                            replace_with_compressed(file_path, secondary_temp_output_file)
                            #log_text.insert(END, f"{os.path.basename(file_path)} 已通过二次压缩更新所有副本\n")
                            secondary_success_files.append((file_path, "二次成功"))
                            os.remove(secondary_temp_output_file)  # 删除临时文件
                        else:
                            log_text.insert(END, f"二次压缩后的文件与原视频不一致，认为是转码失败\n")
                            failed_files.append((file_path, "二次压缩后不一致"))
                    else:
                        failed_files.append((file_path, "二次压缩失败"))

                    # If secondary compression fails or secondary compressed file does not match original, keep temporary files for analysis
                    if not secondary_compression_successful or not compare_videos(file_path,
                                                                                  secondary_temp_output_file):
                        log_text.insert(END,
                                        f"保留临时文件: {temp_output_file} 和 {secondary_temp_output_file} 以供分析\n")
                    else:
                        os.remove(temp_output_file)  # 删除临时文件
                        os.remove(secondary_temp_output_file)  # 删除临时文件
            else:
                log_text.insert(END, f"{os.path.basename(file_path)} 符合标准码率要求，无需压缩\n")
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # Convert to MB
                skipped_files.append((file_path, pix_fmt, codec_name, profile, file_size))
        except ValueError as ve:
            log_text.insert(END, f"处理文件 {file_path} 时出错: {ve}\n")
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # Convert to MB
            skipped_files.append((file_path, "未知", "未知", "未知", file_size))
            if os.path.exists(temp_output_file):
                log_text.insert(END, f"保留临时文件: {temp_output_file} 以供分析\n")
            if os.path.exists(secondary_temp_output_file):
                log_text.insert(END, f"保留临时文件: {secondary_temp_output_file} 以供分析\n")
        except Exception as e:
            log_text.insert(END, f"处理文件 {file_path} 时出错: {e}\n")
            failed_files.append((file_path, str(e)))
            if os.path.exists(temp_output_file):
                log_text.insert(END, f"保留临时文件: {temp_output_file} 以供分析\n")
            if os.path.exists(secondary_temp_output_file):
                log_text.insert(END, f"保留临时文件: {secondary_temp_output_file} 以供分析\n")
        finally:
            progress_var.set((i + 1) / total_files * 100)
            window.update_idletasks()

    final_size = get_folder_size(folder_path)
    size_difference = final_size - initial_size

    report_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file_path = os.path.join(folder_path, f'compression_report_{report_timestamp}.txt')
    with open(report_file_path, 'w', encoding='utf-8') as report_file:
        report_file.write(f"压缩报告 - 时间戳: {report_timestamp}\n")
        report_file.write(f"初始文件夹大小: {initial_size / (1024 * 1024):.2f}MB\n")
        report_file.write(f"最终文件夹大小: {final_size / (1024 * 1024):.2f}MB\n")
        report_file.write(f"节省的空间: {size_difference / (1024 * 1024):.2f}MB\n")
        report_file.write(f"使用的压缩系数: {coefficient}\n")
        report_file.write(f"是否仅使用CPU: {'是' if use_cpu else '否'}\n")
        report_file.write(f"选择的硬件加速器: {hardware_accelerator.upper() if not use_cpu else 'CPU'}\n")
        report_file.write(f"压缩成功的视频文件数量: {len(secondary_success_files)}\n")
        report_file.write(f"跳过的视频文件数量: {len(skipped_files)}\n")
        report_file.write(f"压缩失败的视频文件数量: {len(failed_files)}\n\n")

        if skipped_files:
            report_file.write("跳过的文件列表:\n")
            for file_path, pix_fmt, codec_name, profile, file_size in skipped_files:
                report_file.write(
                    f"文件名: {os.path.basename(file_path)}, 路径: {file_path}, 像素格式: {pix_fmt}, 编码器: {codec_name}, Profile: {profile}, 文件大小: {file_size:.2f}MB\n")
            report_file.write("\n")

        if failed_files:
            report_file.write("压缩失败的文件列表:\n")
            for file_path, reason in failed_files:
                report_file.write(f"文件名: {os.path.basename(file_path)}, 路径: {file_path}, 原因: {reason}\n")
            report_file.write("\n")

        if secondary_success_files:
            report_file.write("成功的文件列表:\n")
            for file_path, status in secondary_success_files:
                report_file.write(f"文件名: {os.path.basename(file_path)}, 路径: {file_path}, 状态: {status}\n")

    log_text.insert(END, f"已完成所有视频处理任务。\n")
    log_text.insert(END, f"详细报告已保存到 {report_file_path}\n")
    log_text.see(END)


def start_processing():
    global processing_thread, stop_processing
    folder_path = folder_path_entry.get().strip()
    if not os.path.isdir(folder_path):
        messagebox.showerror("错误", "文件夹路径无效")
        return

    try:
        coefficient = float(compression_factor_input.get().strip())
    except ValueError:
        messagebox.showerror("错误", "输入的压缩系数无效，请输入数字")
        return

    use_cpu = cpu_only_checkbox_var.get()

    stop_processing = False
    progress_var.set(0)
    processing_thread = threading.Thread(target=process_folder, args=(folder_path, coefficient, use_cpu))
    processing_thread.start()


def stop_processing_func():
    global stop_processing
    stop_processing = True


def update_bitrates(*args):
    try:
        coefficient = float(compression_factor_input.get().strip())
    except ValueError:
        coefficient = 15.0  # 默认值

    std_bitrate_1080p30 = 1920 * 1080 * 30 / (coefficient * 1000000)
    std_bitrate_4k60 = 3840 * 2160 * 60 / (coefficient * 1000000)

    std_bitrate_label.config(
        text=f"1920x1080@30fps 8bit420 标准码率: {std_bitrate_1080p30:.2f}Mbps\n3840x2160@60fps 8bit420 标准码率: {std_bitrate_4k60:.2f}Mbps")

# 主窗口的一些逻辑
# 转码按钮
def start_transcoding():
    global processing_thread, stop_processing
    folder_path = folder_path_entry.get().strip()
    output_folder_path = output_folder_path_entry.get().strip()

    if not os.path.isdir(folder_path):
        messagebox.showerror("错误", "工作文件夹路径无效")
        return
    if not os.path.isdir(output_folder_path):
        messagebox.showerror("错误", "输出目录路径无效")
        return
    if folder_path == output_folder_path:
        messagebox.showerror("错误", "工作文件夹路径和输出目录路径不能相同，请选择空目录避免错误覆盖")
        return
    try:
        coefficient = float(compression_factor_input.get().strip())
    except ValueError:
        messagebox.showerror("错误", "输入的压缩系数无效，请输入数字")
        return

    use_cpu = cpu_only_checkbox_var.get()

    stop_processing = False
    progress_var.set(0)
    processing_thread = threading.Thread(target=process_folder_with_output, args=(folder_path, output_folder_path, coefficient, use_cpu))
    processing_thread.start()

# 浏览输出文件夹按钮
def browse_output_folder():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        output_folder_path_entry.delete(0, END)
        output_folder_path_entry.insert(0, folder_selected)

# 浏览文件夹按钮
def browse_folder():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        folder_path_entry.delete(0, END)
        folder_path_entry.insert(0, folder_selected)

# 定义超链接
def open_link(event):
    webbrowser.open("https://gitee.com/richkerman/FilmProductionTools/blob/master/README.md")

# 创建主窗口
window = Tk()
window.title("H265视频批量压缩工具 by电不撕")
window.geometry("630x630")  # 调整窗口尺寸以适应新布局

# 设置窗口图标
icon_path = os.path.join(os.path.dirname(__file__), "FPT_favicon.ico")
if os.path.isfile(icon_path):
    window.iconbitmap(icon_path)

# 上方框架（左右分栏）
top_frame = Frame(window)
top_frame.pack(side=TOP, fill=X, padx=10, pady=10)

# 左上方框架
left_upper_frame = Frame(top_frame)
left_upper_frame.pack(side=LEFT, anchor=N, padx=10, pady=10)

# 文件夹路径输入框和浏览按钮
folder_path_label = Label(left_upper_frame, text="工作文件夹路径:")
folder_path_label.pack(pady=5, anchor=W)
folder_path_entry = Entry(left_upper_frame, width=40)
folder_path_entry.pack(pady=5, anchor=W)
browse_button = Button(left_upper_frame, text="浏览处理文件夹", command=browse_folder)
browse_button.pack(pady=5, anchor=W)

# 输出文件夹路径输入框和浏览按钮
output_folder_path_label = Label(left_upper_frame, text="输出目录路径（替换模式不起用）:")
output_folder_path_label.pack(pady=5, anchor=W)
output_folder_path_entry = Entry(left_upper_frame, width=40)
output_folder_path_entry.pack(pady=5, anchor=W)
browse_output_button = Button(left_upper_frame, text="浏览输出文件夹", command=browse_output_folder)
browse_output_button.pack(pady=5, anchor=W)

# 压缩系数输入框和解释文本
global compression_factor_input, std_bitrate_label  # 将这些控件定义为全局变量
compression_factor_label = Label(left_upper_frame, text="压缩系数（默认15）:")
compression_factor_label.pack(pady=5, anchor=CENTER)
compression_factor_input = Entry(left_upper_frame, width=10)
compression_factor_input.insert(0, "15")
compression_factor_input.pack(pady=5, anchor=CENTER)
explanation_label = Label(left_upper_frame,
                          text="默认每15百万个像素将使用1兆比特的空间量压缩存储",
                          wraplength=300, justify=LEFT)
explanation_label.pack(pady=5, anchor=W)
explanation_label = Label(left_upper_frame,
                          text="调整压缩系数可计算高清和4K的目标码率供参考",
                          wraplength=300, justify=LEFT)
explanation_label.pack(pady=5, anchor=CENTER)

# 标准码率显示
std_bitrate_label = Label(left_upper_frame, text="")
std_bitrate_label.pack(pady=5, anchor=CENTER)

# 绑定事件以更新标准比特率显示
compression_factor_input.bind("<KeyRelease>", update_bitrates)

# 右上方框架
right_upper_frame = Frame(top_frame)
right_upper_frame.pack(side=RIGHT, anchor=N, padx=10, pady=10)

# 加载并显示PNG图像
avatar_image_path = os.path.join(os.path.dirname(__file__), "qr", "avatar.png")
try:
    # 使用Pillow加载PNG文件并转换为适合显示的格式
    avatar_image = Image.open(avatar_image_path).resize((128, 128))
    avatar_photo = ImageTk.PhotoImage(avatar_image)
    avatar_label = Label(right_upper_frame, image=avatar_photo)
    avatar_label.image = avatar_photo  # 保持引用，防止垃圾回收
    avatar_label.pack(pady=5, anchor=CENTER)
except IOError:
    print("未能加载avatar.png文件")

# 平台超链接
platform_links = [
    ("快手", "https://v.kuaishou.com/5eo8Cv"),
    ("抖音", "https://v.douyin.com/CeiJMCp3o"),
    ("红书", "https://www.xiaohongshu.com/user/profile/60ed03f7000000000100bf52"),
    ("B站", "https://b23.tv/jITjmL8"),
    ("视频号", "https://gitee.com/richkerman/FilmProductionTools#%E5%85%B3%E6%B3%A8%E6%88%91")
]

def open_link(event, url):
    webbrowser.open(url)

def show_qr_code(label, qr_name):
    try:
        qr_path = os.path.join(os.path.dirname(__file__), "qr", f"{qr_name}.png")
        qr_image = Image.open(qr_path).resize((128, 128))
        qr_photo = ImageTk.PhotoImage(qr_image)
        label.config(image=qr_photo)
        label.image = qr_photo  # 保持引用，防止垃圾回收
    except IOError:
        print(f"未能加载{qr_name}的二维码图片")

def restore_avatar(label):
    label.config(image=avatar_photo)
    label.image = avatar_photo  # 保持引用，防止垃圾回收

link_frame = Frame(right_upper_frame)
link_frame.pack(pady=5, anchor=CENTER)

for platform, url in platform_links:
    link_label = Label(link_frame, text=platform, fg="blue", cursor="hand2")
    link_label.pack(side=LEFT, padx=5)
    link_label.bind("<Button-1>", lambda e, u=url: open_link(e, u))
    link_label.bind("<Enter>", lambda e, l=avatar_label, n=platform: show_qr_code(l, n))
    link_label.bind("<Leave>", lambda e, l=avatar_label: restore_avatar(l))
    link_label.config(font=("TkDefaultFont", 10, "underline"))

# 复选框
replace_hard_links_var = BooleanVar(value=True)
replace_hard_links_checkbox = Checkbutton(right_upper_frame, text="替换所有硬链接（转码模式不起作用）", variable=replace_hard_links_var)
replace_hard_links_checkbox.pack(pady=5, anchor=W)

cpu_only_checkbox_var = BooleanVar(value=False)
cpu_only_checkbox = Checkbutton(right_upper_frame, text="仅使用CPU压缩(没显卡的选)", variable=cpu_only_checkbox_var)
cpu_only_checkbox.pack(pady=5, anchor=W)

# 在全局变量中添加 compress_color 变量
compress_color = BooleanVar(value=True)

# 在 GUI 创建部分添加复选框
compress_color_checkbox = Checkbutton(right_upper_frame, text="压缩色度位深", variable=compress_color)
compress_color_checkbox.pack(pady=5, anchor=W)

# 项目页超链接
project_page_url = "https://gitee.com/richkerman/FilmProductionTools"
project_page_label = Label(right_upper_frame, text="前往项目页", fg="blue", cursor="hand2")
project_page_label.pack(pady=5, anchor=CENTER)
project_page_label.bind("<Button-1>", lambda e, u=project_page_url: open_link(e, u))
project_page_label.config(font=("TkDefaultFont", 10, "underline"))
# 项目页超链接2
project_page_url = "https://gitee.com/richkerman/FilmProductionTools#%E4%B8%BB%E8%A6%81%E9%80%89%E9%A1%B9"
project_page_label = Label(right_upper_frame, text="了解更多关于硬链接和硬件加速选项的说明", fg="blue", cursor="hand2")
project_page_label.pack(pady=5, anchor=CENTER)
project_page_label.bind("<Button-1>", lambda e, u=project_page_url: open_link(e, u))
project_page_label.config(font=("TkDefaultFont", 10, "underline"))

# 按钮
button_frame = Frame(right_upper_frame)
button_frame.pack(pady=5, anchor=CENTER)
execute_button = Button(button_frame, text="转码替换", command=start_processing)
execute_button.pack(side=LEFT, padx=10)
transcode_button = Button(button_frame, text="转码", command=start_transcoding)
transcode_button.pack(side=LEFT, padx=10)
stop_button = Button(button_frame, text="终止", command=stop_processing_func)
stop_button.pack(side=LEFT, padx=10)

# 下方框架
bottom_frame = Frame(window)
bottom_frame.pack(side=BOTTOM, fill=BOTH, expand=True, padx=10, pady=10)

# 进度条
progress_var = DoubleVar()
progress_bar = ttk.Progressbar(bottom_frame, variable=progress_var, maximum=100, length=750)
progress_bar.pack(pady=5)

# 日志显示框
log_text = scrolledtext.ScrolledText(bottom_frame, wrap=WORD, width=90, height=10)
log_text.pack(fill=BOTH, expand=True, pady=5)

# 全局变量
processing_thread = None
stop_processing = False

# 检测硬件加速器
hardware_accelerator = None
if check_nvenc():
    hardware_accelerator = 'nvenc'
elif check_amf():
    hardware_accelerator = 'amf'
elif check_qsv():
    hardware_accelerator = 'qsv'

if hardware_accelerator:
    log_text.insert(END, f"检测到支持的硬件加速器: {hardware_accelerator.upper()}\n")
else:
    log_text.insert(END, "未检测到支持的硬件加速器，将使用CPU进行编码\n")

# 初始化标准比特率显示


# [其余函数如 browse_folder, start_processing, calculate_standard_bitrate 等保持不变]

# 初始化标准比特率显示
update_bitrates()

# 运行主循环
window.mainloop()


