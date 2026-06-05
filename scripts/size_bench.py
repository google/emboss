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

_MB = "/opt/microblaze/microblazebe--glibc--stable-2025.08-1/bin/microblaze-buildroot-linux-gnu"

# Measurement matrix. clang has no MicroBlaze back end and needs extra wiring to
# find the bare-metal ARM C++ headers, so clang is x86-64-only here; cross
# targets use their gcc toolchains. Host binutils `size`/`nm`/`objdump` read the
# x86-64 objects for both gcc and clang; cross targets use their own binutils.
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
        "target": "MicroBlaze",
        "compilers": [
            {
                "name": "gcc",
                "cxx": f"{_MB}-g++",
                "nm": f"{_MB}-nm",
                "objdump": f"{_MB}-objdump",
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
    '  extern "C" void bench_##NAME(char *a, char *b, ::std::size_t n) { \\\n'
    "    auto va = ::emboss::benchmark::MAKER(a, n); \\\n"
    "    auto vb = ::emboss::benchmark::MAKER(b, n); \\\n"
    "    g_sink ^= static_cast<::std::uint64_t>(va.Ok()); \\\n"
    "    va.CopyFrom(vb); \\\n"
    "  }\n\n" + "".join(f"BENCH({v}, Make{v}View)\n" for v in BENCHMARK_VIEWS)
)

# Highlight driver: forces the optimized many_conditionals Ok() to be emitted.
MANYCOND_DRIVER = (
    "#include <cstdint>\n\n"
    '#include "testdata/many_conditionals.emb.h"\n\n'
    "volatile bool emboss_result_sink;\n"
    'extern "C" void large_ok(const char *buf) {\n'
    "  auto v = ::emboss::test::MakeLargeConditionalsView(buf, 100);\n"
    "  emboss_result_sink = v.Ok();\n"
    "}\n"
)
MANYCOND_OK_SYMBOL = r"GenericLargeConditionalsView<.*>::Ok\(\) const$"


def run(args, **kw):
    """Runs a command, returning stripped stdout; raises on non-zero exit."""
    return subprocess.run(
        args, cwd=kw.pop("cwd", REPO), capture_output=True, text=True, check=True, **kw
    ).stdout.strip()


def have(compiler):
    """True if the compiler's executable is available."""
    cxx = compiler["cxx"]
    return bool(shutil.which(cxx) or (os.path.isabs(cxx) and os.path.exists(cxx)))


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


def insn_count(objdump, obj):
    """Static instruction count: disassembly lines that begin with an address."""
    out = subprocess.run(
        [objdump, "-d", obj], cwd=REPO, capture_output=True, text=True
    ).stdout
    return sum(1 for ln in out.splitlines() if re.match(r"\s+[0-9a-f]+:", ln))


def symbol_bytes(nm, obj, pattern):
    """Size in bytes of the last symbol matching `pattern` (nm --size-sort -S)."""
    out = subprocess.run(
        [nm, "--size-sort", "-S", "--demangle", obj],
        cwd=REPO,
        capture_output=True,
        text=True,
    ).stdout
    matches = [ln for ln in out.splitlines() if re.search(pattern, ln)]
    if not matches:
        return None
    return int(matches[-1].split()[1], 16)


def compile_obj(compiler, flags, driver_path, include_dir, obj):
    """Compiles a driver TU; returns True on success."""
    cmd = (
        [compiler["cxx"]]
        + COMMON_FLAGS.split()
        + flags.split()
        + compiler["flags"].split()
        + ["-I" + REPO, "-I" + include_dir, "-c", driver_path, "-o", obj]
    )
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True).returncode == 0


def measure_current(work):
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

    versions = {}
    results = {}
    for entry in TARGETS:
        target = entry["target"]
        results[target] = {}
        for compiler in entry["compilers"]:
            if not have(compiler):
                continue
            cname = compiler["name"]
            try:
                versions[f"{target}/{cname}"] = run(
                    [compiler["cxx"], "--version"]
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
                            "insns": insn_count(compiler["objdump"], obj),
                        }
                if have_manycond:
                    obj = os.path.join(work, f"mc_{target}_{cname}_{cfg}.o")
                    if compile_obj(compiler, cfg_flag, manycond_drv, include_dir, obj):
                        cell["many_conditionals_ok"] = {
                            "text": symbol_bytes(
                                compiler["nm"], obj, MANYCOND_OK_SYMBOL
                            ),
                            "insns": insn_count(compiler["objdump"], obj),
                        }
                results[target][cname][cfg] = cell
    return {"compiler_versions": versions, "results": results}


# ---- git revision driving (hold the schema fixed; vary only the generator) ----


def current_ref():
    r = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    return r.stdout.strip() if r.returncode == 0 else run(["git", "rev-parse", "HEAD"])


def measure_revision(rev, original_ref, work_root):
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
        return {"sha": sha, **measure_current(work)}
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
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    work_root = tempfile.mkdtemp(dir=args.out_dir)

    out = {"revisions": []}
    if args.revisions == ["HEAD"]:
        # Single-shot: measure the working tree as-is (no checkout dance).
        out["revisions"].append(
            {
                "sha": run(["git", "rev-parse", "HEAD"]),
                **measure_current(tempfile.mkdtemp(dir=work_root)),
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
                out["revisions"].append(measure_revision(rev, original, work_root))
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
