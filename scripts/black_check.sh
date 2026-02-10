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

# Checks Python formatting without modifying files.
# Usage: bazel run //:black_check

# Change to workspace directory
cd "${BUILD_WORKSPACE_DIRECTORY}" || exit 1

# Find the black_runner binary in runfiles
RUNFILES_DIR="${BASH_SOURCE[0]}.runfiles"
BLACK_RUNNER="${RUNFILES_DIR}/_main/black_runner"

exec "${BLACK_RUNNER}" --check --diff .
