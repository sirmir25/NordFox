#!/usr/bin/env python3
"""Render NordFox marketing artwork from the same primitives as the app icon.

Outputs (all committed, regenerate with `python3 branding/generate_art.py`):

    branding/og-banner.png        1200x630  social card / README header
    site/img/platform-linux.png    600x360  download tile
    site/img/platform-macos.png    600x360  download tile
    site/img/platform-windows.png  600x360  download tile

The fox mark and the Nord palette are imported from generate_icon.py so the
artwork can never drift away from the icon that actually ships.

Nothing here draws a vendor logo: the platform tiles are typographic, so the
project is not redistributing anyone else's trademark.
"""

from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_icon import (  # noqa: E402
    AURORA_ORANGE,
    AURORA_PURPLE,
    AURORA_YELLOW,
    FROST_BRIGHT,
    FROST_DEEP,
    FROST_TEAL,
    POLAR_NIGHT_DARK,
    POLAR_NIGHT_MID,
    SNOW_BRIGHT,
    render_icon,
)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# Nord "night" end of the palette, one step darker than POLAR_NIGHT_DARK, for
# the top of the banner sky.
NIGHT_DEEP = (35, 40, 50)

# Font candidates in preference order. macOS first (this is where the art is
# regenerated), then the usual Linux families so CI can rebuild it too.
FONT_CANDIDATES = {
    "bold": [
        "/System/Library/Fonts/Avenir Next.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ],
    "regular": [
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ],
    "mono": [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    ],
}

# Wanted style, in preference order, per kind. Face order inside a .ttc is not
# consistent between collections — Avenir Next starts at Bold, Helvetica Neue
# starts at Regular — so faces are matched by name rather than by index.
FONT_STYLES = {
    "bold": ("Demi Bold", "Bold", "Medium", "Regular"),
    "regular": ("Regular", "Medium", "Book"),
    "mono": ("Regular", "Book"),
}


def load_font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES[kind]:
        if not os.path.exists(path):
            continue
        faces = {}
        for index in range(24):
            try:
                face = ImageFont.truetype(path, size, index=index)
            except OSError:
                break
            faces.setdefault(face.getname()[1], face)
        if not faces:
            continue
        for style in FONT_STYLES[kind]:
            if style in faces:
                return faces[style]
        return next(iter(faces.values()))
    return ImageFont.load_default(size)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def vertical_gradient(size, stops):
    """Multi-stop vertical gradient. `stops` is [(position 0..1, colour), ...]."""
    width, height = size
    strip = Image.new("RGB", (1, height))
    for y in range(height):
        t = y / max(1, height - 1)
        lower = stops[0]
        upper = stops[-1]
        for index in range(len(stops) - 1):
            if stops[index][0] <= t <= stops[index + 1][0]:
                lower, upper = stops[index], stops[index + 1]
                break
        span = max(1e-6, upper[0] - lower[0])
        strip.putpixel((0, y), lerp(lower[1], upper[1], (t - lower[0]) / span))
    return strip.resize(size).convert("RGBA")


def aurora_band(size, y_frac, colour, alpha, thickness, wavelength, phase):
    """A glowing aurora ribbon.

    Built column by column rather than as a stroked arc: each x gets a
    vertical band whose alpha falls off from the centre line, so the ribbon
    glows from the inside out instead of reading as a drawn line. The centre
    line follows a slow sine so the ribbon drapes rather than arcs.
    """
    import math

    width, height = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    pixels = layer.load()
    centre = height * y_frac
    for x in range(width):
        wave = math.sin(x / wavelength + phase)
        # Taper both ends so the ribbon fades out instead of hitting the edge.
        edge = min(1.0, min(x, width - 1 - x) / (width * 0.22))
        y_centre = centre + wave * height * 0.055
        span = thickness * (1.0 + 0.35 * math.sin(x / (wavelength * 0.6) + phase))
        top = max(0, int(y_centre - span))
        bottom = min(height - 1, int(y_centre + span))
        for y in range(top, bottom + 1):
            # Rounding top/bottom to ints can push a pixel just past the
            # band edge; clamp so the exponent never sees a negative base.
            fade = max(0.0, 1.0 - abs(y - y_centre) / max(1.0, span))
            value = int(alpha * (fade ** 1.7) * edge)
            if value > 0:
                pixels[x, y] = (*colour, value)
    return layer.filter(ImageFilter.GaussianBlur(radius=max(2.0, thickness * 0.5)))


def star_field(size, count, seed=7):
    """Sparse dim stars. Deterministic so the art is reproducible."""
    import random

    rng = random.Random(seed)
    width, height = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for _ in range(count):
        x = rng.uniform(0, width)
        y = rng.uniform(0, height * 0.62)
        radius = rng.uniform(0.6, 1.7)
        alpha = int(rng.uniform(35, 130) * (1 - y / (height * 0.62)))
        draw.ellipse((x - radius, y - radius, x + radius, y + radius),
                     fill=(*SNOW_BRIGHT, max(0, alpha)))
    return layer


def mountains(size, horizon_frac, scale=1.0):
    """Two low-poly ridges. The far one is hazier and sits behind the near one.

    `horizon_frac` is where the far ridge's base sits; `scale` shrinks the peak
    heights so the ridge line can be kept clear of overlaid text.
    """
    width, height = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    horizon = height * horizon_frac

    far_base = horizon
    far = [(0, far_base)]
    peaks_far = [(0.08, 0.55), (0.22, 0.78), (0.37, 0.48), (0.52, 0.72),
                 (0.68, 0.42), (0.84, 0.66), (1.0, 0.52)]
    for x_frac, depth in peaks_far:
        far.append((width * x_frac, far_base - height * 0.13 * depth * scale))
    far += [(width, height), (0, height)]
    draw.polygon(far, fill=(*lerp(POLAR_NIGHT_MID, FROST_DEEP, 0.22), 255))

    near_base = horizon + height * 0.09
    near = [(0, near_base)]
    peaks_near = [(0.14, 0.62), (0.30, 0.34), (0.46, 0.80), (0.63, 0.40),
                  (0.79, 0.70), (0.93, 0.44), (1.0, 0.58)]
    for x_frac, depth in peaks_near:
        near.append((width * x_frac, near_base - height * 0.11 * depth * scale))
    near += [(width, height), (0, height)]
    draw.polygon(near, fill=(*lerp(POLAR_NIGHT_DARK, (18, 22, 30), 0.45), 255))
    return layer


def night_sky(size, horizon_frac=0.74, aurora=True, ridge_scale=1.0):
    """The shared background: graded sky, stars, aurora, ridge line."""
    canvas = vertical_gradient(size, [
        (0.00, NIGHT_DEEP),
        (0.42, POLAR_NIGHT_DARK),
        (0.78, POLAR_NIGHT_MID),
        (1.00, POLAR_NIGHT_DARK),
    ])
    canvas = Image.alpha_composite(canvas, star_field(size, int(size[0] * 0.17)))
    if aurora:
        width, height = size
        for y_frac, colour, alpha, thickness, wavelength, phase in [
            (0.20, FROST_TEAL, 165, height * 0.055, width * 0.30, 0.0),
            (0.28, FROST_BRIGHT, 145, height * 0.042, width * 0.24, 1.7),
            (0.37, AURORA_PURPLE, 105, height * 0.030, width * 0.19, 3.1),
            (0.45, AURORA_YELLOW, 60, height * 0.022, width * 0.16, 4.6),
        ]:
            canvas = Image.alpha_composite(
                canvas,
                aurora_band(size, y_frac, colour, alpha, thickness, wavelength, phase),
            )
    canvas = Image.alpha_composite(canvas, mountains(size, horizon_frac, ridge_scale))
    return canvas


def paste_glow(canvas, sprite, position, radius, strength=150):
    """Composite `sprite` with a soft coloured halo behind it."""
    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    glow.paste(sprite, position, sprite)
    glow = glow.filter(ImageFilter.GaussianBlur(radius=radius))
    glow.putalpha(glow.getchannel("A").point(lambda a: a * strength // 255))
    canvas = Image.alpha_composite(canvas, glow)
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    layer.paste(sprite, position, sprite)
    return Image.alpha_composite(canvas, layer)


def render_banner(width=1200, height=630):
    # The ridge is kept low and shallow so it never collides with the chip row.
    canvas = night_sky((width, height), horizon_frac=0.88, ridge_scale=0.62)
    draw = ImageDraw.Draw(canvas)

    icon_size = 232
    icon = render_icon(icon_size)
    icon_x, icon_y = 96, (height - icon_size) // 2 - 26
    canvas = paste_glow(canvas, icon, (icon_x, icon_y), radius=34, strength=130)
    draw = ImageDraw.Draw(canvas)

    text_x = icon_x + icon_size + 68

    title_font = load_font("bold", 104)
    draw.text((text_x, icon_y + 2), "NordFox", font=title_font, fill=SNOW_BRIGHT)

    rule_y = icon_y + 128
    draw.line((text_x, rule_y, text_x + 92, rule_y), fill=(*FROST_BRIGHT, 255), width=3)

    tagline_font = load_font("regular", 34)
    draw.text((text_x, rule_y + 26), "A quieter web.",
              font=tagline_font, fill=(*FROST_BRIGHT, 255))
    draw.text((text_x, rule_y + 70), "Hardened Firefox ESR, Nord-styled.",
              font=tagline_font, fill=(*FROST_TEAL, 235))

    chip_font = load_font("mono", 21)
    chips = ["Windows", "Linux", "macOS"]
    chip_x = text_x
    chip_y = rule_y + 140
    for label in chips:
        box = draw.textbbox((0, 0), label, font=chip_font)
        chip_w = box[2] - box[0] + 34
        chip_h = box[3] - box[1] + 22
        draw.rounded_rectangle(
            (chip_x, chip_y, chip_x + chip_w, chip_y + chip_h),
            radius=chip_h // 2,
            fill=(*POLAR_NIGHT_MID, 205),
            outline=(*FROST_DEEP, 255),
            width=2,
        )
        draw.text((chip_x + 17, chip_y + 11 - box[1]), label,
                  font=chip_font, fill=(*SNOW_BRIGHT, 235))
        chip_x += chip_w + 14

    foot_font = load_font("mono", 19)
    draw.text((text_x, height - 84),
              "no telemetry  ·  no Pocket  ·  no DRM  ·  built from source",
              font=foot_font, fill=(*lerp(FROST_DEEP, SNOW_BRIGHT, 0.40), 255))

    # A single warm accent, echoing the diamond on the fox's blaze.
    draw.polygon(
        [(width - 74, 60), (width - 56, 92), (width - 74, 124), (width - 92, 92)],
        fill=(*AURORA_ORANGE, 200),
    )
    return canvas


def render_platform_tile(title, subtitle, filename, accent, width=600, height=360):
    canvas = night_sky((width, height), horizon_frac=0.86, ridge_scale=0.7)
    draw = ImageDraw.Draw(canvas)

    icon_size = 96
    icon = render_icon(icon_size)
    canvas = paste_glow(canvas, icon, (44, 40), radius=20, strength=120)
    draw = ImageDraw.Draw(canvas)

    title_font = load_font("bold", 46)
    draw.text((44, 168), title, font=title_font, fill=SNOW_BRIGHT)

    sub_font = load_font("regular", 24)
    draw.text((44, 226), subtitle, font=sub_font, fill=(*accent, 240))

    file_font = load_font("mono", 17)
    draw.text((44, 282), filename, font=file_font,
              fill=(*lerp(FROST_DEEP, SNOW_BRIGHT, 0.45), 255))

    # Accent rule down the right edge ties the three tiles into a set.
    draw.rectangle((width - 8, 0, width, height), fill=(*accent, 220))
    return canvas


def main():
    out_banner = os.path.join(HERE, "og-banner.png")
    render_banner().convert("RGB").save(out_banner, "PNG", optimize=True)
    print(f"  wrote {os.path.relpath(out_banner, REPO)}  (1200x630)")

    site_img = os.path.join(REPO, "site", "img")
    os.makedirs(site_img, exist_ok=True)
    tiles = [
        ("Windows", "10 and 11 · x86_64", "installer .exe  ·  portable .zip",
         FROST_BRIGHT, "platform-windows.png"),
        ("Linux", "glibc · x86_64", "portable .tar.bz2", FROST_TEAL,
         "platform-linux.png"),
        ("macOS", "Apple Silicon · arm64", "NordFox-arm64.dmg", AURORA_PURPLE,
         "platform-macos.png"),
    ]
    for title, subtitle, filename, accent, out_name in tiles:
        path = os.path.join(site_img, out_name)
        render_platform_tile(title, subtitle, filename, accent).convert("RGB").save(
            path, "PNG", optimize=True
        )
        print(f"  wrote {os.path.relpath(path, REPO)}  (600x360)")


if __name__ == "__main__":
    main()
