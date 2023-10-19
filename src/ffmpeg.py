import subprocess

def get_length(filepath):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                             "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", filepath],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    return float(result.stdout)

def two_pass_encode(filepath, bitrate, output_filepath):
    # run ffmpeg without window and below normal priority
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    creationflags = subprocess.BELOW_NORMAL_PRIORITY_CLASS

    # pass 1
    subprocess.run(["ffmpeg", "-y", "-i", filepath, "-vcodec", "libvpx-vp9", "-b:v", str(bitrate), "-pass", "1", "-an", "-f", "webm", "-f", "null", "NUL"],
        startupinfo=startupinfo, creationflags=creationflags)
    # pass 2
    subprocess.run(["ffmpeg", "-y", "-i", filepath, "-vcodec", "libvpx-vp9", "-b:v", str(bitrate), "-c:a", "libopus", "-pass", "2", "-f", "webm", output_filepath], 
        startupinfo=startupinfo)