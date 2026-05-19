#!/bin/bash
# Run scripts/embedded_bench.sh twice — once on master, once on the current
# branch — and print a side-by-side comparison.
#
# Usage:  scripts/embedded_compare.sh [base-ref]
#         base-ref defaults to master.
#
# Must be run from a clean working tree. Restores the originally-checked-out
# branch at the end.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

BASE="${1:-master}"
BRANCH_REF="$(git symbolic-ref --short HEAD)"

# Refresh the index's stat cache; without this, a prior write to a
# tracked file (e.g. running the regen script earlier) leaves a stale
# diff-index even though the contents are identical to HEAD.
git update-index --refresh >/dev/null 2>&1 || true
if ! git diff-index --quiet HEAD; then
  echo "Working tree has uncommitted changes; commit/stash first." >&2
  exit 1
fi

OUT_BRANCH="$(mktemp -d)"
OUT_BASE="$(mktemp -d)"

echo "Running on $BRANCH_REF..."
scripts/embedded_bench.sh "$OUT_BRANCH" > "$OUT_BRANCH/log.txt" 2>&1

echo "Running on $BASE..."
restore_branch() {
  # Discard any goldens the regen script may have rewritten on the way
  # back to the original branch.
  git checkout -- testdata/golden_cpp/ 2>/dev/null || true
  git checkout -- testdata/many_conditionals.emb 2>/dev/null || true
  rm -f testdata/imported_genfiles.emb
  git checkout "$BRANCH_REF" >/dev/null 2>&1 || true
}
trap restore_branch EXIT

git checkout "$BASE" >/dev/null
# Pull the test schema/benchmark/scripts forward so the comparison
# measures the generator output, not the test surface area.
git checkout "$BRANCH_REF" -- \
    testdata/many_conditionals.emb \
    compiler/back_end/cpp/testcode/many_conditionals_benchmark.cc \
    scripts/embedded_bench.sh \
    scripts/regenerate_goldens.py >/dev/null
bash scripts/embedded_bench.sh "$OUT_BASE" > "$OUT_BASE/log.txt" 2>&1

# regen rewrote the goldens against master's generator; throw those
# changes away so the trap can switch branches cleanly.
git checkout -- testdata/golden_cpp/ testdata/many_conditionals.emb 2>/dev/null || true
rm -f testdata/imported_genfiles.emb

# --- Format report ---
echo
echo "============================================================"
echo "  $BASE  →  $BRANCH_REF"
echo "============================================================"
python3 - "$OUT_BASE/log.txt" "$OUT_BRANCH/log.txt" <<'PY'
import re, sys

base_path, branch_path = sys.argv[1], sys.argv[2]

def parse(path):
    with open(path) as f:
        text = f.read()
    out = {}
    current_target = None
    for line in text.splitlines():
        m = re.match(r"=== (.+) ===", line)
        if m:
            current_target = m.group(1)
            out[current_target] = {}
            continue
        m = re.match(r"--- (.+) ---", line)
        if m:
            label = m.group(1)
            out[current_target]["_pending_label"] = label
            continue
        # Size line like "  18962      0      1  18963   4a13  /path"
        m = re.match(r"\s*(\d+)\s+\d+\s+\d+\s+\d+\s+[0-9a-f]+\s+\S+", line)
        if m and "_pending_label" not in out.get(current_target, {}):
            out[current_target]["TU .text"] = int(m.group(1))
            continue
        # nm size line: "address size W symbol"
        m = re.match(r"[0-9a-f]+\s+([0-9a-f]+)\s+\w\s", line)
        if m and "_pending_label" in out[current_target]:
            label = out[current_target].pop("_pending_label")
            out[current_target][label] = int(m.group(1), 16)
    return out

base = parse(base_path)
branch = parse(branch_path)

targets = list(base.keys())
metrics = ["TU .text", "LargeConditionals::Ok()", "DisjunctionConditionals::Ok()"]

w_target = max(len(t) for t in targets)
print(f"{'Target':<{w_target}}  {'Metric':<32} {'Base':>10} {'Branch':>10} {'Delta':>10} {'%':>7}")
print("-" * (w_target + 75))
for tgt in targets:
    for m in metrics:
        b = base[tgt].get(m)
        n = branch[tgt].get(m)
        if b is None or n is None:
            continue
        delta = n - b
        pct = (delta / b * 100) if b else 0
        print(f"{tgt:<{w_target}}  {m:<32} {b:>10} {n:>10} {delta:>+10} {pct:>+6.1f}%")
PY
