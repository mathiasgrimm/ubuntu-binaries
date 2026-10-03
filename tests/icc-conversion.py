#!/usr/bin/env python3
"""Check that bundled ImageMagick converts pixels between ICC profiles with Little CMS.

Without a color management delegate, -profile only attaches the new profile and the
pixels stay unchanged. The fixtures use saturated Display P3 colors whose sRGB values
are known, so an unconverted image fails.
"""
import io
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from icc_profiles import p3_to_srgb, profile  # noqa: E402
from PIL import Image, ImageCms  # noqa: E402

BIN = Path(os.environ.get('BIN_DIR', '/opt/bin'))
MAGICK = str(BIN / 'magick')
# Display P3 inputs. Four move by 8 to 40 levels in 8-bit sRGB; neutrals and
# primaries that clip to sRGB primaries must stay where they are.
COLORS = [
    (255, 0, 0), (0, 255, 0), (0, 0, 255), (230, 30, 30), (255, 128, 0),
    (40, 200, 60), (60, 40, 200), (128, 128, 128), (255, 255, 255), (0, 0, 0),
]
BLOCK = 8


def run(*args):
    return subprocess.run([str(a) for a in args], check=True, capture_output=True).stdout


def expected(color):
    return tuple(round(v * 255) for v in p3_to_srgb(tuple(c / 255 for c in color)))


def fixture(colors, mode='RGB', alpha=255):
    """One 8x8 block per color, so lossy encoders keep flat interiors."""
    image = Image.new(mode, (BLOCK * len(colors), BLOCK))
    for index, color in enumerate(colors):
        value = color + ((alpha,) if mode == 'RGBA' else ())
        image.paste(value, (index * BLOCK, 0, (index + 1) * BLOCK, BLOCK))
    return image


def centers(path):
    """Center pixel of every block, as decoded by Pillow."""
    with Image.open(path) as image:
        return [image.getpixel((index * BLOCK + BLOCK // 2, BLOCK // 2)) for index in range(len(COLORS))]


def close(actual, wanted, tolerance, label):
    for got, want, color in zip(actual, wanted, COLORS):
        if any(abs(g - w) > tolerance for g, w in zip(got, want)):
            raise SystemExit(f'{label}: Display P3 {color} became {got}, expected {want} +/- {tolerance}')


def description(path):
    with Image.open(path) as image:
        icc = image.info.get('icc_profile')
    if not icc:
        raise SystemExit(f'{path.name}: no embedded ICC profile')
    return ImageCms.getProfileDescription(ImageCms.ImageCmsProfile(io.BytesIO(icc))).strip()


version = run(MAGICK, '-version').decode()
delegates = next(line for line in version.splitlines() if line.startswith('Delegates'))
if ' lcms' not in delegates:
    raise SystemExit('magick was built without the lcms delegate: ' + delegates)

with tempfile.TemporaryDirectory() as directory:
    tmp = Path(directory)
    p3, srgb = tmp / 'display-p3.icc', tmp / 'srgb.icc'
    p3.write_bytes(profile('Display P3'))
    srgb.write_bytes(profile('sRGB'))
    wanted = [expected(color) for color in COLORS]
    moved = [c for c, w in zip(COLORS, wanted) if max(abs(a - b) for a, b in zip(c, w)) >= 8]
    assert len(moved) >= 4, moved

    # 1. Tagged PNG, prepared the way the quality metric scripts prepare inputs.
    fixture(COLORS).save(tmp / 'p3.png', icc_profile=p3.read_bytes())
    run(MAGICK, f'{tmp}/p3.png[0]', '-profile', srgb, '-alpha', 'off', '-depth', '8', f'PNG24:{tmp}/srgb.png')
    close(centers(tmp / 'srgb.png'), wanted, 1, 'PNG24')
    if description(tmp / 'srgb.png') != 'sRGB (generated test profile)':
        raise SystemExit('converted PNG does not carry the target profile')

    # 2. The same conversion at 16-bit precision.
    raw = run(MAGICK, tmp / 'p3.png', '-profile', srgb, '-depth', '16', '-endian', 'MSB', 'rgb:-')
    samples = struct.unpack(f'>{len(raw) // 2}H', raw)
    width = BLOCK * len(COLORS)
    for index, color in enumerate(COLORS):
        offset = 3 * ((BLOCK // 2) * width + index * BLOCK + BLOCK // 2)
        want = p3_to_srgb(tuple(c / 255 for c in color))
        got = samples[offset:offset + 3]
        if any(abs(g / 65535 - w) > 0.0005 for g, w in zip(got, want)):
            raise SystemExit(f'16-bit: Display P3 {color} became {got}, expected {want}')

    # 3. An untagged image is treated as already sRGB: the profile is assigned, pixels stay.
    fixture(COLORS).save(tmp / 'untagged.png')
    run(MAGICK, tmp / 'untagged.png', '-profile', srgb, f'PNG24:{tmp}/assigned.png')
    close(centers(tmp / 'assigned.png'), COLORS, 0, 'untagged')

    # 4. Alpha survives conversion, and black/white flattening composites converted colors.
    fixture(COLORS, 'RGBA', 128).save(tmp / 'p3-alpha.png', icc_profile=p3.read_bytes())
    run(MAGICK, tmp / 'p3-alpha.png', '-profile', srgb, '-depth', '8', f'PNG32:{tmp}/srgb-alpha.png')
    close([c[:3] for c in centers(tmp / 'srgb-alpha.png')], wanted, 1, 'RGBA')
    if any(c[3] != 128 for c in centers(tmp / 'srgb-alpha.png')):
        raise SystemExit('alpha changed during color conversion')
    # This HDRI build keeps out-of-gamut values until it writes or clamps the image, so
    # flattening right after -profile composites unclamped values. -clamp clips them first.
    for name, background in (('black', 0), ('white', 1)):
        for clamp in ([], ['-clamp']):
            out = tmp / f'flat-{name}{"-clamp" if clamp else ""}.png'
            run(MAGICK, f'{tmp}/p3-alpha.png[0]', '-profile', srgb, *clamp, '-background', name,
                '-alpha', 'remove', '-alpha', 'off', '-depth', '8', f'PNG24:{out}')
            with Image.open(out) as image:
                assert image.mode == 'RGB', image.mode
            converted = [p3_to_srgb(tuple(c / 255 for c in color), clip=bool(clamp)) for color in COLORS]
            flattened = [tuple(min(255, max(0, round((v * 128 / 255 + background * 127 / 255) * 255))) for v in c)
                         for c in converted]
            close(centers(out), flattened, 1, f'flattened on {name}{" after -clamp" if clamp else ""}')

    # 5. JPEG keeps its ICC profile in APP2 markers. Compare with Pillow's own decode.
    fixture(COLORS).save(tmp / 'p3.jpg', quality=100, subsampling=0, icc_profile=p3.read_bytes())
    decoded = centers(tmp / 'p3.jpg')
    run(MAGICK, f'{tmp}/p3.jpg[0]', '-profile', srgb, '-depth', '8', f'PNG24:{tmp}/jpeg-srgb.png')
    close(centers(tmp / 'jpeg-srgb.png'), [expected(c) for c in decoded], 2, 'JPEG')

    # 6. Ubuntu's PHP Imagick profileImage() gives the same pixels as the bundled CLI.
    script = tmp / 'profile.php'
    script.write_text('<?php $i = new Imagick($argv[1]); $i->profileImage("icc", file_get_contents($argv[2]));'
                      ' $i->setImageDepth(8); $i->writeImage("png24:" . $argv[3]);')
    run('php', script, tmp / 'p3.png', srgb, tmp / 'php.png')
    close(centers(tmp / 'php.png'), centers(tmp / 'srgb.png'), 1, 'PHP Imagick profileImage')

print('magick ' + delegates)
print('Display P3 to sRGB pixel conversion, alpha, flattening, JPEG and Imagick parity OK')
