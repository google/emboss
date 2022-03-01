# Design Sketch: Protocol Buffers <=> Emboss Translation

## Overview

There are many tools that operate on Protocol Buffer objects ("Protos").
Providing a way to translate between Protos and Emboss structures would allow
those tools to be used without writing a tedious translation layer.


## Defining an Equivalent Proto `message`

For each Emboss `struct`, `bits`, `enum`, and primitive type, there would need
to be some equivalent Proto encoding -- likely a `message` for each `struct` or
`bits`, a Proto `enum` inside a `message` for each `enum` (see below), and a
Proto primitive type for each Emboss primitive type.

There are two basic ways that the Proto definition could be generated:

1.  Human-Authored `.proto` Definitions:

    This requires more human effort when trying to use Emboss structures as
    Protos, likely approaching the level of effort to just hand-write a
    translation layer.  It *might* make it easier to use an existing Proto
    definition.

    It would also require significantly more flexibility, and therefore more
    complexity, in the Emboss compiler.

2.  Emboss Generates a `.proto` File:

    This option is likely to create slightly "unnatural" Proto definitions (see
    below for more details), but requires very little human effort to create a
    translation to a Proto.

    Escape hatches for "partially hand-coded" translations should be
    considered, even if they are not implemented in the first pass at Emboss
    <=> Proto translation.

Because a human always has the option to hand code their own translation, this
document will assume option 2: the Emboss compiler generates a Proto
definition.


### Proto2 vs Proto3

The current state of Google Protocol Buffers is a bit messy, with both "version
2" ("Proto2") and "version 3" ("Proto3") Protocol Buffers.  Proto2 and Proto3
can (mostly) freely interoperate -- Proto2 files can import and use messages
from Proto3 files and vice versa -- and both have long-term support guarantees
from Google.  Differences between Proto2 and Proto3 are highlighted below: it
is not clear whether Emboss should generate Proto2, Proto3, or both (via a flag
or file-level property).


### Primitive Types

#### `Int`, `UInt`

`Int` and `UInt` can map to Proto's `int32`, `int64`, `uint32`, and `uint64`.
Smaller integers can be extended to the next-largest Proto integer size.


#### `Float`

`Float` maps to Proto's `float` and `double`.


#### `Flag`

`Flag` maps to Proto's `bool`.


#### (Future) Emboss String/Blob Type

A future Emboss string or blob type would translate to Proto's `string` or
`bytes`.  It is likely that an Emboss "string" will be `bytes` in Proto, since
Emboss is unlikely to enforce UTF-8 compliance.

Note that Proto (version 2 only?) C++ does not enforce UTF-8 compliance on
`string`, which can lead to crashes when the message is decoded in Python,
Java, or another language that properly enforces string encoding.


### Arrays

Unidimensional arrays map neatly to `repeated` Proto fields.

Multidimensional arrays must be handled with a wrapper `message` at each
dimension after the first.

Because of the way that Proto wire format works (see [Translation Between
Emboss View and Proto Wire Format](#between-emboss-view-and-proto-wire-format),
below), there is a slight technical advantage to wrapping the outermost array
in its own message.  This does make the (Proto) API a bit awkward, but not too
bad:

```c++
auto element = structure.array_field().v(2);
auto nested_element = structure.array_2d_field().v(2).v(1);
```

vs

```c++
auto element = structure.array_field(2);
auto nested_element = structure.array_2d_field(2).v(1);
```


### Conditional Fields

In Proto2, conditional fields map fairly well to the concept of "presence" for
fields.  Proto2 allows non-present fields to be read -- returning the default
value for that field -- but this is not an issue for Emboss, which can easily
generate the appropriate <code>has_*field*()</code> calls.

Proto3 does not track existence for primitive types the way that Proto2 does.
The "recommended" workaround is to use standardized wrapper types
(`google.protobuf.FloatValue`, `google.protobuf.Int32Value`, etc.), which
introduce an extra layer.  There is a second workaround, related to the slightly
weird way that Proto handles `oneof`: if the primitive field is inside a
`oneof`, then it is *not* always present.  A `oneof` may contain a single
member, so primitive-typed fields could be generated as something like:

```
message Foo {
  oneof field_1_oneof {
    int32 field_1 = 1;
  }
}
```

Note that in Emboss, changing a field from unconditionally present to
conditionally present is (usually) a backwards-compatible change.


### (Future) Emboss Union Construct

An Emboss union construct would be necessary to take advantage of runtime space
savings from using a Proto `oneof`.


### `struct` and `bits`

`struct` and `bits` map neatly to `message`, with few issues.


#### Anonymous `bits`

Anonymous `bits` get "flattened" so that their fields appear to be part of their
enclosing structure.  This should be handled reasonably well via treating
read-write virtual fields as members of the `message`, and by suppressing the
"private" fields, such as anonymous `bits`.


#### Proto Field IDs

Proto requires each field to have a unique tag ID.  We propose that, for fields
with a fixed start location, the start location + 1 is used for a default tag
ID: since a change to a field's start location would be a breaking change to the
Emboss definition, it should be reasonably stable.  For fields with a variable
start location, virtual fields, or where the programmer wants a specific tag,
the attribute `[(proto) id]` can be used to specify the ID.

The "+ 1" is required since `0` is not a valid Proto tag ID.


### `enum`

The Emboss `enum` construct does not map cleanly to the Proto `enum` construct,
with different issues in Proto2 vs Proto3.

Common to both, the names of Proto `enum` values are hoisted into the same
namespace as the `enum` itself (consistent with the C's handling of `enum`),
which means that multiple `enum`s in the same context cannot hold the same value
name.  This can be handled -- somewhat awkwardly -- by wrapping the `enum` in a
"namespace" `message`, like:

```
message SomeEnum {
  enum SomeEnum {
    VALUE1 = 1;
    VALUE2 = 2;
  }
}
```

Additionally, Proto `enum` values must fit in an `int32`, whereas Emboss `enum`
values may require up to a `uint64`.

Proto2: In Proto2, `enum`s are closed: unknown values are ignored on message
parse, so `enum` fields can never have an unknown value at runtime.  Emboss
`enum`s, much like C `enum`s, can hold unknown values.

Proto3: In Proto3, `enum`s are open, like Emboss `enum`s, but every Proto3
`enum` must have a first entry whose value is `0`.  In order to avoid
compatibility issues, Emboss should emit a well-known name for the `0` value in
every case.  There is a second issue in Proto3: there is no "has" bit for enum
fields, so conditional enum fields have to be wrapped in a struct.
(TODO(bolms): are Proto3 `enum`s signed, unsigned, or either?)

Thus, for Proto2, `enum`s would produce something like:

```
message SomeEnum {
  enum SomeEnum {
    VALUE1 = 1;
    VALUE2 = 2;
  }
  oneof {
    SomeEnum value = 1;
    int64 integer_value = 2;
  }
}
```

which would be included in structures as:

```
message SomeStruct {
  optional SomeEnum some_enum = 1;  // NOT SomeEnum.SomeEnum
}
```

For Proto3, the situation ends up similar:

```
message SomeEnum {
  enum SomeEnum {
    DEFAULT = 0;
    VALUE1 = 1;
    VALUE2 = 2;
  }
  SomeEnum value = 1;
}

message SomeStruct {
  optional SomeEnum some_enum = 1;  // NOT SomeEnum.SomeEnum
}
```


#### `enum` Name Restrictions

Proto enforces a (very slightly) stricter rule for the names of values within
an `enum` than Emboss does: they must not collide *even when translated to
CamelCase*.

For example, Emboss allows:

```
enum Foo:
  BAR_1_1 = 2
  BAR_11 = 11
```

When translated to CamelCase, `BAR_1_1` and `BAR_11` both become `Bar11`, and
thus are not allowed to be part of the same `enum` in Proto.

It may be sufficient to require `.emb` authors to update their `enum`s when
attempting to compile to Proto.


### Bookkeeping Fields

Emboss structures often have "bookkeeping" fields that are either irrelevant to
typical Proto consumers, or place unusual restrictions.

For example, fields which are used to calculate the offset of other fields are
generally not useful to Proto consumers:

```
struct Foo:
  0 [+4]  UInt  header_length (h)
  h [+4]  UInt  first_body_message
```

**These fields would still need to be set correctly when translating *from*
Proto to Emboss.**

Some of the pain could likely be mitigated via a [default
values](#default_values.md) feature, when implemented.

Field-length fields are somewhat trickier:

```
struct Foo:
  0 [+4]  UInt      message_length (m)
  4 [+m]  UInt:8[]  message_bytes
```

In Proto, `message_length` becomes an implicit part of `message_bytes`, since
`message_bytes` knows its own length.  For simple fields cases, as above, we
can likely have the Emboss compiler "just figure it out" and fold
`message_length` into `message_bytes`.  For more complex cases, we will
probably need to have explicit annotations (`[(proto) set_length_by: x =
some_expression]`), or just require applications using the Proto side to set
length fields correctly.

A similar problem happens with "message type" fields:

```
struct Foo:
  0 [+4]  MessageType  message_type (mt)
  if mt == MessageType.BAR:
    4 [+8]  Bar  bar
  if mt == MessageType.BAZ:
    4 [+16]  Baz  baz
  # ...
```

This will probably be easier to handle with a `union` construct in Emboss.
Again, "complex" cases will probably have to be handled by application code.


## Translation

### Between Emboss View and Proto In-Memory Format

Translation should be relatively straightforward; when going from Emboss to
Proto, the problem is roughly equivalent to serializing a View to text, and for
Proto to Emboss it is roughly equivalent to deserializing a View from text.

One minor difference is that the *deserialization* from Proto must occur in
dependency order, while serialization can happen in any order.  In Emboss text
format, *serialization* happens in dependency order, and deserialization happens
in whatever order is specified in the text.

As with deserialization from text, it is possible for the Proto message to
include untranslatable entries (e.g., an Emboss `Int:16` would stored in a Proto
`int32`; a too-large value in the Proto `message` should be rejected).


### Between Emboss View and Proto Wire Format

Since the Proto wire format is extremely stable and documented, it would be
possible for Emboss to emit code to directly translate between Emboss structs
and proto wire format.

*Serialization* is relatively straightforward; except for arrays, the code
structure is almost identical to the text serialization code structure.

*Deserialization* is problematic.  First and foremost, Proto does not specify an
order in which the fields of a structure will be serialized, so it is entirely
possible for the Emboss view to see a dependent field before its prerequisite
(e.g., have a variable-offset field before the offset specifier field).
Secondly, Proto repeated fields aren't really "arrays"; on the wire, other
fields can appear *in between* elements of repeated fields.  For Emboss, this
means that every array in the structure would have to maintain a cursor during
deserialization.

It *may* still be desirable to support serialization without trying to support
deserialization, or to support deserialization for a subset of structures, so
that we can send protos to/from microcontrollers: this would be an alternative
to Nanopb for some cases.


### Between Emboss View and [Nanopb](https://github.com/nanopb/nanopb)

In order to translate between Emboss views and Protos on microcontrollers and
other limited-memory devices, it may make sense to generate Emboss <=> Nanopb
code.  On top of the standard Proto generator, we would have to implement a
Nanopb options file generator, and translation code.


## Miscellaneous Notes

### Overlays

Emboss was designed with the notion that some backends would need their own
attributes -- for example, the `[(cpp) namespace]` attribute, and here there
are a number of `[(proto)]` attributes.

However, adding back-end-specific attributes still requires changes to be made
directly to the `.emb` file, which may be inconvenient for `.emb`s from third
parties.

Ideally, one could write an "overlay file," like:

```
message Foo
  [(proto) attr = value]

  field
    [(proto) field_attr = value]
```

This is not needed for a first pass at a Proto back end, but should be
considered.


### Generating an `.emb` From a `.proto`

There are cases where it would be useful to generate a microcontroller-friendly
representation of an existing Proto, rather than the other way around.

For most `message`s, it would be relatively straightforward to generate a
`struct`, like:

```
message Foo {
  optional int32 bar = 1;
  optional bool baz = 2;
  optional string qux = 3;
}
```

to:

```
struct Foo:
  0          [+4]             bits:
    0 [+1]    Flag  has_bar
    1 [+1]    Flag  has_baz
    if has_baz:
      2 [+1]  Flag  baz
    2 [+1]    Flag  has_qux

  if has_bar:
    4          [+4]           Int:32    bar

  if has_qux:
    8          [+4]           UInt:32   qux_offset
    12         [+4]           UInt:32   qux_length
    qux_offset [+qux_length]  UInt:8[]  qux
```

The main issue is that it would be difficult to maintain equivalent
backwards-compatibility guarantees to the ones that Proto provides as messages
evolve.

Also note that this format is fairly close to the [Cap'n
Proto](https://capnproto.org/) format.
