FROM alpine:3.23 AS builder

RUN apk add --no-cache \
    build-base \
    file \
    cmake \
    ninja \
    git \
    pkgconf \
    libpng-dev \
    libpng-static \
    libjpeg-turbo-dev \
    libjpeg-turbo-static \
    zlib-dev \
    zlib-static

# Verify the tag against its recorded commit. The tag's tree pins the bundled
# Brotli, Highway and skcms submodule commits, so only those three are fetched.
ARG VERSION
ARG COMMIT
RUN git clone --depth 1 --branch ${VERSION} https://github.com/libjxl/libjxl.git /src/libjxl && \
    cd /src/libjxl && \
    test "$(git rev-parse HEAD)" = "${COMMIT}" && \
    git submodule update --init --depth 1 third_party/brotli third_party/highway third_party/skcms && \
    git submodule status third_party/brotli third_party/highway third_party/skcms

WORKDIR /src/libjxl

# JPEGXL_STATIC links -static, -static-libgcc and -static-libstdc++.
# skcms handles color management; PNG and JPEG input use the static Alpine libraries.
RUN cmake -B build -G Ninja \
      -DCMAKE_BUILD_TYPE=Release \
      -DBUILD_TESTING=OFF \
      -DJPEGXL_STATIC=ON \
      -DJPEGXL_ENABLE_DEVTOOLS=ON \
      -DJPEGXL_ENABLE_SKCMS=ON \
      -DJPEGXL_ENABLE_SJPEG=OFF \
      -DJPEGXL_ENABLE_OPENEXR=OFF \
      -DJPEGXL_ENABLE_BENCHMARK=OFF \
      -DJPEGXL_ENABLE_EXAMPLES=OFF \
      -DJPEGXL_ENABLE_JNI=OFF \
      -DJPEGXL_ENABLE_MANPAGES=OFF \
      -DJPEGXL_ENABLE_DOXYGEN=OFF \
      -DJPEGXL_ENABLE_PLUGINS=OFF \
      -DJPEGXL_ENABLE_VIEWERS=OFF \
      -DJPEGXL_ENABLE_TCMALLOC=OFF \
      -DJPEGXL_ENABLE_FUZZERS=OFF && \
    cmake --build build --target ssimulacra2 butteraugli_main -j$(nproc)

# Emit dependency provenance into the build log for artifact updates.
RUN cat /etc/alpine-release && \
    apk list --installed libpng-static libjpeg-turbo-static zlib-static musl && \
    git rev-parse HEAD && git submodule status third_party/brotli third_party/highway third_party/skcms

# Strip symbol tables -- these are shipped artifacts, not debugging targets
RUN strip /src/libjxl/build/tools/ssimulacra2 /src/libjxl/build/tools/butteraugli_main

# Both shipped artifacts must be static and have no ELF interpreter or dependencies.
RUN for binary in /src/libjxl/build/tools/ssimulacra2 /src/libjxl/build/tools/butteraugli_main; do \
      file "$binary" && \
      file "$binary" | grep -Eq 'statically linked|static-pie linked' && \
      readelf -h "$binary" | grep -q 'Machine:.*Advanced Micro Devices X86-64' && \
      ! readelf -l "$binary" | grep -q INTERP && \
      ! readelf -d "$binary" | grep -q NEEDED || exit 1; \
    done

FROM scratch
COPY --from=builder /src/libjxl/build/tools/ssimulacra2 /ssimulacra2
COPY --from=builder /src/libjxl/build/tools/butteraugli_main /butteraugli_main
