# Ubuntu Binaries

Static command-line binaries for **Ubuntu 24.04 AMD64 (x86_64)**, distributed as a Composer package. No Laravel or hosting provider is required.

Derived from [mathiasgrimm/laravel-cloud-binaries](https://github.com/mathiasgrimm/laravel-cloud-binaries). The build recipes use Alpine/musl to produce self-contained Linux executables; the supported runtime is tested on Ubuntu 24.04 AMD64. These binaries do not run natively on macOS or ARM64.

This package is under development. It has not been published to Packagist or released yet.

## Included tools

`jpegoptim`, `optipng`, `pngquant`, `cwebp`, `dwebp`, `avifenc`, `avifdec`, `gifsicle`, `ffmpeg`, `ffprobe`, `magick`, `zstd`, `qpdf`, `ssimulacra2`, and `butteraugli_main`.

SVGO is an npm package and is not included. Bundled ImageMagick is a standalone executable; it does not replace the library used by PHP's Imagick extension.

## Installation and PATH

After publication:

```sh
composer require mathiasgrimm/ubuntu-binaries
```

Executables live in `vendor/mathiasgrimm/ubuntu-binaries/bin`. Composer also creates convenience proxies in `vendor/bin`. Use the dedicated package directory when other packages provide executables with the same names.

For shell commands:

```sh
export PATH="$PWD/vendor/mathiasgrimm/ubuntu-binaries/bin:$PATH"
```

For Laravel, add this to `app/Providers/AppServiceProvider.php`, preserving your existing boot logic:

```php
public function boot(): void
{
    if (PHP_OS_FAMILY === 'Linux' && php_uname('m') === 'x86_64') {
        putenv('PATH='.base_path('vendor/mathiasgrimm/ubuntu-binaries/bin').PATH_SEPARATOR.getenv('PATH'));
    }
}
```

This exposes executable names to PHP child commands in web requests, queue workers and Artisan. ImageMagick delegates are one example. PATH cannot override a hardcoded absolute executable path. Restart long-running workers after deployment.

Keep the package as a production dependency when deploying with `composer install --no-dev`. No copying into your application repository or post-update hook is required.

## Versions

Latest stable upstream tool releases checked on 2026-10-01. libjxl, libvmaf and Little CMS were checked on 2026-10-02. Tags and source revisions are recorded in `versions.json`; build versions are in `Makefile`. `artifacts.json` records the shipped executable sizes and SHA-256 hashes.

| Component | Version |
|---|---|
| jpegoptim | v1.5.6 |
| pngquant | 3.0.3 |
| libwebp | v1.6.0 |
| libavif | v1.4.2 |
| gifsicle | v1.96 |
| ffmpeg | n9.0.2 |
| imagemagick | 7.1.2-32 |
| zstd | v1.5.7 |
| qpdf | v12.4.2 |
| dav1d | 1.5.4 |
| optipng | 7.9.1 |
| libjxl (`ssimulacra2`, `butteraugli_main`) | v0.12.0 |
| libvmaf (in ffmpeg) | v3.2.1 |
| Little CMS (in magick) | 2.19.1 |

libavif includes the upstream grid metadata fix, so no backport is applied. AOM encodes AVIF; dav1d is the preferred decoder, with AOM available explicitly. Grid encoding preserves metadata and exact image dimensions; it does not imply lossless encoding.

FFmpeg includes WebP encoding for ImageMagick delegates. For pixel-exact APNG intermediate frames, retain ImageMagick's `video:intermediate-format=pam` setting: a WebP intermediate may be lossy depending on the ImageMagick delegate.

FFmpeg also includes the `libvmaf` filter. libvmaf has its floating-point features, so `float_ssim` and `float_ms_ssim` are available. Its default VMAF models are built in, so the filter needs no model file. `float_ms_ssim` needs images of at least 176 pixels on each side. The libvmaf v3.2.1 source still reports version 3.2.0 to pkg-config. Its log files report the source commit, `f85a853`, as the version.

ImageMagick includes Little CMS. With an embedded ICC profile, `-profile` converts the pixels to the new profile. Without Little CMS, it only attached the new profile and kept the pixels. An image without an embedded profile keeps its pixels and gets the new profile.

`magick` is a Q16-HDRI build. After `-profile`, colors outside the new profile keep values below 0 or above 1 until the image is written or clamped. So an operation that comes next, such as `-alpha remove`, uses the unclamped values. Add `-clamp` after `-profile` to clip the values first.

`ssimulacra2` and `butteraugli_main` are the libjxl metric tools. They read PNG and JPEG. `butteraugli_main reference distorted --pnorm 3` prints the maximum distance on the first line and `3-norm: <value>` on the second. Both tools choose SIMD code for the CPU at runtime, and libvmaf does the same. Scores are floating point values, so a different CPU or architecture can give slightly different results. Compare scores with a tolerance.

Compared with libavif 1.2.1 in the Cloud package, avifdec now applies AVIF rotation and mirroring when writing PNG/JPEG pixels. It also removes the corresponding Exif orientation to avoid applying it twice. Consumers must account for this before replacing an older decoder. libavif also changed AOM quality mapping and default tuning, so application quality scales need revalidation. See the [upstream release notes](https://github.com/AOMediaCodec/libavif/releases/tag/v1.4.0).

Upgrades can change compressed output sizes, quality and metadata behavior. The package tests cover codec availability, metadata, alpha and lossless pixel preservation, but do not establish bitstream identity across versions.

## Build and verify

Docker must support `linux/amd64`; building on ARM64 uses emulation and can be slow.

```sh
make all
make test-only
```

All build and test commands explicitly select AMD64. Build images and temporary containers use an `ubuntu-binaries` namespace to avoid colliding with the original package. `make clean` removes this checkout's generated binaries. Changing pinned versions requires rebuilding the affected binaries.

Tests run in Ubuntu 24.04 and exercise actual encoding/decoding, AVIF grid metadata, decoder pixel parity, FFmpeg WebP/APNG delegates and all executable versions. They also convert saturated Display P3 colors to sRGB and check the resulting pixel values, and they run SSIMULACRA2, Butteraugli and libvmaf on generated identical, distorted and transparent fixtures. Architecture and static-link checks reject artifacts for the wrong platform or requiring shared libraries.

## Licensing

See [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) and `licenses/`. Individual binaries have their own licenses. Build recipes and source references are included alongside the artifacts.
