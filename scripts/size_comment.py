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

"""Renders a Markdown PR comment from size_bench.py JSON (base vs head)."""

import json
import re
import sys

MARKER = "<!-- emboss-size-bench -->"


def short_ver(v):
    """Pull an X.Y[.Z] version number out of a compiler --version line."""
    # Compilers print the real version last (after any distro/buildroot tag).
    matches = re.findall(r"\d+\.\d+(?:\.\d+)?", v or "")
    return matches[-1] if matches else "?"


CONFIGS = ["Os", "O2", "O0"]


def cell(rev, target, compiler, config):
    return (rev["results"].get(target, {}).get(compiler, {}) or {}).get(
        config, {}
    ) or {}


def delta(base_v, head_v, unit=""):
    """'1234 B  🟢−5' style cell: head value + colored delta (smaller is better)."""
    if head_v is None:
        return "—"
    s = f"{head_v}{unit}"
    if base_v is None:
        return s
    d = head_v - base_v
    if d == 0:
        return s
    pct = f"{d / base_v * 100:+.1f}%" if base_v else ""
    icon = "🟢" if d < 0 else "🔴"
    return f"{s}  {icon}{d:+d} ({pct})"


def rows(base, head):
    """Ordered (target, compiler) pairs present in head."""
    out = []
    for target in head["results"]:
        for compiler in head["results"][target]:
            out.append((target, compiler))
    return out


def table(base, head, config):
    lines = [
        "| Target · Compiler | Code size | Instructions | `many_conditionals Ok()` |",
        "|---|--:|--:|--:|",
    ]
    for target, compiler in rows(base, head):
        b = cell(base, target, compiler, config)
        h = cell(head, target, compiler, config)
        bb, hb = b.get("benchmark", {}), h.get("benchmark", {})
        bm, hm = b.get("many_conditionals_ok", {}), h.get("many_conditionals_ok", {})
        lines.append(
            f"| {target} · {compiler} "
            f"| {delta(bb.get('text'), hb.get('text'), ' B')} "
            f"| {delta(bb.get('insns'), hb.get('insns'))} "
            f"| {delta(bm.get('text'), hm.get('text'), ' B')} |"
        )
    return "\n".join(lines)


def verdict(base, head):
    """Headline focused on `.text` (size) regressions, with a worst-case call-out."""
    worst = None  # (delta_bytes, pct, label)
    improved = 0
    for target, compiler in rows(base, head):
        for config in CONFIGS:
            b = cell(base, target, compiler, config)
            h = cell(head, target, compiler, config)
            for key, label in (
                ("benchmark", "bench .text"),
                ("many_conditionals_ok", "Ok()"),
            ):
                bv = (b.get(key) or {}).get("text")
                hv = (h.get(key) or {}).get("text")
                if bv is None or hv is None:
                    continue
                if hv > bv:
                    pct = (hv - bv) / bv * 100 if bv else 0.0
                    if worst is None or (hv - bv) > worst[0]:
                        worst = (hv - bv, pct, f"{target} {compiler} {label} -{config}")
                elif hv < bv:
                    improved += 1
    if worst:
        d, pct, lbl = worst
        return f"⚠️ largest size regression +{d} B ({pct:+.1f}%) on {lbl}"
    if improved:
        return f"🟢 smaller in {improved} place(s), none larger"
    return "✅ no change"


def render(data):
    revs = data.get("revisions", [])
    if len(revs) < 2:
        return MARKER + "\n_Need a base and head revision to compare._"
    base, head = revs[0], revs[-1]
    versions = " · ".join(
        f"{k.replace('/', ' ')} {short_ver(v)}"
        for k, v in head.get("compiler_versions", {}).items()
    )

    out = [
        MARKER,
        "### 📐 Generated code size & instructions",
        f"`{base['sha'][:9]} → {head['sha'][:9]}` · smaller is better · **{verdict(base, head)}**",
        "",
        "<sub>**Code size** (compiled `.text` bytes) and **Instructions** (objdump count) are totals "
        "for the generated code of the all-features `benchmark.emb` fixture. **`many_conditionals Ok()`** "
        "is the size (bytes) of the optimized conditional-validation method, a highlight. "
        "Δ vs the merge-base · 🟢 smaller / 🔴 larger.</sub>",
        "",
        "#### `-Os` (embedded)",
        table(base, head, "Os"),
        "",
        "<details><summary><code>-O2</code> / <code>-O0</code></summary>",
        "",
        "**`-O2`**",
        table(base, head, "O2"),
        "",
        "**`-O0`**",
        table(base, head, "O0"),
        "",
        "</details>",
        "",
        f"<sub>Compilers: {versions}. `benchmark.emb` is a fixed fixture (Ok()+CopyFrom over every "
        "top-level view); it is pulled forward from head, so only the code generator under test "
        "varies between base and head.</sub>",
    ]
    return "\n".join(out)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "size_results/size_bench.json"
    with open(path) as f:
        print(render(json.load(f)))


if __name__ == "__main__":
    main()
