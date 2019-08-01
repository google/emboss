workspace(name = "com_google_emboss")

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("@bazel_tools//tools/build_defs/repo:git.bzl", "git_repository")

# googletest
git_repository(
    name = "com_google_googletest",
    remote = "https://github.com/google/googletest",
    commit = "f899e81e43407c9a3433d9ad3a0a8f64e450ba44",
    shallow_since = "1563302555 -0400",
)

git_repository(
    name = "com_google_absl",
    remote = "https://github.com/abseil/abseil-cpp",
    commit = "44efe96dfca674a17b45ca53fc77fb69f1e29bf4",
    shallow_since = "1562769772 +0000",
)
