# Copyright 2019 Google LLC
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

"""Provides a simple memoizing decorator."""


def memoize(f):
    """Memoizes f.

    The @memoize decorator returns a function which caches the results of f, and
    returns directly from the cache instead of calling f when it is called again
    with the same arguments.

    Memoization has some caveats:

    Most importantly, the decorated function will not be called every time the
    function is called.  If the memoized function `f` performs I/O or relies on
    or changes global state, it may not work correctly when memoized.

    This memoizer only works for functions taking positional arguments.  It does
    not handle keywork arguments.

    This memoizer only works for hashable arguments -- tuples, ints, etc.  It does
    not work on most iterables.

    This memoizer returns a function whose __name__ and argument list may differ
    from the memoized function under reflection.

    This memoizer never evicts anything from its cache, so its memory usage can
    grow indefinitely.

    Depending on the workload and speed of `f`, the memoized `f` can be slower
    than unadorned `f`; it is important to use profiling before and after
    memoization.

    Usage:
        @memoize
        def function(arg, arg2, arg3):
           ...

    Arguments:
        f: The function to memoize.

    Returns:
        A function which acts like f, but faster when called repeatedly with the
        same arguments.
    """
    cache = {}

    def _memoized(*args):
        assert all(
            arg.__hash__ for arg in args
        ), "Arguments to memoized function {} must be hashable.".format(f.__name__)
        if args not in cache:
            cache[args] = f(*args)
        return cache[args]

    return _memoized
