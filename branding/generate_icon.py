#!/usr/bin/env python3
"""Generate a NordFox .icns icon at all macOS sizes."""
import os
import shutil
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFilter

# Nord palette
POLAR_NIGHT_DARK = (46, 52, 64)        # #2E3440
POLAR_NIGHT_MID  = (59, 66, 82)        # #3B4252
FROST_DEEP       = (94, 129, 172)      # #5E81AC
FROST_BRIGHT     = (136, 192, 208)     # #88C0D0
FROST_TEAL       = (143, 188, 187)     # #8FBCBB
SNOW_BRIGHT      = (236, 239, 244)     # #ECEFF4
AURORA_ORANGE    = (208, 135, 112)     # #D08770
AURORA_YELLOW    = (235, 203, 139)     # #EBCB8B
AURORA_PURPLE    = (180, 142, 173)     # #B48EAD

ICONSET_SIZES = [
    ("icon_16x16.png", 16),
    ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32),
    ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
    ("icon_512x512@2x.png", 1024),
]


def linear_gradient(size, top, bottom):
    """Vertical gradient from top color to bottom color."""
    base = Image.new("RGBA", (1, size), 0)
    for y in range(size):
        t = y / max(1, size - 1)
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        base.putpixel((0, y), (r, g, b, 255))
    return base.resize((size, size))


def squircle_mask(size, radius_frac=0.225):
    """Approximate macOS Big-Sur 'squircle' rounded square via rounded rectangle."""
    mask = Image.new("L", (size * 4, size * 4), 0)
    d = ImageDraw.Draw(mask)
    radius = int(size * 4 * radius_frac)
    d.rounded_rectangle((0, 0, size * 4 - 1, size * 4 - 1),
                        radius=radius, fill=255)
    return mask.resize((size, size), Image.LANCZOS)


def draw_fox(size, detailed=True):
    """Low-poly fox head on a transparent layer.

    Drawn 4x supersampled and downscaled with LANCZOS so polygon edges
    stay crisp at every icon size. `detailed=False` drops the eyes,
    nose and forehead facets and enlarges the silhouette ~8% so the
    mark stays legible at 16-32 px.
    """
    ss = 4
    big = size * ss
    layer = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    grow = 1.0 if detailed else 1.08

    def pts(*fracs):
        """Normalized (x, y) fractions -> supersampled pixel coords."""
        return [
            ((0.5 + (x - 0.5) * grow) * big, (0.5 + (y - 0.5) * grow) * big)
            for x, y in fracs
        ]

    # Silhouette: ears + head, all SNOW_BRIGHT.
    d.polygon(pts((0.19, 0.13), (0.43, 0.30), (0.30, 0.49)), fill=SNOW_BRIGHT)   # left ear
    d.polygon(pts((0.81, 0.13), (0.57, 0.30), (0.70, 0.49)), fill=SNOW_BRIGHT)   # right ear
    d.polygon(
        pts((0.26, 0.33), (0.74, 0.33), (0.87, 0.52), (0.50, 0.89), (0.13, 0.52)),
        fill=SNOW_BRIGHT,
    )  # head: wide cheeks tapering to a chin point

    # Inner ears — deep frost.
    d.polygon(pts((0.235, 0.195), (0.385, 0.305), (0.30, 0.425)), fill=FROST_DEEP)
    d.polygon(pts((0.765, 0.195), (0.615, 0.305), (0.70, 0.425)), fill=FROST_DEEP)

    if detailed:
        # Forehead: frost side facets with a snow blaze down the centre.
        d.polygon(pts((0.26, 0.33), (0.44, 0.33), (0.36, 0.52), (0.13, 0.52)),
                  fill=FROST_BRIGHT)
        d.polygon(pts((0.74, 0.33), (0.56, 0.33), (0.64, 0.52), (0.87, 0.52)),
                  fill=FROST_BRIGHT)
        # Teal cheek shading under each frost facet.
        d.polygon(pts((0.13, 0.52), (0.295, 0.52), (0.20, 0.60)), fill=FROST_TEAL)
        d.polygon(pts((0.87, 0.52), (0.705, 0.52), (0.80, 0.60)), fill=FROST_TEAL)
        # Single warm accent — aurora-orange diamond on the blaze.
        d.polygon(pts((0.50, 0.355), (0.545, 0.43), (0.50, 0.505), (0.455, 0.43)),
                  fill=AURORA_ORANGE)

        # Eyes — angular dark facets.
        d.polygon(pts((0.315, 0.525), (0.425, 0.51), (0.385, 0.615)), fill=POLAR_NIGHT_DARK)
        d.polygon(pts((0.685, 0.525), (0.575, 0.51), (0.615, 0.615)), fill=POLAR_NIGHT_DARK)

        # Nose — dark triangle at the chin.
        d.polygon(pts((0.445, 0.745), (0.555, 0.745), (0.50, 0.835)), fill=POLAR_NIGHT_DARK)

    return layer.resize((size, size), Image.LANCZOS)


def aurora_arc(size, draw, color, y_frac, width_frac, alpha=180):
    """Draw a subtle aurora-style horizontal arc."""
    cx, cy = size // 2, int(size * y_frac)
    rx = int(size * 0.42)
    ry = int(size * 0.10)
    bbox = (cx - rx, cy - ry, cx + rx, cy + ry)
    draw.arc(bbox, start=200, end=340,
             fill=(color[0], color[1], color[2], alpha),
             width=max(1, int(size * width_frac)))


def render_icon(size):
    """Render the NordFox icon at `size` × `size` pixels."""
    # 1. Background: gradient inside a squircle
    bg = linear_gradient(size, FROST_DEEP, POLAR_NIGHT_DARK)
    mask = squircle_mask(size)
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    icon.paste(bg, (0, 0), mask)

    detailed = size > 32

    # 2. Aurora arcs near the top (subtle glow, behind the ears).
    #    Skipped at small sizes — they read as noise below 32 px.
    if detailed:
        overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        aurora_arc(size, od, FROST_BRIGHT,  0.24, 0.022, alpha=200)
        aurora_arc(size, od, FROST_TEAL,    0.30, 0.018, alpha=150)
        aurora_arc(size, od, AURORA_PURPLE, 0.36, 0.012, alpha=110)
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=max(0.3, size / 200)))
        # Mask the overlay to the squircle
        masked_overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        masked_overlay.paste(overlay, (0, 0), mask)
        icon = Image.alpha_composite(icon, masked_overlay)

    # 3. Geometric fox head, with a soft drop shadow.
    fox = draw_fox(size, detailed=detailed)

    shadow_alpha = fox.getchannel("A").point(lambda a: a * 150 // 255)
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 255), (max(1, size // 200), max(1, size // 100)),
                 shadow_alpha)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=max(0.5, size / 120)))
    masked_shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    masked_shadow.paste(shadow, (0, 0), mask)
    icon = Image.alpha_composite(icon, masked_shadow)

    # Clip the fox to the squircle too (in case it overflows)
    masked_fox = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    masked_fox.paste(fox, (0, 0), mask)
    icon = Image.alpha_composite(icon, masked_fox)

    # 4. Top highlight gloss (very subtle)
    gloss = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gloss)
    gd.ellipse(
        (-size // 4, -size, size + size // 4, size // 2),
        fill=(255, 255, 255, 28),
    )
    masked_gloss = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    masked_gloss.paste(gloss, (0, 0), mask)
    icon = Image.alpha_composite(icon, masked_gloss)

    return icon


def main():
    # Default: regenerate branding/firefox.icns in place.
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    iconset_dir = os.path.join(out_dir, "NordFox.iconset")
    os.makedirs(iconset_dir, exist_ok=True)

    for name, size in ICONSET_SIZES:
        path = os.path.join(iconset_dir, name)
        img = render_icon(size)
        img.save(path, "PNG")
        print(f"  wrote {name}  ({size}x{size})")

    preview_path = os.path.join(out_dir, "preview.png")
    render_icon(512).save(preview_path, "PNG")
    print(f"  wrote preview.png  (512x512)")

    icns_path = os.path.join(out_dir, "firefox.icns")
    subprocess.run(["iconutil", "-c", "icns", iconset_dir, "-o", icns_path],
                   check=True)
    shutil.rmtree(iconset_dir)
    print(f"\nNordFox.icns -> {icns_path}")


if __name__ == "__main__":
    main()
