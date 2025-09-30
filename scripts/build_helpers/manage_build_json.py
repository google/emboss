#!/usr/bin/env python3

# Copyright 2025 Google LLC
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

"""Creates and validates the `build.json` file."""

import argparse
import json
import os
import subprocess
import sys

# The Bazel targets that define the embossc compiler sources.
EMBOSSC_TARGETS = [
    "//compiler/back_end/cpp:emboss_codegen_cpp",
    "//compiler/front_end:emboss_front_end",
]

# The Bazel target for the C++ runtime sources.
RUNTIME_CPP_TARGET = "//runtime/cpp:cpp_utils"


def get_bazel_query_output(query):
    """Runs a Bazel query and returns the output as a list of strings."""
    result = subprocess.run(
        ["bazel", "query", query],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip().split("\n")


def get_source_files_for_targets(targets):
    """Queries Bazel for all source files in the transitive dependencies."""
    query = f"kind('source file', deps({'+'.join(targets)}))"
    output = get_bazel_query_output(query)
    return sorted(
        [
            f.replace("//", "").replace(":", "/")
            for f in output
            if f.startswith("//") and not f.startswith("//external")
        ]
    )


def read_build_json(file_path):
    """Reads build.json, strips comments, and returns the parsed JSON data."""
    with open(file_path, "r") as f:
        content = "".join(line for line in f if not line.strip().startswith("//"))
    return json.loads(content)


def find_init_py_files(source_files):
    """Finds all __init__.py files in the directories of the source files."""
    init_py_files = set()
    checked_dirs = set()

    for source_file in source_files:
        dir_path = os.path.dirname(source_file)
        while dir_path and dir_path not in checked_dirs:
            checked_dirs.add(dir_path)
            init_py = os.path.join(dir_path, "__init__.py")
            if os.path.exists(init_py):
                init_py_files.add(init_py)
            # Move to the parent directory
            parent_dir = os.path.dirname(dir_path)
            if parent_dir == dir_path:  # Root directory
                break
            dir_path = parent_dir

    return sorted(list(init_py_files))


def generate_build_json(output_path):
    """Generates the build.json file from Bazel sources."""
    print("Generating fresh source lists from Bazel...")
    embossc_sources = get_source_files_for_targets(EMBOSSC_TARGETS)
    embossc_sources.append("embossc")
    init_py_sources = find_init_py_files(embossc_sources)
    all_embossc_sources = sorted(list(set(embossc_sources + init_py_sources)))

    runtime_cpp_sources = get_source_files_for_targets([RUNTIME_CPP_TARGET])

    build_data = {
        "embossc_sources": all_embossc_sources,
        "emboss_runtime_cpp_sources": runtime_cpp_sources,
    }

    # Use json.dumps to get a formatted string, then inject comments.
    json_string = json.dumps(build_data, indent=2)
    json_string = json_string.replace(
        '"embossc_sources":',
        '// A list of all source files required to build the Emboss compiler.\n  "embossc_sources":',
    )
    json_string = json_string.replace(
        '"emboss_runtime_cpp_sources":',
        '// A list of all source files required for the Emboss C++ runtime.\n  "emboss_runtime_cpp_sources":',
    )

    with open(output_path, "w") as f:
        f.write(json_string)
        f.write("\n")

    print(f"Successfully generated {output_path}")
    return 0


def validate_build_json(file_path):
    """Validates that the on-disk build.json file is up-to-date."""
    print("Generating fresh source lists from Bazel for validation...")
    fresh_embossc_sources = get_source_files_for_targets(EMBOSSC_TARGETS)
    fresh_embossc_sources.append("embossc")
    init_py_sources = find_init_py_files(fresh_embossc_sources)
    all_fresh_embossc_sources = sorted(
        list(set(fresh_embossc_sources + init_py_sources))
    )
    fresh_runtime_cpp_sources = get_source_files_for_targets([RUNTIME_CPP_TARGET])

    print(f"Reading existing sources from {file_path}...")
    on_disk_data = read_build_json(file_path)
    on_disk_embossc_sources = on_disk_data.get("embossc_sources", [])
    on_disk_runtime_cpp_sources = on_disk_data.get("emboss_runtime_cpp_sources", [])

    embossc_diff = set(all_fresh_embossc_sources) ^ set(on_disk_embossc_sources)
    runtime_diff = set(fresh_runtime_cpp_sources) ^ set(on_disk_runtime_cpp_sources)

    if not embossc_diff and not runtime_diff:
        print("build.json is up-to-date.")
        return 0

    print("\nERROR: build.json is out of date!", file=sys.stderr)

    def print_diff(title, fresh_set, on_disk_set):
        added = sorted(list(fresh_set - on_disk_set))
        removed = sorted(list(on_disk_set - fresh_set))
        if added or removed:
            print(f"  {title}:", file=sys.stderr)
            for f in added:
                print(f"    + {f}", file=sys.stderr)
            for f in removed:
                print(f"    - {f}", file=sys.stderr)

    print_diff(
        "embossc_sources",
        set(fresh_embossc_sources),
        set(on_disk_embossc_sources),
    )
    print_diff(
        "emboss_runtime_cpp_sources",
        set(fresh_runtime_cpp_sources),
        set(on_disk_runtime_cpp_sources),
    )

    print(
        "\nPlease run 'scripts/build_helpers/manage_build_json.py' to update.",
        file=sys.stderr,
    )
    return 1


def main():
    parser = argparse.ArgumentParser(description="Manage the build.json file.")
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate that build.json is up-to-date.",
    )
    args = parser.parse_args()

    workspace_root = os.environ.get("BUILD_WORKSPACE_DIRECTORY", os.getcwd())
    build_json_path = os.path.join(workspace_root, "build.json")

    if args.validate:
        return validate_build_json(build_json_path)
    else:
        return generate_build_json(build_json_path)


if __name__ == "__main__":
    sys.exit(main())
