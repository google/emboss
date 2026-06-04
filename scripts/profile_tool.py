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

"""Profiles Emboss generator output size across git revisions and compiler flags.

For each requested revision the tool:
  1. Checks out the revision.
  2. Pulls the benchmark schema and harness forward from the starting revision,
     so the comparison measures the code generator and not the test surface.
  3. Runs scripts/embedded_bench.sh under each compiler configuration.
  4. Collects the per-target TU size and per-Ok()-symbol sizes.
  5. Writes a markdown report with deltas against the first (baseline) revision.

Must be run from the repo root with a clean working tree. The originally
checked-out branch and a clean tree are restored on completion (or failure).

Example:
  python3 scripts/profile_tool.py --revisions <baseline-sha> HEAD
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile

# Default compiler configurations to sweep, as name -> flag string. Override
# with --configs pointing at a JSON file of the same shape.
DEFAULT_CONFIGS = {
    "Os": "-std=c++17 -Os -ffunction-sections -fdata-sections -fno-exceptions -fno-rtti",
    "O2": "-std=c++17 -O2 -ffunction-sections -fdata-sections -fno-exceptions -fno-rtti",
    "O0": "-std=c++17 -O0 -ffunction-sections -fdata-sections -fno-exceptions -fno-rtti",
}

# Files pulled forward from the starting revision to every profiled revision so
# the schema and harness stay fixed while only the generator under test varies.
BENCHMARK_FILES = [
    "testdata/many_conditionals.emb",
    "scripts/embedded_bench.sh",
    "scripts/regenerate_goldens.py",
    "scripts/profile_tool.py",  # keep this script itself consistent
]


def run_cmd(args, cwd=None, env=None, capture=True):
    """Runs a command, returning stripped stdout, raising on non-zero exit."""
    try:
        result = subprocess.run(
            args, cwd=cwd, env=env, capture_output=capture, text=True, check=True
        )
        return result.stdout.strip() if capture else ""
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {' '.join(args)}")
        if capture:
            print(f"Stdout:\n{e.stdout}")
            print(f"Stderr:\n{e.stderr}")
        raise


def get_current_branch_or_commit(repo_dir):
    """Returns the current branch name, or the commit SHA if detached."""
    result = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_dir)


def is_dirty(repo_dir):
    """Returns True if the working tree has uncommitted changes."""
    return bool(run_cmd(["git", "status", "--porcelain"], cwd=repo_dir))


def parse_bench_output(text):
    """Parses embedded_bench.sh output into {target: {tu_size, symbols}}."""
    results = {}
    current_target = None
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # Target header: "=== <target> ==="
        m = re.match(r"=== (.*) ===", line)
        if m:
            current_target = m.group(1)
            results[current_target] = {"symbols": {}}
            i += 1
            continue

        if current_target:
            # `size` column header, followed by the size row on the next line.
            if re.match(r"text\s+data\s+bss\s+dec\s+hex\s+filename", line):
                i += 1
                if i < len(lines):
                    m_sizes = re.match(
                        r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([0-9a-fA-F]+)\s+(\S+)",
                        lines[i].strip(),
                    )
                    if m_sizes:
                        results[current_target]["tu_size"] = int(m_sizes.group(1))
                i += 1
                continue

            # Symbol header: "--- <symbol> ---", followed by the nm line.
            m_sym = re.match(r"--- (.*) ---", line)
            if m_sym:
                current_symbol = m_sym.group(1)
                i += 1
                if i < len(lines):
                    nm_line = lines[i].strip()
                    if (
                        nm_line
                        and not nm_line.startswith("---")
                        and not nm_line.startswith("===")
                    ):
                        # nm --size-sort -S: "<address> <size> <type> <name>"
                        parts = nm_line.split()
                        if len(parts) >= 2:
                            try:
                                size = int(parts[1], 16)
                                results[current_target]["symbols"][
                                    current_symbol
                                ] = size
                            except ValueError:
                                pass
                        i += 1
                continue

        i += 1
    return results


def run_bench_for_config(repo_dir, config_flags, out_dir):
    """Runs embedded_bench.sh once with the given flags and parses its output."""
    env = os.environ.copy()
    env["EMBOSS_BENCH_FLAGS"] = config_flags
    bench_out_dir = os.path.join(out_dir, "bench_run")
    if os.path.exists(bench_out_dir):
        shutil.rmtree(bench_out_dir)
    os.makedirs(bench_out_dir)

    stdout = run_cmd(
        ["bash", "scripts/embedded_bench.sh", bench_out_dir],
        cwd=repo_dir,
        env=env,
    )
    return parse_bench_output(stdout)


def simplify_symbol_name(sym):
    """Shortens a Generic<Name>View<...>::Method symbol to <Name>::Method."""
    m = re.search(r"Generic([A-Za-z0-9_]+)View<.*>::([A-Za-z0-9_]+)", sym)
    if m:
        return f"{m.group(1)}::{m.group(2)}"
    parts = sym.split("::")
    if len(parts) >= 2:
        return "::".join(parts[-2:])
    return sym


def _delta_cell(value, baseline):
    """Formats a "+N (+P%)" delta cell, or "-"/"N/A" when not comparable."""
    if baseline is None or not isinstance(value, int):
        return "N/A"
    delta = value - baseline
    pct = (delta / baseline * 100) if baseline else 0.0
    return f"{delta:+d} ({pct:+.1f}%)"


def generate_report(results, configs, out_dir):
    """Writes a markdown report of TU and per-symbol sizes with baseline deltas."""
    report_path = os.path.join(out_dir, "profile_report.md")
    revisions = list(results.keys())
    with open(report_path, "w") as f:
        f.write("# Emboss Optimization Profile Report\n\n")
        if not revisions:
            f.write("No results.\n")
            return

        baseline_rev = revisions[0]
        f.write(f"Baseline revision: `{baseline_rev}`\n\n")

        for config_name, config_flags in configs.items():
            f.write(f"## Configuration: {config_name}\n")
            f.write(f"Flags: `{config_flags}`\n\n")

            targets = set()
            for rev in revisions:
                if results[rev].get(config_name):
                    targets.update(results[rev][config_name].keys())

            if not targets:
                f.write("No targets built for this configuration.\n\n")
                continue

            for target in sorted(targets):
                f.write(f"### Target: {target}\n\n")

                symbols = set()
                for rev in revisions:
                    data = results[rev].get(config_name, {}).get(target)
                    if data:
                        symbols.update(data["symbols"].keys())
                symbols = sorted(symbols)

                headers = ["Revision", "TU Size (bytes)", "Delta"]
                for sym in symbols:
                    headers.extend([f"{simplify_symbol_name(sym)} (bytes)", "Delta"])
                f.write("| " + " | ".join(headers) + " |\n")
                f.write("| " + " | ".join(["---"] * len(headers)) + " |\n")

                base = results[baseline_rev].get(config_name, {}).get(target)
                for rev in revisions:
                    data = results[rev].get(config_name, {}).get(target)
                    row = [f"`{rev}`"]
                    if not data:
                        row.extend(["N/A", ""] * (1 + len(symbols)))
                        f.write("| " + " | ".join(row) + " |\n")
                        continue

                    tu_size = data.get("tu_size", "N/A")
                    row.append(str(tu_size))
                    if rev == baseline_rev:
                        row.append("-")
                    else:
                        base_tu = base.get("tu_size") if base else None
                        row.append(_delta_cell(tu_size, base_tu))

                    for sym in symbols:
                        sym_size = data["symbols"].get(sym, "N/A")
                        row.append(str(sym_size))
                        if rev == baseline_rev:
                            row.append("-")
                        else:
                            base_sym = base["symbols"].get(sym) if base else None
                            row.append(_delta_cell(sym_size, base_sym))

                    f.write("| " + " | ".join(row) + " |\n")
                f.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--revisions",
        nargs="+",
        default=["HEAD"],
        help="Git revisions to profile; the first is the baseline.",
    )
    parser.add_argument(
        "--configs",
        help="JSON file of compiler configurations (name -> flag string).",
    )
    parser.add_argument(
        "--out-dir",
        default="profile_results",
        help="Directory for the report and raw results.",
    )
    args = parser.parse_args()

    repo_dir = os.getcwd()
    if is_dirty(repo_dir):
        print("Error: working tree is dirty. Please commit or stash changes.")
        return 1

    configs = DEFAULT_CONFIGS
    if args.configs:
        with open(args.configs) as f:
            configs = json.load(f)

    original_rev = get_current_branch_or_commit(repo_dir)
    print(f"Original revision: {original_rev}")

    results = {}  # rev -> config -> target -> metrics
    os.makedirs(args.out_dir, exist_ok=True)
    tmp_run_dir = tempfile.mkdtemp(dir=args.out_dir)

    try:
        for rev in args.revisions:
            print(f"\n--- Processing revision: {rev} ---")
            rev_sha = run_cmd(["git", "rev-parse", rev], cwd=repo_dir)
            print(f"Resolved {rev} to {rev_sha}; checking out...")
            run_cmd(["git", "checkout", rev_sha], cwd=repo_dir)

            print("Pulling forward benchmark files...")
            for path in BENCHMARK_FILES:
                try:
                    run_cmd(["git", "checkout", original_rev, "--", path], cwd=repo_dir)
                except subprocess.CalledProcessError:
                    print(f"  Warning: could not pull forward {path}")

            results[rev] = {}
            for config_name, config_flags in configs.items():
                print(f"  Running config {config_name} ({config_flags})...")
                try:
                    results[rev][config_name] = run_bench_for_config(
                        repo_dir, config_flags, tmp_run_dir
                    )
                except Exception as e:  # noqa: BLE001 - report and continue
                    print(f"    Error running config {config_name}: {e}")
                    results[rev][config_name] = None

            run_cmd(["git", "reset", "--hard"], cwd=repo_dir)
    finally:
        print(f"\nRestoring original revision: {original_rev}...")
        run_cmd(["git", "checkout", original_rev], cwd=repo_dir)
        run_cmd(["git", "reset", "--hard"], cwd=repo_dir)
        shutil.rmtree(tmp_run_dir, ignore_errors=True)

    with open(os.path.join(args.out_dir, "raw_results.json"), "w") as f:
        json.dump(results, f, indent=2)

    generate_report(results, configs, args.out_dir)
    print(f"\nProfile complete. Report written to {args.out_dir}/profile_report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
