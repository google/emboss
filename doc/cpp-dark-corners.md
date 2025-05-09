# C++ Dark Corners

Emboss is intended to protect end users from C++, to the extent that that is
possible.  Further, because Emboss code gets imported into end user projects,
it may be used in situations that are difficult to anticipate.  Because of
this, Emboss C++ contributors need to be much more aware of edge cases in C++
than the typical C++ programmer.


## A Short Defense of C++

C++ is an *old* language, with nearly-perfect backwards compatibility to the
original *C*89 standard — more than 35 years, as of the time of writing! — and
that is a long time to acquire... quirks.  Many (though not all) of the dark
corners in C++23 originated in C89 (or, more realistically, in K&R C, which
dates back to 1972).

The computing world of the 1970s, 1980s, and into the 1990s was significantly
different than the computing world of the 2010s or 2020s: between 1995 and
2015, a premium desktop computer got approximately 200 times faster, with
around 200 times as much RAM and 2000 times as much storage — many compiler
checks and optimizations were computationally infeasible in 1995, much less
1989 or 1972.  The field of Software Engineering also advanced significantly,
as professional programmers learned how to design programs and languages to
minimize programmer errors.

All of this is to say: C++ was originally designed in a time when many of the
things we now take for granted were completely unknown.

Of course, that does not automatically excuse those dark corners existing in
C++23 — C++ is an evolving language, after all.  However, the C++ standards
committee has to balance many competing interests: backwards compatibility
remains extremely important in C++, *including* for performance.  Nonetheless,
the committee has managed to clean things up in most of the standards.  For
example:

*    C++17: dropped [trigraphs][trigraphs], and changed the rules for
     unsigned-to-signed casts such that `static_cast<signed>(MAX_UINT)` is
     always `== -1`
*    C++20: cleaned up the rules for shifts; `-10 << 1 == -20` instead of
     undefined behavior
*    C++23: allows whitespace after `\` at the end of a line
*    C++26: automatic memory initialization by default (`int x; f(x);` is no
     longer undefined).

[trigraphs]: https://en.cppreference.com/w/cpp/language/operator_alternative#Trigraphs_.28removed_in_C.2B.2B17.29


## Types of Dark Corners

C++ has four basic categories of behavior to watch out for:

1.  Undefined behavior
2.  Implementation-defined behavior
3.  Standard quirks
4.  C++-as-implemented


### Undefined Behavior

Undefined behavior is the class of "dark corners" that gets, by far, the most
attention in the wider world, so I will not go into too much detail here.
[John Regehr's introduction on the subject][regehr_ub] provides a good
overview.

[regehr_ub]: https://blog.regehr.org/archives/213

The short version is that if your program ever performs what the standard calls
"undefined behavior," (often shortened to "UB" in the wider world) your program
is not *and never was* a C++ program, according to the standard, and therefore
*none of the guarantees in the standard apply*.

If you invoke undefined behavior, the compiler is allowed to do *anything*: it
can do exactly what you would naïvely expect, it can format your hard drive, it
can emit a program that formats your hard drive, or anything in between.  This
uncertainty combined with danger (sometimes your use of undefined behavior Just
Works, at least until a new compiler version shows up and turns your working
code into a [security vulnerability][cve_2009_1897]) makes undefined behavior
the most dangerous type of dark corner in C++.

[cve_2009_1897]: https://nvd.nist.gov/vuln/detail/CVE-2009-1897

Examples of undefined behavior in C++ include dereferencing `nullptr` or
reading uninitialized memory.

This document covers a number of specific types of undefined behavior,
including some categories that do not get a lot of attention in the wider world
of C++ development.


### Implementation-Defined Behavior

In addition to the "undefined" class of behaviors, the C++ standard has a class
of "implementation-defined behavior," where a conforming C++ compiler has to
have well-defined behavior, but the exact behavior is up to each compiler
implementation (where "implementation" means a particular version of a compiler
used with a specific set of options and targetting a specific platform —
though, in practice, compilers tend to have mostly stable
implementation-defined behavior between *versions*).

Some cases of implementation-defined behavior are well-known among C++
developers: for example, the size of `long` varies between 32 and 64 bits on
common platforms (but the latest C++ standard only specifies that `long` is at
least 32 bits — a conforming implementation could, for example, have 128-bit
`long` or 48-bit `long`).

Implementation-defined behavior is tricky for Emboss because it tends to be
stable on a single platform, but vary between platforms — sometimes only on
relatively obscure platforms.  This kind of issue is difficult to catch through
automated testing — you would need to run the test suite tens of thousands of
times, on every compiler on every platform with every set of valid compiler
flags.  This is infeasible, even for very large teams.

For example, most or all Itanium compilers defined unsigned-to-signed casts to
return 0 if the high bit of the unsigned value was 1, at least until C++17
standardized 2's-complement casting.  Emboss has never (to the Emboss authors'
knowledge) been used on Itanium, and we have no intention of setting up an
Itanium testing environment (even if we could find an Itanium-based machine to
do so!).


### Standard Quirks

C++ also has various behaviors that are fully-defined, but surprising to most
developers.  For example, the ["digraph" alternative operator
representations][cppreference_alternative_operator_representations]:

[cppreference_alternative_operator_representations]: https://en.cppreference.com/w/cpp/language/operator_alternative

| Primary | Alternative |
| ------- | ----------- |
| `{`     | `<%`        |
| `}`     | `%>`        |
| `[`     | `<:`        |
| `]`     | `:>`        |
| `#`     | `%:`        |

The "alternative" representations can be freely used in place of the "primary"
representations.  These two code snippets are exactly equivalent in standard
C++:

```c++
#include <string>
#include <vector>
int f(const std::vector<int> &v) {
  return v[0];
}
```

```c++
%:include <string>
%:include <vector>
int f(const std::vector<int> &v) <%
  return v<:0:>;
%>
```

Alternative representations do not have to be used consistently.  This is also
equivalent in C++ (but many editors and IDEs will complain about the "unclosed"
brace and "unopened" bracket!):

```c++
%:include <string>
#include <vector>
int f(const std::vector<int> &v) {
  return v<:0];
%>
```


### C++-as-Implemented

The final category of C++ dark corners is where the lofty theory of the C++
standard meets the messiness and imperfection of the real world: there is no
C++ compiler that perfectly and *only* implements any version of the C++
standard.  The differences between standard and practice fall into two
categories:


#### Compiler Bugs

Emboss currently has workarounds for four (4) verified compiler bugs in its
code base, and it is likely that it is affected by others.  One of the known
bugs results in silent miscompilation — in certain circumstances, client code
using Emboss would return incorrect results, with no diagnostic message from
the compiler (luckily, this was discovered by Emboss's test suite).

In theory, Emboss is only required to work on *correct* C++ compilers, but in
practice we want it to work on (at least) all the common C++ compilers, even
though those compilers have bugs.


#### Vendor Extensions

All major compiler vendors implement their own extensions on top of the C++
standard — features that *that vendor* guarantees, but which are not part of
the standard and which other compilers may or may not support.

Most of the time, these do not affect Emboss development, but sometimes they
can be useful — if used judiciously, with fallbacks for compilers that do not
support them.

A trivial example of a vendor extension is that `$` is allowed in identifiers
on every major compiler (and almost every tool that processes C++ source code),
albeit with a warning on most of them: `void ca$h();` is a valid C++ source
file according to real-world compilers.


## Emboss Compatibility

Emboss has a very long backwards-compatibility guarantee for C++: a standard
must have been released for at least 10 years before Emboss can rely on it.

| Standard | Release Date | Emboss Support Until |
| -------- | ------------ | -------------------- |
| C++14    | 2014-12      | 2028-01-01           |
| C++17    | 2017-12      | 2031-01-01           |
| C++20    | 2020-12      | 2034-11-01           |
| C++23    | 2024-10      | 2037-01-01?          |

This kind of long guarantee is common in the embedded development space, where
compilers are often provided by vendors, and are often old versions (for
example, at least one team using Emboss for active development was still using
a vendor-provided C++11 compiler in late 2024).

Unfortunately, this means that Emboss developers must be aware of and avoid
dark corners that have been fixed in the latest versions of C++, or bugs that
have been fixed in newer versions of C++ compilers.


## C++ Memory Model: Regions

Many C++ developers believe that the C++ memory model matches the simple
"memory is a giant array" model that *processors* use: that is, that C++ (more
or less) just exposes the machine.

This is not true, and it is a significant source of danger.


### Memory Regions and Pointer Arithmetic

C++ divides memory into many, *many* tiny regions: every variable definition
and every memory allocation gets its own region.  It then, further, defines any
arithmetic operation whose result would point outside of that region as
*overflow*, which is, in turn, considered to be undefined behavior:

```c++
int f() {
  int z = 1;
  int *zptr = &z;
  int *zptr_minus_one = zptr - 1;  // Undefined
  return *(zptr_minus_one + 1);    // Already in undefined land
}
```

Pointing "inside" the region means *either* pointing to a memory location
within the region *or* to the memory location immediately after the region
("one past" the end of an array, where non-array objects are treated as if they
are arrays of length 1):

```c++
int f() {
  int z = 1;
  int *zptr = &z;
  int *zptr_plus_one = zptr + 1;  // OK
  return *(zptr_plus_one - 1);    // OK
}
```

Note that even though it is valid to create a pointer to "one past" the end of
an object, it is still undefined behavior to *dereference* that pointer:

```c++
int f() {
  int z = 1;
  int *zptr = &z;
  int *zptr_plus_one = zptr + 1;  // OK
  return *zptr_plus_one;          // Undefined
}
```

Comparisons between pointers into different regions are also problematic:

```c++
bool f() {
  int s, t;
  return &s > &t;  // Undefined (through C++20)
                   // Unspecified result (since C++23)
}
```

Note that equality comparisons are not quite as strict:

```c++
bool f() {
  int s, t;
  return &s == &t;  // OK, false
}

bool g() {
  int s, t;
  return &s != &t;  // OK, true
}
```

But things can get tricky when combined with "one past the end" pointers:

```c++
bool f() {
  int s, t;
  return (&s) + 1 == &t;  // Unspecified result
}

bool g() {
  int s, t;
  return (&s) + 1 != &t;  // Unspecified result
}
```

You also cannot serialize and deserialize pointers (at least, you cannot use
the result):

```c++
int f() {
  int z = 1;
  std::stringstream s;
  void *zptr;
  s << &z;
  s >> zptr;

  // Undefined (until C++23?)
  return *reinterpret_cast<int*>(zptr);
}
```

(Note: you *may* be able to do this in C++23 and later: it's not clear to the
author of this document.)

There is an exception to this: the `printf` and `scanf` functions with the `%p`
format specifier are specially blessed to allow it:

```c++
int f() {
  int z = 1;
  char buf[200];
  void *zptr;
  snprintf(buf, sizeof buf, "%p", &z);
  sscanf(buf, "%p", &zptr);

  // OK
  return *reinterpret_cast<int*>(zptr);
}
```

This blessing is not actually listed in the C++ standard: it is listed in the
*C* standard, in a section that the C++ standard merely refers to.

In the C++ standards through C++20, these rules are summarized in the section
called "Safely-derived pointers;" e.g., C++20 (N4860), §6.7.5.4.3
"Safely-derived pointers [basic.stc.dynamic.safety]."

C++23 relaxed *some* of the rules and removed the section that summarized them:
now, you have to find the rules scattered elsewhere in the standard.


### The Strict Aliasing Rule

In addition to being its own "island" of memory, each region gets *one type*
for its entire lifetime, and (with specific exceptions), treating that memory
as if it were a different type is not allowed.  Specifically, access to a
particular object or subobject must treat the object as one of:

1.  The object's type
2.  `char`
3.  `unsigned char`
4.  `std::byte` (since C++17)
5.  `std::make_signed<typeof(region)>::type`
6.  `std::make_unsigned<typeof(region)>::type`
7.  `T __attribute__((__may_alias__))` (Clang and GCC, maybe ICC?)
8.  Anything (all versions of MSVC, `{g++,clang++} -fno-strict-aliasing`)

The last method hints at a fact of the real world: the strict aliasing rule is
controversial, and even compilers that claim that type punning is not allowed
usually do not actually do anything with it.

Nonetheless, at least *some* compilers take advantage of strict aliasing during
optimization, and so in Emboss we are generally limited to the first 4 options,
although 5 and 6 would be acceptable, and 7 and 8 can be used with guards for
specific compilers.


#### Unions and Strict Aliasing

Many developers try to use `union` to perform type punning:

```c++
union Z { int a; short b; };

short f(int a) {
  Z z;
  z.a = a;

  return z.b;  // Undefined  (C++11 §9.2 & §9.5)
}
```

This is undefined behavior: a `union` has exactly one "live" member at any
given moment in the program's execution, and trying to access a non-live member
is undefined behavior.


#### Theoretical Issue: `std::uint8_t`

Although not an issue in any real-world compiler, `std::uint8_t` does not have
to be an alias of `unsigned char` or `char`, even on systems where `unsigned
char` and `char` are 8 bits: `std::uint8_t` could be a so-called "extended
integer type," which does not have the aliasing exception for `char` or
`unsigned char`:

```c++
std::uint8_t f() {
  int z = 1;

  // In theory, undefined on some compilers.
  return *reinterpret_cast<std::uint8_t*>(&z);
}
```

In practice, there are no real-world compilers that do this, so it is not a
real-world issue.


#### Proper Bit Casting

The main reason programmers violate strict aliasing is that they are trying to
*bit cast*: to reinterpret the bit pattern of some object as some other type.

There is a correct, safe way to do this, which is via `std::memcpy()`:

```c++
template <typename T, typename U>
T bit_cast(const U &value) {
  T result;
  memcpy(&result, &value, sizeof result);
  return result;
}
```

(Note that a [real implementation][absl_bit_cast] needs more checking to be
safe.)

[absl_bit_cast]: https://github.com/abseil/abseil-cpp/blob/master/absl/base/casts.h#L152

This is, unfortunately, not `constexpr`-safe until C++23.

In Emboss, these kinds of bit casts are (surprisingly) rare because Emboss
cannot rely on specifics of how a type is represented on the host machine.


### Why the Region Model?

So: why does C++ have this complicated region model and all these rules around
pointer arithmetic?

The short answer is: garbage collection!

The longer answer is: a lot of reasons, but originally garbage collection!

Both the C and C++ standards were written in such a way that a C++
implementation could be conformant even with a *compacting* garbage collector.
Things like pointer order could therefore change at any time.  Serializing and
then deserializing a pointer "hides" that pointer from the garbage collector,
and is therefore disallowed.  The strict aliasing rule means that the compiler
can always figure out *what* bytes in memory actually correspond to pointers,
and the runtime can update those pointers if it moves the region they point
into.

As of C++23, [garbage collection support was officially dropped from the
standard][cpp23_removing_garbage_collection_support], but many of the related
rules are still in place, so garbage collection is clearly not the *only*
reason.

[cpp23_removing_garbage_collection_support]: https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2021/p2186r2.html

In some cases, the rules still account for edge cases: for example, if a memory
region is allocated very close to the upper or lower edge of the address space,
pointer arithmetic that leaves the region could actually overflow the backing
integer.  If two objects happen to be allocated next to each other in memory (a
fairly common occurrence for stack objects), then a pointer to one-past one
object may have the same numeric value as another object.  And strict aliasing,
at least in theory, can enable certain optimizations that are otherwise
impossible.


## C++ Memory Model: Alignment

C++ types have *alignment* requirements.  The wording in the standard ([N3337
§ 3.11][cpp11_alignment]) is dense, but in practice it means: objects in C++
have to exist at memory addresses that are equal to 0 modulo their alignment.
For most modern compilers, for example, `std::int32_t` will have 4-byte (32
bit) alignment, and so `std::int32_t` can only exist at addresses ending with
`00` in binary (`0`, `4`, `8` or `c` in hexadecimal), like `0x4dac` or
`0x0ee0`.  In C++, you can get the alignment of a type with `alignof`, like
`alignof(int)`, which is guaranteed to return a positive power of 2 (1, 2, 4,
8, etc.).

[cpp11_alignment]: https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf#page=89

Alignment requirements are set by the C++ implementation, based on the target
hardware.  Most implementations set their alignment requirements based on *best
performance*, not absolute need: compilers for ARMv6 and later, for example,
still use 32-bit alignment for `int32_t`, even though the processor itself is
capable of doing unaligned reads: the C++ standard does not differentiate
between "recommended" and "required" alignment.

Trying to access a type through an unaligned pointer is *undefined behavior*,
even if all aliasing, initialization, etc. rules have been followed:

```c++
int f() {
  void *buf = operator new(sizeof(int) + 1);
  memset(buf, 0);

  // Undefined (on almost all C++ implementations)
  int result = *reinterpret_cast<int*>(buf + 1);
  operator delete(buf);
  return result;
}
```

Historically, C++ implementations did not actually enforce alignment or exploit
the undefined behavior there, which leads developers on many platforms to think
that unaligned access is fine.  This is not actually true, and can cause
problems [even on processor architectures like x86][x86_alignment_bug].

[x86_alignment_bug]: https://pzemtsov.github.io/2016/11/06/bug-story-alignment-on-x86.html


### Alignment and Packed Structs

"Packed struct" is a generic term for a vendor extension which allows a
programmer to annotate a `struct` or `class` definition such that data members
of that `struct` will be placed with no padding, even if it means that those
members are misaligned.  For example, on GCC or Clang:

```c++
// offsetof(X, i) == 4 (on most platforms)
struct X {
  char c;
  std::int32_t i;
};

// offsetof(PackedX, i) == 1
struct __attribute__((packed)) PackedX {
  char c;
  std::int32_t i;
};
```

Although packed structs are vendor extensions, they all have similar rules and
restrictions.

First, although you can access misaligned data members through a packed struct,
the access has to be done *directly* through the packed struct: taking the
address of an unaligned member can be dangerous:

```c++
int f() {
  PackedX x = { 'a', 10 };
  g(x.i);                   // OK: direct access to i
  std::int32_t *p = &x.i;   // OK so far, but will give a warning

  int y;
  memcpy(&y, p, sizeof y);  // OK: memcpy() has no alignment requirements

  return *p;                // Undefined behavior: p is misaligned
}
```

Somewhat less well-known is that packed structs only relax their *internal*
alignment restrictions: the packed struct *itself* still has an alignment!
(Although on many compilers, the alignment of the packed struct is `1`.)


## Miscellaneous Issues

### Namespace Resolution

Most C++ developers use `some_namespace::Name` to get at `Name` when they are
not in `some_namespace` scope.  Most of the time this is fine, but it can cause
errors.  The problem is that C++ starts name searches at the current scope.
For example, take the following code:

```c++
// my_function.h
namespace util {
void MyFunction();
}  // namespace util

namespace my::deeply::nested::ns {
inline void UsesMyFunction() { util::MyFunction(); }
}  // namespace my::deeply::nested::ns
```

As written here, this will compile and work as intended.  However, it relies on
there being no `my::util`, `my::deeply::util` or `my::deeply::nested::util`
namespace visible at the site of the `util::MyFunction()` call.  If someone
else writes:

```c++
// my_util.h

namespace my::util {
void SpecialFunction();
}  // namespace my::util
```

And then yet another person tries to `#include` both files in the wrong order:

```c++
// application.cc

#include "my_util.h"
#include "my_function.h"
```

They will end up with a compilation error:

```
> g++ -c application.cc
In file included from application.cc:4:
my_function.h: In function ‘void my::deeply::nested::ns::UsesMyFunction()’:
my_function.h:8:38: error: ‘MyFunction’ is not a member of ‘my::util’; did you mean ‘util::MyFunction’?
    8 | inline void UsesMyFunction() { util::MyFunction(); }
      |                                      ^~~~~~~~~~
my_function.h:4:6: note: ‘util::MyFunction’ declared here
    4 | void MyFunction();
      |      ^~~~~~~~~~
```

Note how unhelpful G++'s error message is: "I can't find util::MyFunction(),
did you mean util::MyFunction()?"  Clang's error is better:

```
> clang++ -c application.cc
In file included from application.cc:4:
./my_function.h:8:32: error: no member named 'MyFunction' in namespace 'my::util'; did you mean '::util::MyFunction'?
inline void UsesMyFunction() { util::MyFunction(); }
                               ^~~~~~~~~~~~~~~~
                               ::util::MyFunction
./my_function.h:4:6: note: '::util::MyFunction' declared here
void MyFunction();
     ^
1 error generated.
```

Of course, it gets worse if `::my::util::MyFunction()` *is* defined:

```
> g++ -c application.cc
In file included from application.cc:4:
my_function.h: In function ‘void my::deeply::nested::ns::UsesMyFunction()’:
my_function.h:8:48: error: too few arguments to function ‘void my::util::MyFunction(int)’
    8 | inline void UsesMyFunction() { util::MyFunction(); }
      |                                ~~~~~~~~~~~~~~~~^~
In file included from application.cc:3:
my_util.h:5:6: note: declared here
    5 | void MyFunction(int);
      |      ^~~~~~~~~~
```

And worst of all is if `my::util::MyFunction()` has compatible arguments: in
that case, the wrong `MyFunction()` will be silently called!

This is most important in generated code — which ends up in user-controlled
namespaces — but as a blanket rule all Emboss code should use the `::` prefix
for *all* top-level namespaces, even namespaces like `std`.


### Reserved Names

C++ reserves certain name patterns for language implementations, and other name
patterns for future versions of the C++ standard.  In particular, names that
start with `_` (in most contexts) or which contain `__` anywhere are reserved.

C reserves many name patterns if you `#include` specific headers: "Each header
declares or defines all identifiers listed in its associated subclause, and
optionally declares or defines identifiers listed in its associated future
library directions subclause and identifiers which are always reserved either
for any use or for use as file scope identifiers."  (C23 §7.1.3)  For example,
if you `#include <errno.h>` or `#include <cerrno>`: "Additional macro
definitions, beginning with E and a digit or E and an uppercase letter, may
also be specified by the implementation." (C23 §7.5)

Although it is not part of the C or C++ standards, [POSIX reserves many names
for its use][posix_reserved_names], including some names that are also reserved
by C.  One particular pattern that is routinely violated in application code is
the use of any name with the `_t` suffix: POSIX reserves all such names for
POSIX implementors and for future revisions of POSIX.

[posix_reserved_names]: https://pubs.opengroup.org/onlinepubs/9699919799/functions/V2_chap02.html
