# Emboss C++ User Guide

[TOC]

## General Principles

In C++, Emboss generates *view* classes which *do not* take ownership of any
data.  Application code is expected to manage the actual binary data.  However,
Emboss views are extremely cheap to construct (often free when optimizations are
turned on), so it is expected that applications can pass around pointers to
binary data and instantiate views as needed.

All of the generated C++ code is in templates, so only code that is actually
called will be linked into your application.

Unless otherwise noted, all code for a given Emboss module will be generated in
the namespace given by the module's `[(cpp) namespace]` attribute.


### Read-Only vs Read-Write vs C++ `const`

Emboss views can be applied to read-only or read-write storage:

```c++
void CopyX(const std::vector<char> &src, std::vector<char> *dest) {
  auto source_view = MakeXView(&src);
  auto dest_view = MakeXView(dest);
  dest_view.x().Write(source_view.x().Read());
}
```

When applied to read-only storage, methods like `Write()` or
`UpdateFromTextStream()` won't compile:

```c++
void WontCompile(const std::vector<char> &data) {
  auto view = MakeXView(&data);
  view.x().Write(10);  // Won't compile.
}
```

This is separate from the C++ `const`ness of the view itself!  For example, the
following will work with no issue:

```c++
void WillCompileAndRun(std::vector<char> *data) {
  const auto view = MakeXView(&data);
  view.x().Write(10);
}
```

This works because views are like pointers.  In C++, you can have any
combination of `const`/non-`const` pointer to `const`/non-`const` data:

```c++
char *             ncnc;  // Pointer is mutable, and points to mutable data.
const char *       ncc;   // Point is mutable, but points to const data.
char const *       ncc2;  // Another way of writing const char *
char *const        cnc;   // Pointer is constant, but points to mutable data.
using char_p = char *;
const char_p       cnc2;  // Another way of writing char *const
const char *const  cc;    // Pointer is constant, and points to constant data.
using c_char_p = const char *;
const c_char_p *   cc2;   // Another way of writing const char *const
```

The Emboss view equivalents are:

```c++
GenericMyStructView<ContiguousBuffer<char, ...>>              ncnc;
GenericMyStructView<ContiguousBuffer<const char, ...>>        ncc;
GenericMyStructView<ContiguousBuffer<char const, ...>>        ncc2;
GenericMyStructView<ContiguousBuffer<char, ...>> const        cnc;
const GenericMyStructView<ContiguousBuffer<char, ...>>        cnc2;
GenericMyStructView<ContiguousBuffer<const char, ...>> const  cc;
const GenericMyStructView<ContiguousBuffer<const char, ...>>  cc2;
```

For this reason, `const` methods of views work on `const` *views*, not
necessarily on `const` data: for example, `UpdateFromTextStream()` is a `const`
method, because it does not modify the view itself, but it will not work if the
view points to `const` data.  This is analogous to writing through a constant
pointer, like: `char *const p = &some_char; *p = 'z';`.

Conversely, non-`const` methods, such as `operator=`, still work on views of
`const` data.  This is analogous to `pointer_to_const_char =
other_pointer_to_const_char`.


## Example: Fixed-Size `struct`

Given a simple, fixed-size `struct`:

```
[(cpp) namespace = "example"]

struct MyStruct:
  0 [+4]  UInt  field_a
  4 [+4]  Int   field_b
  8 [+4]  Bcd   field_c
```

Emboss will generate code with this public C++ interface:

```c++
namespace example {

// The view class for the struct.  Views are like pointers: they do not own
// their storage.
//
// `Storage` is typically some ::emboss::support::ContiguousBuffer (which uses
// contiguous memory as backing storage), but you would typically just use
// `auto`:
//
//     auto view = MakeMyStructView(&container);
//
// If you need to make a view of some non-RAM backing storage (e.g., a register
// file on a remote device, accessed via SPI), you can provide your own Storage.
template <class Storage>
class GenericMyStructView final {
 public:
  // Typically, you do not need to explicitly call any of the constructors.

  // The default constructor gives you a "null" view: you cannot read or write
  // through the view, Ok() and IsComplete() return false, and so on.
  GenericMyStructView();

  // A non-"null" view must be constructed with an appropriate Storage.
  explicit GenericMyStructView(Storage bytes);

  // Views can be copy-constructed and assigned from views of "compatible"
  // Storage.  For ContiguousBuffer, that means ContiguousBuffer over any of the
  // char types -- char, unsigned char, and signed char.  std::uint8_t and
  // std::int8_t are typically aliases of char types, but are not required to
  // be by the C++ standard.
  template <typename OtherStorage>
  GenericMyStructView(const GenericMyStructView<OtherStorage> &other);

  template <typename OtherStorage>
  GenericMyStructView<Storage> &operator=(
      const GenericMyStructView<OtherStorage> &other);


  // Ok() returns true if the Storage is big enough for the struct (for
  // MyStruct, at least 12 bytes), and all fields are Ok().  For this struct,
  // the Int and UInt fields are always Ok(), and the Bcd field is Ok() if none
  // of its nibbles has a value greater than 9.
  bool Ok() const;

  // IsComplete() returns true if the Storage is big enough for the struct.
  // This is most useful when you are reading bytes from some stream: you can
  // read until IsComplete() is true, and then use IntrinsicSizeInBytes() to
  // find out how many bytes are actually used by the struct, and Ok() to find
  // out if the bytes are correct.
  //
  // An alternate way of thinking about it is: Ok() tells you if you can read a
  // structure; IsComplete() tells you if you can write to it.
  bool IsComplete() const;


  // The Equals() and UncheckedEquals() methods check if two structs are
  // *logically* equal.  Equals() performs Ok() and bounds checks,
  // UncheckedEquals() does not: UncheckedEquals() is useful when you need
  // maximum performance, and can guarantee that your structures are Ok()
  // before calling UncheckedEquals().
  template <typename OtherStorage>
  bool Equals(GenericMyStructView<OtherStorage> other) const;
  template <typename OtherStorage>
  bool UncheckedEquals(GenericMyStructView<OtherStorage> other) const;

  // CopyFrom() and UncheckedCopyFrom() copy the bytes of the source structure
  // directly from its Storage.  CopyFrom() performs bounds checks to ensure
  // that there are enough bytes available in the source; UncheckedCopyFrom()
  // does not.  With ContiguousBuffer storage, these should have essentially
  // identical performance to memcpy().
  template <typename OtherStorage>
  void CopyFrom(GenericMyStructView<OtherStorage> other) const;
  template <typename OtherStorage>
  void UncheckedCopyFrom(GenericMyStructView<OtherStorage> other) const;


  // UpdateFromTextStream() attempts to update the structure from text format.
  // The Stream class provides a simple interface for getting and ungetting
  // characters; typically, you would use ::emboss::UpdateFromText(view,
  // some_string) instead of calling this yourself.
  template <class Stream>
  bool UpdateFromTextStream(Stream *stream) const;

  // WriteToTextStream() writes a textual representation of the structure to the
  // provided stream.  Typically, you would use ::emboss::WriteToString(view)
  // instead.
  template <class Stream>
  void WriteToTextStream(Stream *stream,
                         ::emboss::TextOutputOptions options) const;


  // Each field in the struct will have a method to get its corresponding view.
  //
  // The exact types of the returned views are not contractual.
  ::emboss::prelude::UIntView<...> field_a() const;
  ::emboss::prelude::IntView<...> field_b() const;
  ::emboss::prelude::BcdView<...> field_c() const;


  // The built-in virtual fields also have methods to get their views:
  // $size_in_bytes has IntrinsicSizeInBytes(), $max_size_in_bytes has
  // MaxSizeInBytes(), and $min_size_in_bytes has MinSizeInBytes().
  //
  // Because $min_size_in_bytes and $max_size_in_bytes are always constant,
  // their corresponding field methods are always static constexpr.  Because
  // $size_in_bytes is also constant for MyStruct, IntrinsicSizeInBytes() will
  // also be static constexpr for GenericMyStructView:
  //
  // For any virtual field, you can use its Ok() method to find out if you can
  // Read() its value:
  //
  //     if (view.IntrinsicSizeInBytes().Ok()) {
  //       // The size of the struct is known.
  //       DoSomethingWithNBytes(view.IntrinsicSizeInBytes().Read());
  //     }
  //
  // For constant values, Ok() will always return true.
  //
  // For MyStruct, my_struct_view.IntrinsicSizeInBytes().Read(),
  // my_struct_view.MinSizeInBytes().Read(), and
  // my_struct_view.MaxSizeInBytes().Read() will all return 12.
  //
  // For constexpr fields, you can also get their values from functions in the
  // structure's namespace, which also lets you skip the Read():
  //
  //     MyStruct::IntrinsicSizeInBytes()
  //     MyStruct::MaxSizeInBytes()
  //     MyStruct::MinSizeInBytes()
  static constexpr IntrinsicSizeInBytesView IntrinsicSizeInBytes();
  static constexpr MinSizeInBytesView MinSizeInBytes();
  static constexpr MaxSizeInBytesView MaxSizeInBytes();

  // The IntrinsicSizeInBytes() method returns the view of the $size_in_bytes
  // virtual field.  Because $size_in_bytes is constant, this is a static
  // constexpr method.
  //
  // Typically, you would use IntrinsicSizeInBytes().Ok() and
  // IntrinsicSizeInBytes().Read():
  //
  //   if (view.IntrinsicSizeInBytes().Ok()) {
  //     // The size of the struct is known.
  //     DoSomethingWithNBytes(view.IntrinsicSizeInBytes().Read());
  //   }
  //
  // Because MyStruct is always 12 bytes,
  // GenericMyStructView::IntrinsicSizeInBytes().Ok() will always be true.
  static constexpr UIntView<...> IntrinsicSizeInBytes();

  // If you need to get at the raw bytes underneath the view, you can get the
  // view's Storage.
  Storage BackingStorage() const;
};


// An overload of MakeMyStructView is provided which accepts a pointer to a
// container type: this generally works with STL and STL-like containers of
// chars, that have size() and data() methods.  This is known to work with
// std::vector<char>, std::array<char>, std::string, absl:: and
// std::string_view, and some others.  Note that you need to call this with a
// pointer to the container:
//
//     auto view = MakeMyStructView(&container);
//
// IMPORTANT: this does *not* keep a reference to the actual container, so if
// you call a container method that invalidates data() (such as
// std::vector<>::reserve()), you will have to make a new view.
template <typename Container>
inline GenericMyStructView<...> MakeMyStructView(Container *arg);

// Alternately, a "C-style" overload is provided, if you just have a pointer and
// length:
template <typename CharType>
inline GenericMyStructView<...> MakeMyStructView(CharType *buffer,
                                                 std::size_t length);


// In addition to the View class, a namespace will be generated with the
// compile-time constant elements of the class.  This is a convenience, so that
// you can write something like:
//
//     std::array<char, MyStruct::IntrinsicSizeInBytes()>
//
// instead of:
//
//     std::array<char, GenericMyStructView<ContiguousBuffer<
//                              char>>::IntrinsicSizeInBytes().Read()>
namespace MyStruct {

// Because MyStruct only has some constant virtual fields, the namespace
// MyStruct only contains a few corresponding functions.  Note that the
// functions here return values, not views:
inline constexpr unsigned int IntrinsicSizeInBytes();
inline constexpr unsigned int MaxSizeInBytes();
inline constexpr unsigned int MinSizeInBytes();

}  // namespace MyStruct
}  // namespace example
```


## TODO(bolms): Example: Variable-Size `struct`


## TODO(bolms): Example: `enum`


## TODO(bolms): Example: `bits`


