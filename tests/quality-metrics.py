#!/usr/bin/env python3
"""Run SSIMULACRA2, Butteraugli and libvmaf SSIM/MS-SSIM on generated fixtures.

Inputs are prepared like an image quality report: 8-bit sRGB PNG24 through the
bundled magick, with transparent images flattened on black and on white first.
Scores are floating point and may differ slightly between CPUs, so distorted cases
use tolerances. Identical inputs must give the exact perfect score.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from icc_profiles import profile  # noqa: E402
from PIL import Image  # noqa: E402

BIN = Path(os.environ.get('BIN_DIR', '/opt/bin'))
SIZE = 256  # libvmaf float_ms_ssim needs at least 176 pixels per side.
# Measured on Ubuntu 24.04 AMD64 with the AVX2 code paths. An SSE4-only CPU gave
# SSIMULACRA2 up to 0.07 lower and Butteraugli within 1e-5; libvmaf was identical.
EXPECTED = {
    'mild': {'ssimulacra2': 95.09240659, 'butteraugli_max': 0.6945775747, 'butteraugli_3norm': 0.383793,
             'ssim': 0.996899, 'ms_ssim': 0.999797},
    'strong': {'ssimulacra2': 20.12953708, 'butteraugli_max': 9.1076507568, 'butteraugli_3norm': 4.861822,
               'ssim': 0.930586, 'ms_ssim': 0.978507},
    'alpha-black': {'ssimulacra2': 36.56712309, 'butteraugli_max': 8.4143333435, 'butteraugli_3norm': 3.764814,
                    'ssim': 0.967254, 'ms_ssim': 0.986949},
    'alpha-white': {'ssimulacra2': 37.67345035, 'butteraugli_max': 8.3676118851, 'butteraugli_3norm': 3.705378,
                    'ssim': 0.967538, 'ms_ssim': 0.986204},
}
TOLERANCE = {'ssimulacra2': 0.25, 'butteraugli_max': 0.002, 'butteraugli_3norm': 0.002, 'ssim': 1e-5, 'ms_ssim': 1e-5}


def run(*args):
    result = subprocess.run([str(a) for a in args], capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f'{args[0]} failed ({result.returncode}): {result.stderr.strip()[:500]}')
    return result.stdout


def texture(x, y):
    """Integer-only pattern: smooth gradients, 16 px blocks and fine detail."""
    block = ((x // 16 + y // 16) % 2) * 64
    return (x, (y + block) % 256, (((x ^ y) & 31) * 4 + block + (x * y >> 9)) % 256)


def noise(seed):
    while True:
        seed = (1103515245 * seed + 12345) & 0x7FFFFFFF
        yield seed >> 16


def distort(rgb, levels, amplitude, values):
    """Posterize to the given step, then add deterministic noise."""
    return tuple(min(255, max(0, (c // levels) * levels + levels // 2 + next(values) % (2 * amplitude + 1) - amplitude)) for c in rgb)


def image(pixel, mode='RGB', size=SIZE):
    out = Image.new(mode, (size, size))
    out.putdata([pixel(x, y) for y in range(size) for x in range(size)])
    return out


def prepare(source, dest, srgb, background=None):
    flatten = ['-alpha', 'off'] if background is None else ['-background', background, '-alpha', 'remove', '-alpha', 'off']
    run(BIN / 'magick', f'{source}[0]', '-profile', srgb, *flatten, '-depth', '8', f'PNG24:{dest}')
    with Image.open(dest) as prepared:
        if prepared.mode != 'RGB' or prepared.size != (SIZE, SIZE):
            raise SystemExit(f'{dest.name}: prepared as {prepared.mode} {prepared.size}')


def metrics(reference, distorted, work):
    lines = run(BIN / 'butteraugli_main', reference, distorted, '--pnorm', '3').strip().splitlines()
    if len(lines) != 2 or not lines[1].startswith('3-norm:'):
        raise SystemExit('unexpected butteraugli_main output: ' + repr(lines))
    values = {'butteraugli_max': float(lines[0]), 'butteraugli_3norm': float(lines[1].split(':')[1])}
    values['ssimulacra2'] = float(run(BIN / 'ssimulacra2', reference, distorted).strip().splitlines()[-1])
    version, frame = vmaf(reference, distorted, work)
    values.update(ssim=frame['float_ssim'], ms_ssim=frame['float_ms_ssim'], vmaf=frame['vmaf'], libvmaf=version)
    return values


def vmaf(reference, distorted, work):
    """libvmaf JSON version and first-frame metrics. The first input is the distorted image."""
    log = work / 'vmaf.json'
    graph = ('[0:v]scale=out_color_matrix=bt709,format=yuv444p[d];[1:v]scale=out_color_matrix=bt709,format=yuv444p[r];'
             f'[d][r]libvmaf=feature=name=float_ssim|name=float_ms_ssim:log_fmt=json:log_path={log}:n_threads=1')
    run(BIN / 'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-i', distorted, '-i', reference,
        '-lavfi', graph, '-f', 'null', '-')
    report = json.loads(log.read_text())
    log.unlink()
    return report['version'], report['frames'][0]['metrics']


ffmpeg = run(BIN / 'ffmpeg', '-hide_banner', '-buildconf')
if '--enable-libvmaf' not in ffmpeg:
    raise SystemExit('ffmpeg was configured without --enable-libvmaf')
options = run(BIN / 'ffmpeg', '-hide_banner', '-h', 'filter=libvmaf')
for option in ('feature', 'model', 'log_fmt', 'log_path', 'n_threads'):
    if f' {option} ' not in options:
        raise SystemExit(f'libvmaf filter lacks the {option} option')

with tempfile.TemporaryDirectory() as directory:
    tmp = Path(directory)
    srgb = tmp / 'srgb.icc'
    srgb.write_bytes(profile('sRGB'))
    image(texture).save(tmp / 'reference.png')
    mild, strong = noise(1), noise(2)
    image(lambda x, y: distort(texture(x, y), 2, 1, mild)).save(tmp / 'mild.png')
    image(lambda x, y: distort(texture(x, y), 32, 8, strong)).save(tmp / 'strong.png')
    alpha = noise(3)
    image(lambda x, y: texture(x, y) + (x,), 'RGBA').save(tmp / 'alpha-reference.png')
    image(lambda x, y: distort(texture(x, y), 32, 8, alpha) + (x,), 'RGBA').save(tmp / 'alpha-distorted.png')

    for name in ('reference', 'mild', 'strong'):
        prepare(tmp / f'{name}.png', tmp / f'{name}-prepared.png', srgb)
    for background in ('black', 'white'):
        for name in ('reference', 'distorted'):
            prepare(tmp / f'alpha-{name}.png', tmp / f'alpha-{name}-{background}.png', srgb, background)

    scores = {
        'identical': metrics(tmp / 'reference-prepared.png', tmp / 'reference-prepared.png', tmp),
        'mild': metrics(tmp / 'reference-prepared.png', tmp / 'mild-prepared.png', tmp),
        'strong': metrics(tmp / 'reference-prepared.png', tmp / 'strong-prepared.png', tmp),
    }
    for background in ('black', 'white'):
        scores[f'alpha-{background}'] = metrics(tmp / f'alpha-reference-{background}.png',
                                                tmp / f'alpha-distorted-{background}.png', tmp)

    # Below 176 pixels per side, libvmaf leaves out float_ms_ssim and ffmpeg still succeeds.
    small = noise(4)
    image(texture, size=64).save(tmp / 'small.png')
    image(lambda x, y: distort(texture(x, y), 32, 8, small), size=64).save(tmp / 'small-distorted.png')
    _, frame = vmaf(tmp / 'small.png', tmp / 'small-distorted.png', tmp)
    if 'float_ms_ssim' in frame or not 0 < frame['float_ssim'] < 1:
        raise SystemExit(f'unexpected libvmaf metrics for a 64x64 image: {frame}')

print(json.dumps(scores, indent=2, sort_keys=True))

perfect = scores['identical']
if (perfect['ssimulacra2'] != 100 or perfect['butteraugli_max'] != 0 or perfect['butteraugli_3norm'] != 0
        or abs(perfect['ssim'] - 1) > 1e-6 or abs(perfect['ms_ssim'] - 1) > 1e-6):
    raise SystemExit('identical images did not get perfect scores')
mild, strong = scores['mild'], scores['strong']
if not (mild['ssimulacra2'] > strong['ssimulacra2'] and mild['ssim'] > strong['ssim']
        and mild['ms_ssim'] > strong['ms_ssim'] and mild['butteraugli_max'] < strong['butteraugli_max']
        and mild['butteraugli_3norm'] < strong['butteraugli_3norm']):
    raise SystemExit('stronger distortion did not score worse on every metric')
if scores['alpha-black']['ssimulacra2'] == scores['alpha-white']['ssimulacra2']:
    raise SystemExit('black and white flattening gave identical scores')
for case, wanted in EXPECTED.items():
    for key, value in wanted.items():
        if abs(scores[case][key] - value) > TOLERANCE[key]:
            raise SystemExit(f'{case} {key} is {scores[case][key]}, expected {value} +/- {TOLERANCE[key]}')
print('SSIMULACRA2, Butteraugli and libvmaf float_ssim/float_ms_ssim scores OK')
