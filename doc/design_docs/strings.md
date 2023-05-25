# String Support for Emboss

GitHub Issue [#28](https://github.com/google/emboss/issues/28)

## Background

It is somewhat common to embed short strings into binary structures; examples
include serial numbers and firmware revisions, although in some cases even
things like IP addresses are encoded as ASCII text embedded in a larger binary
message.

Historically, we have modeled such fields in Emboss by using `UInt:8[]`; that
is, arrays of 8-bit uints.  This is more-or-less functional, but can be awkward
for things like text format output, and provides no way to add assertions to
string fields.

String support is complicated by the fact that there are several common ways of
delimiting strings:

1.  Length determined by another field -- that is, the size of the string is
    explicit.
2.  The string is *terminated* by a specific byte value, usually `'\0'`.  In
    this case, there may be additional "garbage" bytes after the terminator,
    which should not be considered to be part of the string.
3.  The string is *padded* by a specific byte value, usually 32 (`' '`).  In
    this case, the "padding" character can usually occur inside the string,
    and only trailing padding characters should be trimmed off.

For both terminated and padded strings, some formats allow the string to run to
the very end of its field, with no terminator/padding, and some require the
terminator/padding.  In general, it seems that terminated strings are more
likely to require the terminator, while padded strings can usually be entered
with no padding.

There are, no doubt, other ways of delimiting strings.  These seem to be rare
and sui generis, and can often be handled by modeling them as length-determined
strings, then applying the necessary logic in code.

There are also multiple *encodings* for strings, such as ASCII, ISO/IEC 8859-1
("Latin-1"), UTF-8, UTF-16, etc.  UTF-16 seems to be rare outside of
Windows-based software and Java.  Hardware almost always appears to use ASCII
(encoded as one character per byte, with the high bit always clear), although
Java ME-based systems may use UTF-16.


## Proposal

### Bytestrings Only

All strings in Emboss should be considered to be opaque blobs of bytes;
interpretation as ASCII, Latin-1, UTF-8, etc. should be left to the application.

UTF-16 strings are explicitly not handled by this proposal.  In principle, one
could add a "byte width" parameter to the string types, or use a prefix like `W`
to indicate "wide string" types, but it does not seem important for now.  This
decision can be revisited later.


### New Built-In Types

Add three new types to the Prelude (names subject to change):

1.  `FixString`, a string whose contents should be the entire field containing
    the `FixString`.  When writing to a `FixString`, the value must be exactly
    the same length as the field.

    `CouldWriteValue()` should return `true` for all strings that are exactly
    the correct length.

    `FixString` is very close to a notional `Blob` type or the current
    `UInt:8[]` type, except for differences in text format.

2.  `ZString`, a terminated string.  A `ZString` with no arguments uses a null
    byte (`'\0'`) as the terminator.  An optional argument can be used to
    specify the terminator -- a `ZString(36)`, for example, would be terminated
    by `$`.  When reading, the value returned is all bytes up to, but not
    including, the first terminator byte.  When writing, for compatibility, the
    entire field should be written, using the terminator value for padding if
    there is extra space.  A second optional parameter can be used to specify
    that the terminator is not required: `ZString(0, false)` can fill the
    underlying field with no terminator.

    `CouldWriteValue()` should return `true` if the value is no longer than the
    field and the value does not *contain* any instances of the terminator
    byte.

3.  `PaddedString`, a padded string.  A `PaddedString` with no arguments uses
    space (`' '`, 32) as the padding value.  An optional argument can be used to
    specify the padding -- a `PaddedString(0)`, for example, would be padded
    with null bytes.  When reading, the end of the string is discovered by
    walking *backwards* from the end until a non-padding byte is found, then
    returning all bytes from the start of the string to the end.  When writing,
    any excess bytes will be filled with the padding value.

    Although, technically, "at least one byte of padding" could be enforced by
    making the `PaddedString` one byte shorter and following it with a one-byte
    field whose value *must* be the padding byte, for convenience `PaddedString`
    should take a second optional parameter to specify that the terminator *is*
    required: `PaddedString(32, true)` must have at least one space at the end.

    `CouldWriteValue()` should return `true` if the value is no longer than the
    field and the value does not *end with* the padding byte.


### String Constants

String constants (used in constructs such as `[requires: this == "abcd"]`) may
take two forms:

1.  `"A quoted string using C-style escapes like \n"`

    In addition to standard C89 escapes (as interpreted by an ASCII Unix
    compiler):

    *   `\0` => 0
    *   `\a` => 7
    *   `\b` => 8
    *   `\t` => 9
    *   `\n` => 10
    *   `\v` => 11
    *   `\f` => 12
    *   `\r` => 13
    *   `\"` => 34
    *   `\'` => 39
    *   `\?` => 63 (part of the C standard, but rarely used)
    *   `\\` => 92
    *   <code>\x*hh*</code> => 0x*hh*

    The following non-C-standard escapes should be allowed:

    *   `\e` => 27 (not actually standard, but common)
    *   <code>\d*nnn*</code> => *nnn*
    *   <code>\x{*hh*}</code> => 0x*hh*
    *   <code>\d{*nnn*}</code> => *nnn*

    Note that the standard C escape <code>\\*nnn*</code> is explicitly not
    supported.  C treats *nnn* as octal, which is often surprising, and modern
    languages (the cut off date appears to be about 1993 -- right between Python
    2 and Java) have largely dropped support for the octal escapes.

    Based on a brief survey, only `\n`, `\t`, `\"`, `\\`, and `\'` appear to be
    (nearly) universal among popular programming languages.  <code>\x*hh*</code>
    is very common, though not universal.  <code>\u*nnnn*</code>, where *nnnn*
    is a Unicode hex value to be encoded as UTF-8 or UTF-16, also appears to be
    common, but only for text strings.

    To avoid ambiguity, the un-braced <code>\x*hh*</code> escape should be
    required to have 2 hex digits, and the <code>\d*nnn*</code> escape should be
    required to have exactly 3 decimal digits.  The braced versions --
    <code>\x{*hh*}</code> and <code>\d{*nnn*}</code> -- could have any number of
    digits, but should be required to evaluate to a value in the range 0 to 255:
    that is, `\d{000000100}` should be allowed, but `\d{256}` should not.

    `\` characters should not be allowed outside of the escape sequences
    specified here.

    For now, only 7-bit ASCII printable characters (byte values 32 through 126)
    should be allowed in `"quoted strings"`, even though `.emb` files generally
    allow UTF-8.  This requirement may be relaxed in the future.

2.  A list of bytes in `{}`, where each byte is either a single-quoted character
    (`'a'`) or a numeric constant (e.g., `0x20` or `32`).

    For ease of transition from existing `UInt:8[]` fields, explicit index
    markers (`[8]:`) in the list should be allowed if the index exactly matches
    the current cursor index; this matches output from the current Emboss text
    format for `UInt:8[]`.

The existing parameter system will need to be extended to allow default values,
and to allow `external` types to accept parameters if they do not already.


### String Field Methods (C++)

#### C++ String Type Parameterization

All methods that accept or return a string value should be templated on the C++
type to use (`std::string`, `std::string_view`, `char *`, etc.).

For methods that accept a string parameter (`Write`, etc.), the template
argument should be inferred, and they can be called without specifying the type.

For methods that only return a string value (`Read`, etc.), the template
argument would need to be specified: `Read<std::string_view>()`.

`char *` should not be accepted as a return type, due to problems with ensuring
that there is actually a null byte at the end of the string.

As an input type, `char *` is like to need explicit specialization.

In many (most? all?) cases, methods should have no problem with some types that
are not really "string" types, such as `std::vector<char>`.

String types that use `signed char` or `unsigned char` instead of `char` (e.g.,
`std::basic_string<unsigned char>`) should be explicitly supported.

If the `BackingStorage` is not `ContiguousBuffer` (or some equivalent), it seems
that it might be easy to hit undefined behavior with something like
`Read<std::string_view>()`, since the iterator type returned by `begin()` and
`end()` would not correctly model `std::contiguous_iterator`.  The cautious
approach would be to disable `Read()` and `UncheckedRead()` if the backing
storage is not `ContiguousBuffer`; readout to something like `std::string` could
still be explicitly performed using the `begin()`/`end()` iterators.
Alternately, for non-`ContiguousBuffer` backing storage, `Read()` could be
explicitly limited to a small set of known-good types, such as `std::string` and
`std::vector<char>`.


#### Methods

`Read()`, `UncheckedRead()`, `Write()`, and `UncheckedWrite()` should be defined
as one would expect.

`ToString()` should be an alias for `Read()`, to ease conversion from
`UInt:8[]`.

`CouldWriteValue()` should be defined as specified in the previous section.

`Ok()` should return `true` if the string has storage (though it could be
zero-length storage) and the bytes match the requirements (e.g., if a terminator
or padding byte is required, `Ok()` should only return `true` if such a byte is
present).

`Size()` should return the (logical) length of the string in bytes.

`MaxSize()` should return `BackingStorage().SizeInBytes()` or
`BackingStorage().SizeInBytes() - 1` if the string requires a padding or
terminator byte.

`begin()`, `end()`, `rbegin()`, `rend()` should be defined as expected for a
C++ container type.

`operator[]` should return the value of a single byte at the specified offset.


#### `emboss::String` Type

(This section should not be considered particularly authoritative; the actual
implementation could differ greatly if another strategy is turns out to be
easier or less complex in practice.)

Because values retrieved from the different string types can be used
interchangeably at the expression layer (e.g., `let s = condition ? z_string :
fix_string`), there must be a way for all views over strings to return a common
type.  This is complicated by two requirements:

1.  `emboss::String` should not allocate memory.
2.  `emboss::String` needs to handle backing storage that is not
    `ContiguousBuffer`.  It also needs to handle constant strings (`let x =
    "string"`), and be able to assign `Storage`-based strings to constant
    strings and vice versa.

To satisfy the first requirement, `emboss::String` will need to hold a reference
to the underlying storage, not actually copy bytes.

One way to satisfy the second requirement would be to simply copy the string's
bytes out to a new buffer, but that conflicts with the first requirement.
Instead, it should be a sum type over a `Storage` type parameter and a constant
string, like:

```c++
template <typename Storage>
class String {
 public:
  String();
  String(const char *data, int size);
  String(Storage);
  // ... operator= ...
  int size() constexpr;
  char operator[](int index) constexpr {
    return storage_.Index() == 0 ? backports::Get<0>(storage_)[index]
                                 : backports::Get<1>(storage_).data()[index];
  }
  // ... begin(), end(), etc. ...

 private:
  // TODO: replace backports::Variant with std::variant in 2027, when Emboss
  // requires C++17.
  backports::Variant<const char *, Storage> storage_;
};
```

At least for now, `emboss::String` does not need to be exposed as a documented,
supported API -- user code can use `Read<std::string_view>()` and similar
operations as needed, with full knowledge of the underlying storage type.

Comparisons and assignments between `emboss::String`s with different `Storage`
type parameters do not need to be supported, since they cannot be generated by
the code generator -- C++ codegen would only need those operations for
`emboss::String`s that are derived from the same parent structure.


### Handling in Other Languages

C++ is unusual in that it does not differentiate at a language level between
text strings and byte strings.  Most other languages have different types for
byte strings and text strings.

For all languages that differentiate, Emboss strings should be treated as byte
strings or byte arrays (Python3 `bytes`, Rust `Vec<u8>`, Proto `bytes`, etc.)

Other than this caveat, Emboss string support should be straightforward in other
languages.


### Text Format

Text format output should use the `"quoted string"` style.  Byte values outside
the range 32 through 126 should be emitted as escapes.  Values with standard
shorthand escapes (10 => `'\n'`, 0 => `'\0'`, etc.) should be emitted as such.
For other values, hex escapes with exactly two digits (e.g., `\x06`, not `\x6`)
should be emitted.  It may be desirable to allow some `[text_format]` control
over the output in the future.

Text format input should allow both `"quoted string"` and list-of-bytes styles,
with exactly the same rules as string constants in an `.emb` file, except that
bytes > 126 might be allowed in a `"quoted string"`.


### Expressions

#### Type System Changes

In order to facilitate `[requires]` on string types, the new types should have a
new 'string' expression type.


#### Runtime Representation

In this proposal, no string manipulation are allowed, so temporary strings
(which might require memory allocation) will not be necessary.


#### String Attribute Representation

Attributes values are currently represented by a special `AttributeValue` type
which can hold either an `Expression` or a `String`.  With a string expression
type, `AttributeValue` can be replaced by a plain `Expression`.  This will
require changes to everything that touches `AttributeValue`.

Alternately, `AttributeValue` could be left in the IR with only `Expression`,
in which case only code that touches string attributes (`[byte_order]` and
`[(cpp) namespace]`) needs to change.


#### String Comparisons

Comparison operations (`==`, `<`, `>`, `>=`, `<=`, `!=`) should be allowed,
since these can be handled by passing references to existing memory.

Equality and inequality (`==` and `!=`) should be defined in the expected way:
two strings are equal iff they are the same length and the corresponding bytes
in each string have the same value, and they are unequal if they are not equal.

For ordering, strings should be compared lexically, using the binary value of
each byte, with no regard for semantic collation.  That is, `"Z" < "a"`, since
`'Z'` is 90 and `'a'` is 97.

When one string is a strict prefix of another string, the shorter string should
be "less than" the longer; e.g., `"abc" < "abcdef"`.  This is the same as the
natural ordering for zero-terminated strings.


#### Future String Operations

It may be desirable, at some future point, to allow various string
manipulations, such as concatenation or repetition, at least for compile-time
strings.

A substring operation should be possible without requiring memory allocation.

Indexing into a string (`str[offset]`) should be allowed if/when indexing into
an array is finally supported.


### Arrays of Strings

In some cases, it may be desirable to have an array of strings, like:

```
struct Foo:
  0 [+100]  ZString[10]  list
```

Although somewhat awkward, the existing explicit-length syntax should work:

```
struct Foo:
  0 [+100]  ZString:80[10]  list  # 10 10-byte (80-bit) strings
```
