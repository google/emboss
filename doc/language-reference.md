# Emboss Language Reference

## Top Level Structure

An `.emb` file contains four sections: a documentation block, imports, an
attribute block, containing attributes which apply to the whole module, followed
by a list of type definitions:

```
# Documentation block (optional)
-- This is an example of an .emb file, with every section.

# Imports (optional)
import "other.emb" as other
import "project/more.emb" as project_more

# Attribute block (optional)
[$default byte_order: "LittleEndian"]
[(cpp) namespace: "foo::bar::baz"]
[(java) namespace: "com.example.foo.bar.baz"]

# Type definitions
enum Foo:
  ONE    = 1
  TEN    = 10
  PURPLE = 12

struct Bar:
  0 [+4]  Foo       purple
  4 [+4]  UInt      payload_size (s)
  8 [+s]  UInt:8[]  payload
```

The documentation and/or attribute blocks may be omitted if they are not
necessary.


### Comments

Comments start with `#` and extend to the end of the line:

```
struct Foo:  # This is a comment
  # This is a comment
  0 [+1]  UInt  field  # This is a comment
```

Comments are ignored.  They should not be confused with
[*documentation*](#documentation), which is intended to be used by some back
ends.


## Documentation

Documentation blocks may be attached to modules, types, fields, or enum values.
They are different from comments in that they will be used by the
(not-yet-ready) documentation generator back-end.

Documentation blocks take the form of any number of lines starting with `-- `:

```
-- This is a module documentation block.  Text in this block will be attached to
-- the module as documentation.
--
-- This is a new paragraph in the same module documentation block.
--
-- Module-level documentation should describe the purpose of the module, and may
-- point out the most salient features of the module.

struct Message:
  -- This is a documentation block attached to the Message structure.  It should
  -- describe the purpose of Message, and how it should be used.
  0 [+4]  UInt         header_length
    -- This is documentation for the header_length field.  Again, it should
    -- describe this specific field.
  4 [+4]  MessageType  message_type  -- Short docs can go on the same line.
```

Documentation should be written in CommonMark format, ignoring the leading
`-- `.


## Imports

An `import` line tells Emboss to read another `.emb` file and make its types
available to the current file under the given name.  For example, given the
import line:

```
import "other.emb" as helper
```

then the type `Type` from `other.emb` may be referenced as `helper.Type`.

The `--import-dir` command-line flag tells Emboss which directories to search
for imported files; it may be specified multiple times.  If no `--import-dir` is
specified, Emboss will search the current working directory.


## Attributes

Attributes are an extensible way of adding arbitrary information to a module,
type, field, or enum value.  Currently, only whitelisted attributes are allowed
by the Emboss compiler, but this may change in the future.

Attributes take a form like:

```
[name: value]            # name has value for the current entity.
[$default name: value]   # Default name to value for all sub-entities.
[(backend) name: value]  # Attribute for a specific back end.
```


### `byte_order`

The `byte_order` attribute is used to specify the byte order of `bits` fields
and of field with an atomic type, such as `UInt`.

`byte_order` takes a string value, which must be either `"BigEndian"`,
`"LittleEndian"`, or `"Null"`:

```
[$default byte_order: "LittleEndian"]

struct Foo:
  [$default byte_order: "Null"]

  0 [+4]  UInt  bar
    [byte_order: "BigEndian"]

  4 [+4]  bits:
    [byte_order: "LittleEndian"]

    0  [+23]  UInt  baz
    23 [+9]   UInt  qux

  8 [+1]  UInt  froble
```

A `$default` byte order may be set on a module or structure.

The `"BigEndian"` and `"LittleEndian"` byte orders set the byte order to big or
little endian, respectively.  That is, for little endian:

```
  byte 0   byte 1   byte 2   byte 3
+--------+--------+--------+--------+
|76543210|76543210|76543210|76543210|
+--------+--------+--------+--------+
 ^      ^ ^      ^ ^      ^ ^      ^
 07    00 15    08 23    16 31    24
 ^^^^^^^^^^^^^^^ bit ^^^^^^^^^^^^^^^
```

And for big endian:

```
  byte 0   byte 1   byte 2   byte 3
+--------+--------+--------+--------+
|76543210|76543210|76543210|76543210|
+--------+--------+--------+--------+
 ^      ^ ^      ^ ^      ^ ^      ^
 31    24 23    16 15    08 07    00
 ^^^^^^^^^^^^^^^ bit ^^^^^^^^^^^^^^^
```

The `"Null"` byte order is used if no `byte_order` attribute is specified.
`"Null"` indicates that the byte order is unknown; it is an error if a
byte-order-dependent field that is not exactly 8 bits has the `"Null"` byte
order.


### `requires`

The `requires` attribute may be placed on an atomic field (e.g., type `UInt`,
`Int`, `Flag`, etc.) to specify a predicate that values of that field must
satisfy, or on a `struct` or `bits` to specify relationships between fields that
must be satisfied.

```
struct Foo:
  [requires: bar < qux]

  0 [+4]  UInt  bar
    [requires: this <= 999_999_999]

  4 [+4]  UInt  qux
    [requires: 100 <= this <= 1_000_000_000]

  let bar_plus_qux = bar + qux
    [requires: this >= 199]
```

For `[requires]` on a field, other fields may not be referenced, and the value
of the current field must be referred to as `this`.

For `[requires]` on a `struct` or `bits`, any atomic field in the structure may
be referenced.


### `(cpp) namespace`

The `namespace` attribute is used by the C++ back end to determine which
namespace to place the generated code in:

```
[(cpp) namespace: "foo::bar::baz"]
```

A leading `::` is allowed, but not required; the previous example could also be
written as:

```
[(cpp) namespace: "::foo::bar::baz"]
```

Internally, Emboss will translate either of these into a nested `namespace foo {
namespace bar { namespace baz { ... } } }` wrapping the generated C++ code for
this module.

The `namespace` attribute may only be used at the module level; all structures
and enums within a module will be placed in the same namespace.

### `(cpp) enum_case`

The `enum_case` attribute can be specified for the C++ backend to specify
in which case the enum values should be emitted to generated source. It does
not change the text representation, which always uses the original emboss
definition name as the canonical name.

Currently, the supported cases are`SHOUTY_CASE` and `kCamelCase`.

A `$default` enum case can be set on a module, struct, bits, or enum and
applies to all enum values within that module, struct, bits, or enum
definition.

For example, to use `kCamelCase` by default for all enum values in a module:

```
[$default enum_case: "kCamelCase"]
```

This will change enum names like `UPPER_CHANNEL_RANGE_LIMIT` to
`kUpperChannelRangeLimit` in the C++ source for all enum values in the module.
Multiple case names can be specified, which is especially useful when
transitioning between two cases:

```
[enum_case: "SHOUTY_CASE, kCamelCase"]
```

### `text_output`

The `text_output` attribute may be attached to a `struct` or `bits` field to
control whether or not the field is included when emitting the text format
version of the structure.  For example:

```
struct SuppressedField:
  0 [+1]  UInt  a
  1 [+1]  UInt  b
    [text_output: "Skip"]
```

The text format output (as from `emboss::WriteToString()` in C++) would be of
the form:

```
{ a: 1 }
```

instead of the default:

```
{ a: 1, b: 2 }
```

For completeness, `[text_output: "Emit"]` may be used to explicitly specify that
a field should be included in text output.


### `external` specifier attributes

The `addressable_unit_size`, `type_requires`, `fixed_size_in_bits`, and
`is_integer` attributes are used on `external` types to tell the compiler what
it needs to know about the `external` types.  They are currently
unstable, and should only be used internally.


## Type Definitions

Emboss allows you to define structs, unions, bits, and enums, and uses externals
to define "basic types."  Types may be defined in any order, and may freely
reference other types in the same module or any imported modules (including the
implicitly-imported prelude).

### `struct`

A `struct` defines a view of a sequence of bytes.  Each field of a `struct` is a
view of some particular subsequence of the `struct`'s bytes, whose
interpretation is determined by the field's type.

For example:

```
struct FramedMessage:
  -- A FramedMessage wraps a Message with magic bytes, lengths, and CRC.
  [$default byte_order: "LittleEndian"]
  0   [+4]  UInt     magic_value
  4   [+4]  UInt     header_length (h)
  8   [+4]  UInt     message_length (m)
  h   [+m]  Message  message
  h+m [+4]  UInt     crc32
    [byte_order: "BigEndian"]
```

The first line introduces the `struct` and gives it a name.  This name may be
used in field definitions to specify that the field has a structured type, and
is used in the generated code.  For example, to read the `message_length` from a
sequence of bytes in C++, you would construct a `FramedMessageView` over the
bytes:

```c++
// vector<uint8_t> bytes;
auto framed_message_view = FramedMessageView(&bytes[0], bytes.size());
uint32_t message_length = framed_message_view.message_length().Read();
```

(Note that the `FramedMessageView` does not take ownership of the bytes: it only
provides a view of them.)

Each field starts with a byte range (`0 [+4]`) that indicates *where* the field
sits in the struct.  For example, the `magic_value` field covers the first four
bytes of the struct.

Field locations *do not have to be constants*.  In the example above, the
`message` field starts at the end of the header (as determined by the
`header_length` field) and covers `message_length` bytes.

After the field's location is the field's *type*.  The type determines how the
field's bytes are interpreted: the `header_length` field will be interpreted as
an unsigned integer (`UInt`), while the `message` field is interpreted as a
`Message` -- another `struct` type defined elsewhere.

After the type is the field's *name*: this is a name used in the generated code
to access that field, as in `framed_message_view.message_length()`.  The name
may be followed by an optional *abbreviation*, like the `(h)` after
`header_length`.  The abbreviation can be used elsewhere in the `struct`, but is
not available in the generated code: `framed_message_view.h()` wouldn't compile.

Finally, fields may have attributes and documentation, just like any other
Emboss construct.


#### `$next`

The keyword `$next` may be used in the offset expression of a physical field:

```
struct Foo:
  0     [+4]  UInt  x
  $next [+2]  UInt  y
  $next [+1]  UInt  z
  $next [+4]  UInt  q
```

`$next` translates to a built-in constant meaning "the end of the previous
physical field."  In the example above, `y` will start at offset 4 (0 + 4), `z`
starts at offset 6 (4 + 2), and `q` at 7 (6 + 1).

`$next` may be used in `bits` as well as `struct`s:

```
bits Bar:
  0     [+4]  UInt  x
  $next [+2]  UInt  y
  $next [+1]  UInt  z
  $next [+4]  UInt  q
```

You may use `$next` like a regular variable.  For example, if you want to leave
a two-byte gap between `z` and `q` (so that `q` starts at offset 9):

```
struct Foo:
  0       [+4]  UInt  x
  $next   [+2]  UInt  y
  $next   [+1]  UInt  z
  $next+2 [+4]  UInt  q
```

`$next` is particularly useful if your datasheet defines structures as lists of
fields without offsets, or if you are translating from a C or C++ packed
`struct`.


#### Parameters

`struct`s and `bits` can take runtime parameters:

```
struct Foo(x: Int:8, y: Int:8):
  0 [+x]  UInt:8[]  xs
  x [+y]  UInt:8[]  ys

enum Version:
  VERSION_1 = 10
  VERSION_2 = 20

struct Bar(version: Version):
  0 [+1]  UInt  payload
  if payload == 1 && version == Version.VERSION_1:
    1 [+10]  OldPayload1  old_payload_1
  if payload == 1 && version == Version.VERSION_2:
    1 [+12]  NewPayload1  new_payload_1
```

Each parameter must have the form *name`:` type*.  Currently, the *type* can
be:

*   <code>UInt:*n*</code>, where *`n`* is a number from 1 to 64, inclusive.
*   <code>Int:*n*</code>, where *`n`* is a number from 1 to 64, inclusive.
*   The name of an Emboss `enum` type.

`UInt`- and `Int`-typed parameters are integers with the corresponding range:
for example, an `Int:4` parameter can have any integer value from -8 to +7.

`enum`-typed parameters can take any value in the `enum`'s native range.  Note
that Emboss `enum`s are *open*, so unnamed values are allowed.

Parameterized structures can be included in other structures by passing their
parameters:

```
struct Baz:
  0 [+1]     Version       version
  1 [+1]     UInt:8        size
  2 [+size]  Bar(version)  bar
```


#### Virtual "Fields"

It is possible to define a non-physical "field" whose value is an expression:

```
struct Foo:
  0 [+4]  UInt  bar
  let two_bar = 2 * bar
```

These virtual "fields" may be used like any other field in most circumstances:

```
struct Bar:
  0           [+4]  Foo   foo
  if foo.two_bar < 100:
    foo.two_bar [+4]  UInt  uint_at_offset_two_bar
```

Virtual fields may be integers, booleans, or an enum:

```
enum Size:
  SMALL = 1
  LARGE = 2

struct Qux:
  0 [+4]  UInt  x
  let x_is_big = x > 100
  let x_size = x_is_big ? Size.LARGE : Size.SMALL
```

When a virtual field has a constant value, you may refer to it using its type:

```
struct Foo:
  let foo_offset = 0x120
  0 [+4]  UInt  foo

struct Bar:
  Foo.foo_offset [+4]  Foo  foo
```

This does not work for non-constant virtual fields:

```
struct Foo:
  0 [+4]  UInt  foo
  let foo_offset = foo + 10

struct Bar:
  Foo.foo_offset [+4]  Foo  foo  # Won't compile.
```

Note that, in some cases, you *must* use Type.field, and not field.field:

```
struct Foo:
  0 [+4]  UInt  foo
  let foo_offset = 10

struct Bar:
  # Won't compile: foo.foo_offset depends on foo, which depends on
  # foo.foo_offset.
  foo.foo_offset [+4]  Foo  foo

  # Will compile: Foo.foo_offset is a static constant.
  Foo.foo_offset [+4]  Foo  foo
```

This limitation may be lifted in the future, but it has no practical effect.


##### Aliases

Virtual fields of the form `let x = y` or `let x = y.z.q` are allowed even when
`y` or `q` are composite fields.  Virtuals of this form are considered to be
*aliases* of the referred field; in generated code, they may be written as well
as read, and writing through them is equivalent to writing to the aliased field.


##### Simple Transforms

Virtual fields of the forms `let x1 = y + 1`, `let x2 = 2 + y`, `let x3 = y -
3`, and `let x4 = 4 - y`, where `y` is a writeable field, will be writeable in
the generated code.  When writing through these fields, the transformed field
will be set to an appropriate value.  For example, writing `5` to `x1` will
actually write `4` to `y`, and writing `6` to `x4` will write `-2` to `y`.  This
can be used to model fields whose raw values should be adjusted by some constant
value, e.g.:

```
struct PosixDate:
  0 [+1]  Int  raw_year
    -- Number of years since 1900.

  let year = raw_year + 1900
    -- Gregorian year number.

  1 [+1]  Int  zero_based_month
    -- Month number, from 0-11.  Good for looking up a month name in a table.

  let month = zero_based_month + 1
    -- Month number, from 1-12.  Good for printing directly.

  2 [+1]  Int  day
    -- Day number, one-based.
```


#### Subtypes

A `struct` definition may contain other type definitions:

```
struct Foo:
  struct Bar:
    0 [+2]  UInt  baz
    2 [+2]  UInt  qux

  0 [+4]  Bar  bar
  4 [+4]  Bar  bar2
```


#### Conditional fields

A `struct` field may have fields which are only present under some
circumstances.  For example:

```
struct FramedMessage:
  0 [+4]  enum  message_id:
    TYPE1 = 1
    TYPE2 = 2

  if message_id == MessageId.TYPE1:
    4 [+16]  Type1Message  type_1_message

  if message_id == MessageId.TYPE2:
    4 [+8]   Type2Message  type_2_message
```

The `type_1_message` field will only be available if `message_id` is `TYPE1`,
and similarly the `type_2_message` field will only be available if `message_id`
is `TYPE2`.  If `message_id` is some other value, then neither field will be
available.


#### Inline `struct`

It is possible to define a `struct` inline in a `struct` field.  For example:

```
struct Message:
  [$default byte_order: "BigEndian"]
  0 [+4]  UInt    message_length
  4 [+4]  struct  payload:
    0 [+1]   UInt    incoming
    2 [+2]   UInt    scale_factor
```

This is equivalent to:

```
struct Message:
  [$default byte_order: "BigEndian"]

  struct Payload:
    0 [+1]   UInt    incoming
    2 [+2]   UInt    scale_factor

  0 [+4]  UInt     message_length
  4 [+4]  Payload  payload
```

This can be useful as a way to group related fields together.


#### Using `struct` to define a C-like `union`

Emboss doesn't support C-like `union`s directly via built in type
definitions. However, you can use Emboss's overlapping fields feature to
effectively create a `union`:

```
struct Foo:
  0 [+1] UInt a
  0 [+2] UInt b
  0 [+4] UInt c
```


#### Automatically-Generated Fields

A `struct` will have `$size_in_bytes`, `$max_size_in_bytes`, and
`$min_size_in_bytes` virtual field automatically generated.  These virtual field
can be referenced inside the Emboss language just like any other virtual field:

```
struct Inner:
  0 [+4]  UInt  field_a
  4 [+4]  UInt  field_b

struct Outer:
  0 [+1]                       UInt   message_type
  if message_type == 4:
    4 [+Inner.$size_in_bytes]  Inner  payload
```


##### `$size_in_bytes`

An Emboss `struct` has an *intrinsic* size, which is the size required to hold
every field in the `struct`, regardless of how many bytes are in the buffer that
backs the `struct`.  For example:

```
struct FixedSize:
  0 [+4]  UInt  long_field
  4 [+2]  UInt  short_field
```

In this case, `FixedSize.$size_in_bytes` will always be `6`, even if a
`FixedSize` is placed in a larger field:

```
struct Envelope:
  # padded_payload.$size_in_bytes == FixedSize.$size_in_bytes == 6
  0 [+8]  FixedSize  padded_payload
```

The intrinsic size of a `struct` might not be constant:

```
struct DynamicallySizedField:
  0 [+1]       UInt      length
  1 [+length]  UInt:8[]  payload
  # $size_in_bytes == 1 + length

struct DynamicallyPlacedField:
  0 [+1]       UInt  offset
  offset [+1]  UInt  payload
  # $size_in_bytes == offset + 1

struct OptionalField:
  0 [+1]    UInt  version
  if version > 3:
    1 [+1]  UInt  optional_field
  # $size_in_bytes == (version > 3 ? 2 : 1)
```

If the intrinsic size is dynamic, it can still be read dynamically from a field:

```
struct Envelope2:
  0 [+1]             UInt                   payload_size
  1 [+payload_size]  DynamicallySizedField  payload
  let padding_bytes = payload_size - payload.$size_in_bytes
```


##### `$max_size_in_bytes`

The `$max_size_in_bytes` virtual field is a constant value that is at least as
large as the largest possible value for `$size_in_bytes`.  In most cases, it
will exactly equal the largest possible message size, but it is possible to
outsmart Emboss's bounds checker.

```
struct DynamicallySizedStruct:
  0 [+1]       UInt      length
  1 [+length]  UInt:8[]  payload

struct PaddedContainer:
  0 [+DynamicallySizedStruct.$max_size_in_bytes]  DynamicallySizedStruct  s
  # s will be 256 bytes long.
```


##### `$min_size_in_bytes`

The `$min_size_in_bytes` virtual field is a constant value that is no larger
than the smallest possible value for `$size_in_bytes`.  In most cases, it will
exactly equal the smallest possible message size, but it is possible to
outsmart Emboss's bounds checker.

```
struct DynamicallySizedStruct:
  0 [+1]       UInt      length
  1 [+length]  UInt:8[]  payload

struct PaddedContainer:
  0 [+DynamicallySizedStruct.$min_size_in_bytes]  DynamicallySizedStruct  s
  # s will be 1 byte long.
```


### `enum`

An `enum` defines a set of named integers.

```
enum Color:
  BLACK   = 0
  RED     = 1
  GREEN   = 2
  YELLOW  = 3
  BLUE    = 4
  MAGENTA = 5
  CYAN    = 6
  WHITE   = 7

struct PaletteEntry:
  0 [+1]  UInt   id
  1 [+1]  Color  color
```

Enum values are always read the same way as `Int` or `UInt` -- that is, as an
unsigned integer or as a 2's-complement signed integer, depending on whether the
`enum` contains any negative values or not.

Enum values do not have to be contiguous, and may repeat:

```
enum Baud:
  B300     = 300
  B600     = 600
  B1200    = 1200
  STANDARD = 1200
```

All values in a single `enum` must either be between -9223372036854775808
(-2^63) and 9223372036854775807 (2^(63)-1), inclusive, or between 0 and
18446744073709551615 (2^(64)-1), inclusive.

It is valid to have an `enum` field that is too small to contain some values in
the `enum`:

```
enum LittleAndBig:
  LITTLE  = 1
  BIG     = 0x1_0000_0000

struct LittleOnly:
  0 [+1]  LittleAndBig:8  little_only  # Too small to hold LittleAndBig.BIG
```

Emboss `enum`s are *open*: they may take values that are not defined in the
`.emb`, as long as those values are in range.  The `is_signed` and
`maximum_bits` attributes, below, may be used to control the allowed range of
values.


#### `is_signed` Attribute

The attribute `is_signed` may be used to explicitly specify whether an `enum`
is signed or unsigned.  Normally, an `enum` is signed if there is at least one
negative value, and unsigned otherwise, but this behavior can be overridden:

```
enum ExplicitlySigned:
  [is_signed: true]
  POSITIVE = 10
```


#### `maximum_bits` Attribute

The attribute `maximum_bits` may be used to specify the *maximum* width of an
`enum`: fields of `enum` type may be smaller than `maximum_bits`, but never
larger:

```
enum ExplicitlySized:
  [maximum_bits: 32]
  MAX_VALUE = 0xffff_ffff

struct Foo:
  0 [+4]  ExplicitlySized  four_bytes  # 32-bit is fine
  #4 [+8]  ExplicitlySized  eight_bytes  # 64-bit field would be an error
```

If not specified, `maximum_bits` defaults to `64`.

This also allows back end code generators to use smaller types for `enum`s, in
some cases.


#### Inline `enum`

It is possible to provide an enum definition directly in a field definition in a
`struct` or `bits`:

```
struct TurnSpecification:
  0 [+1]  UInt  degrees
  1 [+1]  enum  direction:
    LEFT  = 0
    RIGHT = 1
```

This example creates a nested `enum` `TurnSpecification.Direction`, exactly as
if it were written:

```
struct TurnSpecification:
  enum Direction:
    LEFT  = 0
    RIGHT = 1

  0 [+1]  UInt       degrees
  1 [+1]  Direction  direction
```

This can be useful when a particular `enum` is short and only used in one place.

Note that `maximum_bits` and `is_signed` cannot be used on an inline `enum`.
If you need to use either of these attributes, make a separate `enum`.


### `bits`

A `bits` defines a view of an ordered sequence of bits.  Each field is a view of
some particular subsequence of the `bits`'s bits, whose interpretation is
determined by the field's type.

The structure of a `bits` definition is very similar to a `struct`, except that
a `struct` provides a structured view of bytes, where a `bits` provides a
structured view of bits.  Fields in a `bits` must have bit-oriented types (such
as other `bits`, `UInt`, `Bcd`, `Flag`).  Byte-oriented types, such as
`struct`s, may not be embedded in a `bits`.

For example:

```
bits ControlRegister:
  -- The `ControlRegister` holds basic control values.

  4 [+12]  UInt  horizontal_start_offset
    -- The number of pixel clock ticks to wait after the start of a line
    -- before starting to draw pixel data.

  3 [+1]   Flag  horizontal_overscan_disable
    -- If set, the electron gun will be disabled during the overscan period,
    -- otherwise the overscan color will be used.

  0 [+3]   UInt  horizontal_overscan_color
    -- The palette index of the overscan color to use.

struct RegisterPage:
  -- The registers of the BGA (Bogus Graphics Array) card.

  0 [+2]  ControlRegister  control_register
    [byte_order: "LittleEndian"]
```

The first line introduces the `bits` and gives it a name.  This name may be
used in field definitions to specify that the field has a structured type, and
is used in the generated code.

For example, to write a `horizontal_overscan_color` of 7 to a pair of bytes in
C++, you would use:

```c++
// vector<uint8_t> bytes;
auto register_page_view = RegisterPageWriter(&bytes[0], bytes.size());
register_page_view.control_register().horizontal_overscan_color().Write(7);
```

Similar to `struct`, each field starts with a *bit* range (`4 [+12]`) that
indicates which bits it covers.  For example, the `horizontal_overscan_disable`
field only covers bit 3.  Bit 0 always corresponds to the lowest-order bit the
bitfield; that is, if a `UInt` covers the same bits as the `bits` construct,
then bit 0 in the `bits` will be the same as the `UInt` mod 2.  This is often,
but not always, how bits are numbered in protocol specifications.

After the field's location is the field's *type*.  The type determines how the
field's bits are interpreted: typical choices are `UInt` (for unsigned
integers), `Flag` (for boolean flags), and `enum`s.  Other `bits` may also be
used, as well as any `external` types declared with `[addressable_unit_size:
1]`.

Fields may have attributes and documentation, just like any other Emboss
construct.

In generated code, reading or writing any field of a `bits` construct will cause
the entire field to be read or written -- something to keep in mind when reading
or writing a memory-mapped register space.


#### Anonymous `bits`

It is possible to use an anonymous `bits` definition directly in a `struct`;
for example:

```
struct Message:
  [$default byte_order: "BigEndian"]
  0 [+4]     UInt  message_length
  4 [+4]     bits:
    0 [+1]   Flag  incoming
    1 [+1]   Flag  last_fragment
    2 [+4]   UInt  scale_factor
    31 [+1]  Flag  error
```

In this case, the fields of the `bits` will be treated as though they are fields
of the outer struct.


#### Inline `bits`

Like `enum`s, it is also possible to define a named `bits` inline in a `struct`
or `bits`.  For example:

```
struct Message:
  [$default byte_order: "BigEndian"]
  0 [+4]     UInt  message_length
  4 [+4]     bits  payload:
    0 [+1]   Flag  incoming
    1 [+1]   Flag  last_fragment
    2 [+4]   UInt  scale_factor
    31 [+1]  Flag  error
```

This is equivalent to:

```
struct Message:
  [$default byte_order: "BigEndian"]

  bits  Payload:
    0 [+1]   Flag  incoming
    1 [+1]   Flag  last_fragment
    2 [+4]   UInt  scale_factor
    31 [+1]  Flag  error

  0 [+4]  UInt     message_length
  4 [+4]  Payload  payload
```

This can be useful as a way to group related fields together.


#### Automatically-Generated Fields

A `bits` will have `$size_in_bits`, `$max_size_in_bits`, and `$min_size_in_bits`
virtual fields automatically generated.  These virtual fields can be referenced
inside the Emboss language just like any other virtual field:

```
bits Inner:
  0 [+4]  UInt  field_a
  4 [+4]  UInt  field_b

struct Outer:
  0 [+1]                      UInt   message_type
  if message_type == 4:
    4 [+Inner.$size_in_bits]  Inner  payload
```


##### `$size_in_bits`

Like a `struct`, an Emboss `bits` has an *intrinsic* size, which is the size
required to hold every field in the `bits`, regardless of how many bits are
in the buffer that backs the `bits`.  For example:

```
bits FixedSize:
  0 [+3]  UInt  long_field
  3 [+1]  Flag  short_field
```

In this case, `FixedSize.$size_in_bits` will always be `4`, even if a
`FixedSize` is placed in a larger field:

```
struct Envelope:
  # padded_payload.$size_in_bits == FixedSize.$size_in_bits == 4
  0 [+8]  FixedSize  padded_payload
```

Unlike `struct`s, the size of `bits` must known at compile time; there are no
dynamic `$size_in_bits` fields.


##### `$max_size_in_bits`

Since `bits` must be fixed size, the `$max_size_in_bits` field has the same
value as `$size_in_bits`.  It is provided for consistency with
`$max_size_in_bytes`.


##### `$min_size_in_bits`

Since `bits` must be fixed size, the `$min_size_in_bits` field has the same
value as `$size_in_bits`.  It is provided for consistency with
`$min_size_in_bytes`.


### `external`

An `external` type is used when a type cannot be defined in Emboss itself;
instead, external code must be provided to manipulate the type.

Emboss's built-in types, such as `UInt`, `Bcd`, and `Flag`, are defined this way
in a special file called the *prelude*.  For example, `UInt` is defined as:

```
external UInt:
  -- UInt is an automatically-sized unsigned integer.
  [type_requires: $is_statically_sized && 1 <= $static_size_in_bits <= 64]
  [is_integer: true]
  [addressable_unit_size: 1]
```

`external` types are an unstable feature.  Contact `emboss-dev` if you would
like to add your own `external`s.


## Builtin Types and the Prelude

Emboss has a built-in module called the *Prelude*, which contains types that are
automatically usable from any module.  In particular, types like `Int` and
`UInt` are defined in the Prelude.

The Prelude is (more or less) a standard Emboss file, called `prelude.emb`, that
is embedded in the Emboss compiler.

<!-- TODO(bolms): When the documentation generator backend is built, generate
the Prelude documentation from prelude.emb. -->


### `UInt`

A `UInt` is an unsigned integer.  `UInt` can be anywhere from 1 to 64 bits in
size, and may be used both in `struct`s and in `bits`.  `UInt` fields may be
referenced in integer expressions.


### `Int`

An `Int` is a signed two's-complement integer.  `Int` can be anywhere from 1 to
64 bits in size, and may be used both in `struct`s and in `bits`.  `Int` fields
may be referenced in integer expressions.


### `Bcd`

(Note: `Bcd` is subject to change.)

A `Bcd` is an unsigned binary-coded decimal integer.  `Bcd` can be anywhere from
1 to 64 bits in size, and may be used both in `struct`s and in `bits`.  `Bcd`
fields may be referenced in integer expressions.

When a `Bcd`'s size is not a multiple of 4 bits, the high-order "digit" is
treated as if it were zero-extended to a multiple of 4 bits.  For example, a
7-bit `Bcd` value can store any number from 0 to 79.


### `Flag`

A `Flag` is a 1-bit boolean value.  A stored value of `0` means `false`, and a
stored value of `1` means `true`.


### `Float`

A `Float` is a floating-point value in an IEEE 754 binaryNN format, where NN is
the bit width.

Only 32- and 64-bit `Float`s are supported.  There are no current plans to
support 16- or 128-bit `Float`s, nor the nonstandard x86 80-bit `Float`s.

IEEE 754 does not specify which NaN bit patterns are signalling NaNs and which
are quiet NaNs, and thus Emboss also does not specify which NaNs are which.
This means that a quiet NaN written through an Emboss view one system could be
read out as a signalling NaN through an Emboss view on a different system.  If
this is a concern, the application must explicitly check for NaN before doing
arithmetic on any floating-point value read from a `Float` field.


## General Syntax

### Names

All names in Emboss must be ASCII, for compatibility with languages such as C
and C++ that do not support Unicode identifiers.

Type names in Emboss are always `CamelCase`.  They must start with a capital
letter, contain at least one lower-case letter, and contain only letters and
digits.  They are required to match the regex
`[A-Z][a-zA-Z0-9]*[a-z][a-zA-Z0-9]*`

Imported module names and field names are always `snake_case`.  They must start
with a lower-case letter, and may only contain lower-case letters, numbers, and
underscore.  They must match the regex `[a-z][a-z_0-9]*`.

Enum value names are always `SHOUTY_CASE`.  They must start with a capital
letter, may only contain capital letters, numbers, and underscore, and must be
at least two characters long.  They must match the regex
`[A-Z][A-Z_0-9]*[A-Z_][A-Z_0-9]*`.

Additionally, names that are used as keywords in common programming languages
are disallowed.  A complete list can be found in the [Grammar
Reference](grammar.md).


### Expressions

#### Primary expressions

Emboss primary expressions are field names (like `field` or `field.subfield`),
numeric constants (like `9` or `0x1_0000_0000`), enum value names (like
`Enum.VALUE`), and the boolean constants `true` and `false`.

Subfields may be specified using `.`; e.g., `foo.bar` references the `bar`
subfield of the `foo` field.  Emboss parses `.` before any expressions: unlike
many languages, something like `(foo).bar` is a syntax error in Emboss.

Enum values generally must be qualified by their type; e.g., `Color.RED` rather
than just `RED`.  Enums defined in other modules must use the imported module
name, as in `styles.Color.RED`.


#### Operators and Functions

Note: Emboss currently has a relatively limited set of operators because
operators have been implemented as needed.  If you could use an operator that is
not on the list, email `emboss-dev@`, and we'll see about adding it.

Emboss operators have the following precedence (tightest binding to loosest
binding):

1.  `()` `$max()` `$present()` `$upper_bound()` `$lower_bound()`
2.  unary `+` and `-` ([see note 1](#note-1-unary-plusminus-precedence))
3.  `*`
4.  `+` `-`
5.  `<` `>` `==` `!=` `>=` `<=` ([see note 2](#note-2-chained-and-mixed-comparisons))
6.  `&&` `||` ([see note 3](#note-3-logical-andor-precedence))
7.  `?:` ([see note 4](#note-4-choice-operator-precedence))


###### Note 1 (Unary Plus/Minus Precedence)

Only one unary `+` or `-` may be applied to an expression without parentheses.
These expressions are valid:

```
-5
+6
-(-x)
```

These are not:

```
- -5
-+5
+ +5
+-5
```


###### Note 2 (Chained and Mixed Comparisons)

The relational operators may be chained like so:

```
10 <= x < 50        # 10 <= x && x < 50
10 <= x == y < 50   # 10 <= x && x == y && y < 50
100 > y >= 2        # 100 > y && y >= 2
x == y == 15        # x == y && y == 15
```

These are not:

```
10 < x > 50
10 < x == y >= z
x == y >= z <= 50
```

If one specifically wants to compare the result of a comparison, parentheses
must be used:

```
(x > 15) == (y > 15)
(x > 15) == true
```

The `!=` operator may not be chained.

A chain may contain either `<`, `<=`, and/or `==`, or `>`, `>=`, and/or `==`.
Greater-than comparisons may not be mixed with less-than comparisons.


###### Note 3 (Logical And/Or Precedence)

The boolean logical operators have the same precedence, but may not be mixed
without parentheses.  The following are allowed:

```
x && y && z
x || y || z
(x || y) && z
x || (y && z)
```

The following are not allowed:

```
x || y && z
x && y || z
```


###### Note 4 (Choice Operator Precedence)

The choice operator `?:` may not be chained without parentheses.  These are OK:

```
q ? x : (r ? y : z)
q ? (r ? x : y) : z
```

This is not:

```
q ? x : r ? y : z  # Is this `(q?x:r)?y:z` or `q?x:(r?y:z)`?
q ? r ? x : y : z  # Technically unambiguous, but visually confusing
```


##### `()`

Parentheses are used to override precedence.  The subexpression inside the
parentheses will be evaluated as a unit:

```
3 * 4 + 5 == 17
3 * (4 + 5) == 27
```

The value inside the parentheses can have any type; the value of the resulting
expression will have the same type.


##### `$present()`

The `$present()` function takes a field as an argument, and returns `true` if
the field is present in its structure.

```
struct PresentExample:
  0 [+1]    UInt  x
  if false:
    1 [+1]  UInt  y
  if x > 10:
    2 [+1]  UInt  z
  if $present(x):  # Always true
    0 [+1]  Int  x2
  if $present(y):  # Always false
    1 [+1]  Int  y2
  if $present(z):  # Equivalent to `if x > 10`
    2 [+1]  Int  z2
```

`$present()` takes exactly one argument.

The argument to `$present()` must be a reference to a field.  It can be a nested
reference, like `$present(x.y.z.q.r)`.  The type of the field does not matter.

`$present()` returns a boolean.


##### `$max()`

The `$max()` function returns the maximum value out of its arguments:

```
$max(1) == 1
$max(-10, -5) == -5
$max(1, 2, 3, 4, 5, 6, 7, 8, 9, 10) == 10
```

`$max()` requires at least one argument.  There is no explicit limit on the
number of arguments, but at some point the Emboss compiler will run out of
memory.

All arguments to `$max()` must be integers, and it returns an integer.


##### `$upper_bound()`

The `$upper_bound()` function returns a value that is at least as high as the
maximum possible value of its argument:

```
$upper_bound(1) == 1
$upper_bound(-10) == -10
$upper_bound(foo) == 255  # If foo is UInt:8
$upper_bound($max(foo, 500)) == 500  # If foo is UInt:8
```

Generally, `$upper_bound()` will return a tight bound, but it is possible to
outsmart Emboss's bounds checker.

`$upper_bound()` takes a single integer argument, and returns a single integer
argument.


##### `$lower_bound()`

The `$lower_bound()` function returns a value that is no greater than the
minimum possible value of its argument:

```
$lower_bound(1) == 1
$lower_bound(-10) == -10
$lower_bound(foo) == -127  # If foo is Int:8
$lower_bound($min(foo, -500)) == -500  # If foo is Int:8
```

Generally, `$lower_bound()` will return a tight bound, but it is possible to
outsmart Emboss's bounds checker.

`$lower_bound()` takes a single integer argument, and returns a single integer
argument.


##### Unary `+` and `-`

The unary `+` operator returns its argument unchanged.

The unary `-` operator subtracts its argument from 0:

```
3 * -4 == 0 - 12
-(3 * 4) == -12
```

Unary `+` and `-` require an integer argument, and return an integer result.


##### `*`

`*` is the multiplication operator:

```
3 * 4 == 12
10 * 10 == 100
```

The `*` operator requires two integer arguments, and returns an integer.


##### `+` and `-`

`+` and `-` are the addition and subtraction operators, respectively:

```
3 + 4 == 7
3 - 4 == -1
```

The `+` and `-` operators require two integer arguments, and return an integer
result.


##### `==` and `!=`

The `==` operator returns `true` if its arguments are equal, and `false` if not.

The `!=` operator returns `false` if its arguments are equal, and `true` if not.

Both operators take two boolean arguments, two integer arguments, or two
arguments of the same enum type, and return a boolean result.


##### `<`, `<=`, `>`, and `>=`

The `<` operator returns `true` if its first argument is numerically less than
its second argument.

The `>` operator returns `true` if its first argument is numerically greater
than its second argument.

The `<=` operator returns `true` if its first argument is numerically less than
or equal to its second argument.

The `>=` operator returns `true` if its first argument is numerically greater
than or equal to its second argument.

All of these operators take two integer arguments, and return a boolean value.


##### `&&` and `||`

The `&&` operator returns `false` if either of its arguments are `false`, even
if the other argument cannot be computed.  `&&` returns `true` if both arguments
are `true`.

The `||` operator returns `true` if either of its arguments are `true`, even if
the other argument cannot be computed.  `||` returns `false` if both arguments
are `false`.

The `&&` and `||` operators require two boolean arguments, and return a boolean
result.


##### `?:`

The `?:` operator, used like <code>*condition* ? *if\_true* :
*if\_false*</code>, returns *`if_true`* if *`condition`* is `true`, otherwise
*`if_false`*.

Other than having stricter type requirements for its arguments, it behaves like
the C, C++, Java, JavaScript, C#, etc. conditional operator `?:` (sometimes
called the "ternary operator").

The `?:` operator's *`condition`* argument must be a boolean, and the
*`if_true`* and *`if_false`* arguments must have the same type.  It returns the
same type as *`if_true`* and *`if_false`*.


### Numeric Constant Formats

Numeric constants in Emboss may be written in decimal, hexadecimal, or binary
format:

```
12      # The decimal value of 6 + 6.
012     # The same value; NOT interpreted as octal.
0xc     # The same value, written in hexadecimal.
0xC     # Hex digits may be written in capital letters.
        # Note that the 'x' must be lower-case: 0XC is not allowed.
0b1100  # The same value, in binary.
```

Decimal numbers may use `_` as a thousands separator:

```
1_000_000  # 1e6
123_456_789
```

Hexadecimal and binary numbers may use `_` as a separator every 4 or 8 digits:

```
0x1234_5678_9abc_def0
0x12345678_9abcdef0
0b1010_0101_1010_0101
0b10100101_10100101
```

If separators are used, they *must* be thousands separators (for decimal
numbers) or 4- or 8-digit separators (for binary or hexadecimal numbers); `_`
may *not* be placed arbitrarily.  Binary and hexadecimal numbers must be
consistent about whether they use 4- or 8-digit separators; they cannot be
mixed in the same constant:

```
1000_000              # Not allowed: missing the separator after 1.
1_000_00              # Not allowed: separators must be followed by a multiple
                      # of 3 digits.
0x1234_567            # Not allowed: separators must be followed by a multiple
                      # of 4 or 8 digits.
0x1234_5678_9abcdef0  # Not allowed: cannot mix 4- and 8-digit separators.
```
