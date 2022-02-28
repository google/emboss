# Design Sketch: Initializer Values for Fields

## Motivation

It is often useful to initialize a structure to some "un-set" value before
starting to modify it.  For many structures, a simple `memset(buffer, sizeof
*buffer, 0)` suffices, but other structures require specific values at specific
locations, which are tedious to write out in user code.

This design proposes two main elements:

1.  A way to specify initializer values for specific fields.
2.  A new feature in the generated C++ code to set the memory underlying a view
    to those initializer values, or to 0 if no initializer was specified.


## Initializer Value Syntax

### Attribute

The most straightforward option is to use the existing attribute syntax:

    struct Foo:
      0 [+2]  UInt  bar
        [initialize_to: 7]

The exact name TBD, but it should be somewhat visually distinct from the
existing `$default` keyword for attributes, which specifies that an attribute
should be used for all descendants of the current node, unless overridden:

    [$default byte_order = "LittleEndian"]


### New Syntax

Other options might add new syntax.


#### Suffix `= value`

Suffix `= value` looks somewhat similar to the "initialize on construction"
syntax in languages like C++:

    struct Foo:
      0 [+2]  UInt  bar = 7

    class Foo {
      int bar = 7;
    };

However, it also looks somewhat confusingly similar to the field number
specifiers in Proto:

    message Foo {
      optional uint32 bar = 7;
    }


#### Something Else?

It is difficult to come up with a syntax that is clear and concise, especially
to a reader who is not particularly familiar with Emboss:

    struct Foo:
      0 [+2]  UInt  bar := 7

    struct Foo:
      0 [+2]  UInt  bar [7]

    struct Foo:
      0 [+2]  UInt [initialize to 7]  bar

Feel free to propose other options.


## `Initialize()` Method

Emboss *views* do not own their backing storage: creating a view does not
allocate memory, it just provides a structured, well, view of existing bytes.
This means that there is not a natural place to automatically initialize a
struct, the way that there is for an object in a typical programming language.

Instead, I propose adding an `Initialize()` method (name TBD) to each view,
which can be called to explicitly initialize the underlying memory.

For `external` (`UInt`, `Bcd`, etc.) and `enum` views, `Initialize()` should
just set the initializer value specified in the `.emb` file, or `0` if none was
specified.

For structure views (`struct` and `bits`), `Initialize()` should set the
initializer values of each of their fields, recursively.

TBD whether `Initialize()` should also zero out any bytes that are not part
of any concrete field.


## Implementation Notes

This is a moderately complex change, touching both the front end and C++ back
end of the compiler, as well as the C++ runtime.


### Front End Changes

On the front end, adding a new attribute is definitely the most straightforward
change: mostly just adding the new attribute to `attributes.py`, and updating a
few things in `dependency_checker.py`, `expression_bounds.py`, and possibly
`constraints.py` to inspect the new attribute.


### C++ Back End Changes

On the back end, there are a couple of implementation strategies.

The easiest strategy is to generate an `Initialize()` method on each structure
type that recursively calls `Initialize()` on each field within the structure
(in dependency-safe order, similar to `WriteToTextStream()`).

An alternate strategy would be to generate an "empty image" for each structure,
and have `Initialize()` `memcpy()` the image into its backing storage.  This
seems like it would be faster at runtime, but may bloat binary size quite a bit
-- a 4kb `struct` would need 4kb of const data in your binary to support
`Initialize()`, whereas iteratively calling `Initialize()` on each element of
an array does not require any extra code space for each element of the array.
For this reason, there would likely still need to be a fallback to recursively
calling `Initialize()`.

Either way, fields with an explicit initializer value need to be wrapped in a
view adapter when accessed, similar to how `[requires]` is handled now.

Enum views can be generated with a simple `Initialize()` method that just sets
their backing storage to 0.


### C++ Runtime Changes

Each of the views for Prelude types (`UInt`, `Int`, `Flag`, etc.) in
`runtime/cpp/emboss_prelude.h` will need to have the new `Initialize()` method.
