#!/bin/bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Builds what `size_bench.py --speed` needs for deterministic retired-instruction
# counts: a plugin-enabled qemu-user (arm + microblaze + microblazeel) and the
# instruction-counter TCG plugin (scripts/emboss_insncount.c). The distro
# qemu-user is built without --enable-plugins, so a from-source qemu is required.
#
# Usage:
#   scripts/build_qemu_plugin.sh [QEMU_VERSION] [DEST_DIR]
# then point the harness at the results:
#   export EMBOSS_QEMU_DIR=<DEST_DIR>/qemu-build
#   export EMBOSS_QEMU_PLUGIN=<DEST_DIR>/emboss_insncount.so
#   python3 scripts/size_bench.py --speed --out-dir out
#
# Build deps (Debian/Ubuntu): meson ninja-build pkg-config libglib2.0-dev python3.
# Speed toolchains (used by size_bench.py, not by this script): the Bootlin
# microblaze[el] gcc and g++-arm-linux-gnueabihf. The distro qemu-user package is
# not needed -- the from-source binaries built here are invoked directly.
set -euo pipefail

QEMU_VERSION="${1:-10.0.11}"
DEST="${2:-$HOME/emboss-qemu}"
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$DEST"
cd "$DEST"

TARBALL="qemu-${QEMU_VERSION}.tar.xz"
[ -f "$TARBALL" ] || curl -fsSL "https://download.qemu.org/${TARBALL}" -o "$TARBALL"
[ -d "qemu-${QEMU_VERSION}" ] || tar -xf "$TARBALL"

echo "Configuring qemu-user (arm, microblaze, microblazeel) with plugins..."
rm -rf qemu-build && mkdir qemu-build && cd qemu-build
"../qemu-${QEMU_VERSION}/configure" \
  --target-list=arm-linux-user,microblaze-linux-user,microblazeel-linux-user \
  --enable-plugins --disable-system --disable-tools --disable-docs \
  --disable-werror --disable-debug-info
ninja qemu-arm qemu-microblaze qemu-microblazeel
cd ..

echo "Building the instruction-counter plugin..."
gcc -O2 -shared -fPIC \
  -I"qemu-${QEMU_VERSION}/include/qemu" $(pkg-config --cflags glib-2.0) \
  -o "$DEST/emboss_insncount.so" "$SCRIPTS/emboss_insncount.c"

cat <<EOF

Built:
  qemu:   $DEST/qemu-build/{qemu-arm,qemu-microblaze,qemu-microblazeel}
  plugin: $DEST/emboss_insncount.so

Now run the speed benchmark with:
  export EMBOSS_QEMU_DIR=$DEST/qemu-build
  export EMBOSS_QEMU_PLUGIN=$DEST/emboss_insncount.so
  python3 scripts/size_bench.py --speed --out-dir out
EOF
