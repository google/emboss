# Design: Alternate Enum Field Cases

This document is provided for historical interest.  This feature is now
implemented in the form of the `[enum_case]` attribute on `enum` values, which
can also be `$default`ed on module, struct, bits, and enum definitions.

## Motivation

Currently, the Emboss compiler requires that enum fields are `SHOUTY_CASE`, but
this is discouraged in some code styles, such as
[Google's C++ style guide][google-cpp-style] which prefers`kPrefixedCamelCase`.
This design considers options for allowing other cases in enums and their
possible design.

### Open Issues

This design document is related to the following open GitHub issue:
* [#59][issue-59]

## Design

This design will focus on the implementation for the C++ backend, as that is the
only currently-supported backend in Emboss. However, this approach should be
valid for other backends if and when they are supported, and it is encouraged
that new backends that support this or similar functionality use the same or a
similar design.

### The `enum_case` Attribute

An attribute will be added to the C++ backend: `enum_case`. It would apply to
all enum fields and specifies which case to use for enum members. More than one
case can be specified, in which case the backend will emit both enum member
names with the same values. Initially this will support two cases:

  * `SHOUTY_CASE` - (default) All-capital case with words separated by an underscore
  * `kCamelCase` - Capitalized camel case prefixed with "k"

The options will be provided as a string to the attribute as comma-separated
values. At least one value must be present. More options can be supported in the
future, and the implementation in the C++ backend will be written so that new
case options shouldn't require much more than adding an identifier and a translation
function.

Translations will always be *from* `SHOUTY_CASE` since that is the requirement
in an Emboss definition file. For `kCamelCase`, the words will be split on the
underscore, the first letter of each word will remain capitalized, and all
following letters of each word will be lowercased, then prefixed with the "k".

### Transitioning From `SHOUTY_CASE` To `kCamelCase`

The intended purpose of allowing multiple `enum_case` options to be specified is
to enable transitioning between two cases in the event that the Emboss
definition and the client code that uses the definitions cannot be updated
atomically.

When more than one option is present the backend will emit a definition that
includes all specified name-value pairs. The names will be emitted in the order
specified, so a reverse name lookup from an enum value will return the first
case provided. Thus adding an additional case (by appending to the end of the
comma-separated list) should be fully backwards-compatible.

Removing a case will always be backwards-incompatible, so care should be taken
to migrate client code to the new case before removing an old case.

### Examples

The examples below modify an existing Emboss definition:

```
enum Foo:
  BAR             = 1
  BAZ             = 2
  MULTI_WORD_ENUM = 4
```

#### Use `kCamelCase` Instead

To allow C++ code to use `kBar`, `kBaz`, or `kMultiWordEnum` to refer to the
enum members instead of `BAR`, `BAZ`, or `MULTI_WORD_ENUM`, the `enum_case`
attribute can be added to each field:
```
enum Foo:
  BAR             = 1  [(cpp) enum_case: "kCamelCase"]
  BAZ             = 2  [(cpp) enum_case: "kCamelCase"]
  MULTI_WORD_ENUM = 4  [(cpp) enum_case: "kCamelCase"]
```

This would emit code similar to:

```c++
enum class Foo: uint64_t {
  kBar = 1,
  kBaz = 2,
  kMultiWordEnum = 4,
};
```

Note that as written, this would *not* allow C++ code to refer to `Foo::BAR`,
`Foo::BAZ`, or `Foo::MULTI_WORD_ENUM`.

#### Default `enum_case`

Additionally, the same code would be emitted with either of the following:

```
enum Foo:
  [$default (cpp) enum_case: "kCamelCase"]
  BAR             = 1
  BAZ             = 2
  MULTI_WORD_ENUM = 4
```

or

```
[$default (cpp) enum_case: "kCamelCase"]

...

enum Foo:
  BAR             = 1
  BAZ             = 2
  MULTI_WORD_ENUM = 4
```

With the differences being that the former would have the `enum_case` attribute
apply to any new fields of `Foo` by default, and the latter woulds apply to all
enum fields in the Emboss definition file by default.

#### Transitioning To `kCamelCase`

In the case that `Foo` should use `kCamelCase` but it is used in code that must
be updated separately from the `.emb` file and backwards-compatibility must be
maintained, the `enum_case` attribute will need multiple options specified. For
instance:

```
enum Foo:
  [$default (cpp) enum_case: "SHOUTY_CASE, kCamelCase"]
  BAR             = 1
  BAZ             = 2
  MULTI_WORD_ENUM = 4
```

would emit code similar to:

```cpp
enum class Foo: uint64_t {
  BAR = 1,
  kBar = 1,
  BAZ = 2,
  kBaz = 2,
  MULTI_WORD_ENUM = 4,
  kMultiWordEnum = 4,
};
```

Note that using `enum_case: "kCamelCase, SHOUTY_CASE"` would technically be
backwards-incompatible as that would change the result of code like
`TryToGetNameFromEnum(Foo::BAR)` from `"BAR"` to `"kBar"`, but if there are no
usages of that functionality, it would be backwards-compatible as well.

Once all usages of `Foo` have been migrated to `kShoutyCase`, and there is no
client code that uses `SHOUTY_CASE` or relies on the reverse lookup
functionality mentioned above, then the `SHOUTY_CASE` could be removed. The
usual caveats of backwards-incompatible changes apply.

## Alternatives Considered

In the development of this design, some other alternative designs were
considered. A short explanation is provided of each below.

### Loosen Enum Name Requirements

The "obvious" approach to allow names like `kCamelCase` is to simply loosen the
requirement that an enum field name must be `SHOUTY_CASE`.

#### Pros

  * Flexible and straightforward for users

#### Cons

  * Adds complexity to the grammar and front-end.
    * Not as simple of an implementation as it first appears.
  * Allows Emboss definition files to diverge from each other, which goes
    against the design goals of Emboss where all .emb files should look similar
    to each other.
    * Additionally it adds cognitive overhead in reading an unfamiliar Emboss
      definition in a different "style".
  * Backend/language considerations.
    * A style used in C++ (`kCamelCase`) would also be used in languages where
      that is not the style.
    * Setting the name for all languages could cause issues in languages where
      the case of a variable has semantic meaning, like the visibility of a
      variable in `Go`.

### Specifying An Exact Name In Attributes

Instead of specifying a case transformation in an attribute, provide the
specific name to be emitted. For example:

```
enum Foo:
  BAR             = 1  [(cpp) name: "kBar"]
  BAZ             = 2  [(cpp) name: "kBaz"]
  MULTI_WORD_ENUM = 4  [(cpp) name: "kMultiWordEnum"]
```

Note that the proposed `enum_case` design does not preclude an attribute of this
nature for resolving other use-cases. Under the principle of "specific overrides
general" a `name`-like attribute could override any `enum_case` attribute. See
the [future work](#future-work) section below for planned work on this.

#### Pros

  * Simple to implement
  * Applies to more than just `enum` fields.
  * Applies to other use cases (working around restrictions/reserved keywords in
    backends that are not also restricted/reserved in Emboss).

#### Cons

  * Not possible to provide a `$default` attribute that applies generically to
    all enum fields.
    * This would require an attribute added to every enum member if the intent
      is to always use a particular style.
    * Requires a user to specify the translation for every field, making it
      easier to mix cases or styles unintentionally.
      * If mixing cases is intended, this is still possible with the `enum_case`
	    attribute by overriding the default.

### Transitional Cases or Attributes

This alternative design would still use `enum_case` or something similar, but
not allow multiple case options to be asserted. Instead, either a new
transition-specific case or a transitional attribute would be used to mark a
transition in progress. For example:

```
enum Foo:
  BAR             = 1  [(cpp) enum_case: "kCamelCase-transitional"]
  BAZ             = 2  [(cpp) enum_case: "kCamelCase-transitional"]
  MULTI_WORD_ENUM = 4  [(cpp) enum_case: "kCamelCase-transitional"]
```

or

```
enum Foo:
  BAR             = 1
    [(cpp) enum_case: "kCamelCase"]
    [(cpp) enum_case_transitional: true]
  BAZ             = 2
    [(cpp) enum_case: "kCamelCase"]
    [(cpp) enum_case_transitional: true]
  MULTI_WORD_ENUM = 4
    [(cpp) enum_case: "kCamelCase"]
    [(cpp) enum_case_transitional: true]
```

These would emit both `SHOUTY_CASE` and `kCamelCase` forms for each value.

#### Pros

  * Explicitly marks a transition in progress, and the reason for having
    multiple aliasing names to the same enumerated value.
  * Allows codegen to include `[[deprecated]]` attributes in the generated code
    so that build time warnings/errors are produced when building client code.
    * However, this could be supported by tagging the cases as transitional, see
      the [future work](#future-work) section for planned work on this.

#### Cons

  * Requires migrating twice to transition between two non-`SHOUTY_CASE` cases
    (old -> shouty -> new)
  * Requires two separate attributes or a suffix to the case name, which can
    cause readability issues
  * Doesn't allow supporting more than 2 cases if needed, and requires that one
    case be `SHOUTY_CASE`.

## Implementation

### Front End

Now that the attribute checking is separate for the front end and backend
([#80][pr-80]), only a small change (to both the grammar and the IR) is required
to support attributes on enum values. Specifically:

#### Grammar

Change the existing grammar
```
enum-value                             -> constant-name "=" expression doc?
                                          Comment? eol enum-value-body?
enum-value-body                        -> Indent doc-line* Dedent
```

to

```
enum-value                             -> constant-name "=" expression doc?
                                          attribute* Comment? eol
                                          enum-value-body?
enum-value-body                        -> Indent doc-line* attribute-line*
                                          Dedent
```

#### Intermediate Representation

The only change to IR to support this design would require a
`Repeated(Attribute)` member field to `EnumValue`.

### Back End

The C++ backend can likely retain the same templates for codegen. This design
should only require a change in codegen to read the attribute on an attribute
name-value pair and translate the name (potentially multiple times for multiple
specified cases).

## Future Work

### The `name` attribute

Cases may cause name collisions which are not present in `SHOUTY_CASE`, so there
should be some means to override the generated name. For instance, consider:

```
enum Port:
  # Names taken from manufacturer's programming manual.
  USB    = 128   -- USB port, virtual port 0    # kUsb
  USB_1  = 129   -- USB port, virtual port 1    # kUsb1
  USB1   = 1440  -- USB port 1, virtual port 0  # kUsb1 -- collision
  USB1_1 = 1441  -- USB port 1, virtual port 1  # kUsb11
```

Additionally, there are other use-cases for setting an alternate name to the one
used in the Emboss definition. Thus, an attribute should be provided that can
override all naming, including the default name setting in Emboss and any
`enum_case` attributes. For instance:

```
enum Port:
  # Names taken from manufacturer's programming manual.
  USB    = 128   -- USB port, virtual port 0
    [(cpp) name: "kUsb"]
  USB_1  = 129   -- USB port, virtual port 1
    [(cpp) name: "kUsb_1"]
  USB1   = 1440  -- USB port 1, virtual port 0
    [(cpp) name: "kUsb1"]
  USB1_1 = 1441  -- USB port 1, virtual port 1
    [(cpp) name: "kUsb1_1")
```

This would not emit names like `kUsb11` even if a `$default` case was set to
`kCamelCase` because the `name` attribute would always override other naming
settings. Similar to `enum_case`, multiple names could be provided in a comma
separated list.

This will be completed in future work, the specifics of which may be updated
here or in a separate design. However, the implementation of `enum_case` should
be made to allow `name` or a similar attribute to be added without major
refactoring.

### Deprecated Cases/Names

When transitioning between cases or alternate names, it would be useful to mark
the old field as `[[deprecated]]` in the C++ source, so that client code that
uses the generated Emboss code will produce build-time warnings or errors and
alert maintainers that there will be an upcoming breaking change that could
break the client code's build.

One way to do this would be to allow tagging a name or case as deprecated in
the attribute string itself. For instance:

```
enum Foo:
  BAR = 1
    [(cpp) enum_case: "SHOUTY_CASE -deprecated, kCamelCase"]
  BAZ = 2
    [(cpp) enum_case: "SHOUTY_CASE -deprecated, kCamelCase"]
  MULTI_WORD_ENUM = 4
    [(cpp) enum_case: "SHOUTY_CASE -deprecated, kCamelCase"]
```

This would follow the normal `$default` rules as it would be the same as any
other attribute value, so for instance, to set `SHOUTY_CASE` to be deprecated in
favor of `kCamelCase` for all members of the enum:

```
enum Foo:
  [$default (cpp) enum_case: "SHOUTY_CASE -deprecated, kCamelCase"]
  BAR = 1
  BAZ = 2
  MULTI_WORD_ENUM = 4
```

and to set it for all enums in the module:

```
[$default (cpp) enum_case: "SHOUTY_CASE -deprecated, kCamelCase"]

...

enum Foo:
  BAR = 1
  BAZ = 2
  MULTI_WORD_ENUM = 4
```

This will be completed in future work, the specifics of which may be updated
here or in a separate design. However, the implementation of `enum_case` should
be made to allow adding `-deprecated` or a similar approach without major
refactoring.




[google-cpp-style]: https://google.github.io/styleguide/cppguide.html#Enumerator_Names
[issue-59]: https://github.com/google/emboss/issues/59
[pr-80]: https://github.com/google/emboss/pull/80
