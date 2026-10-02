# AVIF build

The AMD64 pair uses upstream libavif v1.4.2, dav1d 1.5.4 and AOM. No grid metadata patch is applied: the upstream release contains that fix. Source revisions are recorded in `versions.json`.

`make bin/avifenc` builds and extracts both executables. The Dockerfile verifies the dav1d commit, static linkage and x86-64 architecture. The runtime tests exercise the actual outputs on Ubuntu 24.04.

AOM remains the encoder and explicit decoder fallback. The default decoder is dav1d. `make test-avif` verifies 8/10/12-bit, 4:2:0/4:4:4, color/alpha, still/grid and lossless cases, along with ICC/XMP/Exif metadata and orientation semantics.

Build logs record Alpine and linked dependency versions. Alpine 3.23 package updates may change transitive libraries; the build is not claimed to be byte-for-byte reproducible. Artifact hashes and sizes are generated after a successful build.

The current artifacts link Alpine 3.23.6 packages: AOM 3.14.1-r0, libpng 1.6.59-r0, libjpeg-turbo 3.1.2-r0, zlib 1.3.2-r0 and musl 1.2.5-r23. libargparse is pinned upstream at ee74d1b53bd680748af14e737378de57e2a0a954.
