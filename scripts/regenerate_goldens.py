#!/usr/bin/env python3
"""Regenerates testdata/golden_cpp/*.h files.

Run from the repo root. Mirrors the cpp_golden_test list in
compiler/back_end/cpp/BUILD.
"""

import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Golden tests: emb file (under testdata/) -> golden file (under testdata/golden_cpp/).
# All cpp_golden_test entries from compiler/back_end/cpp/BUILD.
GOLDENS = [
    ("anonymous_bits.emb", "anonymous_bits.emb.h"),
    ("bits.emb", "bits.emb.h"),
    ("absolute_cpp_namespace.emb", "absolute_cpp_namespace.emb.h"),
    ("alignments.emb", "alignments.emb.h"),
    ("auto_array_size.emb", "auto_array_size.emb.h"),
    ("bcd.emb", "bcd.emb.h"),
    ("complex_offset.emb", "complex_offset.emb.h"),
    ("complex_structure.emb", "complex_structure.emb.h"),
    ("condition.emb", "condition.emb.h"),
    ("cpp_namespace.emb", "cpp_namespace.emb.h"),
    ("dynamic_size.emb", "dynamic_size.emb.h"),
    ("enum_case.emb", "enum_case.emb.h"),
    ("enum.emb", "enum.emb.h"),
    ("explicit_sizes.emb", "explicit_sizes.emb.h"),
    ("float.emb", "float.emb.h"),
    ("imported.emb", "imported.emb.h"),
    ("inline_type.emb", "inline_type.emb.h"),
    ("int_sizes.emb", "int_sizes.emb.h"),
    ("large_array.emb", "large_array.emb.h"),
    ("nested_structure.emb", "nested_structure.emb.h"),
    ("next_keyword.emb", "next_keyword.emb.h"),
    ("no_cpp_namespace.emb", "no_cpp_namespace.emb.h"),
    ("no_enum_traits.emb", "no_enum_traits.emb.h"),
    ("parameters.emb", "parameters.emb.h"),
    ("requires.emb", "requires.emb.h"),
    ("start_size_range.emb", "start_size_range.emb.h"),
    ("subtypes.emb", "subtypes.emb.h"),
    ("text_format.emb", "text_format.emb.h"),
    ("uint_sizes.emb", "uint_sizes.emb.h"),
    ("virtual_field.emb", "virtual_field.emb.h"),
    ("importer.emb", "importer.emb.h"),
    ("importer2.emb", "importer2.emb.h"),
    ("many_conditionals.emb", "many_conditionals.emb.h"),
]


# imported_genfiles.emb is produced by a genrule from imported.emb.
# Reproduce that sed transformation so the golden stays in sync.
def _ensure_imported_genfiles():
    src = os.path.join(REPO, "testdata", "imported.emb")
    dst = os.path.join(REPO, "testdata", "imported_genfiles.emb")
    with open(src, "r") as f:
        contents = f.read()
    contents = contents.replace("emboss::test", "emboss::test::generated")
    with open(dst, "w") as f:
        f.write(contents)


def _no_enum_traits_args(emb_file):
    # The golden test for no_enum_traits.emb actually runs with default
    # (traits-enabled) settings; the file just verifies that the schema
    # parses when traits are disabled in downstream tests.
    return []


def main():
    _ensure_imported_genfiles()
    try:
        embossc = os.path.join(REPO, "embossc")
        out_dir = os.path.join(REPO, "testdata", "golden_cpp")
        failures = []
        for emb, golden in GOLDENS + [
            ("imported_genfiles.emb", "imported_genfiles.emb.h")
        ]:
            emb_path = os.path.join("testdata", emb)
            cmd = (
                [
                    embossc,
                    "--import-dir=.",
                    "--import-dir=testdata",
                    "--output-file=" + golden,
                    "--output-path=" + out_dir,
                ]
                + _no_enum_traits_args(emb)
                + [emb_path]
            )
            result = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
            if result.returncode != 0:
                failures.append((emb, result.stderr))
                print(f"FAIL {emb}\n{result.stderr}", file=sys.stderr)
            else:
                print(f"OK   {emb}")
        if failures:
            sys.exit(1)
    finally:
        # imported_genfiles.emb is a build artifact; remove it so it doesn't
        # collide with the genrule that produces it during a bazel build.
        gen = os.path.join(REPO, "testdata", "imported_genfiles.emb")
        if os.path.exists(gen):
            os.remove(gen)


if __name__ == "__main__":
    main()
