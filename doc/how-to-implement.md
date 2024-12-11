# How to Implement Changes to Emboss

<!-- TODO(bolms): write and link to guides on the `embossc` design -->

## Getting the Code

The master Emboss repository lives at https://github.com/google/emboss — you
can `git clone` that repository directly, or make [a fork on
GitHub](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/about-forks)
and then `git clone` your fork.


## Prerequisites

In order to run Emboss, you will need [Python 3](https://www.python.org/).
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
bazel test ...:all
```

Bazel will download the necessary prerequisites, compile the (C++) code, and
run all the tests.

Note that each C++ test actually runs multiple times with Emboss `#define`
options.  (The Emboss repository goes one step further and runs each of *those*
tests under multiple compilers and optimization options.)

Note: if you are making changes to the Emboss grammar, you can ignore failures
in `docs_are_up_to_date_test` until you have your updated grammar finalized:
that test ensures that certain generated documentation files are up to date
when code reaches the main repository.  See [Checked-In Generated
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
