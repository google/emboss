# Design Sketch: Integer-Value-of-Enum Function

## Overview

It is sometimes useful to use the integer value of an enumerated name:

    enum Foo:
      ZZ = 17

    struct Bar:
      [requires: id == Foo.ZZ]  # Type error
      0 [+4]  UInt  id

In the current Emboss expression language, there is no way to perform this
comparison.


## `$to_int()` Function

A `$to_int()` function (name TBD), taking an `enum` value and returning the
same numeric value with type integer, would fix this problem:

    enum Foo:
      ZZ = 17

    struct Bar:
      [requires: id == $to_int(Foo.ZZ)]
      0 [+4]  UInt  id


## `$from_int()` Function (Optional)

The opposite function would also be useful in some circumstances, but would
take a lot more effort: new syntax would be needed for a type-parameterized
function.

A couple of possible syntaxes:

    $int_to<EnumType>(7)   # 1
    EnumType.$from_int(7)  # 2
    EnumType(7)            # 3

The first option resembles type-parameterized functions in many languages, but
may require some tricky modifications to Emboss's strict LR(1) grammar.

The second option looks like a class method (a la Python) or a static method (a
la C++/Java/C#), and *may* require a less-difficult change to the Emboss
grammar... but there are some messy bits in the grammar around how `.` is
handled, and the notation does not scale to multiple types.

The third option is more C-like, *still* requires grammar updates, and does not
provide any obvious solution for any other, future type-parameterized functions.


## Implementation Notes

`$to_int()` would require changes in a lot of places, though each change should
be small.

`$from_int()` would require changes in pretty much the same places, but a few
of them would be significantly more complex.

Basically anywhere that walks or evaluates an `ir_data.Expression` would need to
be updated to know about the new function.  A probably-incomplete list:

    compiler/back_end/header_generator.py
    compiler/front_end/constraints.py
    compiler/front_end/expression_bounds.py
    compiler/front_end/type_check.py
    compiler/util/ir_util.py

Additionally, for `$to_int()`, minor tweaks would need to be made to
`tokenizer.py` (add the new function name) and `module_ir.py` (register the new
name as a function in the syntax).

For `$from_int()`, the list is essentially the same, except that `module_ir.py`
would need much larger updates to allow whichever new syntax, and some of the
other changes would be more complex in order to verify that the type parameter
was actually an `enum`.
