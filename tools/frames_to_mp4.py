"""캡처한 화면(파일 이름 = 시작 후 ms)을 실제 시간 간격 그대로 mp4로 잇는다.

    python tools/frames_to_mp4.py <프레임 폴더> <출력.mp4>
"""
import os
import subprocess
import sys

src, out = sys.argv[1], sys.argv[2]
frames = sorted(f for f in os.listdir(src) if f.endswith(".jpg"))
times = [int(f[:-4]) for f in frames]
lst = os.path.join(src, "list.txt")
with open(lst, "w", encoding="utf-8") as fh:
    for i, f in enumerate(frames):
        dur = ((times[i + 1] - times[i]) if i + 1 < len(frames) else 1000) / 1000
        fh.write(f"file '{f}'\nduration {dur:.3f}\n")
    fh.write(f"file '{frames[-1]}'\n")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-vf", "fps=20,format=yuv420p",
                "-c:v", "libx264", "-crf", "22", "-preset", "medium", "-movflags", "+faststart", out], check=True)
print(out, len(frames), "frames", round(times[-1] / 1000), "s", os.path.getsize(out) // 1024, "KB")
