# How to Implement Changes to Emboss

<!-- TODO(bolms): write and link to guides on the `embossc` design -->

## Getting the Code

The master Emboss repository lives at https://github.com/google/emboss — you
can `git clone` that repository directly, or make [a fork on
GitHub](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/about-forks)
and then `git clone` your fork.


## Prerequisites

In order to run Emboss, you will need [Python](https://www.python.org/).
Emboss supports all versions of Python that are [still supported by the
(C)Python codevelopers](https://devguide.python.org/versions/), but versions
older than that generally will not work.

The Emboss tests run under [Bazel](https://bazel.build/).  In order to run the
tests, you will need to [install Bazel](https://bazel.build/start) on your
system.


## Running Tests

Emboss has a reasonably extensive test suite.  In order to run the test suite,
`cd` into the top `emboss` directory, and run:

```sh
bazel test ...
```

Bazel will download the necessary prerequisites, compile the (C++) code, and
run all the tests.  Tests will take a moment to compile and run; Bazel will
show running status, like this:

```
Starting local Bazel server and connecting to it...
[502 / 782] 22 actions, 21 running
    Compiling runtime/cpp/test/emboss_memory_util_test.cc; 10s linux-sandbox
    Compiling runtime/cpp/test/emboss_memory_util_test.cc; 10s linux-sandbox
    Creating runfiles tree bazel-out/k8-fastbuild/bin/compiler/front_end/emboss_front_end.runfiles; 2s local
    Creating runfiles tree bazel-out/k8-fastbuild/bin/compiler/front_end/synthetics_test.runfiles; 1s local
    Creating runfiles tree bazel-out/k8-fastbuild/bin/compiler/front_end/make_parser_test.runfiles; 1s local
    Creating runfiles tree bazel-out/k8-fastbuild/bin/compiler/back_end/cpp/header_generator_test.runfiles; 1s local
    Compiling absl/strings/str_join.h; 0s linux-sandbox
    Creating runfiles tree bazel-out/k8-fastbuild/bin/compiler/front_end/generate_cached_parser.runfiles; 0s local ...
```

You may see a few `WARNING` messages; these are generally harmless.

Once Bazel finishes running tests, you should see a list of all tests and their
status (all should be `PASSED` if you just cloned the main Emboss repo):

```
Starting local Bazel server and connecting to it...
INFO: Analyzed 226 targets (98 packages loaded, 4080 targets configured).
INFO: Found 116 targets and 110 test targets...
INFO: Elapsed time: 65.577s, Critical Path: 22.22s
INFO: 862 processes: 372 internal, 490 linux-sandbox.
INFO: Build completed successfully, 862 total actions
//compiler/back_end/cpp:alignments_test                                  PASSED in 0.2s
//compiler/back_end/cpp:alignments_test_no_opts                          PASSED in 0.1s
//compiler/back_end/cpp:anonymous_bits_test                              PASSED in 0.2s
//compiler/back_end/cpp:anonymous_bits_test_no_opts                      PASSED in 0.1s
[... many more tests ...]
//runtime/cpp/test:emboss_prelude_test                                   PASSED in 0.2s
//runtime/cpp/test:emboss_prelude_test_no_opts                           PASSED in 0.2s
//runtime/cpp/test:emboss_text_util_test                                 PASSED in 0.2s
//runtime/cpp/test:emboss_text_util_test_no_opts                         PASSED in 0.2s

Executed 110 out of 110 tests: 110 tests pass.
```

If a test fails, you will see lines at the end like:

```
//compiler/back_end/cpp:alignments_test                                  FAILED in 0.0s
  /usr/local/home/bolms/.cache/bazel/_bazel_bolms/444a471ee8e028e0535394d088883276/execroot/_main/bazel-out/k8-fastbuild/testlogs/compiler/back_end/cpp/alignments_test/test.log

Executed 110 out of 110 tests: 109 tests pass and 1 fails locally.
```

You can read the `test.log` file to find out where the failure occurred.

Note that each C++ test actually runs multiple times with different Emboss
`#define` options, so a single failure may cause multiple Bazel tests to fail:

```
//compiler/back_end/cpp:alignments_test                                  FAILED in 0.0s
  /usr/local/home/bolms/.cache/bazel/_bazel_bolms/1c6e4694f903a02feef32c92ec3f1cae/execroot/_main/bazel-out/k8-fastbuild/testlogs/compiler/back_end/cpp/alignments_test/test.log
//compiler/back_end/cpp:alignments_test_no_checks                        FAILED in 0.0s
  /usr/local/home/bolms/.cache/bazel/_bazel_bolms/1c6e4694f903a02feef32c92ec3f1cae/execroot/_main/bazel-out/k8-fastbuild/testlogs/compiler/back_end/cpp/alignments_test_no_checks/test.log
//compiler/back_end/cpp:alignments_test_no_checks_no_opts                FAILED in 0.0s
  /usr/local/home/bolms/.cache/bazel/_bazel_bolms/1c6e4694f903a02feef32c92ec3f1cae/execroot/_main/bazel-out/k8-fastbuild/testlogs/compiler/back_end/cpp/alignments_test_no_checks_no_opts/test.log
//compiler/back_end/cpp:alignments_test_no_opts                          FAILED in 0.0s
  /usr/local/home/bolms/.cache/bazel/_bazel_bolms/1c6e4694f903a02feef32c92ec3f1cae/execroot/_main/bazel-out/k8-fastbuild/testlogs/compiler/back_end/cpp/alignments_test_no_opts/test.log

Executed 168 out of 168 tests: 164 tests pass and 4 fail locally.
```

(The Emboss repository goes one step further and runs each of *those* tests
under multiple compilers and optimization options.)

If you are working on fixing a failure in one particular test, you can tell
Bazel to run just that test by specifying the name of the test on the command
line:

```
bazel test //compiler/back_end/cpp:alignments_test
```

This can be quicker than re-running the entire test suite.


### `docs_are_up_to_date_test`

If you are making changes to the Emboss grammar, you can ignore failures in
`docs_are_up_to_date_test` until you have your updated grammar finalized: that
test ensures that certain generated documentation files are up to date when
code reaches the main repository.  See [Checked-In Generated
Code](#checked-in-generated-code), below.


## Implementing a Feature

The the Emboss compiler is under [`compiler/`](../compiler/), with
[`front_end/`](../compiler/front_end/), [`back_end/`](../compiler/front_end/),
and [`util/`](../compiler/util/) directories for the front end, back end, and
shared utilities, respectively.

The C++ runtime library is under [`runtime/cpp/`](../runtime/cpp).


### Coding Style

For Python, Emboss uses the default style of
the [Black](https://black.readthedocs.io/en/stable/) code formatter.[^genfile]

[^genfile]: There is one, very large, generated `.py` file checked into the
    Emboss repository that is intentionally excluded from code formatting —
    both because it can hang the formatter and because the formatted version
    takes noticeably longer for CPython to load.

For C++, Emboss uses the `--style=Google` preset of
[ClangFormat](https://clang.llvm.org/docs/ClangFormat.html).


## Writing Tests

Most code changes require tests: bug fixes should have at least one test that
fails before the bug fix and passes after the fix, and new features should have
many tests that cover all aspects of how the feature might be used.


### Python

The Emboss Python tests use the Python
[`unittest`](https://docs.python.org/3/library/unittest.html) module.  Most
[tests of the Emboss front end](../compiler/front_end/) are structured as:

1.  Run a small `.emb` file through the front end, stopping immediately before
    the step under test, and hold the result IR (intermediate representation).
2.  Run the step under test on that IR, making sure that there are either no
    errors, or that the errors are expected.
3.  For the "no errors" tests, check various properties of the resulting IR to
    ensure that the step under test did what it was supposed to.


### C++

The Emboss C++ tests use [the GoogleTest
framework](https://google.github.io/googletest/).

[Pure runtime tests](../runtime/cpp/test) `#include` the C++ runtime library
headers and manually instantiate them, then test various properties.

[Generated code tests](../compiler/back_end/cpp/testcode/), which incidentally
test the runtime library as well, work by using a header generated from a [test
`.emb`](../testdata/) and interacting with the generated Emboss code the way
that a user might do so.


## Writing Documentation

If you are adding a feature to Emboss, make sure to update [the
documentation](../doc/).  In particular, the [language
reference](../doc/language-reference.md) and the [C++ code
reference](cpp-reference.md) are very likely to need to be updated.


## Checked-In Generated Code

There are several checked-in generated files in the Emboss source repository.
As a general rule, this is not a best practice, but it is necessary in order to
achieve the "zero installation" use of the Emboss compiler, where an end user
can simply `git clone` the repository and run the `embossc` executable directly
— even if the cloned repository lives on a read-only filesystem.

In order to minimize the chances of any of those files becoming stale, each one
has a unit test that checks that the file in the Emboss directory matches what
its generator would currently generate.
