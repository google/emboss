workspace(name = "com_google_emboss")

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("@bazel_tools//tools/build_defs/repo:git.bzl", "git_repository")

# googletest
git_repository(
    name = "com_google_googletest",
    remote = "https://github.com/google/googletest",
    commit = "2f2e72bae991138cedd0e3d06a115022736cd568",
    shallow_since = "1563302555 -0400",
)

git_repository(
    name = "com_google_absl",
    remote = "https://github.com/abseil/abseil-cpp",
    commit = "3020b58f0d987073b8adab204426f82c3f60b283",
    shallow_since = "1562769772 +0000",
)

http_archive(
  name = "bazel_skylib",
  urls = ["https://github.com/bazelbuild/bazel-skylib/releases/download/1.2.1/bazel-skylib-1.2.1.tar.gz"],
  sha256 = "f7be3474d42aae265405a592bb7da8e171919d74c16f082a5457840f06054728",
)
