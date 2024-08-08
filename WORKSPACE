workspace(name = "com_google_emboss")

load("@bazel_tools//tools/build_defs/repo:git.bzl", "git_repository")
load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

# googletest
git_repository(
    name = "com_google_googletest",
    commit = "2f2e72bae991138cedd0e3d06a115022736cd568",
    remote = "https://github.com/google/googletest",
    shallow_since = "1563302555 -0400",
)

git_repository(
    name = "com_google_absl",
    commit = "3020b58f0d987073b8adab204426f82c3f60b283",
    remote = "https://github.com/abseil/abseil-cpp",
    shallow_since = "1562769772 +0000",
)

http_archive(
    name = "bazel_skylib",
    sha256 = "f7be3474d42aae265405a592bb7da8e171919d74c16f082a5457840f06054728",
    urls = ["https://github.com/bazelbuild/bazel-skylib/releases/download/1.2.1/bazel-skylib-1.2.1.tar.gz"],
)

http_archive(
    name = "rules_python",
    sha256 = "c68bdc4fbec25de5b5493b8819cfc877c4ea299c0dcb15c244c5a00208cde311",
    strip_prefix = "rules_python-0.31.0",
    url = "https://github.com/bazelbuild/rules_python/releases/download/0.31.0/rules_python-0.31.0.tar.gz",
)

load("@rules_python//python:repositories.bzl", "py_repositories", "python_register_toolchains")

py_repositories()

# Use Python 3.9 for bazel Python rules.
python_register_toolchains(
    name = "python3",
    python_version = "3.9",
)

load("@python3//:defs.bzl", "interpreter")