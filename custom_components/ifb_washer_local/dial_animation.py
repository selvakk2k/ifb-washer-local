"""Animated GIF Dial and Touch Console generator for IFB Washer Local."""

from __future__ import annotations

import math
import os
from typing import Sequence

from PIL import Image, ImageDraw, ImageFont


def _get_font(size: int = 12, bold: bool = False) -> ImageFont.ImageFont:
    """Attempt to load a clean truetype font, fallback to default."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/noto/NotoSans-Regular.ttf",
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def generate_animated_dial_gif(
    output_path: str,
    active_name: str,
    active_code: int,
    target_name: str,
    target_code: int,
    left_programs: Sequence[tuple[int, str]],
    right_programs: Sequence[tuple[int, str]],
    is_top_load: bool = False,
) -> str:
    """Generate an animated GIF showing the dial rotating to target program."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if is_top_load:
        _generate_top_load_console_gif(
            output_path, target_name, target_code, list(left_programs) + list(right_programs)
        )
    else:
        _generate_rotary_dial_gif(
            output_path, active_name, active_code, target_name, target_code, left_programs, right_programs
        )

    return output_path


def _generate_rotary_dial_gif(
    output_path: str,
    active_name: str,
    active_code: int,
    target_name: str,
    target_code: int,
    left_programs: Sequence[tuple[int, str]],
    right_programs: Sequence[tuple[int, str]],
) -> None:
    width, height = 540, 270
    cx, cy = 270, 135
    outer_r = 64
    inner_r = 50

    font_title = _get_font(10, bold=True)
    font_body = _get_font(11, bold=False)
    font_bold = _get_font(11, bold=True)
    font_center = _get_font(12, bold=True)
    font_sub = _get_font(10, bold=False)

    all_programs = list(right_programs) + list(left_programs)
    total_ticks = max(len(all_programs), 1)

    start_angle = -90.0
    target_angle = 0.0

    for i, (p_code, _) in enumerate(all_programs):
        angle = (i * (360.0 / total_ticks)) - 90
        if p_code == active_code:
            start_angle = angle
        if p_code == target_code:
            target_angle = angle

    # Shortest angular rotation path
    diff = (target_angle - start_angle) % 360
    if diff > 180:
        diff -= 360

    num_anim_frames = 6
    num_pulse_frames = 3
    frames = []

    # Animation phases: rotation then target pulse
    angles = [start_angle + (diff * (step / (num_anim_frames - 1))) for step in range(num_anim_frames)]

    for f_idx, current_needle_angle in enumerate(angles):
        img = Image.new("RGBA", (width, height), (19, 22, 28, 255))
        draw = ImageDraw.Draw(img)

        # Draw left header
        draw.text((20, 14), "LEFT ARC", fill=(107, 114, 128), font=font_title)
        # Draw right header
        draw.text((370, 14), "RIGHT ARC", fill=(107, 114, 128), font=font_title)

        # Draw left column
        item_h = 24
        start_y_left = cy - (len(left_programs) * item_h // 2)
        for idx, (code, name) in enumerate(left_programs):
            y = start_y_left + (idx * item_h)
            is_target = code == target_code
            if is_target:
                draw.rounded_rectangle([14, y - 2, 174, y + 18], radius=4, fill=(0, 52, 71), outline=(0, 210, 255), width=2)
                draw.text((22, y + 1), f"➔ {name}", fill=(0, 210, 255), font=font_bold)
            else:
                draw.text((22, y + 1), f"• {name}", fill=(156, 163, 175), font=font_body)

        # Draw right column
        start_y_right = cy - (len(right_programs) * item_h // 2)
        for idx, (code, name) in enumerate(right_programs):
            y = start_y_right + (idx * item_h)
            is_target = code == target_code
            if is_target:
                draw.rounded_rectangle([366, y - 2, 526, y + 18], radius=4, fill=(0, 52, 71), outline=(0, 210, 255), width=2)
                draw.text((374, y + 1), f"➔ {name}", fill=(0, 210, 255), font=font_bold)
            else:
                draw.text((374, y + 1), f"• {name}", fill=(156, 163, 175), font=font_body)

        # Draw tick marks
        for i, (p_code, _) in enumerate(all_programs):
            tick_ang = (i * (360.0 / total_ticks)) - 90
            rad = math.radians(tick_ang)
            x1 = cx + (outer_r + 3) * math.cos(rad)
            y1 = cy + (outer_r + 3) * math.sin(rad)
            x2 = cx + (outer_r + 12) * math.cos(rad)
            y2 = cy + (outer_r + 12) * math.sin(rad)

            is_target = p_code == target_code
            col = (0, 210, 255, 255) if is_target else (75, 85, 99, 255)
            w = 3 if is_target else 1
            draw.line([(x1, y1), (x2, y2)], fill=col, width=w)
            if is_target:
                draw.ellipse([x2 - 3, y2 - 3, x2 + 3, y2 + 3], fill=(0, 210, 255))

        # Draw outer bezel
        draw.ellipse([cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r], fill=(36, 41, 51), outline=(75, 85, 99), width=2)

        # Draw inner knob
        draw.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r], fill=(24, 27, 34), outline=(17, 19, 23), width=2)

        # Draw needle pointer
        n_rad = math.radians(current_needle_angle)
        nx = cx + (inner_r - 6) * math.cos(n_rad)
        ny = cy + (inner_r - 6) * math.sin(n_rad)
        draw.line([(cx, cy), (nx, ny)], fill=(0, 210, 255), width=3)
        draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=(0, 210, 255))

        # Knob Center Text
        draw.text((cx, cy - 14), target_name[:14], fill=(255, 255, 255), font=font_center, anchor="mm")
        draw.text((cx, cy + 8), f"Code {target_code}", fill=(0, 210, 255), font=font_sub, anchor="mm")

        frames.append(img.convert("RGB"))

    # Add pause frames at the end so target stays clearly visible
    for _ in range(num_pulse_frames):
        frames.append(frames[-1])

    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=180,
        loop=0,
    )


def _generate_top_load_console_gif(
    output_path: str,
    target_name: str,
    target_code: int,
    all_programs: list[tuple[int, str]],
) -> None:
    width, height = 540, 200
    font_title = _get_font(11, bold=True)
    font_bold = _get_font(10, bold=True)
    font_body = _get_font(10, bold=False)

    frames = []
    row1 = all_programs[:6]
    row2 = all_programs[6:12]

    for blink_idx in range(4):
        is_on = blink_idx % 2 == 0
        img = Image.new("RGBA", (width, height), (19, 22, 28, 255))
        draw = ImageDraw.Draw(img)

        # Header bar
        draw.rounded_rectangle([20, 14, width - 20, 48], radius=6, fill=(26, 30, 38), outline=(45, 51, 63))
        draw.text((36, 26), "TOP LOAD TOUCH CONSOLE", fill=(107, 114, 128), font=font_title)
        draw.text((width - 36, 26), f"Target: {target_name} (Code {target_code})", fill=(0, 210, 255), font=font_title, anchor="ra")

        for row_idx, row_items in enumerate([row1, row2]):
            y = 66 + (row_idx * 48)
            btn_w = 78
            gap = 8
            total_w = len(row_items) * btn_w + (len(row_items) - 1) * gap
            start_x = (width - total_w) // 2

            for col_idx, (code, name) in enumerate(row_items):
                x = start_x + col_idx * (btn_w + gap)
                is_target = code == target_code
                short_name = name[:10]

                if is_target and is_on:
                    draw.rounded_rectangle([x, y, x + btn_w, y + 38], radius=6, fill=(0, 52, 71), outline=(0, 210, 255), width=2)
                    draw.ellipse([x + 6, y + 14, x + 16, y + 24], fill=(0, 210, 255))
                    draw.text((x + 22, y + 14), short_name, fill=(0, 210, 255), font=font_bold)
                elif is_target and not is_on:
                    draw.rounded_rectangle([x, y, x + btn_w, y + 38], radius=6, fill=(0, 35, 50), outline=(0, 150, 180), width=1)
                    draw.ellipse([x + 6, y + 14, x + 16, y + 24], fill=(0, 150, 180))
                    draw.text((x + 22, y + 14), short_name, fill=(0, 210, 255), font=font_bold)
                else:
                    draw.rounded_rectangle([x, y, x + btn_w, y + 38], radius=6, fill=(28, 32, 39), outline=(45, 51, 63))
                    draw.ellipse([x + 6, y + 14, x + 16, y + 24], fill=(55, 65, 81))
                    draw.text((x + 22, y + 14), short_name, fill=(156, 163, 175), font=font_body)

        # Water level bar
        draw.text((36, 172), "WATER LEVEL (1-10):  ■ ■ ■ ■ ■ ■ □ □ □ □", fill=(0, 210, 255), font=font_body)
        frames.append(img.convert("RGB"))

    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=300,
        loop=0,
    )
