#!/bin/sh
set -eu
BIN_DIR=${BIN_DIR:-/opt/bin}
export PATH="$BIN_DIR:$PATH"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
for binary in jpegoptim optipng pngquant cwebp dwebp avifenc avifdec gifsicle ffmpeg ffprobe magick zstd qpdf; do
    file "$BIN_DIR/$binary" | grep -Eq 'x86-64.*(statically linked|static-pie linked).*stripped$'
    readelf -h "$BIN_DIR/$binary" | grep -q 'Machine:.*Advanced Micro Devices X86-64'
    if readelf -l "$BIN_DIR/$binary" | grep -q INTERP || readelf -d "$BIN_DIR/$binary" | grep -q NEEDED; then
        echo "Dynamic dependency in $binary" >&2; exit 1
    fi
done
jpegoptim --version
optipng -v
pngquant --version
cwebp -version
dwebp -version
avifenc --version
avifdec --version
gifsicle --version
ffmpeg -version
ffprobe -version
magick -version
magick -version | grep -Eq '^Delegates \(built-in\):.* lcms( |$)'
zstd --version
qpdf --version
magick -size 48x32 gradient:red-blue -depth 8 "$tmp/input.png"
magick "$tmp/input.png" -depth 8 "rgb:$tmp/original.rgb"
cp "$tmp/input.png" "$tmp/optimized.png"
optipng -quiet "$tmp/optimized.png"
magick "$tmp/optimized.png" -depth 8 "rgb:$tmp/optimized.rgb"
cmp "$tmp/original.rgb" "$tmp/optimized.rgb"
pngquant --force --output "$tmp/quantized.png" "$tmp/input.png"
test "$(magick "$tmp/quantized.png" -format '%wx%h' info:)" = 48x32
cwebp -quiet -lossless "$tmp/input.png" -o "$tmp/image.webp"
dwebp "$tmp/image.webp" -o "$tmp/decoded.png"
magick "$tmp/decoded.png" -depth 8 "rgb:$tmp/decoded.rgb"
cmp "$tmp/original.rgb" "$tmp/decoded.rgb"
magick "$tmp/input.png" "$tmp/image.jpg"
jpegoptim --max=85 "$tmp/image.jpg"
test "$(magick "$tmp/image.jpg" -format '%wx%h' info:)" = 48x32
magick -delay 10 "$tmp/input.png" \( "$tmp/input.png" -flip \) -loop 0 "$tmp/image.gif"
gifsicle -O3 "$tmp/image.gif" -o "$tmp/optimized.gif"
test "$(magick "$tmp/optimized.gif" -format '%n' info: | head -c 1)" = 2
printf 'Ubuntu binaries roundtrip\n' > "$tmp/text"
zstd -q "$tmp/text" -o "$tmp/text.zst"
zstd -q -d "$tmp/text.zst" -o "$tmp/roundtrip"
cmp "$tmp/text" "$tmp/roundtrip"
python3 - "$tmp/input.pdf" <<'PYTHON'
from PIL import Image
import sys
Image.new('RGB', (16, 16), 'white').save(sys.argv[1], 'PDF')
PYTHON
qpdf "$tmp/input.pdf" "$tmp/rewritten.pdf"
qpdf --check "$tmp/rewritten.pdf"
test "$(qpdf --show-npages "$tmp/rewritten.pdf")" = 1
echo 'All 13 AMD64 static tools and format smoke checks passed'
