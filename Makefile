# ── Versions ────────────────────────────────────────────────
JPEGOPTIM_VERSION := v1.5.6
OPTIPNG_VERSION := 7.9.1
PNGQUANT_VERSION  := 3.0.3
LIBWEBP_VERSION := v1.6.0
LIBAVIF_VERSION := v1.4.2
DAV1D_VERSION := 1.5.4
DAV1D_COMMIT := 54706fc6bc0cdecab7e9593974a4039cc038fca7
GIFSICLE_VERSION     := v1.96
FFMPEG_VERSION := n9.0.2
IMAGEMAGICK_VERSION := 7.1.2-32
ZSTD_VERSION         := v1.5.7
QPDF_VERSION := v12.4.2
LCMS2_VERSION := lcms2.19.1
LCMS2_COMMIT := 21c582a594fe5279f90c0b93437c398f93bf62b0
# ────────────────────────────────────────────────────────────

BINARIES := bin/jpegoptim bin/optipng bin/pngquant bin/cwebp bin/dwebp bin/avifenc bin/avifdec bin/gifsicle bin/ffmpeg bin/ffprobe bin/magick bin/zstd bin/qpdf

.PHONY: all test test-only test-avif clean clean-images clean-all

all: $(BINARIES)

# --- jpegoptim ---
bin/jpegoptim: jpegoptim/Dockerfile Makefile
	mkdir -p bin
	docker build --platform linux/amd64 --build-arg VERSION=$(JPEGOPTIM_VERSION) -t ubuntu-binaries-jpegoptim ./jpegoptim
	docker rm -f tmp-ubuntu-jpegoptim 2>/dev/null || true
	docker create --name tmp-ubuntu-jpegoptim ubuntu-binaries-jpegoptim /true
	docker cp tmp-ubuntu-jpegoptim:/jpegoptim bin/jpegoptim
	docker rm tmp-ubuntu-jpegoptim

# --- optipng ---
bin/optipng: optipng/Dockerfile Makefile
	mkdir -p bin
	docker build --platform linux/amd64 --build-arg VERSION=$(OPTIPNG_VERSION) -t ubuntu-binaries-optipng ./optipng
	docker rm -f tmp-ubuntu-optipng 2>/dev/null || true
	docker create --name tmp-ubuntu-optipng ubuntu-binaries-optipng /true
	docker cp tmp-ubuntu-optipng:/optipng bin/optipng
	docker rm tmp-ubuntu-optipng

# --- pngquant ---
bin/pngquant: pngquant/Dockerfile Makefile
	mkdir -p bin
	docker build --platform linux/amd64 --build-arg VERSION=$(PNGQUANT_VERSION) -t ubuntu-binaries-pngquant ./pngquant
	docker rm -f tmp-ubuntu-pngquant 2>/dev/null || true
	docker create --name tmp-ubuntu-pngquant ubuntu-binaries-pngquant /true
	docker cp tmp-ubuntu-pngquant:/pngquant bin/pngquant
	docker rm tmp-ubuntu-pngquant

# --- cwebp + dwebp (single image, two binaries) ---
bin/cwebp bin/dwebp: cwebp/Dockerfile Makefile
	mkdir -p bin
	docker build --platform linux/amd64 --build-arg VERSION=$(LIBWEBP_VERSION) -t ubuntu-binaries-cwebp ./cwebp
	docker rm -f tmp-ubuntu-cwebp 2>/dev/null || true
	docker create --name tmp-ubuntu-cwebp ubuntu-binaries-cwebp /true
	docker cp tmp-ubuntu-cwebp:/cwebp bin/cwebp
	docker cp tmp-ubuntu-cwebp:/dwebp bin/dwebp
	docker rm tmp-ubuntu-cwebp

# --- avifenc + avifdec (single image, two binaries) ---
bin/avifenc bin/avifdec: avifenc/Dockerfile Makefile
	mkdir -p bin
	docker build --platform linux/amd64 --build-arg VERSION=$(LIBAVIF_VERSION) --build-arg DAV1D_VERSION=$(DAV1D_VERSION) --build-arg DAV1D_COMMIT=$(DAV1D_COMMIT) -t ubuntu-binaries-avifenc ./avifenc
	docker rm -f tmp-ubuntu-avifenc 2>/dev/null || true
	docker create --name tmp-ubuntu-avifenc ubuntu-binaries-avifenc /true
	docker cp tmp-ubuntu-avifenc:/avifenc bin/avifenc
	docker cp tmp-ubuntu-avifenc:/avifdec bin/avifdec
	docker rm tmp-ubuntu-avifenc

# --- gifsicle ---
bin/gifsicle: gifsicle/Dockerfile Makefile
	mkdir -p bin
	docker build --platform linux/amd64 --build-arg VERSION=$(GIFSICLE_VERSION) -t ubuntu-binaries-gifsicle ./gifsicle
	docker rm -f tmp-ubuntu-gifsicle 2>/dev/null || true
	docker create --name tmp-ubuntu-gifsicle ubuntu-binaries-gifsicle /true
	docker cp tmp-ubuntu-gifsicle:/gifsicle bin/gifsicle
	docker rm tmp-ubuntu-gifsicle

# --- ffmpeg + ffprobe (single image, two binaries) ---
bin/ffmpeg bin/ffprobe: ffmpeg/Dockerfile Makefile
	mkdir -p bin
	docker build --platform linux/amd64 --build-arg VERSION=$(FFMPEG_VERSION) --build-arg LIBWEBP_VERSION=$(LIBWEBP_VERSION) -t ubuntu-binaries-ffmpeg ./ffmpeg
	docker rm -f tmp-ubuntu-ffmpeg 2>/dev/null || true
	docker create --name tmp-ubuntu-ffmpeg ubuntu-binaries-ffmpeg /true
	docker cp tmp-ubuntu-ffmpeg:/ffmpeg bin/ffmpeg
	docker cp tmp-ubuntu-ffmpeg:/ffprobe bin/ffprobe
	docker rm tmp-ubuntu-ffmpeg

# --- magick ---
bin/magick: imagemagick/Dockerfile Makefile
	mkdir -p bin
	docker build --platform linux/amd64 --build-arg VERSION=$(IMAGEMAGICK_VERSION) --build-arg LCMS2_VERSION=$(LCMS2_VERSION) --build-arg LCMS2_COMMIT=$(LCMS2_COMMIT) -t ubuntu-binaries-imagemagick ./imagemagick
	docker rm -f tmp-ubuntu-imagemagick 2>/dev/null || true
	docker create --name tmp-ubuntu-imagemagick ubuntu-binaries-imagemagick /true
	docker cp tmp-ubuntu-imagemagick:/magick bin/magick
	docker rm tmp-ubuntu-imagemagick

# --- zstd ---
bin/zstd: zstd/Dockerfile Makefile
	mkdir -p bin
	docker build --platform linux/amd64 --build-arg VERSION=$(ZSTD_VERSION) -t ubuntu-binaries-zstd ./zstd
	docker rm -f tmp-ubuntu-zstd 2>/dev/null || true
	docker create --name tmp-ubuntu-zstd ubuntu-binaries-zstd /true
	docker cp tmp-ubuntu-zstd:/zstd bin/zstd
	docker rm tmp-ubuntu-zstd

# --- qpdf ---
bin/qpdf: qpdf/Dockerfile Makefile
	mkdir -p bin
	docker build --platform linux/amd64 --build-arg VERSION=$(QPDF_VERSION) -t ubuntu-binaries-qpdf ./qpdf
	docker rm -f tmp-ubuntu-qpdf 2>/dev/null || true
	docker create --name tmp-ubuntu-qpdf ubuntu-binaries-qpdf /true
	docker cp tmp-ubuntu-qpdf:/qpdf bin/qpdf
	docker rm tmp-ubuntu-qpdf

# --- Test on the supported Ubuntu runtime ---
.PHONY: test-runtime
test-runtime:
	docker build --platform linux/amd64 -t ubuntu-binaries-tests ./tests

test: $(BINARIES) test-only

test-avif: test-runtime
	docker run --rm --platform linux/amd64 -v "$(CURDIR)/bin:/opt/bin:ro" -v "$(CURDIR)/tests:/opt/tests:ro" ubuntu-binaries-tests sh -c 'sh /opt/tests/avif.sh && python3 /opt/tests/avif-grid-metadata.py'

test-only: test-avif
	docker run --rm --platform linux/amd64 -v "$(CURDIR)/bin:/opt/bin:ro" -v "$(CURDIR)/tests:/opt/tests:ro" ubuntu-binaries-tests sh -c 'sh /opt/tests/smoke.sh && sh /opt/tests/ffmpeg-webp.sh && php /opt/tests/imagick.php && python3 /opt/tests/icc-conversion.py'

# --- Cleanup ---
clean:
	find bin -mindepth 1 ! -name .gitkeep -delete

clean-images:
	docker rmi -f ubuntu-binaries-jpegoptim ubuntu-binaries-optipng ubuntu-binaries-pngquant ubuntu-binaries-cwebp ubuntu-binaries-avifenc ubuntu-binaries-gifsicle ubuntu-binaries-ffmpeg ubuntu-binaries-imagemagick ubuntu-binaries-zstd ubuntu-binaries-qpdf 2>/dev/null || true

clean-all: clean clean-images
