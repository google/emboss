# Design Sketch: Packed Field Notation

This document is provided for historical interest.  This feature is now
implemented in the form of the `$next` keyword.


## Motivation

Many structures have many or most fields laid out consecutively, possibly with
padding for alignment.  For example:

    struct Simple:
      0 [+2]  UInt  field_1
      2 [+4]  UInt  field_2
      6 [+2]  UInt  field_3

For simple structures of fixed-size fields, the main issue is unchecked
redundancy: it is relatively easy to enter the wrong value for the field
offset, and no compiler checks will help.

For more complex structures with multiple variable-sized fields, this can lead
to unwieldy offsets:

    struct Complex:
      0     [+2]  UInt    header_length (h)
      2     [+h]  Header  header
      2+h   [+2]  UInt    body_length (b)
      4+h   [+b]  Body    body
      4+h+b [+4]  UInt    crc

In both cases, there is some benefit to a shorthand notation that says 'this
field should be placed immediately after the end of the lexically-previous
field.


## Example

(Exact syntax TBD.)

    struct Complex:
      0     [+2]  UInt    header_length (h)
      $next [+h]  Header  header
      $next [+2]  UInt    body_length (b)
      $next [+b]  Body    body
      $next [+4]  UInt    crc

It is tempting to use some more specialized, terser syntax, like:

    struct Complex:
      0  [+2]  UInt    header_length (h)
      ^^ [+h]  Header  header
      ^^ [+2]  UInt    body_length (b)
      ^^ [+b]  Body    body
      ^^ [+4]  UInt    crc

However, an explicit symbol has the advantage that you can use it in
expressions, if needed:

    struct ComplexWithGap:
      0       [+2]  UInt    header_length (h)
      $next   [+h]  Header  header
      $next   [+2]  UInt    body_length (b)
      # 2-byte reserved gap.
      $next+2 [+b]  Body    body
      $next   [+4]  UInt    crc

Or, with a (not-yet-implemented) `$align()` function:

    struct ComplexWithAlignment:
      0                [+2]  UInt    header_length (h)
      $align($next, 4) [+h]  Header  header
      $align($next, 4) [+2]  UInt    body_length (b)
      $align($next, 4) [+b]  Body    body
      $align($next, 4) [+4]  UInt    crc


## Implementation

Assuming the "new symbol" approach:

1.  Pick a new symbol name -- preferably, come up with a few alternatives and
    do a quick survey.  By convention, Emboss built-in symbols start with `$`.
2.  Add the new name to `LITERAL_TOKEN_PATTERNS` in
    `compiler/front_end/tokenizer.py`.
3.  Add a new production for `builtin-word -> "$new_symbol"` to the `_word()`
    function in `module_ir.py`.
4.  Add a new compiler pass before `synthetics.synthesize_fields`, to replace
    the new symbol with the expanded representation.  This should be relatively
    straightforward -- something that uses `fast_traverse_ir_top_down()` to
    find all `ir_data.Structure` elements in the IR, then iterates over the
    field offsets within each structure, and recursively replaces any
    `ir_data.Expression`s with a
    `builtin_reference.canonical_name.object_path[0]` equal to
    `"$new_symbol"`.  It would probably be useful to make
    `traverse_ir._fast_traverse_proto_top_down()` into a public function, so
    that you do not have to re-write `Expression` traversal.

For this change, the back end should not need any modifications.
