# Design Sketch: Explicit Enum Sizes

This document is provided for historical interest.  This feature is now
implemented in the form of the `[maximum_bits]` attribute on `enum`s.  The
`[signedness]` attribute referenced at the bottom of the doc is also
implemented as `[is_signed]`.


## Overview

Currently in Emboss, when rendering an Emboss `enum`, the corresponding C++
`enum` always has either `int64_t` or `uint64_t` as its storage class, e.g.:

    enum class Foo : int64_t {
      // ... values ...
    };

This is because Emboss `enum`s are open (can hold any value, even if it is not
a known enum value) and can be placed in fields of any size up to 64 bits.
E.g.:

    enum Foo:
      AA = 1
      BB = 2
      CC = 3

    struct Bar:
      0 [+1]  Foo  short_foo
      1 [+8]  Foo  long_foo

Since `Foo` doesn't know how big of a field it will eventually be used for --
and it can vary! -- Emboss takes the safe approach of using a 64-bit type in
C++-land.

(Aside: yes, there are cases in real message formats where the same enum is used
in fields of different sizes.  In message formats from multiple manufacturers.
Generally in some overly-clever way.)

However, this means that anyone who directly uses that `enum` type in their own
C++ `class` has to pay for the entire 8 bytes, even if the `enum` would fit in
a much smaller type, and larger values are never needed.


## `[max_value_size_in_bits]` Attribute

This design proposes adding a `[max_value_size_in_bits]` (name TBD) attribute
on `enum`s, which specifies that an `enum` may not be used in a field larger
than a certain size.  This gives the C++ back end (and others) the freedom to
use a smaller underlying type.  For example:

    enum Foo:
      [max_value_size_in_bits: 16]
      AA = 1
      BB = 2
      CC = 3

    struct Bar:
      0 [+1]  Foo  short_foo
      1 [+8]  Foo  long_foo  # Now an error

In the generated C++, this would now produce:

    enum class Foo : uint16_t {
      // ... values ...
    };

Now any C++ classes storing `Foo` would only need to allocate 2 bytes.


## `[signedness]` Attribute (Optional)

Currently, Emboss uses the absence or presence of any negative values to
determine whether an `enum` type uses `uint64_t` or `int64_t` storage:

    enum Unsigned:
      AA = 1

    enum Signed:
      AA = -1

Produces:

    enum class Unsigned : uint64_t {
      AA = 1,
    };

    enum class Signed : int64_t {
      AA = -1,
    };

It may make sense to add an explicit attribute to control signedness, instead
of relying on the "negative value" heuristic.


## Implementation Notes

This is a relatively simple change, even though it touches places throughout
the Emboss codebase.


### Compiler Front End

`attributes.py` needs to be updated with the new attribute.
`_check_that_enum_values_are_representable()` in `constraints.py` needs to be
updated to check the constrained sizes.


### C++ Back End

`_generate_enum_definition()` in `header_generator.py` needs to be updated to
check the new attribute and use it to pick a type, instead of always picking
`::std::int64_t` or `::std::uint64_t`.
