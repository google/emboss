#!/bin/bash

set -e
set -x

# Bazel sets TEST_TMPDIR to a temporary directory for the test to use.
readonly GEN_DIR="$TEST_TMPDIR/generated_headers"
mkdir -p "$GEN_DIR"

# The script's working directory is the root of the runfiles tree.
# All data dependencies are available at their workspace-relative paths.
export PYTHONPATH=.

for emb_file in $(find testdata -maxdepth 1 -name "*.emb" -not -name "importer.emb" -not -name "importer2.emb" -not -name "imported_genfiles.emb"); do
  base_name=$(basename "$emb_file")
  ir_file="$TEST_TMPDIR/${base_name}.ir.json"
  h_file="$GEN_DIR/${base_name}.h"

  # Run the compiler.
  python3 compiler/front_end/emboss_front_end.py --output-file "$ir_file" "$emb_file"
  python3 compiler/back_end/cpp/emboss_codegen_cpp.py --input-file "$ir_file" --output-file "$h_file"
done

# Compare the generated files with the golden files.
echo "Comparing generated files to golden files..."
diff --brief --recursive --strip-trailing-cr --exclude="generate_golden_files.sh" "$GEN_DIR" "testdata/golden_cpp"
