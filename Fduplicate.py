import os
import ffmpeg
import cv2
import numpy as np


def get_video_info(file_path):
    """使用ffmpeg-python获取视频时长和帧率，增加probesize和analyzeduration避免章节错误"""
    try:
        probe = ffmpeg.probe(
            file_path,
            v='error',
            select_streams='v:0',
            show_entries='stream=duration,r_frame_rate,width,height',
            proberesize=5000000,  # 增加probesize值
            analyzeduration=1000000  # 增加analyzeduration值
        )
        duration = float(probe['streams'][0]['duration'])
        frame_rate = probe['streams'][0]['r_frame_rate']
        frame_rate = eval(frame_rate)  # 将帧率字符串转化为浮动值，如"30/1"转换为30
        return duration, frame_rate
    except ffmpeg.Error as e:
        print(f"FFmpeg error while probing file {file_path}: {e}")
        return None, None



def compare_frames(frame1, frame2):
    """计算两帧的差异，返回差异度"""
    return np.sum(np.abs(frame1 - frame2))


def compare_videos(video1, video2):
    """使用OpenCV比较两个视频的每一帧，判断是否相同"""
    cap1 = cv2.VideoCapture(video1)
    cap2 = cv2.VideoCapture(video2)

    # 检查视频的基本属性是否相同
    if cap1.get(cv2.CAP_PROP_FPS) != cap2.get(cv2.CAP_PROP_FPS):
        cap1.release()
        cap2.release()
        return False

    while True:
        ret1, frame1 = cap1.read()
        ret2, frame2 = cap2.read()

        if not ret1 or not ret2:
            break

        # Resize frames to a standard size for comparison
        frame1 = cv2.resize(frame1, (640, 360))
        frame2 = cv2.resize(frame2, (640, 360))

        # Compare the frames
        if compare_frames(frame1, frame2) > 1000:  # 如果差异超过阈值，则认为视频不同
            cap1.release()
            cap2.release()
            return False

    cap1.release()
    cap2.release()
    return True


def find_duplicate_videos(directory):
    """在目录中查找重复的视频文件，包括子文件夹"""
    video_files = []
    for root, dirs, files in os.walk(directory):  # 使用os.walk递归遍历子文件夹
        for file in files:
            if file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                video_files.append(os.path.join(root, file))

    duplicates = []

    # 遍历所有视频文件，逐一比较
    for i in range(len(video_files)):
        for j in range(i + 1, len(video_files)):
            video1_path = video_files[i]
            video2_path = video_files[j]

            # 获取视频信息
            duration1, frame_rate1 = get_video_info(video1_path)
            duration2, frame_rate2 = get_video_info(video2_path)

            # 检查时长和帧率是否完全相同
            if duration1 == duration2 and frame_rate1 == frame_rate2:
                # 如果基本信息相同，进一步检查视频内容是否相同
                if compare_videos(video1_path, video2_path):
                    duplicates.append((video_files[i], video_files[j]))

    return duplicates


def save_duplicates_to_file(duplicates, output_file):
    """将重复视频文件信息保存到.txt文件中"""
    with open(output_file, 'w') as f:
        for dup in duplicates:
            f.write(f"重复文件: {dup[0]} 和 {dup[1]}\n")


def main():
    # 使用input获取命令行输入的文件夹路径
    directory = input("请输入视频文件夹的路径: ")

    if not os.path.isdir(directory):
        print(f"错误: 目录 '{directory}' 不存在或无法访问")
        return

    duplicates = find_duplicate_videos(directory)

    # 如果有重复视频，保存到文本文件
    if duplicates:
        save_duplicates_to_file(duplicates, os.path.join(directory, 'duplicates.txt'))
        print("重复视频信息已保存到 duplicates.txt")
    else:
        print("没有找到重复视频")


if __name__ == "__main__":
    main()
