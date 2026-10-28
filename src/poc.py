import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


# Video settings
WIDTH = 480
HEIGHT = 270
SCALE = 4
OUT_W = WIDTH * SCALE
OUT_H = HEIGHT * SCALE
FPS = 30
DURATION = 10
TOTAL_FRAMES = FPS * DURATION

OUTPUT = Path("out/poc.mp4")


def find_ffmpeg():
    """Locate FFmpeg or provide a useful diagnostic error."""
    found = shutil.which("ffmpeg")

    if found:
        return found

    candidates = [
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "/bin/ffmpeg",
        "/opt/homebrew/bin/ffmpeg",
    ]

    for candidate in candidates:
        path = Path(candidate)
        if path.is_file() and os.access(str(path), os.X_OK):
            return str(path)

    print("ERROR: FFmpeg could not be found.", file=sys.stderr)
    print(f"PATH: {os.environ.get('PATH', '')}", file=sys.stderr)
    print("Checked these locations:", file=sys.stderr)

    for candidate in candidates:
        print(f"  {candidate}", file=sys.stderr)

    raise RuntimeError(
        "FFmpeg is unavailable. Check the Install FFmpeg workflow logs."
    )


def make_frame(frame_number):
    """Create a simple pixel-art documentary scene."""
    img = Image.new("RGB", (WIDTH, HEIGHT), (12, 20, 38))
    draw = ImageDraw.Draw(img)

    # Background stars
    for i in range(35):
        x = (i * 71 + 19) % WIDTH
        y = (i * 43 + 13) % HEIGHT
        draw.point((x, y), fill=(80, 105, 137))

    # Header
    draw.rectangle((0, 0, WIDTH, 35), fill=(20, 35, 59))
    draw.text((14, 10), "ECONOMY  /  ARGENTINA", fill=(230, 237, 247))

    # Simplified pixel-art map shape
    map_points = [
        (155, 65), (180, 58), (200, 70), (207, 92),
        (195, 113), (190, 139), (177, 163), (169, 191),
        (156, 216), (146, 197), (151, 174), (141, 153),
        (146, 128), (137, 109), (145, 88)
    ]
    draw.polygon(map_points, fill=(208, 163, 58), outline=(255, 218, 115))

    # Animated glowing embers
    for i in range(18):
        x = (i * 47 + frame_number * (1 + i % 3)) % WIDTH
        y = (i * 31 - frame_number * (1 + i % 2)) % HEIGHT
        size = 2 + (i % 3)
        draw.rectangle(
            (x, y, x + size, y + size),
            fill=(255, 130 + (i % 4) * 20, 45)
        )

    # Chart panel
    panel = (250, 65, 451, 218)
    draw.rectangle(panel, fill=(20, 32, 53), outline=(76, 97, 124))

    draw.text((264, 77), "INFLATION", fill=(226, 234, 244))
    draw.text((264, 94), "INDEX", fill=(145, 163, 187))

    # Chart grid
    for y in (126, 153, 180, 205):
        draw.line((264, y, 437, y), fill=(47, 62, 83), width=1)

    # Animated rising chart
    chart_points = []
    for i in range(9):
        x = 267 + i * 20
        base_y = 198 - i * 8
        wave = int(4 * np.sin((frame_number / FPS) + i))
        y = max(119, min(203, base_y + wave))
        chart_points.append((x, y))

    draw.line(chart_points, fill=(255, 190, 65), width=3)

    for x, y in chart_points:
        draw.rectangle((x - 2, y - 2, x + 2, y + 2), fill=(255, 225, 140))

    # Bottom caption
    draw.rectangle((0, 238, WIDTH, HEIGHT), fill=(20, 31, 49))
    draw.text(
        (14, 247),
        "A COUNTRY UNDER ECONOMIC PRESSURE",
        fill=(238, 240, 245)
    )

    # Progress indicator
    progress = frame_number / max(TOTAL_FRAMES - 1, 1)
    draw.rectangle((0, 266, WIDTH, 270), fill=(44, 57, 76))
    draw.rectangle((0, 266, int(WIDTH * progress), 270), fill=(245, 183, 55))

    # Upscale with nearest-neighbor to preserve pixel-art style
    img = img.resize(
        (OUT_W, OUT_H),
        Image.Resampling.NEAREST
    )

    return img


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg_path = find_ffmpeg()

    print(f"Using FFmpeg: {ffmpeg_path}")

    version = subprocess.run(
        [ffmpeg_path, "-version"],
        capture_output=True,
        text=True,
        check=True
    )
    print(version.stdout.splitlines()[0])

    command = [
        ffmpeg_path,
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{OUT_W}x{OUT_H}",
        "-r", str(FPS),
        "-i", "-",
        "-an",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(OUTPUT),
    ]

    print("Starting 10-second video render...")

    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE
    )

    try:
        for frame_number in range(TOTAL_FRAMES):
            frame = make_frame(frame_number)
            process.stdin.write(
                np.asarray(frame, dtype=np.uint8).tobytes()
            )

            if (frame_number + 1) % FPS == 0:
                print(
                    f"Rendered {frame_number + 1}/{TOTAL_FRAMES} frames"
                )

        process.stdin.close()
        return_code = process.wait()

        if return_code != 0:
            raise RuntimeError(
                f"FFmpeg exited with code {return_code}."
            )

    except Exception:
        if process.poll() is None:
            process.kill()
            process.wait()
        raise

    if not OUTPUT.is_file() or OUTPUT.stat().st_size == 0:
        raise RuntimeError("Render finished, but the MP4 file is missing.")

    print(f"SUCCESS: Video created at {OUTPUT}")
    print(f"File size: {OUTPUT.stat().st_size} bytes")


if __name__ == "__main__":
    main()
            
