"""Generate small ICC v4 matrix/TRC profiles from published primaries.

Both profiles use the sRGB transfer curve and a D65 white point, adapted to the
D50 profile connection space with Bradford. Generating them keeps fixtures free of
third-party profile licenses and makes the bytes identical on every platform.
"""
import struct

D50 = (0.9642, 1.0, 0.8249)
D65_XY = (0.3127, 0.3290)
PRIMARIES = {
    'sRGB': ((0.640, 0.330), (0.300, 0.600), (0.150, 0.060)),
    'Display P3': ((0.680, 0.320), (0.265, 0.690), (0.150, 0.060)),
}
# IEC 61966-2-1 curve as ICC parametric function type 3: g, a, b, c, d.
SRGB_CURVE = (2.4, 1 / 1.055, 0.055 / 1.055, 1 / 12.92, 0.04045)
BRADFORD = ((0.8951, 0.2664, -0.1614), (-0.7502, 1.7135, 0.0367), (0.0389, -0.0685, 1.0296))


def xy_to_xyz(x, y):
    return (x / y, 1.0, (1 - x - y) / y)


def multiply(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def apply(m, v):
    return tuple(sum(m[i][k] * v[k] for k in range(3)) for i in range(3))


def inverse(m):
    (a, b, c), (d, e, f), (g, h, i) = m
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    return (
        ((e * i - f * h) / det, (c * h - b * i) / det, (b * f - c * e) / det),
        ((f * g - d * i) / det, (a * i - c * g) / det, (c * d - a * f) / det),
        ((d * h - e * g) / det, (b * g - a * h) / det, (a * e - b * d) / det),
    )


def rgb_to_xyz(name):
    """Linear RGB to D65 XYZ matrix for the named primaries."""
    columns = [xy_to_xyz(*xy) for xy in PRIMARIES[name]]
    p = tuple(tuple(columns[j][i] for j in range(3)) for i in range(3))
    scale = apply(inverse(p), xy_to_xyz(*D65_XY))
    return tuple(tuple(p[i][j] * scale[j] for j in range(3)) for i in range(3))


def bradford(source, target):
    cone_source, cone_target = apply(BRADFORD, source), apply(BRADFORD, target)
    diagonal = tuple(tuple(cone_target[i] / cone_source[i] if i == j else 0.0 for j in range(3)) for i in range(3))
    return multiply(inverse(BRADFORD), multiply(diagonal, BRADFORD))


def s15f16(value):
    return struct.pack('>i', round(value * 65536))


def xyz_tag(xyz):
    return b'XYZ \0\0\0\0' + b''.join(s15f16(v) for v in xyz)


def mluc(text):
    encoded = text.encode('utf-16-be')
    return b'mluc\0\0\0\0' + struct.pack('>II2s2sII', 1, 12, b'en', b'US', len(encoded), 28) + encoded


def profile(name):
    """Return ICC v4 display profile bytes for 'sRGB' or 'Display P3'."""
    adaptation = bradford(xy_to_xyz(*D65_XY), D50)
    colorants = multiply(adaptation, rgb_to_xyz(name))
    curve = b'para\0\0\0\0' + struct.pack('>HH', 3, 0) + b''.join(s15f16(v) for v in SRGB_CURVE)
    tags = [
        (b'desc', mluc(name + ' (generated test profile)')),
        (b'cprt', mluc('No copyright, use freely')),
        (b'wtpt', xyz_tag(D50)),
        (b'chad', b'sf32\0\0\0\0' + b''.join(s15f16(v) for row in adaptation for v in row)),
        (b'rXYZ', xyz_tag(tuple(colorants[i][0] for i in range(3)))),
        (b'gXYZ', xyz_tag(tuple(colorants[i][1] for i in range(3)))),
        (b'bXYZ', xyz_tag(tuple(colorants[i][2] for i in range(3)))),
        (b'rTRC', curve),
        (b'gTRC', curve),
        (b'bTRC', curve),
    ]
    offset = 128 + 4 + 12 * len(tags)
    table, data = struct.pack('>I', len(tags)), b''
    for signature, body in tags:
        body += b'\0' * (-len(body) % 4)
        table += signature + struct.pack('>II', offset + len(data), len(body))
        data += body
    size = offset + len(data)
    header = (struct.pack('>I4sI4s4s4s', size, b'\0\0\0\0', 0x04400000, b'mntr', b'RGB ', b'XYZ ')
              + struct.pack('>6H', 2026, 1, 1, 0, 0, 0) + b'acsp' + b'\0' * 24
              + struct.pack('>I', 0) + b''.join(s15f16(v) for v in D50) + b'\0' * 48)
    assert len(header) == 128
    return header + table + data


def decode(value):
    """sRGB/Display P3 encoded value (0-1) to linear light."""
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def encode(value):
    """Linear light to sRGB encoding, extended beyond 0-1 like an unbounded float transform."""
    return value * 12.92 if value <= 0.0031308 else 1.055 * value ** (1 / 2.4) - 0.055


def p3_to_srgb(rgb, clip=True):
    """Analytic relative colorimetric conversion of 0-1 floats.

    With clip=False, out-of-gamut values stay outside 0-1, as in ImageMagick HDRI builds
    until the image is written or clamped.
    """
    matrix = multiply(inverse(rgb_to_xyz('sRGB')), rgb_to_xyz('Display P3'))
    linear = apply(matrix, tuple(decode(c) for c in rgb))
    if clip:
        linear = tuple(min(1.0, max(0.0, v)) for v in linear)
    return tuple(encode(v) for v in linear)
