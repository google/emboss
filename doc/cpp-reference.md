# Emboss C++ Generated Code Reference

## `struct`s

A `struct` will have a corresponding view class, and functions to create views.

### <code>Make*Struct*View</code> free function

```c++
template <typename T>
auto MakeStructView(/* view parameters, */ T *data, size_t size);
```

```c++
template <typename T>
auto MakeStructView(/* view parameters, */ T *container);
```

*`Struct`* will be replaced by the name of the specific `struct` whose view
will be constructed; for example, to make a view for `struct Message`, call the
`MakeMessageView` function.

*View parameters* will be replaced by one argument for each parameter attached
to the `struct`.  E.g., for:

```
struct Foo(x: UInt:8):
   --
```

`MakeFooView` will be:

```c++
template <typename T>
auto MakeFooView(std::uint8_t x, T *data, size_t size);
```

```c++
template <typename T>
auto MakeFooView(std::uint8_t x, T *container);
```

And for:

```
struct Bar(x: UInt:8, y: Int:32):
  --
```

`MakeBarView` will be:

```c++
template <typename T>
auto MakeBarView(std::uint8_t x, std::int32_t y, T *data, size_t size);
```

```c++
template <typename T>
auto MakeBarView(std::uint8_t x, std::int32_t y, T *container);
```

The <code>Make*Struct*View</code> functions construct a view for *`Struct`*
over the given bytes.  For the data/size form, the type `T` must be a character
type: `char`, `const char`, `unsigned char`, `const unsigned char`, `signed
char`, or `const signed char`.  For the container form, the container can be a
`std::vector`, `std::array`, or `std::basic_string` of a character type, or any
other type with a `data()` method that returns a possibly-`const` `char *`,
`signed char *`, or `unsigned char *`, and a `size()` method that returns a size
in bytes.  Google's `absl::string_view` is one example of such a type.

If given a pointer to a `const` character type or a `const` reference to a
container, <code>Make*Struct*View</code> will return a read-only view; otherwise
it will return a read-write view.

The result of <code>Make*Struct*View</code> should be stored in an `auto`
variable:

```c++
auto view = MakeFooView(byte_buffer, available_byte_count);
```

The specific type returned by <code>Make*Struct*View</code> is subject to
change.


### `CopyFrom` method

```c++
template <typename OtherStorage>
void CopyFrom(GenericStructView<OtherStorage> other) const;
```

The `CopyFrom` method copies data from the view `other` into the current view.
When complete, the current view's backing storage will contain the same bytes
as `other`.  This works even if the view's backing storage overlaps, in which
case `other`'s backing storage is modified by the operation.

### `UncheckedCopyFrom` method

```c++
template <typename OtherStorage>
void UncheckedCopyFrom(GenericStructView<OtherStorage> other) const;
```

The `UncheckedCopyFrom` method performs the same operation as `CopyFrom` but
without any checks on the integrity of or the compatibility of the two views.

### `TryToCopyFrom` method

```c++
template <typename OtherStorage>
bool TryToCopyFrom(GenericStructView<OtherStorage> other) const;
```

`TryToCopyFrom` copies data from `other` into the current view, if `other` is
`Ok()` and the current backing storage is large enough to hold `other`'s data.

### `Equals` method

```c++
template <typename OtherStorage>
bool Equals(GenericStructView<OtherStorage> other);
```

The `Equals` method returns `true` if and only if itself and `other` contain the
same fields yielding equivalent values (as measured by the `==` operator).
`Equals()` should only be called if `Ok()` is true on both views.

### `UncheckedEquals` method

```c++
template <typename OtherStorage>
bool UncheckedEquals(GenericStructView<OtherStorage> other);
```

The `UncheckedEquals` method performs the same operation as `Equals`, but
without any checks on the integrity of or the compatibility of the two views
when reading values.  `UncheckedEquals()` should only be called if `Ok()` is
true on both views.

### `Ok` method

```c++
bool Ok() const;
```

The `Ok` method returns `true` if and only if there are enough bytes in the
backing store, and the `Ok` methods of all active fields return `true`.


### `IsComplete` method

```c++
bool IsComplete() const;
```

The `IsComplete` method returns `true` if there are enough bytes in the backing
store to fully contain the `struct`.  If `IsComplete()` returns `true` but
`Ok()` returns `false`, then the structure is broken in some way that cannot be
fixed by adding more bytes.


### `IntrinsicSizeInBytes` method

```c++
auto IntrinsicSizeInBytes() const;
```

or

```c++
static constexpr auto IntrinsicSizeInBytes() const;
```

The `IntrinsicSizeInBytes` method is the [field method](#struct-field-methods)
for [`$size_in_bytes`](language-reference.md#size_in_bytes).  The `Read` method
of the result returns the size of the `struct`, and the `Ok` method returns
`true` if the `struct`'s intrinsic size is known; i.e.:

```c++
if (view.IntrinsicSizeInBytes().Ok()) {
  // The exact return type of view.IntrinsicSizeInBytes().Read() may vary, but
  // it will always be implicitly convertible to std::uint64_t.
  std::uint64_t view_size = view.IntrinsicSizeInBytes().Read();
}
```

Alternately, if you are sure the size is known:

```c++
std::uint64_t view_size = view.IntrinsicSizeInBytes().UncheckedRead();
```

Or, if the size is a compile-time constant:

```c++
constexpr std::uint64_t view_size = StructView::IntrinsicSizeInBytes().Read();
constexpr std::uint64_t view_size2 = Struct::IntrinsicSizeInBytes();
```


### `MaxSizeInBytes` method

```c++
auto MaxSizeInBytes() const;
```

or

```c++
static constexpr auto MaxSizeInBytes() const;
```

The `MaxSizeInBytes` method is the [field method](#struct-field-methods)
for [`$max_size_in_bytes`](language-reference.md#max_size_in_bytes).  The `Read`
method of the result returns the maximum size of the `struct`, and the `Ok`
always method returns `true`.

```c++
assert(view.MaxSizeInBytes().Ok());
// The exact return type of view.MaxSizeInBytes().Read() may vary, but it will
// always be implicitly convertible to std::uint64_t.
std::uint64_t view_size = view.MaxSizeInBytes().Read();
```

Alternately:

```c++
std::uint64_t view_size = view.MaxSizeInBytes().UncheckedRead();
```

Or:

```c++
constexpr std::uint64_t view_size = StructView::MaxSizeInBytes().Read();
constexpr std::uint64_t view_size2 = Struct::MaxSizeInBytes();
```


### `MinSizeInBytes` method

```c++
auto MinSizeInBytes() const;
```

or

```c++
static constexpr auto MinSizeInBytes() const;
```

The `MinSizeInBytes` method is the [field method](#struct-field-methods)
for [`$min_size_in_bytes`](language-reference.md#min_size_in_bytes).  The `Read`
method of the result returns the minimum size of the `struct`, and the `Ok`
always method returns `true`.

```c++
assert(view.MinSizeInBytes().Ok());
// The exact return type of view.MinSizeInBytes().Read() may vary, but it will
// always be implicitly convertible to std::uint64_t.
std::uint64_t view_size = view.MinSizeInBytes().Read();
```

Alternately:

```c++
std::uint64_t view_size = view.MinSizeInBytes().UncheckedRead();
```

Or:

```c++
constexpr std::uint64_t view_size = StructView::MinSizeInBytes().Read();
constexpr std::uint64_t view_size2 = Struct::MinSizeInBytes();
```


### `SizeIsKnown` method

```c++
bool SizeIsKnown() const;
```

or

```c++
static constexpr bool SizeIsKnown() const;
```

The `SizeIsKnown` method is an alias of `IntrinsicSizeInBytes().Ok()`.

The `SizeIsKnown` method returns `true` if the size of the `struct` can be
determined from the bytes that are available.  For example, consider a `struct`
like:

```
struct Message:
  0 [+4]   UInt        payload_length (pl)
  4 [+pl]  UInt:8[pl]  payload
```

The `Message`'s view's `SizeIsKnown` method will return `true` if at least four
bytes are available in the backing store, because it can determine the actual
size of the message if at least four bytes can be read.  If the backing store
contains three or fewer bytes, then `SizeIsKnown` will be false.

Note that if the `struct` contains no dynamically-sized or dynamically-located
fields, then `SizeIsKnown` will be a `static constexpr` method that always
return `true`.


### `SizeInBytes` method

```c++
std::size_t SizeInBytes() const;
```

or

```c++
static constexpr std::size_t SizeInBytes() const;
```

The `SizeInBytes` method returns
`static_cast<std::size_t>(IntrinsicSizeInBytes().Read())`.

The `SizeInBytes` method returns the size of the `struct` in bytes.
`SizeInBytes` asserts that `SizeIsKnown()`, so applications should ensure that
`SizeIsKnown()` before calling `SizeInBytes`.

If the `struct` contains no dynamically-sized or dynamically-located fields,
then `SizeInBytes` will be a `static constexpr` method, and can always be called
safely.


### `UpdateFromTextStream` method

```c++
template <class Stream>
bool UpdateFromTextStream(Stream *stream) const;
```

`UpdateFromTextStream` will read a text-format representation of the structure
from the given `stream` and update fields.  Generally, applications would not
call this directly; instead, use the global `UpdateFromText` method, which
handles setting up a stream from a `std::string`.

### `WriteToTextStream` method

```c++
template <class Stream>
bool WriteToTextStream(Stream *stream, const TextOutputOptions &options) const;
```

`WriteToTextStream` will write a text representation of the current value in a
form that can be decoded by `UpdateFromTextStream`. Generally, applications
would not call this directly; instead, use the global `WriteToString` method,
which handles setting up the stream and returning the resulting string.

### `BackingStorage` method

```c++
Storage BackingStorage() const;
```

Returns the backing storage for the view.  The return type of `BackingStorage()`
is a template parameter on the view.


### `struct` field methods

Each physical field and virtual field in the `struct` will have a corresponding
method in the generated view for that `struct`, which returns a subview of that
field.  For example, take the `struct` definition:

```
struct Foo:
  0 [+4]  UInt  bar
  4 [+4]  Int   baz
  let qux = 2 * bar
  let bar_alias = bar
```

In this case, the generated code will have methods

```c++
auto bar() const;
auto baz() const;
auto qux() const;
auto bar_alias() const;
```

The `bar` method will return a `UInt` view, and `baz()` will return an `Int`
view.  The `qux` method will return a pseudo-`UInt` view which can only be read.
The `bar_alias` method actually forwards to `bar`, and can be both read and
written:

```c++
auto foo_view = MakeFooView(&vector_of_foo_bytes);
uint32_t bar_value = foo_view.bar().Read();
int32_t baz_value = foo_view.baz().Read();
int64_t qux_value = foo_view.qux().Read();
uint32_t bar_alias_value = foo_view.bar_alias().Read();
foo_view.bar_alias().Write(100);
assert(foo_view.bar().Read() == 100);
```

As with <code>Make*Struct*View</code>, the exact return type of field methods is
subject to change; if a field's view must be stored, use an `auto` variable.

Fields in anonymous `bits` are treated as if they were fields of the enclosing
`struct` in the generated code.  Take this `struct`:

```
struct Foo:
  0 [+4]  bits:
    5 [+5]  UInt  bar
```

In C++, `bar` would be read like so:

```c++
auto foo_view = MakeFooView(&vector_of_foo_bytes);
uint8_t bar_value = foo_view.bar().Read();
```

For each field, there is a <code>has_*field*()</code> method, which returns an
object.  `has_` methods are typically used for conditional fields.  Suppose you
have a `struct` like:

```
struct Foo:
  0 [+1]  enum  message_type:
    BAR = 1
  if message_type == MessageType.BAR:
    1 [+25]  Bar  bar
```

When you have a view of a `Foo`, you can call `foo_view.has_bar().Known()` to
find out whether `foo_view` has enough information to determine if the field
`bar` should exist.  If it does `.Known()` returns `true`, you may call
`foo_view.has_bar().Value()` to find out if `bar` should exist.  You can also
call `foo_view.has_bar().ValueOr(false)`, which will return `true` if `bar`'s
status is known, and `bar` exists.

Every field will have a corresponding `has_` method.  In the example above,
`foo_view.has_message_type().Known()` and `foo_view.has_message_type().Value()`
are both supported calls; both will always return `true`.

Note that just because a field "exists," that does not mean that it can be read
from or written to the current message: the field's bytes might be missing, or
present but contain a non-`Ok()` value.  You can use `view.field().Ok()` to
determine if the field can be *read*, and `view.field().IsComplete()` to
determine if the field can be *written*.


### Constant Virtual Fields

Virtual fields whose values are compile-time constants can be read without
instantiating a view:

```
struct Foo:
  let register_number = 0xf8
  0 [+4]  UInt  foo
```

```
// Foo::register_number() is a constexpr function.
static_assert(Foo::register_number() == 0xf8);
```


### <code>*field*().Ok()</code> vs <code>*field*().IsComplete()</code> vs <code>has_*field*()</code>

Emboss provides a number of methods to query different kinds of validity.

<code>has_*field*()</code> is used for checking the existence condition
specified in the `.emb` file:

```
struct Foo:
  0 [+1]    UInt  x
  if x < 10:
    1 [+1]  UInt  y
```

In the .cc file:

```c++
::std::array<char, 2> bytes = { 5, 7 };
auto foo = MakeFooView(&bytes);
assert(foo.x().Read() == 5);

// foo.x() is readable, so the existence condition on y is known.
assert(foo.has_y().Known());

// foo.x().Read() < 10, so y exists in foo.
assert(foo.has_y().Value());

foo.x().Write(15);

// foo.x().Read() >= 10, so y no longer exists in foo.
assert(foo.has_y().Known());
assert(!foo.has_y().Value());

// foo.has_x() is always true, since x's existence condition is just "true".
assert(foo.has_x().Known());
assert(foo.has_x().Value());

// incomplete_foo has 0 bytes of backing storage, so x is unreadable.
auto incomplete_foo = MakeFooView(&bytes[0], 0);

// incomplete_foo.has_x() is known, since it does not depend on anything.
assert(incomplete_foo.has_x().Known());
assert(incomplete_foo.has_x().Value());

// incomplete_foo.x().Ok() is false, since x cannot be read.
assert(!incomplete_foo.x().Ok());

// Since x cannot be read, incomplete_foo.has_y().Known() is false.
assert(!incomplete_foo.has_y().Known());

// Since has_y() is not Known(), calling has_y().Value() will crash if Emboss
// assertions are enabled.
// incomplete_foo.has_y().Value()  // Would crash

// It is safe to call has_y().ValueOr(false).
assert(!incomplete_foo.has_y().ValueOr(false));
```

<code>has_*field*()</code> is notional: it queries whether *`field`* *should* be
present in the view.  Even if <code>has_*field*().Value()</code> is `true`,
<code>*field*().IsComplete()</code> and *field*().Ok() might return `false`.

<code>*field*().IsComplete()</code> tests if there are enough bytes in the
backing storage to hold *`field`*.  If <code>*field*().IsComplete()</code>, it
is safe to call `Write()` on the field with a valid value for that field.
<code>*field*().Ok()</code> tests if there are enough bytes in the backing
storage to hold *`field`*, *and* that those bytes contain a valid value for
*`field`*:

```
struct Bar:
  0 [+1]  Bcd  x
  1 [+1]  Bcd  y
```

```c++
::std::array<char, 1> bytes = { 0xbb };  // Not a valid BCD number.
auto bar = MakeBarView(&bytes);

// There are enough bytes to read and write x.
assert(bar.x().IsComplete());

// The value in x is not correct.
assert(!bar.x().Ok());

// Read() would crash if assertions are enabled.
// bar.x().Read();

// Writing a valid value is safe.
bar.x().Write(99);
assert(bar.x().Ok());

// Notionally, bar should have y, even though y's byte is not available:
assert(bar.has_y().Value());

// Since there is no byte to read y from, y is not complete:
assert(!bar.y().IsComplete());
```

Note that all views have `Ok()` and `IsComplete()` methods.  A view of a
structure is `Ok()` if all of its fields are either `Ok()` or not present, and
<code>has_*field*().Known()</code> is `true` for all fields.

A structure view `IsComplete()` if its `SizeIsKnown()` and its backing storage
contains at least `SizeInBits()` or `SizeInBytes()` bits or bytes.  In other
words: `IsComplete()` is true if Emboss can determine that (just) adding more
bytes to the view's backing storage won't help.  Note that just because
`IsComplete()` is false, that does not mean that adding more bytes *will* help.
It is possible to define incoherent structures that will confuse Emboss, such
as:

```
struct SizeNeverKnown:
  if false:
    0   [+1]  UInt  x_loc
  x_loc [+1]  UInt  x
```

<!-- TODO(bolms): Rename "existence condition" to "presence condition." -->


## `bits` Views

The code generated for a `bits` construct is very similar to the code generated
for a `struct`.  The primary differences are that there is no
<code>Make*Bits*View</code> function and that `SizeInBytes` is replaced by
`SizeInBits`.


### `Ok` method

```c++
bool Ok() const;
```

The `Ok` method returns `true` if and only if there are enough bytes in the
backing store, and the `Ok` methods of all active fields return `true`.


### `IsComplete` method

```c++
bool IsComplete() const;
```

The `IsComplete` method returns `true` if there are enough bytes in the backing
store to fully contain the `bits`.  If `IsComplete()` returns `true` but
`Ok()` returns `false`, then the structure is broken in some way that cannot be
fixed by adding more bytes.


### `IntrinsicSizeInBits` method

```c++
auto IntrinsicSizeInBits() const;
```

or

```c++
static constexpr auto IntrinsicSizeInBits() const;
```

The `IntrinsicSizeInBits` method is the [field method](#bits-field-methods) for
[`$size_in_bits`](language-reference.md#size_in_bits).  The `Read` method of
the result returns the size of the `struct`, and the `Ok` method returns `true`
if the `struct`'s intrinsic size is known; i.e.:

```c++
if (view.IntrinsicSizeInBits().Ok()) {
  std::uint64_t view_size = view.IntrinsicSizeInBits().Read();
}
```

Since the intrinsic size of a `bits` is always a compile-time constant:

```c++
constexpr std::uint64_t view_size = BitsView::IntrinsicSizeInBits().Read();
constexpr std::uint64_t view_size2 = Bits::IntrinsicSizeInBits();
```


### `MaxSizeInBits` method

```c++
auto MaxSizeInBits() const;
```

or

```c++
static constexpr auto MaxSizeInBits() const;
```

The `MaxSizeInBits` method is the [field method](#struct-field-methods)
for [`$max_size_in_bits`](language-reference.md#max_size_in_bits).  The `Read`
method of the result returns the maximum size of the `bits`, and the `Ok`
always method returns `true`.

```c++
assert(view.MaxSizeInBits().Ok());
// The exact return type of view.MaxSizeInBits().Read() may vary, but it will
// always be implicitly convertible to std::uint64_t.
std::uint64_t view_size = view.MaxSizeInBits().Read();
```

Alternately:

```c++
std::uint64_t view_size = view.MaxSizeInBits().UncheckedRead();
```

Or:

```c++
constexpr std::uint64_t view_size = StructView::MaxSizeInBits().Read();
constexpr std::uint64_t view_size2 = Struct::MaxSizeInBits();
```


### `MinSizeInBits` method

```c++
auto MinSizeInBits() const;
```

or

```c++
static constexpr auto MinSizeInBits() const;
```

The `MinSizeInBits` method is the [field method](#struct-field-methods)
for [`$min_size_in_bits`](language-reference.md#min_size_in_bits).  The `Read`
method of the result returns the minimum size of the `bits`, and the `Ok`
always method returns `true`.

```c++
assert(view.MinSizeInBits().Ok());
// The exact return type of view.MinSizeInBits().Read() may vary, but it will
// always be implicitly convertible to std::uint64_t.
std::uint64_t view_size = view.MinSizeInBits().Read();
```

Alternately:

```c++
std::uint64_t view_size = view.MinSizeInBits().UncheckedRead();
```

Or:

```c++
constexpr std::uint64_t view_size = StructView::MinSizeInBits().Read();
constexpr std::uint64_t view_size2 = Struct::MinSizeInBits();
```


### `SizeIsKnown` method

```c++
static constexpr bool SizeIsKnown() const;
```

For a `bits` construct, `SizeIsKnown()` always returns `true`, because the size
of a `bits` construct is always statically known at compilation time.


### `SizeInBits` method

```c++
static constexpr std::size_t SizeInBits() const;
```

The `SizeInBits` method returns the size of the `bits` in bits.  It is
equivalent to `static_cast<std::size_t>(IntrinsicSizeInBits().Read())`.


### `UpdateFromTextStream` method

```c++
template <class Stream>
bool UpdateFromTextStream(Stream *stream) const;
```

`UpdateFromTextStream` will read a text-format representation of the structure
from the given `stream` and update fields.  Generally, applications would not
call this directly; instead, use the global `UpdateFromText` method, which
handles setting up a stream from a `std::string`.

### `WriteToTextStream` method

```c++
template <class Stream>
bool WriteToTextStream(Stream *stream, const TextOutputOptions &options) const;
```

`WriteToTextStream` will write a text representation of the current value in a
form that can be decoded by `UpdateFromTextStream`. Generally, applications
would not call this directly; instead, use the global `WriteToString` method,
which handles setting up the stream and returning the resulting string.

### `bits` field methods

As with `struct`, each field in a `bits` will have a corresponding method of the
same name generated, and each such method will return a view of the given field.
Take the module:

```
bits Bar:
  0 [+12]  UInt  baz
  31 [+1]  Flag  qux
  let two_baz = baz * 2

struct Foo:
  0 [+4]  Bar  bar
```

In this case, the generated code in the `Bar` view will have methods

```c++
auto baz() const;
auto qux() const;
auto two_baz() const;
```

The `baz` method will return a `UInt` view, and `qux()` will return a `Flag`
view:

```c++
auto foo_view = MakeFooView(&vector_of_foo_bytes);
uint16_t baz_value = foo_view.bar().baz().Read();
bool qux_value = foo_view.bar().qux().Read();
uint32_t two_baz_value = foo_view.bar().two_baz().Read();
```

The exact return type of field methods is subject to change; if a field's view
must be stored, use an `auto` variable.


## `enum`s

For each `enum` in an `.emb`, the Emboss compiler will generate a corresponding
C++11-style `enum class`.  Take the following Emboss `enum`:

```
enum Foo:
  BAR = 1
  BAZ = 1000
```

Emboss will generate something equivalent to the following C++:

```c++
enum class Foo : uint64_t {
  BAR = 1,
  BAZ = 1000,
};
```

Additionally, like other Emboss entities, `enum`s have corresponding view
classes.


### `TryToGetEnumFromName` free function

```c++
static inline bool TryToGetEnumFromName(const char *name, EnumType *result);
```

The `TryToGetEnumFromName` function will try to match `name` against the names
in the Emboss `enum` definition.  If it finds an exact match, it will return
`true` and update `result` with the corresponding enum value.  If it does not
find a match, it will return `false` and leave `result` unchanged.

Note that `TryToGetNameFromEnum` will not match the text of the numeric value of
an enum; given the `Foo` enum above, `TryToGetEnumFromName("1000", &my_foo)`
would return `false`.


### `TryToGetNameFromEnum` free function

```c++
static inline const char *TryToGetNameFromEnum(EnumType value);
```

`TryToGetNameFromEnum` will attempt to find the textual name for the
corresponding enum value.  If a name is found, it will be returned; otherwise
`TryToGetEnumFromName` will return `nullptr`.  (Note that C++ enums are allowed
to contain numeric values that are not explicitly listed in the enum definition,
as long as they are in range for the underlying integral type.)  If the given
value has more than one name, the first name that appears in the Emboss
definition will be returned.


### `Read` method

```c++
EnumType Read() const;
```

The `Read` method reads the enum from the underlying bytes and returns its
value as a C++ enum.  `Read` will assert that there are enough bytes to read.
If the application cannot tolerate a failed assertion, it should first call
`Ok()` to ensure that it can safely read the enum.  If performance is critical
and the application can assure that there will always be enough bytes to read
the enum, it can call `UncheckedRead` instead.


### `UncheckedRead` method

```c++
EnumType UncheckedRead() const;
```

Like `Read`, `UncheckedRead` reads the enum from the underlying bytes and
returns it value as a C++ enum.  Unlike `Read`, `UncheckedRead` does not attempt
to validate that there are enough bytes in the backing store to actually perform
the read.  In performance-critical situations, if the application is otherwise
able to ensure that there are sufficient bytes in the backing store to read the
enum, `UncheckedRead` may be used.


### `Write` method

```c++
void Write(EnumType value) const;
```

`Write` writes the `value` into the backing store.  Like `Read`, `Write` asserts
that there are enough bytes in the backing store to safely write the enum.  If
the application cannot tolerate an assertion failure, it can use `TryToWrite` or
the combination of `IsComplete` and `CouldWriteValue`.


### `TryToWrite` method

```c++
bool TryToWrite(EnumType value) const;
```

`TryToWrite` attempts to write the `value` into the backing store.  If the
backing store does not have enough bytes to hold the enum field, or `value` is
too large for the specific enum field, then `TryToWrite` will return `false` and
not update anything.


### `CouldWriteValue` method

```c++
static constexpr bool CouldWriteValue(EnumType value);
```

`CouldWriteValue` returns `true` if the given `value` could be written into the
enum field, assuming that there were enough bytes in the backing store to cover
the field.

Although `CouldWriteValue` is `static constexpr`, it is tricky to call
statically; client code that wishes to call it statically must use `decltype`
and `declval` to get the specific type for the specific enum *field* in
question.


### `UncheckedWrite` method

```c++
void UncheckedWrite(EnumType value) const;
```

Like `Write`, `UncheckedWrite` writes the given value to the backing store.
Unlike `Write`, `UncheckedWrite` does not check that there are actually enough
bytes in the backing store to safely write; it should only be used if the
application has ensured that there are sufficient bytes in the backing store in
some other way, and performance is a concern.


### `Ok` method

```c++
bool Ok() const;
```

`Ok` returns `true` if there are enough bytes in the backing store for the enum
field to be read or written.

In the future, Emboss may add a "known values only" annotation to enum fields,
in which case `Ok` would also check that the given field contains a known value.


### `IsComplete` method

```c++
bool IsComplete() const;
```

`IsComplete` returns `true` if there are enough bytes in the backing store for
the enum field to be read or written.


### `UpdateFromTextStream` method

```c++
template <class Stream>
bool UpdateFromTextStream(Stream *stream) const;
```

`UpdateFromTextStream` will read a text-format representation of the enum from
the given `stream` and write it into the backing store.  Generally, applications
would not call this directly; instead, use the global `UpdateFromText` method,
which handles setting up a stream from a `std::string`.

### `WriteToTextStream` method

```c++
template <class Stream>
bool WriteToTextStream(Stream *stream, const TextOutputOptions &options) const;
```

`WriteToTextStream` will write a text representation of the current value in a
form that can be decoded by `UpdateFromTextStream`. Generally, applications
would not call this directly; instead, use the global `WriteToString` method,
which handles setting up the stream and returning the resulting string.

## Arrays

### `operator[]` method

```c++
ElementView operator[](size_t index) const;
```

The `operator[]` method of an array view returns a view of the array element at
`index`.

### `begin()`/`rbegin()` and `end()`/`rend()` methods

```c++
ElementViewIterator<> begin();
ElementViewIterator<> end();
ElementViewIterator<> rbegin();
ElementViewIterator<> rend();
```

The `begin()` and `end()` methods of an array view returns view iterators to the
beginning and past-the-end of the array, respectively. They may be used with
arrays in range-based for loops, for example:

```c++
  auto view = MakeArrayView(...);
  for(auto element : view){
    int a = view.member().Read();
    ...
  }
```

The `rbegin()` and `rend()` methods of an array view returns reverse view
iterators to the end and element preceding the first, respectively.

### `SizeInBytes` or `SizeInBits` method

```c++
size_t SizeInBytes() const;
```

or

```c++
size_t SizeInBits() const;
```

Arrays in `struct`s have the `SizeInBytes` method; arrays in `bits` have the
`SizeInBits` method.  `SizeInBytes` returns the size of the array in bytes;
`SizeInBits` returns the size of the array in bits.


### `ElementCount` method

```c++
size_t ElementCount() const;
```

`ElementCount` returns the number of elements in the array.


### `Ok` method

```c++
bool Ok() const;
```

`Ok` returns `true` if there are enough bytes in the backing store to hold the
entire array, and every element's `Ok` method returns `true`.


### `IsComplete` method

```c++
bool IsComplete() const;
```

`IsComplete` returns `true` if there are sufficient bytes in the backing store
to hold the entire array.


### `ToString` method

```c++
template <class String>
String ToString() const;
```

Intended usage:

```c++
// Makes a copy of view's backing storage.
auto str = view.ToString<std::string>();

// Points to view's backing storage.
auto str_view = view.ToString<std::string_view>();
```

`ToString()` returns a string type constructed from the backing storage of the
array.  Note that `ToString()` is only enabled for arrays of 1-byte values,
such as `UInt:8[]`, and only when the array view's underlying storage is
contiguous.

Although it is intended for use with `std::string` and `std::string_view`,
`ToString()` can work with any C++ type that:

1.  Has a `data()` method that returns a pointer to the string's underlying
    data as a `char` type.
2.  Has a constructor that accepts a `const declval(data())` pointer and a
    `size_t` length.


### `UpdateFromTextStream` method

```c++
template <class Stream>
bool UpdateFromTextStream(Stream *stream) const;
```

`UpdateFromTextStream` will read a text-format representation of the structure
from the given `stream` and update array elements.  Generally, applications
would not call this directly; instead, use the global `UpdateFromText` method,
which handles setting up a stream from a `std::string`.

### `WriteToTextStream` method

```c++
template <class Stream>
bool WriteToTextStream(Stream *stream, const TextOutputOptions &options) const;
```

`WriteToTextStream` will write a text representation of the current value in a
form that can be decoded by `UpdateFromTextStream`. Generally, applications
would not call this directly; instead, use the global `WriteToString` method,
which handles setting up the stream and returning the resulting string.

### `BackingStorage` method

```c++
Storage BackingStorage() const;
```

Returns the backing storage for the view.  The return type of `BackingStorage()`
is a template parameter on the view.

## `UInt`

### Type `ValueType`

```c++
using ValueType = ...;
```

The `ValueType` type alias maps to the least-width C++ unsigned integer type
that contains enough bits to hold any value of the given `UInt`.  For example:

*   a `UInt:32`'s `ValueType` would be `uint32_t`
*   a `UInt:64`'s `ValueType` would be `uint64_t`
*   a `UInt:12`'s `ValueType` would be `uint16_t`
*   a `UInt:2`'s `ValueType` would be `uint8_t`

The `Read` and `Write` families of methods use `ValueType` to return or accept
values, respectively.


### `Read` method

```c++
ValueType Read() const;
```

The `Read` method reads the `UInt` from the underlying bytes and returns its
value as a C++ unsigned integer type.  `Read` will assert that there are enough
bytes to read.  If the application cannot tolerate a failed assertion, it should
first call `Ok()` to ensure that it can safely read the `UInt`.  If performance
is critical and the application can assure that there will always be enough
bytes to read the `UInt`, it can call `UncheckedRead` instead.


### `UncheckedRead` method

```c++
ValueType UncheckedRead();
```

Like `Read`, `UncheckedRead` reads the `UInt` from the underlying bytes and
returns it value as a C++ unsigned integer type.  Unlike `Read`, `UncheckedRead`
does not attempt to validate that there are enough bytes in the backing store to
actually perform the read.  In performance-critical situations, if the
application is otherwise able to ensure that there are sufficient bytes in the
backing store to read the `UInt`, `UncheckedRead` may be used.


### `Write` method

```c++
void Write(ValueType value);
```

`Write` writes the `value` into the backing store.  Like `Read`, `Write` asserts
that there are enough bytes in the backing store to safely write the `UInt`.  If
the application cannot tolerate an assertion failure, it can use `TryToWrite` or
the combination of `IsComplete` and `CouldWriteValue`.


### `TryToWrite` method

```c++
bool TryToWrite(ValueType value);
```

`TryToWrite` attempts to write the `value` into the backing store.  If the
backing store does not have enough bytes to hold the `UInt` field, or `value` is
too large for the `UInt` field, then `TryToWrite` will return `false` and not
update anything.


### `CouldWriteValue` method

```c++
static constexpr bool CouldWriteValue(ValueType value);
```

`CouldWriteValue` returns `true` if the given `value` could be written into the
`UInt` field, assuming that there were enough bytes in the backing store to
cover the field.

Although `CouldWriteValue` is `static constexpr`, it is tricky to call
statically; client code that wishes to call it statically must use `decltype`
and `declval` to get the specific type for the specific `UInt` field in
question.


### `UncheckedWrite` method

```c++
void UncheckedWrite(ValueType value);
```

Like `Write`, `UncheckedWrite` writes the given value to the backing store.
Unlike `Write`, `UncheckedWrite` does not check that there are actually enough
bytes in the backing store to safely write; it should only be used if the
application has ensured that there are sufficient bytes in the backing store in
some other way, and performance is a concern.


### `Ok` method

```c++
bool Ok() const;
```

The `Ok` method returns `true` if there are enough bytes in the backing store to
hold the given `UInt` field.


### `IsComplete` method

```c++
bool IsComplete();
```

The `IsComplete` method returns `true` if there are enough bytes in the backing
store to hold the given `UInt` field.


### `UpdateFromTextStream` method

```c++
template <class Stream>
bool UpdateFromTextStream(Stream *stream) const;
```

`UpdateFromTextStream` will read a text-format representation of the `UInt` from
the given `stream` and update fields.  Generally, applications would not call
this directly; instead, use the global `UpdateFromText` method, which handles
setting up a stream from a `std::string`.

### `WriteToTextStream` method

```c++
template <class Stream>
bool WriteToTextStream(Stream *stream, const TextOutputOptions &options) const;
```

`WriteToTextStream` will write a text representation of the current value in a
form that can be decoded by `UpdateFromTextStream`. Generally, applications
would not call this directly; instead, use the global `WriteToString` method,
which handles setting up the stream and returning the resulting string.

### `SizeInBits` method

```c++
static constexpr int SizeInBits();
```

The `SizeInBits` method returns the size of this specific `UInt` field, in bits.


## `Int`

### Type `ValueType`

```c++
using ValueType = ...;
```

The `ValueType` type alias maps to the least-width C++ signed integer type
that contains enough bits to hold any value of the given `Int`.  For example:

*   a `Int:32`'s `ValueType` would be `int32_t`
*   a `Int:64`'s `ValueType` would be `int64_t`
*   a `Int:12`'s `ValueType` would be `int16_t`
*   a `Int:2`'s `ValueType` would be `int8_t`

The `Read` and `Write` families of methods use `ValueType` to return or accept
values, respectively.


### `Read` method

```c++
ValueType Read() const;
```

The `Read` method reads the `Int` from the underlying bytes and returns its
value as a C++ signed integer type.  `Read` will assert that there are enough
bytes to read.  If the application cannot tolerate a failed assertion, it should
first call `Ok()` to ensure that it can safely read the `Int`.  If performance
is critical and the application can assure that there will always be enough
bytes to read the `Int`, it can call `UncheckedRead` instead.


### `UncheckedRead` method

```c++
ValueType UncheckedRead();
```

Like `Read`, `UncheckedRead` reads the `Int` from the underlying bytes and
returns it value as a C++ signed integer type.  Unlike `Read`, `UncheckedRead`
does not attempt to validate that there are enough bytes in the backing store to
actually perform the read.  In performance-critical situations, if the
application is otherwise able to ensure that there are sufficient bytes in the
backing store to read the `Int`, `UncheckedRead` may be used.


### `Write` method

```c++
void Write(ValueType value);
```

`Write` writes the `value` into the backing store.  Like `Read`, `Write` asserts
that there are enough bytes in the backing store to safely write the `Int`.  If
the application cannot tolerate an assertion failure, it can use `TryToWrite` or
the combination of `IsComplete` and `CouldWriteValue`.


### `TryToWrite` method

```c++
bool TryToWrite(ValueType value);
```

`TryToWrite` attempts to write the `value` into the backing store.  If the
backing store does not have enough bytes to hold the `Int` field, or `value` is
too large for the `Int` field, then `TryToWrite` will return `false` and not
update anything.


### `CouldWriteValue` method

```c++
static constexpr bool CouldWriteValue(ValueType value);
```

`CouldWriteValue` returns `true` if the given `value` could be written into the
`Int` field, assuming that there were enough bytes in the backing store to cover
the field.

Although `CouldWriteValue` is `static constexpr`, it is tricky to call
statically; client code that wishes to call it statically must use `decltype`
and `declval` to get the specific type for the specific `Int` field in question.


### `UncheckedWrite` method

```c++
void UncheckedWrite(ValueType value);
```

Like `Write`, `UncheckedWrite` writes the given value to the backing store.
Unlike `Write`, `UncheckedWrite` does not check that there are actually enough
bytes in the backing store to safely write; it should only be used if the
application has ensured that there are sufficient bytes in the backing store in
some other way, and performance is a concern.


### `Ok` method

```c++
bool Ok() const;
```

The `Ok` method returns `true` if there are enough bytes in the backing store to
hold the given `Int` field.


### `IsComplete` method

```c++
bool IsComplete();
```

The `IsComplete` method returns `true` if there are enough bytes in the backing
store to hold the given `Int` field.


### `UpdateFromTextStream` method

```c++
template <class Stream>
bool UpdateFromTextStream(Stream *stream) const;
```

`UpdateFromTextStream` will read a text-format representation of the `Int` from
the given `stream` and update fields.  Generally, applications would not call
this directly; instead, use the global `UpdateFromText` method, which handles
setting up a stream from a `std::string`.

### `WriteToTextStream` method

```c++
template <class Stream>
bool WriteToTextStream(Stream *stream, const TextOutputOptions &options) const;
```

`WriteToTextStream` will write a text representation of the current value in a
form that can be decoded by `UpdateFromTextStream`. Generally, applications
would not call this directly; instead, use the global `WriteToString` method,
which handles setting up the stream and returning the resulting string.

### `SizeInBits` method

```c++
static constexpr int SizeInBits();
```

The `SizeInBits` method returns the size of this specific `Int` field, in bits.


## `Bcd`

### Type `ValueType`

```c++
using ValueType = ...;
```

The `ValueType` type alias maps to a C++ unsigned integer type that contains
at least enough bits to hold any value of the given `Bcd`.  For example:

*   a `Bcd:32`'s `ValueType` would be `uint32_t`
*   a `Bcd:64`'s `ValueType` would be `uint64_t`
*   a `Bcd:12`'s `ValueType` would be `uint16_t`
*   a `Bcd:2`'s `ValueType` would be `uint8_t`

The `Read` and `Write` families of methods use `ValueType` to return or accept
values, respectively.


### `Read` method

```c++
ValueType Read() const;
```

The `Read` method reads the `Bcd` from the underlying bytes and returns its
value as a C++ unsigned integer type.  `Read` will assert that there are enough
bytes to read, and that the binary representation is a valid BCD integer.  If
the application cannot tolerate a failed assertion, it should first call `Ok()`
to ensure that it can safely read the `Bcd`.  If performance is critical and the
application can assure that there will always be enough bytes to read the `Bcd`,
and that the bytes will be a valid BCD value, it can call `UncheckedRead`
instead.


### `UncheckedRead` method

```c++
ValueType UncheckedRead();
```

Like `Read`, `UncheckedRead` reads the `Bcd` from the underlying bytes and
returns it value as a C++ unsigned integer type.  Unlike `Read`, `UncheckedRead`
does not attempt to validate that there are enough bytes in the backing store to
actually perform the read, nor that the bytes contain an actual BCD number.  In
performance-critical situations, if the application is otherwise able to ensure
that there are sufficient bytes in the backing store to read the `Bcd`,
`UncheckedRead` may be used.


### `Write` method

```c++
void Write(ValueType value);
```

`Write` writes the `value` into the backing store.  Like `Read`, `Write` asserts
that there are enough bytes in the backing store to safely write the `Bcd`.  If
the application cannot tolerate an assertion failure, it can use `TryToWrite` or
the combination of `IsComplete` and `CouldWriteValue`.


### `TryToWrite` method

```c++
bool TryToWrite(ValueType value);
```

`TryToWrite` attempts to write the `value` into the backing store.  If the
backing store does not have enough bytes to hold the `Bcd` field, or `value` is
too large for the `Bcd` field, then `TryToWrite` will return `false` and not
update anything.


### `CouldWriteValue` method

```c++
static constexpr bool CouldWriteValue(ValueType value);
```

`CouldWriteValue` returns `true` if the given `value` could be written into the
`Bcd` field, assuming that there were enough bytes in the backing store to cover
the field.

Although `CouldWriteValue` is `static constexpr`, it is tricky to call
statically; client code that wishes to call it statically must use `decltype`
and `declval` to get the specific type for the specific `Bcd` field in question.


### `UncheckedWrite` method

```c++
void UncheckedWrite(ValueType value);
```

Like `Write`, `UncheckedWrite` writes the given value to the backing store.
Unlike `Write`, `UncheckedWrite` does not check that there are actually enough
bytes in the backing store to safely write; it should only be used if the
application has ensured that there are sufficient bytes in the backing store in
some other way, and performance is a concern.


### `Ok` method

```c++
bool Ok() const;
```

The `Ok` method returns `true` if there are enough bytes in the backing store to
hold the given `Bcd` field, and the bytes contain a valid BCD number: that is,
that every nibble in the backing store contains a value between 0 and 9,
inclusive.


### `IsComplete` method

```c++
bool IsComplete();
```

The `IsComplete` method returns `true` if there are enough bytes in the backing
store to hold the given `Bcd` field.


### `UpdateFromTextStream` method

```c++
template <class Stream>
bool UpdateFromTextStream(Stream *stream) const;
```

`UpdateFromTextStream` will read a text-format representation of the `Bcd` from
the given `stream` and update fields.  Generally, applications would not call
this directly; instead, use the global `UpdateFromText` method, which handles
setting up a stream from a `std::string`.

### `WriteToTextStream` method

```c++
template <class Stream>
bool WriteToTextStream(Stream *stream, const TextOutputOptions &options) const;
```

`WriteToTextStream` will write a text representation of the current value in a
form that can be decoded by `UpdateFromTextStream`. Generally, applications
would not call this directly; instead, use the global `WriteToString` method,
which handles setting up the stream and returning the resulting string.

### `SizeInBits` method

```c++
static constexpr int SizeInBits();
```

The `SizeInBits` method returns the size of this specific `Bcd` field, in bits.


## `Flag`

### `Read` method

```c++
bool Read() const;
```

The `Read` method reads the `Flag` from the underlying bit and returns its
value as a C++ `bool`.  `Read` will assert that the underlying bit is in the
backing store.  If the application cannot tolerate a failed assertion, it should
first call `Ok()` to ensure that it can safely read the `Flag`.  If performance
is critical and the application can assure that there will always be enough
bytes to read the `Flag`, it can call `UncheckedRead` instead.


### `UncheckedRead` method

```c++
bool UncheckedRead();
```

Like `Read`, `UncheckedRead` reads the `Flag` from the underlying bit and
returns it value as a C++ bool.  Unlike `Read`, `UncheckedRead` does not attempt
to validate that the backing bit is actually in the backing store.  In
performance-critical situations, if the application is otherwise able to ensure
that there are sufficient bytes in the backing store to read the `Flag`,
`UncheckedRead` may be used.


### `Write` method

```c++
void Write(bool value);
```

`Write` writes the `value` into the backing store.  Like `Read`, `Write` asserts
that there are enough bytes in the backing store to safely write the `Flag`.  If
the application cannot tolerate an assertion failure, it can use `TryToWrite` or
the combination of `IsComplete` and `CouldWriteValue`.


### `TryToWrite` method

```c++
bool TryToWrite(bool value);
```

`TryToWrite` attempts to write the `value` into the backing store.  If the
backing store does not contain the `Flag`'s bit, then `TryToWrite` will return
`false` and not update anything.


### `CouldWriteValue` method

```c++
static constexpr bool CouldWriteValue(bool value);
```

`CouldWriteValue` returns `true`, as both C++ `bool` values can be written to
any `Flag`.


### `UncheckedWrite` method

```c++
void UncheckedWrite(ValueType value);
```

Like `Write`, `UncheckedWrite` writes the given value to the backing store.
Unlike `Write`, `UncheckedWrite` does not check that there are actually enough
bytes in the backing store to safely write; it should only be used if the
application has ensured that there are sufficient bytes in the backing store in
some other way, and performance is a concern.


### `Ok` method

```c++
bool Ok() const;
```

The `Ok` method returns `true` if the backing store contains the `Flag`'s bit.


### `IsComplete` method

```c++
bool IsComplete();
```

The `IsComplete` method returns `true` if the backing store contains the
`Flag`'s bit.


### `UpdateFromTextStream` method

```c++
template <class Stream>
bool UpdateFromTextStream(Stream *stream) const;
```

`UpdateFromTextStream` will read a text-format representation of the `Flag` from
the given `stream` and update fields.  Generally, applications would not call
this directly; instead, use the global `UpdateFromText` method, which handles
setting up a stream from a `std::string`.

### `WriteToTextStream` method

```c++
template <class Stream>
bool WriteToTextStream(Stream *stream, const TextOutputOptions &options) const;
```

`WriteToTextStream` will write a text representation of the current value in a
form that can be decoded by `UpdateFromTextStream`. Generally, applications
would not call this directly; instead, use the global `WriteToString` method,
which handles setting up the stream and returning the resulting string.

## `Float`

### Type `ValueType`

```c++
using ValueType = ...;
```

The `ValueType` type alias maps to the C++ floating-point type that matches the
`Float` field's type; generally `float` for 32-bit `Float`s and `double` for
64-bit `Float`s.

The `Read` and `Write` families of methods use `ValueType` to return or accept
values, respectively.


### `Read` method

```c++
ValueType Read() const;
```

The `Read` method reads the `Float` from the underlying bytes and returns its
value as a C++ floating point type.  `Read` will assert that there are enough
bytes to read.  If the application cannot tolerate a failed assertion, it should
first call `Ok()` to ensure that it can safely read the `Float`.  If performance
is critical and the application can assure that there will always be enough
bytes to read the `Float`, it can call `UncheckedRead` instead.


### `UncheckedRead` method

```c++
ValueType UncheckedRead();
```

Like `Read`, `UncheckedRead` reads the `Float` from the underlying bytes and
returns it value as a C++ floating point type.  Unlike `Read`, `UncheckedRead`
does not attempt to validate that there are enough bytes in the backing store to
actually perform the read.  In performance-critical situations, if the
application is otherwise able to ensure that there are sufficient bytes in the
backing store to read the `Float`, `UncheckedRead` may be used.


### `Write` method

```c++
void Write(ValueType value);
```

`Write` writes the `value` into the backing store.  Like `Read`, `Write` asserts
that there are enough bytes in the backing store to safely write the `Float`.
If the application cannot tolerate an assertion failure, it can use `TryToWrite`
or the combination of `IsComplete` and `CouldWriteValue`.


### `TryToWrite` method

```c++
bool TryToWrite(ValueType value);
```

`TryToWrite` attempts to write the `value` into the backing store.  If the
backing store does not have enough bytes to hold the `Float` field, then
`TryToWrite` will return `false` and not update anything.


### `CouldWriteValue` method

```c++
static constexpr bool CouldWriteValue(ValueType value);
```

`CouldWriteValue` returns `true`.


### `UncheckedWrite` method

```c++
void UncheckedWrite(ValueType value);
```

Like `Write`, `UncheckedWrite` writes the given value to the backing store.
Unlike `Write`, `UncheckedWrite` does not check that there are actually enough
bytes in the backing store to safely write; it should only be used if the
application has ensured that there are sufficient bytes in the backing store in
some other way, and performance is a concern.


### `Ok` method

```c++
bool Ok() const;
```

The `Ok` method returns `true` if there are enough bytes in the backing store to
hold the given `Float` field.


### `IsComplete` method

```c++
bool IsComplete();
```

The `IsComplete` method returns `true` if there are enough bytes in the backing
store to hold the given `Float` field.


### `UpdateFromTextStream` method

```c++
template <class Stream>
bool UpdateFromTextStream(Stream *stream) const;
```

`UpdateFromTextStream` will read a text-format representation of the `Float`
from the given `stream` and update fields.  Generally, applications would not
call this directly; instead, use the global `UpdateFromText` method, which
handles setting up a stream from a `std::string`.

*Note: this method is not yet implemented.*

### `WriteToTextStream` method

```c++
template <class Stream>
bool WriteToTextStream(Stream *stream, const TextOutputOptions &options) const;
```

`WriteToTextStream` will write a text representation of the current value in a
form that can be decoded by `UpdateFromTextStream`. Generally, applications
would not call this directly; instead, use the global `WriteToString` method,
which handles setting up the stream and returning the resulting string.

*Note: this method is not yet implemented.*


## `::emboss::UpdateFromText` function

```c++
template <typename EmbossViewType>
bool UpdateFromText(EmbossViewType view, const ::std::string &text) const;
```

The `::emboss::UpdateFromText` function constructs an appropriate text strem
object from the given `text` and calls `view`'s `UpdateFromTextStream` method.
This is the preferred way to read Emboss text format in C++.

## `::emboss::WriteToString` function

```c++
template <typename EmbossViewType>
::std::string WriteToString(EmbossViewType view);
template <typename EmbossViewType>
::std::string WriteToString(EmbossViewType view, TextOutputOptions options);
```

The `::emboss::WriteToString` function constructs a string stream, passes it
into the `view`'s `WriteToTextStream` method, and finally returns the text
format of the `view`.

The single-argument form `WriteToString(view)` will return a single line of
text. For more readable output, `WriteToString(view, ::emboss::MultilineText())`
should help.

## `::emboss::TextOutputOptions` class

The `TextOutputOptions` is used to set options for text output, such as numeric
base, whether or not to use multiple lines, etc.

### `PlusOneIndent` method

```c++
TextOutputOptions PlusOneIndent() const;
```

`PlusOneIndent` returns a new `TextOutputOptions` with one more level of
indentation than the current `TextOutputOptions`. This is primarily intended for
use inside of `WriteToTextStream` methods, as a way to get an indented
`TextOutputOptions` to pass to the `WriteToTextStream` methods of child
objects.  However, application callers may use `PlusOneIndent()`, possibly
multiple times, to indent the entire output.

### `Multiline` method

```c++
TextOutputOptions Multiline(bool new_value) const;
```

Returns a new `TextOutputOptions` with the same options as the current
`TextOutputOptions`, except for a new value for `multiline()`.

### `WithIndent` method

```c++
TextOutputOptions WithIndent(::std::string new_value) const;
```

Returns a new `TextOutputOptions` with the same options as the current
`TextOutputOptions`, except for a new value for `indent()`.

### `WithComments` method

```c++
TextOutputOptions WithComments(bool new_value) const;
```

Returns a new `TextOutputOptions` with the same options as the current
`TextOutputOptions`, except for a new value for `comments()`.

### `WithDigitGrouping` method

```c++
TextOutputOptions WithDigitGrouping(bool new_value) const;
```

Returns a new `TextOutputOptions` with the same options as the current
`TextOutputOptions`, except for a new value for `digit_grouping()`.

### `WithNumericBase` method

```c++
TextOutputOptions WithNumericBase(int new_value) const;
```

Returns a new `TextOutputOptions` with the same options as the current
`TextOutputOptions`, except for a new value for `digit_grouping()`. The new
numeric base should be 2, 10, or 16.

### `WithAllowPartialOutput` method

```c++
TextOutputOptions WithAllowPartialOutput(bool new_value) const;
```

Returns a new `TextOutputOptions` with the same options as the current
`TextOutputOptions`, except for a new value for `allow_partial_output()`.

### `current_indent` method

```c++
::std::string current_indent() const;  // Default "".
```

Returns the current indent string.

### `indent` method

```c++
::std::string indent() const;  // Default "  ".
```

Returns the indent string.  The indent string is the string used for a *single*
level of indentation.

### `multiline` method

```c++
bool multiline() const;  // Default false.
```

Returns `true` if text output should use multiple lines, or `false` if text
output should be single-line only.

### `digit_grouping` method

```c++
bool digit_grouping() const;  // Default false.
```

Returns `true` if text output should include digit separators on numbers; i.e.
`1_000_000` instead of `1000000`.

### `comments` method

```c++
bool comments() const;  // Default false.
```

Returns `true` if text output should include comments, e.g., to show numbers in
multiple bases.

### `numeric_base` method

```c++
uint8_t numeric_base() const;  // Default 10.
```

Returns the numeric base that should be used for formatting numbers. This should
always be 2, 10, or 16.

### `allow_partial_output` method

```c++
bool allow_partial_output() const;  // Default false.
```

Returns `true` if text output should attempt to extract fields from a view that
is not `Ok()`.  If so:

*   `WriteToString()` or `WriteToTextStream()` should never `CHECK`-fail.
*   Atomic fields (e.g., `Int`, `UInt`, `enum`, `Flag`, etc. types) will not be
    written to the text stream if they cannot be read.
*   If `comments()` is also `true`, unreadable atomic fields will be commented
    in the text stream.
*   Aggregate fields (`struct`, `bits`, or arrays) will be written, but may be
    missing fields or entirely empty if they have non-`Ok()` members.
