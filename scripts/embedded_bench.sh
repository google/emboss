#!/bin/bash
# Cross-compile the many_conditionals.emb.h header on embedded toolchains and
# report .text and per-function sizes for the generated Ok() methods.
#
# Usage:  scripts/embedded_bench.sh <out-dir>
# Run from the repo root after regenerating goldens / building the header.
#
# Each target compiles a tiny TU that forces the relevant Ok() methods to be
# emitted, then reports `size` on the resulting object file plus a few key
# symbol sizes from `nm`. The script is idempotent: it leaves nothing behind
# inside the repo, only the requested out-dir.

set -euo pipefail

OUT="${1:-/tmp/embedded-bench}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$OUT"

# Regenerate the header from the current .emb file so we measure the live
# state of the generator.
python3 "$REPO/scripts/regenerate_goldens.py" >/dev/null

# Small TU that pulls Ok() into the object file. Without this every Ok() is
# a `weak` symbol the linker would dead-strip if unreachable.
DRIVER="$OUT/driver.cc"
cat > "$DRIVER" <<'CPP'
#include <cstdint>
#include "testdata/many_conditionals.emb.h"

// Sink for results so the compiler can't fold Ok() away.
volatile bool emboss_result_sink;

extern "C" void large_ok(const char *buf) {
  auto v = emboss::test::MakeLargeConditionalsView(buf, 100);
  emboss_result_sink = v.Ok();
}

extern "C" void disjunction_ok(const char *buf) {
  auto v = emboss::test::MakeDisjunctionConditionalsView(buf, 16);
  emboss_result_sink = v.Ok();
}
CPP

# Common flags. -Os for embedded space optimization, -ffunction-sections so
# each function ends up in its own .text.<symbol> section (makes
# nm/objdump --size-sort more meaningful), -fno-exceptions/-fno-rtti to
# match typical embedded builds.
EMBEDDED_FLAGS="-std=c++17 -Os -ffunction-sections -fdata-sections -fno-exceptions -fno-rtti"
INCLUDES="-I$REPO -I$REPO/testdata/golden_cpp"

# Headers reference '...emb.h' from testdata/, but the .emb.h files live in
# testdata/golden_cpp/. Drop a symlink so the include resolves.
mkdir -p "$OUT/include/testdata"
ln -sf "$REPO/testdata/golden_cpp/many_conditionals.emb.h" \
       "$OUT/include/testdata/many_conditionals.emb.h"

report_size() {
  local label="$1"
  local nm_bin="$2"
  local obj="$3"
  echo "=== $label ==="
  # `size` is part of binutils for the same target prefix, but the
  # canonical `size` from host binutils understands ELF objects from any
  # arch we'll see, so we use it unconditionally.
  size "$obj"
  echo "--- LargeConditionals::Ok() ---"
  # nm output has the type-template parameter list itself containing
  # `>` characters, so the regex uses `.*` (greedy) and anchors on
  # `>::Ok() const$` at end of line to ensure we match the outermost
  # `Ok()` method and not any nested inner view's `Ok()`.
  "$nm_bin" --size-sort -S --demangle "$obj" 2>/dev/null \
    | grep -E "GenericLargeConditionalsView<.*>::Ok\(\) const$" | tail -1 \
    || true
  echo "--- DisjunctionConditionals::Ok() ---"
  "$nm_bin" --size-sort -S --demangle "$obj" 2>/dev/null \
    | grep -E "GenericDisjunctionConditionalsView<.*>::Ok\(\) const$" | tail -1 \
    || true
}

# --- ARM Cortex-M4 / Thumb-2 (STM32 family) ---
ARM_OBJ="$OUT/many_conditionals.thumb.o"
arm-none-eabi-g++ $EMBEDDED_FLAGS \
  -mthumb -mcpu=cortex-m4 -mfloat-abi=soft \
  $INCLUDES -I"$OUT/include" \
  -c "$DRIVER" -o "$ARM_OBJ"
report_size "ARM Cortex-M4 (Thumb-2, -Os)" arm-none-eabi-nm "$ARM_OBJ"

# --- MicroBlaze ---
MB_PREFIX="/opt/microblaze/microblazebe--glibc--stable-2025.08-1/bin/microblaze-buildroot-linux-gnu"
MB_OBJ="$OUT/many_conditionals.microblaze.o"
"$MB_PREFIX-g++" $EMBEDDED_FLAGS \
  $INCLUDES -I"$OUT/include" \
  -c "$DRIVER" -o "$MB_OBJ"
report_size "MicroBlaze (big-endian, -Os)" "$MB_PREFIX-nm" "$MB_OBJ"

# --- Host x86-64 reference, same flags, for comparison ---
HOST_OBJ="$OUT/many_conditionals.x86_64.o"
g++ $EMBEDDED_FLAGS \
  $INCLUDES -I"$OUT/include" \
  -c "$DRIVER" -o "$HOST_OBJ"
report_size "Host x86-64 (-Os)" nm "$HOST_OBJ"
