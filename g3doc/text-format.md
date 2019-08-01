<!-- TODO(bolms): this file could use a review to make sure it is still correct
(as of 2017 December).  -->

# Text Format

[TOC]

## Background

Emboss messages may be automatically converted between a human-readable text
format and machine-readable bytes.  For example, if you have the following
`.emb` file:

```
struct Foo:
  0 [+1]  UInt  a
  1 [+1]  UInt  b

struct Bar:
  0 [+2]  Foo  c
  2 [+2]  Foo  d
```

You may decode a Bar like so:

```c++
uint8_t buffer[4];
auto bar_writer = BarWriter(buffer, sizeof buffer);
bar_writer.UpdateFromText(R"(
    {
      c: {
        a: 12
        b: 0x20  # Hex numbers are supported.
      }
      d: {
        a: 33
        b: 0b10110011  # ... as are binary.
      }
    }
)");
assert(bar_writer.c().a().Read() == 12);
assert(bar_writer.c().b().Read() == 32);
assert(bar_writer.d().a().Read() == 33);
assert(bar_writer.d().b().Read() == 0xb3);
```

Note that you can use `#`-style comments inside of the text format.

It is also acceptable to omit fields, in which case they will not be updated:

```c++
bar_writer.UpdateFromText("d { a: 123 }");
assert(bar_writer.c().a().Read() == 12);
assert(bar_writer.d().a().Read() == 123);
```

Because Emboss does not enforce dependencies or duplicate field sets in
`UpdateFromText`, it is currently possible to do something like this:

```
# memory_selector.emb
struct MemorySelector:
  0    [+1]  UInt    addr
  addr [+1]  UInt:8  byte
```

```c++
// memory_select_writer.cc
uint8_t buffer[4];
auto memory_writer = MemoryWriter(buffer, sizeof buffer);
memory_writer.UpdateFromText(R"(
    {
      addr: 1
      byte: 10
      addr: 2
      byte: 20
      addr: 3
      byte: 30
      addr: 0
    }
)");
assert(buffer[1] == 10);
assert(buffer[2] == 20);
assert(buffer[3] == 30);
assert(buffer[0] == 0);
```

*Do not rely on this behavior.*  A future version of Emboss may add tracking to
ensure that this example is an error.


## Text Format Details

The exact text format accepted by an Emboss view depends on the view type.
Extra whitespace is ignored between tokens.  Any place where whitespace is
allowed, the `#` character denotes a comment which extends to the end of the
line.


### `struct` and `bits`

The text format of a `struct` or `bits` is a sequence of name/value pairs
surrounded by braces, where field names are separated from field values by
colons:

    {
      field_name: FIELD_VALUE
      field_name_2: FIELD_VALUE_2
      substructure: {
        subfield: 123
      }
    }

Only fields which are actually listed in the text will be set.

If a field's address depends on another field's value, then the order in which
they are listed in the text format becomes important.  When setting both,
always make sure to set the dependee field before the dependent field.

It is currently possible to specify a field more than once, but this may not be
supported in the future.


### `UInt` and `Int`

`UInt`s and `Int`s accept numeric values in the same formats that are allowed
in Emboss source files:

    123456
    123_456
    0x1234cdef
    0x1234_cdef
    0b10100101
    0b1010_0101
    -123
    -0b111


### `Flag`

`Flag`s expect either `true` or `false`.


### `enum`

An `enum`'s value may be either a name listed in the enum definition, or a
numeric value:

    FOO
    2
    100


### Arrays

An array is a list of values (in the appropriate format for the type of the
array), separated by commas and surrounded by braces.  Values may be optionally
prefixed with index markers of the form `[0]:`, where `0` may be any unsigned
integer.  An extra comma at the end of the list is allowed, but not required:

    { 0, 1, 2, 3, 4, 5, 6, 7 }
    { 0, 1, 2, 3, 4, 5, 6, 7, }
    { 0, 1, 2, 3, 4, [7]: 7, [6]: 6, [5]: 5 }

When no index marker is specified, values are written to the index which is one
greater than the previous value's index:

    { [4]: 4, 5, 6, 7, [0]: 0, 1, 2, 3 }

It is currently possible to specify multiple values for a single index, but
this may not be supported in the future.

*TODO(bolms): In the future section about creating new `external` types, make
sure to note that the `external`'s text format should not start with `[` or
`}`.*



