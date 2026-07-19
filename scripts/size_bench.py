#!/usr/bin/env python3

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

"""Measures the size and instruction count of Emboss-generated code.

Compiles a fixed benchmark schema (testdata/benchmark.emb) plus the
many_conditionals Ok() highlight across a matrix of target x compiler x
optimization level, reporting `.text` bytes and static instruction counts
(from objdump disassembly -- a deterministic stand-in for a runtime benchmark).

With --revisions BASE HEAD, each revision is measured with the benchmark schema
held fixed (pulled forward from HEAD), so only the code generator under test
varies between them. Results, including which compiler/version produced each
number, are written as JSON.

  python3 scripts/size_bench.py --revisions <base-sha> <head-sha> --out-dir out
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Common flags: C++17, per-function/data sections (so `size`/objdump are
# comparable), and no exceptions/RTTI to match typical embedded builds.
COMMON_FLAGS = (
    "-std=c++17 -ffunction-sections -fdata-sections -fno-exceptions -fno-rtti"
)
CONFIGS = {"Os": "-Os", "O2": "-O2", "O0": "-O0"}

# MicroBlaze big-endian (the toolchain the landed #257 numbers were measured on)
# and little-endian, both from Bootlin.
_MB_BE = "/opt/microblaze/microblazebe--glibc--stable-2025.08-1/bin/microblaze-buildroot-linux-gnu"
_MB_LE = "/opt/microblaze/microblazeel--glibc--stable-2025.08-1/bin/microblazeel-buildroot-linux-gnu"

# AMD/Xilinx Vitis MicroBlaze little-endian toolchain: the actually-shipped
# target, so authoritative for LE size. It is proprietary and locally-licensed,
# so it is never present in public CI -- have() skips it there, and the
# open-source Bootlin microblazeel build stands in as the CI little-endian proxy
# (its `.text`/Ok() numbers track BE closely; Vitis is the number that ships).
_VITIS = "/usr/local/google/edatools/xilinx/2025.2/Vitis"
_VITIS_MB = _VITIS + "/gnu/microblaze/lin/bin/mb"
_VITIS_ENV = {"LD_LIBRARY_PATH": _VITIS + "/lib/lnx64.o/Ubuntu/24"}
_VITIS_FLAGS = (
    "-mcpu=v11.0 -mlittle-endian -mxl-barrel-shift -mxl-pattern-compare "
    "-mno-xl-soft-mul -mno-xl-soft-div"
)

# Measurement matrix. clang has no MicroBlaze back end and needs extra wiring to
# find the bare-metal ARM C++ headers, so clang is x86-64-only here; cross
# targets use their gcc toolchains. Host binutils `size`/`nm`/`objdump` read the
# x86-64 objects for both gcc and clang; cross targets use their own binutils.
# A compiler may carry an "env" dict (extra process env, e.g. Vitis'
# LD_LIBRARY_PATH) applied to every compiler/binutils invocation for it.
TARGETS = [
    {
        "target": "x86-64",
        "compilers": [
            {
                "name": "gcc",
                "cxx": "g++",
                "nm": "nm",
                "objdump": "objdump",
                "flags": "",
            },
            {
                "name": "clang",
                "cxx": "clang++",
                "nm": "nm",
                "objdump": "objdump",
                "flags": "",
            },
        ],
    },
    {
        "target": "ARM Cortex-M4",
        "compilers": [
            {
                "name": "gcc",
                "cxx": "arm-none-eabi-g++",
                "nm": "arm-none-eabi-nm",
                "objdump": "arm-none-eabi-objdump",
                "flags": "-mthumb -mcpu=cortex-m4 -mfloat-abi=soft",
            },
        ],
    },
    {
        "target": "MicroBlaze BE",
        "compilers": [
            {
                "name": "gcc",
                "cxx": f"{_MB_BE}-g++",
                "nm": f"{_MB_BE}-nm",
                "objdump": f"{_MB_BE}-objdump",
                "flags": "",
            },
        ],
    },
    {
        # Authoritative little-endian size (the shipped target). Local-only.
        "target": "MicroBlaze LE (Vitis)",
        "compilers": [
            {
                "name": "gcc",
                "cxx": f"{_VITIS_MB}-g++",
                "nm": f"{_VITIS_MB}-nm",
                "objdump": f"{_VITIS_MB}-objdump",
                "flags": _VITIS_FLAGS,
                "env": _VITIS_ENV,
            },
        ],
    },
    {
        # Open-source little-endian proxy (available in CI where Vitis is not).
        "target": "MicroBlaze LE (Bootlin)",
        "compilers": [
            {
                "name": "gcc",
                "cxx": f"{_MB_LE}-g++",
                "nm": f"{_MB_LE}-nm",
                "objdump": f"{_MB_LE}-objdump",
                "flags": "",
            },
        ],
    },
]

# Schema inputs held fixed across revisions so only the generator varies.
PULL_FORWARD = ["testdata/benchmark.emb", "testdata/many_conditionals.emb"]

# Driver over benchmark.emb: one fn per top-level view, each exercising Ok()
# (validate/read) and CopyFrom() (read source + write dest). Compiled, never
# run, so field values / conditional activeness don't matter -- only emitted
# code. Keep the view list in sync with testdata/benchmark.emb.
BENCHMARK_VIEWS = ["Scalars", "Bitfields", "Repeated", "Conditional", "Nested"]
BENCHMARK_DRIVER = (
    "#include <cstddef>\n#include <cstdint>\n\n"
    '#include "testdata/benchmark.emb.h"\n\n'
    "namespace { volatile ::std::uint64_t g_sink; }\n\n"
    "#define BENCH(NAME, MAKER) \\\n"
    '  extern "C" void bench_##NAME(unsigned char *a, unsigned char *b, ::std::size_t n) { \\\n'
    "    auto va = ::emboss::benchmark::MAKER(a, n); \\\n"
    "    auto vb = ::emboss::benchmark::MAKER(b, n); \\\n"
    "    g_sink ^= static_cast<::std::uint64_t>(va.Ok()); \\\n"
    "    va.CopyFrom(vb); \\\n"
    "  }\n\n" + "".join(f"BENCH({v}, Make{v}View)\n" for v in BENCHMARK_VIEWS)
)

# Highlight driver: forces the optimized many_conditionals Ok() methods to be
# emitted. Both LargeConditionals (single-equality switch) and
# DisjunctionConditionals (||-coalesced switch) are measured -- the two shapes
# optimize differently, so both are load-bearing.
MANYCOND_DRIVER = (
    "#include <cstdint>\n\n"
    '#include "testdata/many_conditionals.emb.h"\n\n'
    "volatile bool emboss_result_sink;\n"
    'extern "C" void large_ok(const unsigned char *buf) {\n'
    "  auto v = ::emboss::test::MakeLargeConditionalsView(buf, 100);\n"
    "  emboss_result_sink = v.Ok();\n"
    "}\n"
    'extern "C" void disjunction_ok(const unsigned char *buf) {\n'
    "  auto v = ::emboss::test::MakeDisjunctionConditionalsView(buf, 16);\n"
    "  emboss_result_sink = v.Ok();\n"
    "}\n"
)
MANYCOND_OK_SYMBOL = r"GenericLargeConditionalsView<.*>::Ok\(\) const$"
MANYCOND_DISJ_OK_SYMBOL = r"GenericDisjunctionConditionalsView<.*>::Ok\(\) const$"

# Four TUs exercising distinct instantiations of the optimized Ok(), consumed by
# the later optimization phases:
#   reader_only    -- a read-only View Ok() (the shipped hot path)
#   both           -- read-only View Ok() + read-write Writer Ok()/CopyFrom()
#   writer_only    -- read-write Writer Ok()/CopyFrom() only (Lever B watches this
#                     for a regression when Ok() is deduped onto the reader)
#   residual_heavy -- a residual-guarded schema; stubbed on DisjunctionConditionals
#                     until Phase 2 adds an OuterGuardedUnion schema
# Read-only storage demangles as ContiguousBuffer<char const, ...>; read-write as
# ContiguousBuffer<char, ...>. ok_symbols() splits the two on that `const`.
_OK_HDR = (
    "#include <cstdint>\n\n"
    '#include "testdata/many_conditionals.emb.h"\n\n'
    "volatile bool emboss_ok_sink;\n\n"
)
_LARGE_READER = (
    'extern "C" void reader_ok(const unsigned char *buf) {\n'
    "  emboss_ok_sink = ::emboss::test::MakeLargeConditionalsView(buf, 100).Ok();\n"
    "}\n"
)
_LARGE_WRITER = (
    'extern "C" void writer_ok(unsigned char *a, unsigned char *b) {\n'
    "  auto va = ::emboss::test::MakeLargeConditionalsView(a, 100);\n"
    "  emboss_ok_sink = va.Ok();\n"
    "  va.CopyFrom(::emboss::test::MakeLargeConditionalsView(b, 100));\n"
    "}\n"
)
OK_DRIVERS = {
    "reader_only": _OK_HDR + _LARGE_READER,
    "both": _OK_HDR + _LARGE_READER + _LARGE_WRITER,
    "writer_only": _OK_HDR + _LARGE_WRITER,
    "residual_heavy": _OK_HDR
    + (
        'extern "C" void residual_ok(const unsigned char *buf) {\n'
        "  emboss_ok_sink = "
        "::emboss::test::MakeOuterGuardedUnionView(buf, 12).Ok();\n"
        "}\n"
    ),
}
# The struct whose Ok() each driver instantiates (for symbol classification).
OK_DRIVER_STRUCT = {
    "reader_only": "LargeConditionals",
    "both": "LargeConditionals",
    "writer_only": "LargeConditionals",
    "residual_heavy": "OuterGuardedUnion",
}

# ---- execution speed (opt-in via --speed) --------------------------------------
#
# Speed needs a *runnable* binary, so it uses linux-userspace toolchains (glibc)
# whose output runs under qemu-user -- distinct from the bare-metal size targets
# (arm-none-eabi, Vitis mb-elf), which can't. Two numbers per target:
#   * retired-instruction count -- deterministic, from qemu-user + the bundled
#     TCG plugin (scripts/emboss_insncount.c). This is the primary speed metric.
#   * host wall-clock seconds -- a real-time number, only meaningful natively
#     (x86); recorded for cross targets too but is emulated (qemu) time.
# Plugin-enabled qemu is not the distro build, so its location and the plugin
# .so are taken from env; when absent, retired-insn is skipped and only
# wall-clock (host) / static insn-count (all targets) remain -- the documented
# fallback. See scripts/build_qemu_plugin.sh.
SPEED_FLAGS = "-std=c++17 -Os -fno-exceptions -fno-rtti"
SPEED_ITERS = 5000  # x100 tags = 500k reader Ok() calls; loop dominates startup.
SPEED_TARGETS = [
    {"target": "x86-64", "cxx": "g++", "static": False, "qemu": None},
    {
        "target": "ARM (armhf)",
        "cxx": "arm-linux-gnueabihf-g++",
        "static": True,
        "qemu": "qemu-arm",
    },
    {
        "target": "MicroBlaze BE",
        "cxx": f"{_MB_BE}-g++",
        "static": True,
        "qemu": "qemu-microblaze",
    },
    {
        "target": "MicroBlaze LE",
        "cxx": f"{_MB_LE}-g++",
        "static": True,
        "qemu": "qemu-microblazeel",
    },
]
# Reader Ok() hot loop: a writer sets the tag, the read-only view validates. Both
# views alias one buffer, so the loop's work is dominated by the reader Ok().
SPEED_DRIVER = (
    "#include <chrono>\n#include <cstdint>\n#include <cstdio>\n\n"
    '#include "testdata/many_conditionals.emb.h"\n\n'
    "#ifndef EMBOSS_SPEED_ITERS\n#define EMBOSS_SPEED_ITERS 5000\n#endif\n\n"
    "int main() {\n"
    "  unsigned char buf[128] = {0};\n"
    "  auto w = ::emboss::test::MakeOuterGuardedUnionView(buf, 12);\n"
    "  w.outer().Write(1);\n"
    "  const unsigned char *cbuf = buf;\n"
    "  auto r = ::emboss::test::MakeOuterGuardedUnionView(cbuf, 12);\n"
    "  volatile bool sink = false;\n"
    "  auto t0 = ::std::chrono::steady_clock::now();\n"
    "  for (int i = 0; i < EMBOSS_SPEED_ITERS; ++i)\n"
    "    for (int tag = 0; tag < 100; ++tag) {\n"
    "      w.tag().Write(tag);\n"
    "      sink = r.Ok();\n"
    "    }\n"
    "  auto t1 = ::std::chrono::steady_clock::now();\n"
    '  ::std::printf("wallclock_s=%.6f\\n",\n'
    "                ::std::chrono::duration<double>(t1 - t0).count());\n"
    "  (void)sink;\n"
    "  return 0;\n"
    "}\n"
)


def run(args, **kw):
    """Runs a command, returning stripped stdout; raises on non-zero exit."""
    return subprocess.run(
        args, cwd=kw.pop("cwd", REPO), capture_output=True, text=True, check=True, **kw
    ).stdout.strip()


def have(compiler):
    """True if the compiler's executable is available."""
    cxx = compiler["cxx"]
    return bool(shutil.which(cxx) or (os.path.isabs(cxx) and os.path.exists(cxx)))


def compiler_env(compiler):
    """Process env for invoking `compiler` (and its binutils), or None.

    Some toolchains need extra environment -- e.g. Vitis' mb-g++/mb-nm need
    LD_LIBRARY_PATH to find their shared libs. Returns a full env dict (os.environ
    plus the override) when the compiler declares one, else None.
    """
    extra = compiler.get("env")
    if not extra:
        return None
    env = dict(os.environ)
    env.update(extra)
    return env


def embossc(emb, out_include_dir):
    """Generates the C++ header for `emb` under out_include_dir/testdata/."""
    out = os.path.join(out_include_dir, "testdata")
    os.makedirs(out, exist_ok=True)
    name = os.path.basename(emb) + ".h"
    run(
        [
            os.path.join(REPO, "embossc"),
            "--import-dir=.",
            "--import-dir=testdata",
            "--output-file=" + name,
            "--output-path=" + out,
            os.path.join("testdata", os.path.basename(emb)),
        ]
    )


def text_bytes(obj):
    """`.text` size of an object file, via host binutils `size`."""
    out = run(["size", obj])
    return int(out.splitlines()[1].split()[0])


def insn_count(objdump, obj, env=None):
    """Static instruction count: disassembly lines that begin with an address."""
    out = subprocess.run(
        [objdump, "-d", obj], cwd=REPO, capture_output=True, text=True, env=env
    ).stdout
    return sum(1 for ln in out.splitlines() if re.match(r"\s+[0-9a-f]+:", ln))


def symbol_bytes(nm, obj, pattern, env=None):
    """Size in bytes of the last symbol matching `pattern` (nm --size-sort -S)."""
    out = subprocess.run(
        [nm, "--size-sort", "-S", "--demangle", obj],
        cwd=REPO,
        capture_output=True,
        text=True,
        env=env,
    ).stdout
    matches = [ln for ln in out.splitlines() if re.search(pattern, ln)]
    if not matches:
        return None
    return int(matches[-1].split()[1], 16)


def ok_symbols(nm, obj, struct, env=None):
    """Reader/writer Ok() sizes for Generic<struct>View, as {'reader','writer'}.

    Read-only storage demangles as ContiguousBuffer<char const, ...> and
    read-write as ContiguousBuffer<char, ...>; the `const` in the storage arg
    (before `>::Ok`) tells them apart. Either value is None when its
    instantiation isn't present in the object.
    """
    pattern = rf"Generic{struct}View<.*>::Ok\(\) const$"
    out = subprocess.run(
        [nm, "--size-sort", "-S", "--demangle", obj],
        cwd=REPO,
        capture_output=True,
        text=True,
        env=env,
    ).stdout
    reader = writer = None
    for ln in out.splitlines():
        if not re.search(pattern, ln):
            continue
        size = int(ln.split()[1], 16)
        storage = ln.split(">::Ok")[0]  # exclude the trailing `Ok() const`
        if "const" in storage:
            reader = size if reader is None else max(reader, size)
        else:
            writer = size if writer is None else max(writer, size)
    return {"reader": reader, "writer": writer}


def compile_obj(compiler, flags, driver_path, include_dir, obj):
    """Compiles a driver TU; returns True on success."""
    cmd = (
        [compiler["cxx"]]
        + COMMON_FLAGS.split()
        + flags.split()
        + compiler["flags"].split()
        + ["-I" + REPO, "-I" + include_dir, "-c", driver_path, "-o", obj]
    )
    return (
        subprocess.run(
            cmd, cwd=REPO, capture_output=True, text=True, env=compiler_env(compiler)
        ).returncode
        == 0
    )


def _qemu_bin(name):
    """Resolve a plugin-enabled qemu-user binary: EMBOSS_QEMU_DIR first (a build
    with --enable-plugins), else PATH (the distro build, which usually can't load
    plugins -- only wall-clock works there)."""
    qdir = os.environ.get("EMBOSS_QEMU_DIR")
    if qdir:
        p = os.path.join(qdir, name)
        return p if os.path.exists(p) else None
    return shutil.which(name)


def measure_speed(work, include_dir):
    """Per runnable target: native/emulated wall-clock and (under a plugin-enabled
    qemu) a deterministic retired-instruction count. Returns {target: {...}}."""
    drv = os.path.join(work, "speed_driver.cc")
    with open(drv, "w") as f:
        f.write(SPEED_DRIVER)
    plugin = os.environ.get("EMBOSS_QEMU_PLUGIN")
    have_plugin = bool(plugin and os.path.exists(plugin))
    out = {}
    for st in SPEED_TARGETS:
        cxx = st["cxx"]
        if not (shutil.which(cxx) or os.path.exists(cxx)):
            continue
        exe = os.path.join(work, "speed_" + st["target"].replace(" ", "_"))
        cmd = (
            [cxx]
            + SPEED_FLAGS.split()
            + [f"-DEMBOSS_SPEED_ITERS={SPEED_ITERS}"]
            + (["-static"] if st["static"] else [])
            + ["-I" + REPO, "-I" + include_dir, drv, "-o", exe]
        )
        if subprocess.run(cmd, cwd=REPO, capture_output=True, text=True).returncode:
            continue
        cell = {"iters": SPEED_ITERS, "wallclock_s": None, "retired_insns": None}
        if st["qemu"] is None:
            # Host: native wall-clock is the real-time signal; best of a few runs.
            times = []
            for _ in range(3):
                r = subprocess.run([exe], cwd=REPO, capture_output=True, text=True)
                m = re.search(r"wallclock_s=([\d.]+)", r.stdout)
                if m:
                    times.append(float(m.group(1)))
            if times:
                cell["wallclock_s"] = min(times)
        else:
            # Cross target: retired-instruction count is the deterministic metric
            # (wall-clock under qemu measures emulation, not the target -- skipped).
            qemu = _qemu_bin(st["qemu"])
            if qemu and have_plugin:
                r = subprocess.run(
                    [qemu, "-plugin", plugin, exe],
                    cwd=REPO,
                    capture_output=True,
                    text=True,
                )
                m = re.search(r"insns:\s*(\d+)", r.stderr)
                if m:
                    cell["retired_insns"] = int(m.group(1))
        out[st["target"]] = cell
    return out


def measure_current(work, with_speed=False):
    """Measures the currently checked-out tree across the whole matrix."""
    include_dir = os.path.join(work, "include")
    os.makedirs(include_dir, exist_ok=True)

    # Generate headers with the revision's own embossc (the generator under
    # test). A revision that can't generate the fixed schema is reported as
    # missing rather than skewing a total.
    have_bench = have_manycond = True
    try:
        embossc("benchmark.emb", include_dir)
    except subprocess.CalledProcessError:
        have_bench = False
    try:
        embossc("many_conditionals.emb", include_dir)
    except subprocess.CalledProcessError:
        have_manycond = False

    bench_drv = os.path.join(work, "benchmark_driver.cc")
    manycond_drv = os.path.join(work, "manycond_driver.cc")
    with open(bench_drv, "w") as f:
        f.write(BENCHMARK_DRIVER)
    with open(manycond_drv, "w") as f:
        f.write(MANYCOND_DRIVER)
    ok_drv = {}
    for dname, dsrc in OK_DRIVERS.items():
        p = os.path.join(work, f"ok_{dname}_driver.cc")
        with open(p, "w") as f:
            f.write(dsrc)
        ok_drv[dname] = p

    versions = {}
    results = {}
    for entry in TARGETS:
        target = entry["target"]
        results[target] = {}
        for compiler in entry["compilers"]:
            if not have(compiler):
                continue
            cname = compiler["name"]
            cenv = compiler_env(compiler)
            objdump = compiler["objdump"]
            nm = compiler["nm"]
            try:
                versions[f"{target}/{cname}"] = run(
                    [compiler["cxx"], "--version"], env=cenv
                ).splitlines()[0]
            except Exception:  # noqa: BLE001
                versions[f"{target}/{cname}"] = "?"
            results[target][cname] = {}
            for cfg, cfg_flag in CONFIGS.items():
                cell = {}
                if have_bench:
                    obj = os.path.join(work, f"bench_{target}_{cname}_{cfg}.o")
                    if compile_obj(compiler, cfg_flag, bench_drv, include_dir, obj):
                        cell["benchmark"] = {
                            "text": text_bytes(obj),
                            "insns": insn_count(objdump, obj, cenv),
                        }
                if have_manycond:
                    obj = os.path.join(work, f"mc_{target}_{cname}_{cfg}.o")
                    if compile_obj(compiler, cfg_flag, manycond_drv, include_dir, obj):
                        cell["many_conditionals_ok"] = {
                            "text": symbol_bytes(nm, obj, MANYCOND_OK_SYMBOL, cenv),
                            "disj_text": symbol_bytes(
                                nm, obj, MANYCOND_DISJ_OK_SYMBOL, cenv
                            ),
                            "insns": insn_count(objdump, obj, cenv),
                        }
                    # Per-instantiation Ok() drivers for the later phases.
                    drivers = {}
                    for dname, dpath in ok_drv.items():
                        dobj = os.path.join(
                            work, f"ok_{dname}_{target}_{cname}_{cfg}.o"
                        )
                        if compile_obj(compiler, cfg_flag, dpath, include_dir, dobj):
                            syms = ok_symbols(nm, dobj, OK_DRIVER_STRUCT[dname], cenv)
                            drivers[dname] = {
                                "text": text_bytes(dobj),
                                "insns": insn_count(objdump, dobj, cenv),
                                "reader_ok": syms["reader"],
                                "writer_ok": syms["writer"],
                            }
                    if drivers:
                        cell["ok_drivers"] = drivers
                results[target][cname][cfg] = cell
    out = {"compiler_versions": versions, "results": results}
    if with_speed:
        out["speed"] = measure_speed(work, include_dir)
    return out


# ---- git revision driving (hold the schema fixed; vary only the generator) ----


def current_ref():
    r = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    return r.stdout.strip() if r.returncode == 0 else run(["git", "rev-parse", "HEAD"])


def measure_revision(rev, original_ref, work_root, with_speed=False):
    sha = run(["git", "rev-parse", rev])
    run(["git", "checkout", sha])
    # Pull the fixed schema forward from the starting ref so the only thing that
    # differs between revisions is the generator (and runtime) under test.
    for path in PULL_FORWARD:
        subprocess.run(
            ["git", "checkout", original_ref, "--", path], cwd=REPO, capture_output=True
        )
    try:
        work = tempfile.mkdtemp(dir=work_root)
        return {"sha": sha, **measure_current(work, with_speed=with_speed)}
    finally:
        run(["git", "reset", "--hard"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--revisions",
        nargs="+",
        default=["HEAD"],
        help="Revisions to measure; with two, the first is the base for deltas.",
    )
    parser.add_argument("--out-dir", default="size_results")
    parser.add_argument(
        "--speed",
        action="store_true",
        help="Also measure execution speed (wall-clock + qemu retired-insns). "
        "Needs the linux-user toolchains; retired-insns need a plugin-enabled "
        "qemu via EMBOSS_QEMU_DIR + EMBOSS_QEMU_PLUGIN (see build_qemu_plugin.sh).",
    )
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    work_root = tempfile.mkdtemp(dir=args.out_dir)

    out = {"revisions": []}
    if args.revisions == ["HEAD"]:
        # Single-shot: measure the working tree as-is (no checkout dance).
        out["revisions"].append(
            {
                "sha": run(["git", "rev-parse", "HEAD"]),
                **measure_current(
                    tempfile.mkdtemp(dir=work_root), with_speed=args.speed
                ),
            }
        )
    else:
        if subprocess.run(
            ["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True
        ).stdout.strip():
            print(
                "error: working tree is dirty; commit or stash first.", file=sys.stderr
            )
            return 1
        original = current_ref()
        try:
            for rev in args.revisions:
                print(f"Measuring {rev}...", file=sys.stderr)
                out["revisions"].append(
                    measure_revision(rev, original, work_root, with_speed=args.speed)
                )
        finally:
            run(["git", "checkout", original])
            run(["git", "reset", "--hard"])

    if len(out["revisions"]) >= 2:
        out["base"] = out["revisions"][0]["sha"]
        out["head"] = out["revisions"][-1]["sha"]

    path = os.path.join(args.out_dir, "size_bench.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
