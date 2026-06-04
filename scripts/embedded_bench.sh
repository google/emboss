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

# Cross-compile the generated many_conditionals.emb.h header on embedded
# toolchains and report .text and per-function sizes for the generated Ok()
# methods.
#
# Usage:  scripts/embedded_bench.sh [out-dir]
#         out-dir defaults to /tmp/embedded-bench.
#
# Run from a clean checkout. Each target compiles a tiny freestanding TU that
# forces the relevant Ok() methods to be emitted, then reports `size` on the
# resulting object file plus the key Ok() symbol sizes from `nm`. Only the
# out-dir is written to: the header is refreshed in place via
# scripts/regenerate_goldens.py, whose output is byte-identical to the
# checked-in goldens on a clean tree.
#
# Targets are skipped (with a warning) when their toolchain is missing:
#   * ARM Cortex-M4 / Thumb-2   arm-none-eabi-g++
#   * MicroBlaze (big-endian)   /opt/microblaze/.../microblaze-buildroot-linux-gnu-g++
#   * Host x86-64               g++ (reference)
#
# Compiler flags can be overridden via the EMBOSS_BENCH_FLAGS environment
# variable; profile_tool.py uses this to sweep optimization levels.

set -euo pipefail

OUT="${1:-/tmp/embedded-bench}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$OUT"

# Refresh the golden header from the current .emb + generator so we measure the
# live state of the code generator and not a stale checked-in header.
python3 "$REPO/scripts/regenerate_goldens.py" >/dev/null

# Tiny TU that pulls Ok() into the object file. Without a caller each Ok() is a
# weak inline symbol the linker would dead-strip, leaving nothing to measure.
DRIVER="$OUT/driver.cc"
cat >"$DRIVER" <<'CPP'
#include <cstdint>

#include "testdata/many_conditionals.emb.h"

// Volatile sink so the optimizer can't fold the Ok() call away.
volatile bool emboss_result_sink;

extern "C" void large_ok(const char *buf) {
  auto v = emboss::test::MakeLargeConditionalsView(buf, 100);
  emboss_result_sink = v.Ok();
}
CPP

# -Os for embedded space optimization; -ffunction-sections / -fdata-sections so
# each function lands in its own section (makes the object's `size` and
# `nm --size-sort` directly comparable across compiles); -fno-exceptions /
# -fno-rtti to match typical embedded builds.
EMBEDDED_FLAGS="${EMBOSS_BENCH_FLAGS:-"-std=c++17 -Os -ffunction-sections -fdata-sections -fno-exceptions -fno-rtti"}"

# -I"$REPO" resolves the header's runtime/cpp/*.h includes. The driver includes
# "testdata/many_conditionals.emb.h", but the generated header lives under
# testdata/golden_cpp/, so drop a symlink and add it to the include path.
mkdir -p "$OUT/include/testdata"
ln -sf "$REPO/testdata/golden_cpp/many_conditionals.emb.h" \
  "$OUT/include/testdata/many_conditionals.emb.h"
INCLUDES="-I$REPO -I$OUT/include"

report_size() {
  local label="$1"
  local nm_bin="$2"
  local obj="$3"
  echo "=== $label ==="
  # Host binutils `size` reads ELF objects for every arch we emit here, so use
  # it unconditionally rather than a per-target `size`.
  size "$obj"
  echo "--- LargeConditionals::Ok() ---"
  # The template parameter list itself contains '>' characters, so anchor on
  # '>::Ok() const' at end of line to match the outermost Ok() and not any
  # nested inner view's Ok().
  "$nm_bin" --size-sort -S --demangle "$obj" 2>/dev/null |
    grep -E "GenericLargeConditionalsView<.*>::Ok\(\) const$" | tail -1 ||
    true
}

# --- ARM Cortex-M4 / Thumb-2 (STM32 family) ---
if command -v arm-none-eabi-g++ >/dev/null 2>&1; then
  ARM_OBJ="$OUT/many_conditionals.thumb.o"
  arm-none-eabi-g++ $EMBEDDED_FLAGS \
    -mthumb -mcpu=cortex-m4 -mfloat-abi=soft \
    $INCLUDES -c "$DRIVER" -o "$ARM_OBJ"
  report_size "ARM Cortex-M4 (Thumb-2, -Os)" arm-none-eabi-nm "$ARM_OBJ"
else
  echo "WARNING: arm-none-eabi-g++ not found, skipping ARM Cortex-M4 bench." >&2
fi

# --- MicroBlaze (big-endian) ---
MB_PREFIX="/opt/microblaze/microblazebe--glibc--stable-2025.08-1/bin/microblaze-buildroot-linux-gnu"
if [ -x "$MB_PREFIX-g++" ]; then
  MB_OBJ="$OUT/many_conditionals.microblaze.o"
  "$MB_PREFIX-g++" $EMBEDDED_FLAGS \
    $INCLUDES -c "$DRIVER" -o "$MB_OBJ"
  report_size "MicroBlaze (big-endian, -Os)" "$MB_PREFIX-nm" "$MB_OBJ"
else
  echo "WARNING: MicroBlaze g++ not found at $MB_PREFIX-g++, skipping MicroBlaze bench." >&2
fi

# --- Host x86-64 reference, same flags, for comparison ---
if command -v g++ >/dev/null 2>&1; then
  HOST_OBJ="$OUT/many_conditionals.x86_64.o"
  g++ $EMBEDDED_FLAGS \
    $INCLUDES -c "$DRIVER" -o "$HOST_OBJ"
  report_size "Host x86-64 (-Os)" nm "$HOST_OBJ"
else
  echo "WARNING: g++ not found, skipping Host x86-64 bench." >&2
fi
