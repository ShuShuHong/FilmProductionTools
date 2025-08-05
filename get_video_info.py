import ffmpeg
import json


def get_video_info(file_path):
    try:
        # 使用探针功能来获取媒体信息
        probe = ffmpeg.probe(file_path)

        # 将探针结果转换为JSON字符串并解析为Python对象
        info = json.loads(json.dumps(probe))

        return info
    except ffmpeg.Error as e:
        print(f"Error: {e.stderr.decode('utf-8')}")
        return None


if __name__ == "__main__":
    # 提示用户输入视频文件路径
    video_file_path = input("请输入视频文件路径: ").strip()

    if not video_file_path:
        print("错误：未提供有效的视频文件路径。")
        exit(1)

    video_info = get_video_info(video_file_path)

    if video_info:
        # 打印所有获取到的视频信息
        print(json.dumps(video_info, indent=4))