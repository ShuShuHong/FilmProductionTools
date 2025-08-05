import ffmpeg


def get_video_info(file_path):
    try:
        # 使用 ffmpeg.probe 获取视频文件的详细信息
        probe = ffmpeg.probe(file_path, v='error',
                             show_entries='stream=codec_name,codec_type,width,height,bit_rate,avg_frame_rate,duration')

        # 打印所有的流信息
        for stream in probe['streams']:
            print(f"Stream codec: {stream.get('codec_name', 'N/A')}")
            print(f"Stream type: {stream.get('codec_type', 'N/A')}")
            print(f"Width: {stream.get('width', 'N/A')}")
            print(f"Height: {stream.get('height', 'N/A')}")
            print(f"Bit rate: {stream.get('bit_rate', 'N/A')}")
            print(f"Average frame rate: {stream.get('avg_frame_rate', 'N/A')}")
            print(f"Duration: {stream.get('duration', 'N/A')}")
            print('-' * 40)

        # 总视频时长
        print(f"Total duration: {probe.get('format', {}).get('duration', 'N/A')} seconds")

    except ffmpeg.Error as e:
        print(f"Error: {e}")


# 主程序：让用户在命令行输入文件路径
file_path = input("请输入视频文件的路径：").strip()

# 检查用户输入是否为空
if file_path:
    get_video_info(file_path)
else:
    print("没有输入文件路径！")
