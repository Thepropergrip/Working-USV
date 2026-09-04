from pathlib import Path
import math
import os
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

# Visual reference intent:
# - Ukrainian MAGURA V5/V7: low-profile dark composite hull, matte surfaces,
#   exposed aircraft-style missile rails and compact EO/IR hardware.
# - Mid-size combat USVs: practical marine finishes, restrained wear, salt/water
#   streaking, anti-slip deck surfaces and dark coated hardware.
# These are original procedural textures; no third-party photographs are copied.

ROOT = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd()))
OUT = ROOT / "hires-generated" / "textures"
OUT.mkdir(parents=True, exist_ok=True)
RNG = np.random.default_rng(36073)


def noise(size, sigma=55.0, blur=0.0):
    img = Image.effect_noise(size, sigma).convert("L")
    if blur > 0:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    return img


def colorize(gray, black, white):
    return ImageOps.colorize(gray, black=black, white=white).convert("RGB")


def tile_pattern(size, period=24, kind="weave"):
    tw = max(8, period * 4)
    th = tw
    tile = Image.new("L", (tw, th), 128)
    d = ImageDraw.Draw(tile)
    if kind == "weave":
        for x in range(-th, tw + th, period):
            d.line((x, 0, x + th, th), fill=158, width=max(1, period // 5))
            d.line((x + period // 2, 0, x + period // 2 + th, th), fill=108, width=max(1, period // 7))
        for x in range(-th, tw + th, period):
            d.line((x, th, x + th, 0), fill=146, width=max(1, period // 6))
    else:
        for y in range(0, th, period):
            d.line((0, y, tw, y), fill=150, width=max(1, period // 4))
    out = Image.new("L", size, 128)
    for y in range(0, size[1], th):
        for x in range(0, size[0], tw):
            out.paste(tile, (x, y))
    return out


def scratches(size, count, length=(8, 60), vertical_bias=0.45, value=180):
    img = Image.new("L", size, 0)
    d = ImageDraw.Draw(img)
    w, h = size
    for _ in range(count):
        x = int(RNG.integers(0, w))
        y = int(RNG.integers(0, h))
        L = int(RNG.integers(length[0], length[1] + 1))
        base = math.pi / 2 if RNG.random() < vertical_bias else 0.0
        a = float(RNG.normal(base, 0.35))
        x2 = int(x + math.cos(a) * L)
        y2 = int(y + math.sin(a) * L)
        d.line((x, y, x2, y2), fill=int(RNG.integers(value // 2, value)), width=int(RNG.integers(1, 3)))
    return img.filter(ImageFilter.GaussianBlur(0.45))


def vertical_streaks(size, count=220):
    img = Image.new("L", size, 0)
    d = ImageDraw.Draw(img)
    w, h = size
    for _ in range(count):
        x = int(RNG.integers(0, w))
        y = int(RNG.integers(0, h // 2))
        length = int(RNG.integers(h // 18, h // 3))
        width = int(RNG.integers(1, 8))
        val = int(RNG.integers(20, 90))
        d.line((x, y, x + int(RNG.integers(-4, 5)), min(h - 1, y + length)), fill=val, width=width)
    return img.filter(ImageFilter.GaussianBlur(4.0))


def save_rgba(rgb, alpha, name):
    rgba = rgb.convert("RGBA")
    if alpha is not None:
        rgba.putalpha(alpha)
    path = OUT / name
    rgba.save(path, optimize=True, compress_level=6)
    print(f"HIRES_TEXTURE {name} {rgba.size[0]}x{rgba.size[1]}")
    return path


def build_hull():
    size = (4096, 4096)
    grain = noise(size, 48, 1.0)
    weave = tile_pattern(size, 22, "weave").filter(ImageFilter.GaussianBlur(0.7))
    streak = vertical_streaks(size, 300)
    scuff = scratches(size, 3400, (8, 48), 0.62, 160)
    base = colorize(grain, (29, 35, 39), (70, 80, 87))
    weave_rgb = colorize(weave, (31, 37, 42), (72, 84, 92))
    base = Image.blend(base, weave_rgb, 0.26)
    cool = Image.new("RGB", size, (21, 31, 39))
    base = Image.blend(base, cool, 0.18)
    stain = colorize(streak, (0, 0, 0), (32, 40, 45))
    base = ImageChops.add(base, stain, scale=1.18)
    wear = colorize(scuff, (0, 0, 0), (28, 30, 30))
    base = ImageChops.subtract(base, wear, scale=1.65)
    save_rgba(base, Image.new("L", size, 255), "MAGURA_W6_Hull_Base_HiRes.png")

    # Tangent-space normal map from a restrained composite/weave height field.
    h = np.asarray(Image.blend(weave, grain, 0.38).filter(ImageFilter.GaussianBlur(0.45)), dtype=np.float32) / 255.0
    gy, gx = np.gradient(h)
    strength = 3.2
    nx = -gx * strength
    ny = -gy * strength
    nz = np.ones_like(nx)
    norm = np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.dstack(((nx / norm) * 0.5 + 0.5, (ny / norm) * 0.5 + 0.5, (nz / norm) * 0.5 + 0.5, np.ones_like(nx)))
    Image.fromarray(np.clip(n * 255, 0, 255).astype(np.uint8), "RGBA").save(OUT / "MAGURA_W6_Hull_Normal_HiRes.png", optimize=True, compress_level=6)
    del h, gy, gx, nx, ny, nz, norm, n

    ao = Image.blend(Image.new("L", size, 228), noise(size, 28, 2.0), 0.08)
    rough = Image.blend(Image.new("L", size, 194), grain, 0.20)
    rough = ImageChops.add(rough, streak, scale=1.8)
    metal = Image.new("L", size, 8)
    Image.merge("RGBA", (ao, rough, metal, Image.new("L", size, 255))).save(OUT / "MAGURA_W6_Hull_RoughMet_HiRes.png", optimize=True, compress_level=6)


def build_deck():
    size = (4096, 4096)
    grain = noise(size, 52, 0.8)
    nonskid = tile_pattern(size, 18, "nonskid").filter(ImageFilter.GaussianBlur(0.35))
    scuff = scratches(size, 2600, (6, 42), 0.35, 170)
    base = colorize(grain, (31, 33, 34), (68, 71, 72))
    base = Image.blend(base, colorize(nonskid, (28, 30, 31), (67, 70, 70)), 0.34)
    base = ImageChops.subtract(base, colorize(scuff, (0, 0, 0), (24, 24, 23)), scale=1.7)
    save_rgba(base, Image.new("L", size, 255), "MAGURA_W6_Deck_Base_HiRes.png")
    ao = Image.blend(Image.new("L", size, 235), grain, 0.06)
    rough = Image.blend(Image.new("L", size, 226), nonskid, 0.10)
    metal = Image.new("L", size, 4)
    Image.merge("RGBA", (ao, rough, metal, Image.new("L", size, 255))).save(OUT / "MAGURA_W6_Deck_RoughMet_HiRes.png", optimize=True, compress_level=6)


def build_metal():
    size = (4096, 4096)
    grain = noise(size, 40, 0.7)
    brush = Image.new("L", size, 128)
    d = ImageDraw.Draw(brush)
    for y in range(0, size[1], 6):
        d.line((0, y, size[0], y + int(RNG.integers(-1, 2))), fill=int(RNG.integers(105, 155)), width=1)
    brush = brush.filter(ImageFilter.GaussianBlur(0.55))
    scuff = scratches(size, 4200, (10, 78), 0.30, 190)
    base = colorize(grain, (48, 51, 52), (105, 111, 112))
    base = Image.blend(base, colorize(brush, (55, 58, 58), (110, 115, 115)), 0.32)
    polished = colorize(scuff, (0, 0, 0), (60, 60, 57))
    base = ImageChops.add(base, polished, scale=1.55)
    save_rgba(base, Image.new("L", size, 255), "MAGURA_W6_Metal_Base_HiRes.png")
    ao = Image.blend(Image.new("L", size, 236), grain, 0.07)
    rough = Image.blend(Image.new("L", size, 142), grain, 0.22)
    rough = ImageChops.subtract(rough, scuff, scale=2.25)
    metal = Image.blend(Image.new("L", size, 125), scuff, 0.26)
    Image.merge("RGBA", (ao, rough, metal, Image.new("L", size, 255))).save(OUT / "MAGURA_W6_Metal_RoughMet_HiRes.png", optimize=True, compress_level=6)


def build_armor():
    size = (4096, 4096)
    grain = noise(size, 44, 1.0)
    weave = tile_pattern(size, 30, "weave").filter(ImageFilter.GaussianBlur(0.9))
    scuff = scratches(size, 1800, (6, 32), 0.45, 130)
    base = colorize(grain, (35, 39, 41), (77, 84, 86))
    base = Image.blend(base, colorize(weave, (34, 39, 41), (75, 83, 86)), 0.20)
    base = ImageChops.subtract(base, colorize(scuff, (0, 0, 0), (20, 21, 20)), scale=1.9)
    save_rgba(base, Image.new("L", size, 255), "MAGURA_W6_Armor_Base_HiRes.png")
    ao = Image.blend(Image.new("L", size, 236), grain, 0.06)
    rough = Image.blend(Image.new("L", size, 202), grain, 0.18)
    metal = Image.new("L", size, 10)
    Image.merge("RGBA", (ao, rough, metal, Image.new("L", size, 255))).save(OUT / "MAGURA_W6_Armor_RoughMet_HiRes.png", optimize=True, compress_level=6)


def build_optics():
    size = (2048, 2048)
    w, h = size
    y, x = np.mgrid[0:h, 0:w]
    cx, cy = w / 2.0, h / 2.0
    rr = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / (w / 2.0)
    ang = np.arctan2(y - cy, x - cx)
    mask = (rr <= 1.0).astype(np.float32)
    halo = np.exp(-((rr - 0.72) / 0.11) ** 2)
    sheen = np.clip((np.cos(ang + 2.2) * 0.5 + 0.5) * (1.0 - rr), 0, 1)
    rgb = np.zeros((h, w, 4), dtype=np.uint8)
    rgb[:, :, 0] = np.clip((8 + 28 * halo + 25 * sheen) * mask, 0, 255).astype(np.uint8)
    rgb[:, :, 1] = np.clip((18 + 66 * halo + 56 * sheen) * mask, 0, 255).astype(np.uint8)
    rgb[:, :, 2] = np.clip((42 + 126 * halo + 90 * sheen) * mask, 0, 255).astype(np.uint8)
    rgb[:, :, 3] = 255
    Image.fromarray(rgb, "RGBA").save(OUT / "MAGURA_W6_Optics_Base_HiRes.png", optimize=True, compress_level=6)
    ao = np.full((h, w), 255, dtype=np.uint8)
    rough = np.clip(18 + rr * 18, 0, 255).astype(np.uint8)
    metal = np.full((h, w), 12, dtype=np.uint8)
    alpha = np.clip(mask * 255, 0, 255).astype(np.uint8)
    Image.merge("RGBA", tuple(Image.fromarray(c, "L") for c in (ao, rough, metal, alpha))).save(OUT / "MAGURA_W6_Optics_RoughMet_HiRes.png", optimize=True, compress_level=6)
    # Instrumental glass filter: blue-green multicoat, mostly transparent.
    glass = Image.new("RGBA", size, (5, 35, 48, 106))
    glass.save(OUT / "MAGURA_W6_Glass_Filter_HiRes.png", optimize=True, compress_level=6)


def build_damage():
    size = (4096, 4096)
    grain = noise(size, 62, 1.2)
    soot = noise(size, 92, 9.0)
    base = colorize(grain, (5, 6, 6), (56, 50, 43))
    base = Image.blend(base, colorize(soot, (2, 2, 2), (42, 36, 30)), 0.46)
    scuff = scratches(size, 3200, (8, 70), 0.45, 210)
    base = ImageChops.add(base, colorize(scuff, (0, 0, 0), (56, 50, 42)), scale=1.5)
    save_rgba(base, Image.new("L", size, 255), "MAGURA_W6_Damage_Base_HiRes.png")


if __name__ == "__main__":
    build_hull()
    build_deck()
    build_metal()
    build_armor()
    build_optics()
    build_damage()
    print(f"MAGURA_HIRES_TEXTURES_READY={OUT}")
