FROM alpine:3.23 AS builder

RUN apk add --no-cache \
    build-base \
    file \
    cmake \
    pkgconf \
    git \
    libjpeg-turbo-dev \
    libjpeg-turbo-static \
    libpng-dev \
    libpng-static \
    libwebp-dev \
    libwebp-static \
    freetype-dev \
    freetype-static \
    zlib-dev \
    zlib-static \
    libxml2-dev \
    libxml2-static \
    xz-dev \
    xz-static \
    bzip2-dev \
    bzip2-static \
    brotli-dev \
    brotli-static

# Build libtiff from source (static) - Alpine package lacks tiff-static
RUN git clone --depth 1 --branch v4.7.0 https://gitlab.com/libtiff/libtiff.git /src/libtiff && \
    cd /src/libtiff && \
    cmake -B build \
      -DCMAKE_BUILD_TYPE=Release \
      -DBUILD_SHARED_LIBS=OFF \
      -Dtiff-tools=OFF \
      -Dtiff-tests=OFF \
      -Dtiff-contrib=OFF \
      -Dtiff-docs=OFF && \
    cmake --build build -j$(nproc) && \
    cmake --install build

# Build Little CMS from source (static) so -profile converts pixels between
# ICC profiles. Its optional GPL-3.0 plugins (fast float, threaded) stay off.
ARG LCMS2_VERSION
ARG LCMS2_COMMIT
RUN git clone --depth 1 --branch ${LCMS2_VERSION} https://github.com/mm2/Little-CMS.git /src/lcms2 && \
    test "$(git -C /src/lcms2 rev-parse HEAD)" = "${LCMS2_COMMIT}" && \
    cd /src/lcms2 && \
    cmake -B build \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_LIBDIR=lib \
      -DLCMS2_BUILD_SHARED=OFF \
      -DLCMS2_BUILD_STATIC=ON \
      -DLCMS2_BUILD_TOOLS=OFF \
      -DLCMS2_BUILD_TESTS=OFF \
      -DLCMS2_WITH_FASTFLOAT=OFF \
      -DLCMS2_WITH_THREADED_PLUGIN=OFF && \
    cmake --build build -j$(nproc) && \
    cmake --install build && \
    cat /usr/local/lib/pkgconfig/lcms2.pc

ARG VERSION
RUN git clone --depth 1 --branch ${VERSION} https://github.com/ImageMagick/ImageMagick.git /src/imagemagick

WORKDIR /src/imagemagick

RUN ./configure \
      --disable-shared \
      --enable-static \
      --with-jpeg \
      --with-png \
      --with-webp \
      --with-freetype \
      --with-tiff \
      --with-xml \
      --with-zlib \
      --with-lcms \
      --without-x \
      --without-perl \
      --without-openexr \
      --without-heic \
      --without-jxl \
      --without-raw \
      --without-openjp2 \
      CFLAGS="-Os" CXXFLAGS="-Os" && \
    make -j$(nproc) LDFLAGS="-all-static" LIBS="-lsharpyuv -lbrotlidec -lbrotlicommon"

# Strip symbol tables -- these are shipped artifacts, not debugging targets
RUN strip /src/imagemagick/utilities/magick

# Verify static
RUN file /src/imagemagick/utilities/magick && \
    file /src/imagemagick/utilities/magick | grep -qv "dynamically linked" && \
    echo "Static binary confirmed"

# configure silently drops a delegate it cannot find, so require lcms explicitly.
RUN /src/imagemagick/utilities/magick -version && \
    /src/imagemagick/utilities/magick -version | grep -Eq '^Delegates \(built-in\):.* lcms( |$)'

FROM scratch
COPY --from=builder /src/imagemagick/utilities/magick /magick
