# Design Sketch: Packed Conditional Fields

## Motivation

The [`$next` keyword](archive/next_keyword.md) was introduced to facilitate
writing Emboss definitions for packed or mostly-packed structs, while avoiding

 - the potential error of unintentionally introducing a gap or overlap by
   using the wrong start location,
 - complexity of computing the start location of variable sized fields, and
 - including "redundant" and potentially hardcoded values that must be updated
   separately if the dependent values are updated.

However, one use case not covered by the existing `$next` keyword is that it
does not keep a structure tightly packed if there are conditional fields. For
instance, the structure in
[Example 1](#example-1-conditional-structure-with-next) will have a 4 byte gap
if `type_code` is `1`, even though the `metadata` field is not present.

This tends to be non-intuitive, the author of this design sketch has seen
multiple authors of emboss definitions write `$next` after conditional fields
in this manner and it always results in surprise when it does not work how they
intended, which in this example is to tightly pack `payload` to follow after
`type_code` when `metadata` is not present.

###### Example 1. Conditional structure with $next
```
struct ConditionalExample:
  0       [+2]  UInt       type_code
  if type_code == 0x01:
    $next [+4]  UInt:8[4]  metadata
  $next   [+10] Uint:8[4]  payload
```

## Considerations

There are a few considerations for implementing the behavior that developers
intend when they write code like 
[Example 1](#example-1-conditional-structure-with-next) that are covered in
this section.

### Backwards Compatibility

Updating the functionality of `$next` in this manner could be considered to
break the backwards-compatibility guarantees of Emboss. An existing Emboss
definition may rely on the current behavior of `$next` to produce an intended
layout. However, it's unlikely to be the case, as the goal of `$next` is
explicitly to facilitate writing packed structures. From that point-of-view it
may be more appropriate to consider the current behavior of `$next` to be a
bug.

However, should we need to maintain the existing behavior of `$next` we could
use an alternative symbol (specifics TBD, but possibly `$pack`) for the new
behavior and retain `$next` for backward-compatibility.

For simplicity the rest of this design sketch will use `$next` as if it has the
new behavior in examples, regardless of what decision is made about
compatibility.

### Partially Packed Structures

Another consideration is that any potential solution must work for partially
packed structures, not just fully and tightly packed structures. For instance,
in [Example 2](#example-2-conditional-partially-packed-structure), when the
conditional block is `true`, the `$next` value for `e` should be `14` and `2`
when the block is `false`. This may seem fairly straightforward, but the part
to note is that the implementation must not rely on successive `$next` fields
to provide the correct packing.

###### Example 2. Conditional partially packed structure
```
struct ConditionalPartiallyPackedExample:
  0       [+2]  UInt       a
  if a == 0x01:
    $next [+2]  UInt       b
    10    [+2]  UInt       c
    $next [+2]  UInt       d
  $next   [+2]  UInt       e
```

### Future Features

This proposal also considers two potential future features, one of which is
mentioned in the [`$next` keyword design sketch](archive/next_keyword.md), and
one is mentioned in the emboss code comments.

#### Alignment Function

Another form of (potentially) partially-packed structure would be one where
fields are aligned or otherwise computed using `$next` as a value. To borrow
an example from the [`$next` keyword design sketch](archive/next_keyword.md)
with a slight modification to make it conditional, and using a hypothetical
future `$align(start_location, alignment)` feature, see
[Example 3](#example-3-conditional-alignment-packed).

In this case, `body` should start at the next 4-byte aligned boundary after
the end of `header` if the `header` indicates that the structure doesn't have
a `body_length` field, but start at the next 4-byte aligned boundary after
`body_length` if it is present.

The implementation of the new `$next` should not need to take any of this into
account specifically, but the implementation should be written in such a way
that it will "just work" in the same way that it would work currently other
than the conditional field aspect.

###### Example 3. Conditional alignment-packed
```
struct ConditionalWithAlignment:
  0                [+2]  UInt    header_length (h)
  $align($next, 4) [+h]  Header  header
  if !header.basic_flag:
    $align($next, 4) [+2]  UInt    body_length
  $align($next, 4) [+b]  Body    body
  $align($next, 4) [+4]  UInt    crc
  let b = $present(body_length) ? body_length : 16
```

#### Conditional Block Improvements

Currently Emboss does not support nested conditional blocks, nor does it
support `else` or `elif` conditional blocks. That said, these are mentioned in
the Emboss code comments as potential future features and are common in
languages that offer conditionals, so this proposal considers how they may
impact the new `$next` behavior.

## Proposed Implementation

A high level description of the proposed algorithm for implementing the new
behavior in `$next` (or a new symbol chosen for backward-compatibility) is
provided below, with some error and edge condition checking omitted for
brevity:

 - Similar to the existing algorithm, traverse the IR for `Structure`s
   (`struct`s and `bit`s), but for each structure encountered:
   - Initialize the `lookback` to an empty stack.
   - Initialize `last` to `None`.
   - Iterate over expressions (looking for `$next`):
     - As an incidental action, for each non-virtual and non-synthetic field
       encountered:
       - If `last.existence_condition` is constant and
         `last.existence_condition` is `true`:
         - Clear `lookback` entirely.
         - Push `last` onto `lookback`.
       - Otherwise, if `last.existence_condition` is not the same expression
         as the current `existence_condition`:
         - If any fields in `lookback` have the same `existence_condition` as
           the current field, pop all fields up to and including that field.
         - Push `last` onto `lookback`.
       - Set `last` to the current field.
     - For each `$next` encountered:
       - Initialize `replacement` to be `None`.
       - For each reference in `lookback` as `field`, starting from the bottom
         of the stack and iterating towards the top:
         - If `replacement` is `None`
           - Set `replacement` to `field.start_location + field.size`
           - Note: This branch is equivalent to the existing implementation.
         - Otherwise:
           - Copy `$present(f) ? next : previous` as an expression skeleton
           - Replace
             - `f` with a `FieldRerference` to `field`
             - `next` with `field.start_location + field.size`.
             - `previous` with `replacement`.
           - Set `replacement` to this updated expression.
       - Replace `$next` with `replacement`.

The purpose of using a stack for `lookback` is twofold, firstly it ensures
correct operation with chained conditional blocks one-after-another, such as in
[Example 4](#example-4-consecutive-conditional-blocks), as well as future
support for nested conditionals. In this example, the `lookback` stack for
`crc` should be:

- `(TOP)`
- `baz_data`
- `bar_data`
- `foo_data`
- `code`
- `(BOTTOM)`

And the resulting `$next` expression for `crc` would be (using a fictional
`$end` field for brevity, equivalent to the field offset + field size):

```
($present(baz_data) ? baz_data.$end :
  ($present(bar_data) ? bar_data.$end :
    ($present(foo_data) ? foo_data.$end :
      code.$end)))
```

###### Example 4. Consecutive Conditional Blocks
```
struct ConditionalWithAlignment:
  0     [+1] bits:
    0 [+1] Flag foo
    1 [+1] Flag bar
    2 [+1] Flag baz
  $next [+1] UInt code
  if foo:
    $next [+FooData.$size_in_bytes]   FooData   foo_data
  if bar:
    $next [+BarHeader.$size_in_bytes] BarHeader bar_header
    $next [+BarData.$size_in_bytes]   BarData   bar_data
  if baz:
    $next [+BazData.$size_in_bytes]   BazData   baz_data
  $next [+2] UInt crc
```
