"""
生成 devil_eye 壁纸 (PNG)
纯黑底 + 金色等腰三角 + 眼 + 裂纹
产生三种分辨率: 3840x2160, 2560x1440, 1920x1080
"""
import math
from pathlib import Path
from PIL import Image, ImageDraw

# 颜色
BLACK = (10, 10, 15, 255)
GOLD = (196, 163, 90, 255)
GOLD_DIM = (196, 163, 90, 100)
GOLD_FAINT = (196, 163, 90, 40)

RESOLUTIONS = [
    (3840, 2160, "3840x2160"),
    (2560, 1440, "2560x1440"),
    (1920, 1080, "1920x1080"),
]

OUT_DIR = Path(__file__).parent


def generate_wallpaper(width: int, height: int, label: str):
    """生成指定分辨率的壁纸"""
    img = Image.new("RGBA", (width, height), BLACK)
    draw = ImageDraw.Draw(img)

    # 三角形中心及尺寸（基于高度缩放）
    scale = height / 2000.0
    tri_h = 700 * scale
    tri_base = 600 * scale
    tri_top_y = height * 0.35
    tri_bottom_y = tri_top_y + tri_h

    left_x = width / 2 - tri_base / 2
    right_x = width / 2 + tri_base / 2
    top_x = width / 2

    # 外三角 (8px stroke)
    draw.polygon(
        [(top_x, tri_top_y), (right_x, tri_bottom_y), (left_x, tri_bottom_y)],
        fill=None, outline=GOLD,
        width=max(3, int(8 * scale))
    )

    # 内层三角 (2px, 40% opacity)
    inset1 = 25 * scale
    draw.polygon(
        [(top_x, tri_top_y + inset1), (right_x - inset1 * 0.8, tri_bottom_y - inset1),
         (left_x + inset1 * 0.8, tri_bottom_y - inset1)],
        fill=None, outline=GOLD_DIM,
        width=max(1, int(2 * scale))
    )

    # 最内层三角 (0.5px, 20% opacity)
    inset2 = 45 * scale
    draw.polygon(
        [(top_x, tri_top_y + inset2), (right_x - inset2 * 0.8, tri_bottom_y - inset2),
         (left_x + inset2 * 0.8, tri_bottom_y - inset2)],
        fill=None, outline=GOLD_FAINT,
        width=1
    )

    # 眼 - 杏仁状
    eye_cx = width / 2 + 30 * scale
    eye_cy = tri_top_y + tri_h / 2 + 15 * scale
    eye_w = 240 * scale
    eye_h_top = 200 * scale
    eye_h_bottom = 160 * scale

    # 上弧线
    draw.arc(
        [eye_cx - eye_w / 2, eye_cy - eye_h_top,
         eye_cx + eye_w / 2, eye_cy + eye_h_top],
        180, 360, fill=GOLD, width=max(2, int(5 * scale))
    )
    # 下弧线
    draw.arc(
        [eye_cx - eye_w / 2, eye_cy - eye_h_bottom,
         eye_cx + eye_w / 2, eye_cy + eye_h_bottom],
        0, 180, fill=GOLD, width=max(2, int(5 * scale))
    )

    # 瞳孔 (实心圆, 偏离中心 = unsettled)
    pupil_r_outer = int(44 * scale)
    pupil_r_inner = int(26 * scale)
    pupil_glint_r = int(8 * scale)

    draw.ellipse(
        [eye_cx + int(12 * scale) - pupil_r_outer, eye_cy - int(15 * scale) - pupil_r_outer,
         eye_cx + int(12 * scale) + pupil_r_outer, eye_cy - int(15 * scale) + pupil_r_outer],
        fill=GOLD
    )
    draw.ellipse(
        [eye_cx + int(12 * scale) - pupil_r_inner, eye_cy - int(15 * scale) - pupil_r_inner,
         eye_cx + int(12 * scale) + pupil_r_inner, eye_cy - int(15 * scale) + pupil_r_inner],
        fill=BLACK
    )
    draw.ellipse(
        [eye_cx + int(17 * scale) - pupil_glint_r, eye_cy - int(19 * scale) - pupil_glint_r,
         eye_cx + int(17 * scale) + pupil_glint_r, eye_cy - int(19 * scale) + pupil_glint_r],
        fill=(*GOLD[:3], 150)
    )

    # 裂纹 - 折线
    crack_points = [
        (eye_cx + 130 * scale, eye_cy + 50 * scale),
        (eye_cx + 85 * scale, eye_cy + 20 * scale),
        (eye_cx + 115 * scale, eye_cy - 15 * scale),
        (eye_cx + 70 * scale, eye_cy - 45 * scale),
        (eye_cx + 110 * scale, eye_cy - 85 * scale),
    ]
    for i in range(len(crack_points) - 1):
        draw.line(
            [crack_points[i], crack_points[i + 1]],
            fill=GOLD, width=max(1, int(3 * scale))
        )

    # 裂纹分支
    draw.line(
        [crack_points[2],
         (eye_cx + 155 * scale, eye_cy - 25 * scale)],
        fill=GOLD, width=max(1, int(1.5 * scale))
    )

    # 裂纹三角碎片
    frag_cx = eye_cx + 80 * scale
    frag_cy = eye_cy + 15 * scale
    frag_size = 12 * scale
    draw.polygon(
        [(frag_cx, frag_cy - frag_size),
         (frag_cx + frag_size, frag_cy),
         (frag_cx, frag_cy + frag_size)],
        fill=(*GOLD[:3], 80)
    )

    # 底部金色窄条
    bar_y = tri_bottom_y - 35 * scale
    bar_w = 55 * scale
    bar_h = 10 * scale
    draw.rectangle(
        [width / 2 - bar_w / 2, bar_y,
         width / 2 + bar_w / 2, bar_y + bar_h],
        fill=(*GOLD[:3], 100)
    )

    # 三角顶点强调线
    accent_len = 12 * scale
    draw.line(
        [(top_x, tri_top_y + 12 * scale), (top_x, tri_top_y + 12 * scale + accent_len)],
        fill=GOLD_FAINT, width=max(1, int(1.5 * scale))
    )
    draw.line(
        [(left_x + 15 * scale, tri_bottom_y - 15 * scale),
         (left_x + 15 * scale + accent_len * 0.7, tri_bottom_y - 15 * scale - accent_len * 0.7)],
        fill=GOLD_FAINT, width=max(1, int(1.5 * scale))
    )
    draw.line(
        [(right_x - 15 * scale, tri_bottom_y - 15 * scale),
         (right_x - 15 * scale - accent_len * 0.7, tri_bottom_y - 15 * scale - accent_len * 0.7)],
        fill=GOLD_FAINT, width=max(1, int(1.5 * scale))
    )

    # 保存
    out_path = OUT_DIR / f"devil_wallpaper_{label}.png"
    img.save(out_path, "PNG")
    print(f"Generated: {out_path} ({width}x{height})")

    # 同时保存默认版本的副本
    if label == "2560x1440":
        default_path = OUT_DIR / "devil_wallpaper_default.png"
        img.save(default_path, "PNG")
        print(f"Generated default: {default_path}")

    return out_path


def main():
    print("Generating AKO_devil_agent wallpapers...")
    for w, h, label in RESOLUTIONS:
        generate_wallpaper(w, h, label)
    print("Done.")


if __name__ == "__main__":
    main()