import os
import subprocess
from tqdm import tqdm
import ffmpeg
from datetime import datetime
import shutil
import cv2


def get_video_info(file_path):
    try:
        probe = ffmpeg.probe(file_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        if not video_stream:
            raise ValueError("No video stream found")

        width = int(video_stream.get('width', 0))
        height = int(video_stream.get('height', 0))
        pix_fmt = video_stream.get('pix_fmt', 'unknown')
        bit_rate = int(video_stream.get('bit_rate', 0))
        codec_name = video_stream.get('codec_name', 'unknown')
        profile = video_stream.get('profile', 'unknown')
        fps = float(video_stream.get('avg_frame_rate', '30/1').split('/')[0]) / float(
            video_stream.get('avg_frame_rate', '30/1').split('/')[1])

        return width, height, pix_fmt, bit_rate, codec_name, profile, fps
    except ffmpeg.Error as e:
        print(f"FFmpeg Error: {e.stderr.decode()}")
        raise ValueError(f"无法解析视频信息: {e.stderr.decode()}") from e
    except Exception as e:
        print(f"General Error: {str(e)}")
        raise ValueError(f"无法获取视频信息: {str(e)}") from e


def has_alpha_channel(pix_fmt, codec_name, profile):
    alpha_keywords = ['rgba', 'argb', 'abgr', 'bgra', 'gbrap', 'gbrap10le', 'gbrap12le', 'yuva']
    prores_4444_profiles = ['4444']

    if any(alpha_keyword in pix_fmt for alpha_keyword in alpha_keywords):
        return True
    if codec_name == 'prores' and profile in prores_4444_profiles:
        return True
    return False


def calculate_target_bitrate(width, height, fps, compression_factor):
    pixels_per_second = width * height * fps
    target_bitrate = (pixels_per_second // compression_factor) + 1  # Ensure at least 1 Mbps
    return max(target_bitrate, 1)  # Minimum bitrate is 1 Mbps


def compress_video(input_file, output_file, target_bitrate):
    print(f"开始压缩 {input_file} 到 {output_file}，目标码率: {target_bitrate}Mbps")
    command = [
        'ffmpeg', '-hwaccel', 'cuvid', '-i', input_file,
        '-c:v', 'hevc_nvenc', '-preset', 'fast', '-crf', '28',
        '-b:v', f'{target_bitrate}M', '-c:a', 'aac', '-b:a', '192k',
        '-gpu', '0', output_file
    ]
    with open(os.devnull, 'w') as devnull:
        result = subprocess.run(command, stdout=devnull, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(f"压缩失败: {result.stderr.decode()}")
        return False
    if os.path.getsize(output_file) == 0:
        print(f"生成的文件大小为 0KB，跳过替换")
        return False

    # Check if the compressed file has a valid video stream
    try:
        probe = ffmpeg.probe(output_file)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        if not video_stream:
            print(f"压缩后的文件没有有效的视频轨道，跳过替换")
            return False

        # Check for black screen by analyzing all frames
        if is_black_screen_all_frames(output_file):
            print(f"压缩后的文件包含纯黑帧，检查原视频是否也为纯黑")
            if is_black_screen_all_frames(input_file):
                print(f"原视频也是纯黑视频，不认为是转码失败")
                return True
            else:
                print(f"原视频不是纯黑视频，认为是转码失败")
                return False
    except ffmpeg.Error as e:
        print(f"无法解析压缩后的视频信息: {e.stderr.decode()}")
        return False

    print(f"完成压缩 {input_file} 到 {output_file}")
    return True


def replace_with_compressed(input_file, compressed_file):
    # Update the original file with the contents of the compressed file
    with open(compressed_file, 'rb') as src:
        with open(input_file, 'wb') as dst:
            shutil.copyfileobj(src, dst)
    # Update the modification time to match the compressed file
    stat = os.stat(compressed_file)
    os.utime(input_file, (stat.st_atime, stat.st_mtime))


def is_black_screen_all_frames(video_file):
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        print(f"无法打开视频文件: {video_file}")
        return True

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if frame_count == 0:
        print(f"视频文件帧数为 0: {video_file}")
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
            print(f"已检查 {frame_index}/{frame_count} 帧", end='\r')

    cap.release()
    print(f"已检查所有 {frame_count} 帧")
    return all_black


def is_frame_black(frame):
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mean_intensity = cv2.mean(gray_frame)[0]
    return mean_intensity < 10  # Adjust threshold as needed


def are_frames_identical(frame1, frame2):
    return cv2.norm(frame1, frame2, cv2.NORM_L2) == 0


def secondary_compress_video(input_file, output_file, bitrate='5M'):
    print(f"尝试使用系统 FFmpeg 进行二次压缩 {input_file} 到 {output_file}，目标码率: {bitrate}Mbps")
    cmd = [
        'ffmpeg',
        '-i', input_file,  # Input file
        '-c:v', 'libx265',  # Video codec
        '-b:v', bitrate,  # Video bitrate
        '-c:a', 'copy',  # Copy the original audio stream without re-encoding
        '-preset', 'medium',  # Encoding speed/quality trade-off
        '-x265-params', 'crf=28',  # Quality setting for x265 (lower is better quality)
        output_file  # Output file
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"二次压缩完成. 输出保存到 {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"二次压缩时出错: {e}")
        return False


def compare_videos(video1, video2):
    cap1 = cv2.VideoCapture(video1)
    cap2 = cv2.VideoCapture(video2)

    if not cap1.isOpened() or not cap2.isOpened():
        print("无法打开其中一个视频文件")
        return False

    fps1 = cap1.get(cv2.CAP_PROP_FPS)
    fps2 = cap2.get(cv2.CAP_PROP_FPS)
    if fps1 != fps2:
        print("两个视频的帧率不同")
        return False

    frame_count1 = int(cap1.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_count2 = int(cap2.get(cv2.CAP_PROP_FRAME_COUNT))
    if frame_count1 != frame_count2:
        print("两个视频的帧数不同")
        return False

    frame_index = 0
    while True:
        ret1, frame1 = cap1.read()
        ret2, frame2 = cap2.read()

        if not ret1 or not ret2:
            break

        if not are_frames_identical(frame1, frame2):
            print(f"帧 {frame_index} 不相同")
            return False

        frame_index += 1
        if frame_index % 100 == 0:  # 每处理100帧打印一次进度
            print(f"已比较 {frame_index}/{frame_count1} 帧", end='\r')

    cap1.release()
    cap2.release()
    print(f"已比较所有 {frame_count1} 帧")
    return True


def process_folder(folder_path, compression_factor):
    supported_extensions = (
    '.mp4', '.mkv', '.avi', '.m4v', '.mpg', '.mts', '.ts', '.mov', '.mxf', '.webm', '.flv', '.f4v', '.wmv')
    video_files = []
    skipped_files = []
    failed_files = []
    secondary_success_files = []

    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            if filename.lower().endswith(supported_extensions):
                video_files.append(os.path.join(root, filename))

    total_files = len(video_files)
    print(f"找到 {total_files} 个视频文件。")

    with tqdm(total=total_files, desc="处理视频", unit="file") as pbar:
        for file_path in video_files:
            temp_output_file = ''
            secondary_temp_output_file = ''
            try:
                width, height, pix_fmt, bit_rate, codec_name, profile, fps = get_video_info(file_path)
                bitrate = bit_rate / 1000000  # Convert to Mbps

                print(
                    f"\n处理文件: {file_path}, 宽度: {width}p, 高度: {height}p, 码率: {bitrate:.2f}Mbps, 像素格式: {pix_fmt}, 编码器: {codec_name}, Profile: {profile}, 帧率: {fps}fps")

                # Calculate target bitrate based on resolution and frame rate
                target_bitrate = calculate_target_bitrate(width, height, fps, compression_factor)
                standard_bitrate = target_bitrate * 1.2  # 120% of the calculated target bitrate

                # Check if the pixel format contains an alpha channel or if it's ProRes 4444
                if has_alpha_channel(pix_fmt, codec_name, profile):
                    print(f"{os.path.basename(file_path)} 包含 alpha 通道或使用 ProRes 4444 编码，跳过处理")
                    file_size = os.path.getsize(file_path) / (1024 * 1024)  # Convert to MB
                    skipped_files.append((file_path, pix_fmt, codec_name, profile, file_size))
                    continue

                print(f"计算的目标码率为: {target_bitrate}Mbps, 标准码率为: {standard_bitrate}Mbps")

                if bitrate > standard_bitrate:
                    temp_output_file = os.path.join(os.path.dirname(file_path),
                                                    f'temp_{os.path.basename(file_path)}.mp4')
                    compression_successful = compress_video(file_path, temp_output_file, target_bitrate)

                    if compression_successful:
                        replace_with_compressed(file_path, temp_output_file)
                        print(f"{os.path.basename(file_path)} 已压缩到 {target_bitrate}Mbps 并更新所有副本")
                        os.remove(temp_output_file)  # 删除临时文件
                    else:
                        failed_files.append((file_path, "首次压缩失败"))

                        # 尝试二次压缩
                        secondary_temp_output_file = os.path.join(os.path.dirname(file_path),
                                                                  f'secondary_temp_{os.path.basename(file_path)}.mp4')
                        secondary_compression_successful = secondary_compress_video(file_path,
                                                                                    secondary_temp_output_file,
                                                                                    bitrate=f'{target_bitrate}M')

                        if secondary_compression_successful:
                            if is_black_screen_all_frames(secondary_temp_output_file):
                                print(f"二次压缩后的文件仍然为纯黑，认为是转码失败")
                                failed_files.append((file_path, "二次压缩后仍为纯黑"))
                            elif compare_videos(file_path, secondary_temp_output_file):
                                print(f"二次压缩后的文件与原视频完全一致，认为是转码成功")
                                replace_with_compressed(file_path, secondary_temp_output_file)
                                print(f"{os.path.basename(file_path)} 已通过二次压缩更新所有副本")
                                secondary_success_files.append((file_path, "二次成功"))
                                os.remove(temp_output_file)  # 删除首次压缩的临时文件
                                os.remove(secondary_temp_output_file)  # 删除二次压缩的临时文件
                            else:
                                print(f"二次压缩后的文件与原视频不一致，认为是转码失败")
                                failed_files.append((file_path, "二次压缩后不一致"))
                        else:
                            failed_files.append((file_path, "二次压缩失败"))

                        # 如果二次压缩失败或二次压缩后不一致，保留临时文件
                        if not secondary_compression_successful or not compare_videos(file_path,
                                                                                      secondary_temp_output_file):
                            print(f"保留临时文件: {temp_output_file} 和 {secondary_temp_output_file} 以供分析")
                else:
                    print(f"{os.path.basename(file_path)} 不符合压缩条件")
            except ValueError as ve:
                print(f"处理文件 {file_path} 时出错: {ve}")
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # Convert to MB
                skipped_files.append((file_path, "未知", "未知", "未知", file_size))
                if os.path.exists(temp_output_file):
                    print(f"保留临时文件: {temp_output_file} 以供分析")
                if os.path.exists(secondary_temp_output_file):
                    print(f"保留临时文件: {secondary_temp_output_file} 以供分析")
            except Exception as e:
                print(f"处理文件 {file_path} 时出错: {e}")
                failed_files.append((file_path, str(e)))
                if os.path.exists(temp_output_file):
                    print(f"保留临时文件: {temp_output_file} 以供分析")
                if os.path.exists(secondary_temp_output_file):
                    print(f"保留临时文件: {secondary_temp_output_file} 以供分析")
            finally:
                pbar.update(1)

    # Save skipped files information to a text file
    if skipped_files:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        skipped_file_path = os.path.join(folder_path, f'skipped_files_{timestamp}.txt')
        with open(skipped_file_path, 'w', encoding='utf-8') as skipped_file:
            for file_path, pix_fmt, codec_name, profile, file_size in skipped_files:
                skipped_file.write(
                    f"文件名: {os.path.basename(file_path)}, 路径: {file_path}, 像素格式: {pix_fmt}, 编码器: {codec_name}, Profile: {profile}, 文件大小: {file_size:.2f}MB\n")
        print(f"已保存跳过的文件信息到 {skipped_file_path}")

    # Save failed files information to a text file
    if failed_files:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        failed_file_path = os.path.join(folder_path, f'failed_files_{timestamp}.txt')
        with open(failed_file_path, 'w', encoding='utf-8') as failed_file:
            for file_path, reason in failed_files:
                failed_file.write(f"文件名: {os.path.basename(file_path)}, 路径: {file_path}, 原因: {reason}\n")
        print(f"已保存失败的文件信息到 {failed_file_path}")

    # Save secondary success files information to a text file
    if secondary_success_files:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        secondary_success_file_path = os.path.join(folder_path, f'secondary_success_files_{timestamp}.txt')
        with open(secondary_success_file_path, 'w', encoding='utf-8') as secondary_success_file:
            for file_path, status in secondary_success_files:
                secondary_success_file.write(
                    f"文件名: {os.path.basename(file_path)}, 路径: {file_path}, 状态: {status}\n")
        print(f"已保存二次成功的文件信息到 {secondary_success_file_path}")


def main():
    folder_path = input("请输入工作文件夹路径: ")
    if not os.path.isdir(folder_path):
        print("文件夹路径无效")
        return

    default_compression_factor = 15
    compression_factor_input = input(
        f"请输入压缩系数（默认值为{default_compression_factor}兆，默认情况下每15兆的像素将使用1兆比特的数据量存储；例如：一个4K60帧视频在压缩系数15兆的编码下标准码率为34Mbps；一个1080p30帧视频在压缩系数15兆的编码下标准码率为5Mbps）: ").strip()

    if not compression_factor_input:
        compression_factor = default_compression_factor
    else:
        try:
            compression_factor = float(compression_factor_input) * 1000000
            if compression_factor <= 0:
                raise ValueError("压缩系数必须大于0")
        except ValueError as e:
            print(f"输入的压缩系数无效: {e}")
            return

    process_folder(folder_path, compression_factor)


if __name__ == "__main__":
    main()



