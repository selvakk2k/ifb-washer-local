"""SVG Dial and Touch Console illustration generator for IFB washing machine verification."""

from __future__ import annotations

import base64
import html
import math


def generate_dial_svg(
    active_name: str,
    active_code: int,
    target_name: str,
    target_code: int,
    left_programs: list[tuple[int, str]],
    right_programs: list[tuple[int, str]],
    is_top_load: bool = False,
) -> str:
    """Generate a responsive SVG diagram representing the machine's dial or touch console.

    Returns a base64 data URI suitable for direct markdown embedding:
    ![Dial Layout](data:image/svg+xml;base64,...)
    """
    if is_top_load:
        svg = _generate_top_load_console_svg(
            active_name, active_code, target_name, target_code, left_programs + right_programs
        )
    else:
        svg = _generate_rotary_dial_svg(
            active_name, active_code, target_name, target_code, left_programs, right_programs
        )

    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def _generate_rotary_dial_svg(
    active_name: str,
    active_code: int,
    target_name: str,
    target_code: int,
    left_programs: list[tuple[int, str]],
    right_programs: list[tuple[int, str]],
) -> str:
    """Generate skeuomorphic rotary dial with left & right program columns."""
    width = 540
    height = 300
    cx = 270
    cy = 150
    outer_r = 65
    inner_r = 52

    # Collect all programs to calculate angles
    # Positions 1 to 7 are Right Side (angles approx -60 to 60 or 20 to 160 deg)
    # Positions 8 to 14/15 are Left Side (angles approx 200 to 340 deg)
    total_ticks = len(left_programs) + len(right_programs)
    ticks_svg = []

    # Notch angle calculation
    target_angle = 0
    all_programs = right_programs + left_programs
    for i, (p_code, _) in enumerate(all_programs):
        angle_deg = (i * (360.0 / max(total_ticks, 1))) - 90
        rad = math.radians(angle_deg)
        x1 = cx + (outer_r + 4) * math.cos(rad)
        y1 = cy + (outer_r + 4) * math.sin(rad)
        x2 = cx + (outer_r + 12) * math.cos(rad)
        y2 = cy + (outer_r + 12) * math.sin(rad)

        is_target = p_code == target_code
        color = "#00d2ff" if is_target else "#4b5563"
        stroke_w = "3" if is_target else "1.5"

        if is_target:
            target_angle = angle_deg
            # Glowing marker on the active notch
            ticks_svg.append(
                f'<circle cx="{x2:.1f}" cy="{y2:.1f}" r="4" fill="#00d2ff" filter="url(#glow)"/>'
            )

        ticks_svg.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{color}" stroke-width="{stroke_w}" stroke-linecap="round"/>'
        )

    # Pointer needle coordinates on the knob
    needle_rad = math.radians(target_angle)
    nx = cx + (inner_r - 6) * math.cos(needle_rad)
    ny = cy + (inner_r - 6) * math.sin(needle_rad)

    # Render Left Column Items
    left_rows = []
    item_height = 24
    start_y_left = cy - (len(left_programs) * item_height // 2)
    for idx, (code, name) in enumerate(left_programs):
        y = start_y_left + (idx * item_height)
        is_target = code == target_code
        is_active = code == active_code
        esc_name = html.escape(name)

        if is_target:
            left_rows.append(
                f'<rect x="14" y="{y - 14}" width="160" height="20" rx="4" fill="#003447" stroke="#00d2ff" stroke-width="1.5"/>'
                f'<text x="22" y="{y}" fill="#00d2ff" font-family="system-ui, -apple-system, sans-serif" font-size="11" font-weight="bold">➔ {esc_name}</text>'
            )
        elif is_active:
            left_rows.append(
                f'<rect x="14" y="{y - 14}" width="160" height="20" rx="4" fill="#252a34" stroke="#4b5563" stroke-width="1"/>'
                f'<text x="22" y="{y}" fill="#9ca3af" font-family="system-ui, -apple-system, sans-serif" font-size="10">● {esc_name}</text>'
            )
        else:
            left_rows.append(
                f'<text x="22" y="{y}" fill="#6b7280" font-family="system-ui, -apple-system, sans-serif" font-size="10">{esc_name}</text>'
            )

    # Render Right Column Items
    right_rows = []
    start_y_right = cy - (len(right_programs) * item_height // 2)
    for idx, (code, name) in enumerate(right_programs):
        y = start_y_right + (idx * item_height)
        is_target = code == target_code
        is_active = code == active_code
        esc_name = html.escape(name)

        if is_target:
            right_rows.append(
                f'<rect x="366" y="{y - 14}" width="160" height="20" rx="4" fill="#003447" stroke="#00d2ff" stroke-width="1.5"/>'
                f'<text x="374" y="{y}" fill="#00d2ff" font-family="system-ui, -apple-system, sans-serif" font-size="11" font-weight="bold">➔ {esc_name}</text>'
            )
        elif is_active:
            right_rows.append(
                f'<rect x="366" y="{y - 14}" width="160" height="20" rx="4" fill="#252a34" stroke="#4b5563" stroke-width="1"/>'
                f'<text x="374" y="{y}" fill="#9ca3af" font-family="system-ui, -apple-system, sans-serif" font-size="10">● {esc_name}</text>'
            )
        else:
            right_rows.append(
                f'<text x="374" y="{y}" fill="#6b7280" font-family="system-ui, -apple-system, sans-serif" font-size="10">{esc_name}</text>'
            )

    esc_target = html.escape(target_name)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="240" style="background:#13161c; border-radius:12px; border:1px solid #282d37;">
  <defs>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
    <linearGradient id="bezelGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#3b4252" />
      <stop offset="100%" stop-color="#1f232b" />
    </linearGradient>
    <linearGradient id="knobGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#242933" />
      <stop offset="100%" stop-color="#181a20" />
    </linearGradient>
  </defs>

  <!-- Left Header -->
  <text x="22" y="24" fill="#4b5563" font-family="system-ui, sans-serif" font-size="9" font-weight="bold" letter-spacing="1">LEFT ARC</text>

  <!-- Right Header -->
  <text x="374" y="24" fill="#4b5563" font-family="system-ui, sans-serif" font-size="9" font-weight="bold" letter-spacing="1">RIGHT ARC</text>

  <!-- Left Program List -->
  {''.join(left_rows)}

  <!-- Right Program List -->
  {''.join(right_rows)}

  <!-- Notches around Dial -->
  {''.join(ticks_svg)}

  <!-- Dial Outer Bezel -->
  <circle cx="{cx}" cy="{cy}" r="{outer_r}" fill="url(#bezelGrad)" stroke="#4b5563" stroke-width="1.5" />

  <!-- Dial Inner Knob Body -->
  <circle cx="{cx}" cy="{cy}" r="{inner_r}" fill="url(#knobGrad)" stroke="#111317" stroke-width="2" />

  <!-- Dial Pointer Needle -->
  <line x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="#00d2ff" stroke-width="3" stroke-linecap="round" filter="url(#glow)" />
  <circle cx="{cx}" cy="{cy}" r="5" fill="#00d2ff" />

  <!-- Target Badge inside Center of Dial -->
  <text x="{cx}" y="{cy - 16}" fill="#00d2ff" font-family="system-ui, sans-serif" font-size="9" font-weight="bold" text-anchor="middle" letter-spacing="1">TARGET</text>
  <text x="{cx}" y="{cy + 2}" fill="#ffffff" font-family="system-ui, sans-serif" font-size="11" font-weight="bold" text-anchor="middle">{esc_target}</text>
  <text x="{cx}" y="{cy + 18}" fill="#9ca3af" font-family="system-ui, sans-serif" font-size="9" text-anchor="middle">Code {target_code}</text>
</svg>"""


def _generate_top_load_console_svg(
    active_name: str,
    active_code: int,
    target_name: str,
    target_code: int,
    all_programs: list[tuple[int, str]],
) -> str:
    """Generate touch console fascia illustration for Top Load washing machines."""
    width = 540
    height = 200

    pads = []
    # Render touch buttons in 2 rows of up to 6 buttons
    row1 = all_programs[:6]
    row2 = all_programs[6:12]

    for row_idx, row_items in enumerate([row1, row2]):
        y = 70 + (row_idx * 48)
        btn_w = 78
        gap = 8
        total_w = len(row_items) * btn_w + (len(row_items) - 1) * gap
        start_x = (width - total_w) // 2

        for col_idx, (code, name) in enumerate(row_items):
            x = start_x + col_idx * (btn_w + gap)
            is_target = code == target_code
            esc_name = html.escape(name[:11])

            if is_target:
                pads.append(
                    f'<rect x="{x}" y="{y}" width="{btn_w}" height="38" rx="6" fill="#003447" stroke="#00d2ff" stroke-width="2"/>'
                    f'<circle cx="{x + 10}" cy="{y + 19}" r="4" fill="#00d2ff" filter="url(#glow)"/>'
                    f'<text x="{x + 20}" y="{y + 23}" fill="#00d2ff" font-family="system-ui, sans-serif" font-size="10" font-weight="bold">{esc_name}</text>'
                )
            else:
                pads.append(
                    f'<rect x="{x}" y="{y}" width="{btn_w}" height="38" rx="6" fill="#1c2027" stroke="#2d333f" stroke-width="1"/>'
                    f'<circle cx="{x + 10}" cy="{y + 19}" r="3" fill="#374151"/>'
                    f'<text x="{x + 20}" y="{y + 23}" fill="#9ca3af" font-family="system-ui, sans-serif" font-size="9">{esc_name}</text>'
                )

    esc_target = html.escape(target_name)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="180" style="background:#13161c; border-radius:12px; border:1px solid #282d37;">
  <defs>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>

  <!-- Top Fascia Header -->
  <rect x="20" y="14" width="{width - 40}" height="36" rx="6" fill="#1a1e26" stroke="#2d333f" stroke-width="1"/>
  <text x="36" y="37" fill="#6b7280" font-family="system-ui, sans-serif" font-size="10" font-weight="bold" letter-spacing="1">TOP LOAD TOUCH PANEL</text>
  <text x="{width - 36}" y="37" fill="#00d2ff" font-family="system-ui, sans-serif" font-size="12" font-weight="bold" text-anchor="end">Target: {esc_target} (Code {target_code})</text>

  <!-- Touch Button Matrix with Status LEDs -->
  {''.join(pads)}

  <!-- Bottom Water Level Indicator Bar -->
  <text x="36" y="185" fill="#4b5563" font-family="system-ui, sans-serif" font-size="9" font-weight="bold">WATER LEVEL (1-10):</text>
  <text x="160" y="185" fill="#00d2ff" font-family="system-ui, sans-serif" font-size="9" letter-spacing="3">■ ■ ■ ■ ■ ■ □ □ □ □</text>
</svg>"""
