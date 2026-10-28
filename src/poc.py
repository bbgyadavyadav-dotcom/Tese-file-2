
"""10-second pixel-art video proof of concept."""
import math
import os
import random
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFont

W, H = 480, 270
OUT_W, OUT_H = 1920, 1080
FPS = 30
DURATION = 10
TOTAL = FPS * DURATION
OUT_PATH = "out/poc.mp4"

random.seed(7)
font = ImageFont.load_default()


def clamp(x):
    return max(0.0, min(1.0, x))


def ease(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def inside(poly, x, y):
    ok = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            ok = not ok
        j = i
    return ok


SOUTH_AMERICA = [(120, 150), (165, 145), (190, 170), (180, 215), (160, 255), (148, 235), (138, 190)]
ARGENTINA = [(140, 185), (178, 185), (172, 225), (160, 255), (148, 235)]
AFRICA = [(225, 130), (265, 125), (280, 170), (262, 215), (240, 205), (222, 165)]
EUROPE = [(215, 60), (245, 50), (275, 62), (285, 85), (270, 105), (245, 112), (222, 100), (208, 80)]

SEA = (10, 16, 36)
LAND = (38, 48, 72)
GOLD = (232, 180, 60)
EMBER = (255, 90, 30)

particles = []
for _ in range(2000):
    x, y = random.randint(135, 185), random.randint(183, 256)
    if inside(ARGENTINA, x, y) and len(particles) < 260:
        particles.append({
            "x": x, "y": y,
            "vx": random.uniform(-0.2, 1.1),
            "vy": random.uniform(-1.3, -0.3),
            "delay": random.uniform(0, 1.2),
        })

embers = [
    (random.randint(205, 290), random.randint(45, 115), random.random())
    for _ in range(90)
]


def caption(d, text, alpha=1.0):
    c = mix((0, 0, 0), (240, 240, 240), alpha)
    d.rectangle([0, H - 26, W, H], fill=(0, 0, 0))
    tw = d.textlength(text, font=font)
    d.text(((W - tw) / 2, H - 19), text, font=font, fill=c)


def draw_map(d, t):
    for y in range(0, H, 6):
        d.rectangle([0, y, W, y + 5], fill=mix(SEA, (16, 24, 52), y / H))

    d.polygon(SOUTH_AMERICA, fill=LAND)
    d.polygon(AFRICA, fill=LAND)

    pulse = 0.5 + 0.5 * math.sin(t * 4)
    d.polygon(
        EUROPE,
        fill=mix((150, 40, 20), EMBER, 0.4 + 0.4 * pulse)
    )

    for ex, ey, ph in embers:
        yy = ey - ((t * 14 + ph * 40) % 40)
        if inside(EUROPE, ex, ey):
            d.point((ex, int(yy)), fill=(255, 190, 80))

    fade = ease((t - 4.0) / 2.0)
    shimmer = 0.85 + 0.15 * math.sin(t * 6)
    d.polygon(
        ARGENTINA,
        fill=mix(mix((150, 110, 30), GOLD, shimmer), LAND, fade)
    )

    if t >= 4.0:
        for p in particles:
            lt = max(0.0, t - 4.0 - p["delay"])
            if lt <= 0:
                continue
            px = p["x"] + p["vx"] * lt * 25
            py = p["y"] + p["vy"] * lt * 25
            life = 1 - clamp(lt / 2.2)
            if life > 0:
                d.point(
                    (int(px), int(py)),
                    fill=mix(SEA, GOLD, life)
                )


def draw_chart(d, t):
    d.rectangle([0, 0, W, H], fill=(12, 14, 28))
    x0, y0, x1, y1 = 60, 40, 440, 215
    d.line([x0, y0, x0, y1], fill=(120, 130, 160))
    d.line([x0, y1, x1, y1], fill=(120, 130, 160))

    d.text(
        (x0, 22),
        "INFLATION (ILLUSTRATIVE - NOT REAL DATA)",
        font=font,
        fill=(255, 200, 90)
    )

    prog = ease((t - 7.0) / 2.6)
    n = int(120 * prog)
    pts = []

    for i in range(n + 1):
        u = i / 120
        val = (math.exp(4.2 * u) - 1) / (math.exp(4.2) - 1)
        pts.append((
            x0 + u * (x1 - x0),
            y1 - val * (y1 - y0 - 10)
        ))

    if len(pts) > 1:
        d.line(pts, fill=(255, 80, 60), width=2)
        d.rectangle(
            [
                pts[-1][0] - 2, pts[-1][1] - 2,
                pts[-1][0] + 2, pts[-1][1] + 2
            ],
            fill=(255, 230, 120)
        )


def make_frame(i):
    t = i / FPS
    img = Image.new("RGB", (W, H), SEA)
    d = ImageDraw.Draw(img)

    if t < 7.0:
        draw_map(d, t)
        if t < 4.0:
            caption(d, "Imagine kijiye ek aisa desh, jo 1940s mein ameer tha...")
        else:
            caption(d, "Aaj ye desh inflation aur debt se lad raha hai.")
    else:
        draw_chart(d, t)
        caption(d, "Ye kahani hai Argentina ki.")

    f = min(clamp(t / 0.5), clamp((DURATION - t) / 0.5))
    if f < 1:
        img = Image.blend(
            Image.new("RGB", (W, H), (0, 0, 0)),
            img,
            f
        )

    return img


def main():
    os.makedirs("out", exist_ok=True)

    # Find FFmpeg executable explicitly.
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise RuntimeError(
            "FFmpeg is missing from PATH. Check the Install FFmpeg workflow step."
        )

    cmd = [
        ffmpeg_path, "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{OUT_W}x{OUT_H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "18", "-preset", "veryfast", OUT_PATH,
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    try:
        for i in range(TOTAL):
            frame = make_frame(i).resize(
                (OUT_W, OUT_H),
                Image.Resampling.NEAREST
            )
            proc.stdin.write(frame.tobytes())
    except Exception:
        proc.stdin.close()
        proc.kill()
        proc.wait()
        raise
    else:
        proc.stdin.close()

    code = proc.wait()
    if code != 0:
        raise SystemExit(f"FFmpeg failed with exit code {code}")

    print(f"Wrote {OUT_PATH} ({TOTAL} frames)")


if __name__ == "__main__":
    main()
