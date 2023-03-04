# Design Sketch: Integer Division and Modulus Operators

## Overview

Currently, Emboss does not support division, which limits what it can express
in its expression language.  In particular, it is awkward to handle things like
arrays of 16-bit values whose size is specified in bytes.

The reason Emboss does not yet have support for division is that division is
tricky to handle correctly.  This document attempts to explain the pitfalls and
the proper solutions.

Note that Emboss does not support non-integer arithmetic, so this document only
talks about *integer* division.


## Syntax

### Symbol

Many programming languages use `/` for all division operations, whether they
are "integer" division, floating point division, rational arithmetic division,
matrix division, or anything else.

Very, very few languages (Haskell) use an operator other than `%` for
modulus/remainder, and no popular language overloads `%` with a second meaning.

(Note that Haskell defines `%` as *rational number division*.  `mod` and `rem`
are used for modulus and remainder, respectively, and `div` and `quot` are used
for truncating and flooring division.)

`%` is technically modulus in some languages, and remainder in others, but in
all cases the equality `x == (x / n * n) + x % n` holds, and does not seem to
confuse programmers.


#### C, C++, C#, Java, Go, Python 2, Rust, SQL, ...

All of these languages use `/` for multiple kinds of division, including
integer division.

Python 2 deprecated `/` for integer division; in a Python 2 program with `from
__future__ import division`, `/` is floating-point division.

C++ and Python both allow `/` to be overloaded for user-defined types.


#### JavaScript, TypeScript, Perl 5

These languages use `/` for floating-point division, and do not directly
support integer division; both operands and result must be cast to int:

    ((l | 0) / (r | 0)) | 0  // JS, TS

    int(int($l) / int($r))    # Perl


#### OCaml, Haskell, Python 3

These languages use separate operators for integer and non-integer division.

Integer division:

    l `div` r    -- Haskell
    l / r        (* OCaml *)
    l // r        # Python 3

Non-integer division:

    l / r        -- Haskell
    l /. r       (* OCaml *)
    l / r         # Python 3


#### Emboss

Emboss should use `//` for division, following Python 3's example.

This is the only unambiguous integer division operator used by a TIOBE top-20
language, *and* Python 3's `//` has the same division semantics (flooring
division) as Emboss -- most other programming languages use truncating
(round-toward-0) division.

If Emboss ever gets support for floating-point arithmetic, it should probably
use OCaml's `/.` operator for division on floats.

Because `/` does different things in different popular languages (flooring
integer division, truncating integer division, floating-point division, or
multiple types, depending on operand types), Emboss should not use it.

Emboss should use `%` for modulus, following the example of almost every other
language.


### Precedence

In most programming languages, division is a left-associative operator with
equal precedence to multiplication; i.e. this:

    a * b / c * d

is equivalent to this:

    ((a * b) / c) * d

However, a nontrivial percentage of programmers tend to read it as:

    (a * b) / (c * d)

This may be because, after grade school, most division is expressed in fraction
form, like:

    a * b
    -----
    c * d

Interestingly, fewer programmers seem to mis-read extra division:

    a * b / c / d

is usually (correctly) parsed as:

    ((a * b) / c) / d

Given that confusion, in Emboss, the construct:

    a * b / c * d

should be a syntax error.

The constructs:

    a * b / c / d
    a * b / c + d

could be syntax errors, although the second one (`... + d`), in particular,
seems to get parsed correctly by all programmers in my polling.

This is in keeping with two general rules of Emboss design:

1.  It is better to lock things down at first and gradually ease restrictions
    than the other way around.
2.  Emboss syntax should be as unambiguous as possible, even when it makes
    implementation trickier or `.emb` files slightly wordier.  (See, for
    example, the "separate-but-equal" precedence of the `&&` and `||`
    operators in Emboss.)


## Semantics

### Flooring Division vs Truncating Division

Roughly speaking, there are two common forms of "integer division:" *flooring*
(sometimes called *Euclidean*) and *truncating* (sometimes called
*round-toward-0*) division.

| Operation  | Flooring Result  | Truncating Result |
| ---------- | ---------------- | ----------------- |
| +8 / +3    | 2                | 2                 |
| +8 / -3    | -3               | -2                |
| -8 / +3    | -3               | -2                |
| -8 / -3    | -3               | 2                 |
| +8 % +3    | 2                | 2                 |
| +8 % -3    | -1               | 2                 |
| -8 % +3    | 1                | -2                |
| -8 % -3    | -2               | -2                |

Most programming languages and most CPUs implement truncating division,
[however, truncating division is irregular around
0](https://dl.acm.org/doi/pdf/10.1145/128861.128862), which prevents some kinds
of expression rewrites (e.g., `(x + 6) / 3` is not the same as `x / 3 + 2` when
`x == -4`) and would force Emboss's bounds tracking to have wider bounds in
some common cases, such as modulus by a known constant, where the dividend could
be either positive or negative.

Emboss should use flooring division.


### Undefined Results

Division is the first operation in Emboss's expression language which can have
an undefined result: all other operations are total.

Emboss does have some notion of "invalid value," which it uses at runtime to
handle fields whose backing store does not exist or whose existence condition is
false, however, "invalid value" is not fully propagated in the expression type
system, and it has a somewhat different meaning than "undefined."

Currently, integer types in the Emboss expression language are sets of the
form:

    {x ∈ ℤ | (min ≤ x ∨ min = -infinity) ∧
             (x ≤ max ∨ max = infinity) ∧
             x MOD m = n ∧
             0 ≤ n < m ∧
             min ∈ ℤ ∪ {-infinity} ∧
             max ∈ ℤ ∪ {infinity} ∧
             m ∈ ℤ ∪ {infinity} ∧
             n ∈ ℤ}

where `min`, `max`, `m`, and `n` are parameters.  The special values `infinity`
and `-infinity` for `max` and `min` indicate that there is no known upper or
lower bound, and the special value `infinity` for `m` indicates that `x` has a
constant value equal to `n`.

This will have to change to something like:

    {x ∈ ℤ ∪ {undefined} | ((can_be_undefined ∧ x = undefined) ∨
                            (min ≤ x ≤ max ∧ x MOD m = n)) ∧
                           0 ≤ n < m ∧
                           can_be_undefined ∈ 𝔹 ∧
                           min ∈ ℤ ∪ {-infinity, undefined} ∧
                           max ∈ ℤ ∪ {infinity, undefined} ∧
                           m ∈ ℤ ∪ {infinity} ∧
                           n ∈ ℤ ∪ {undefined}}

where `can_be_undefined` is a new boolean parameter.

This also leaks out into boolean types, which are currently either {true,
false}, {true}, or {false}: they can now be {true, false}, {true}, {false},
{true, false, undefined}, {true, undefined}, {false, undefined}, or
{undefined}.


### Expression Bound Calculations

#### Division

For an expression x of the form `l // r`, Emboss must figure out the five
parameters of the type of x (`x_min`, `x_max`, `x_m`, `x_n`,
`x_can_be_undefined`) from the five parameters of each of the types of `l` and
`r`.

    x_can_be_undefined = l_can_be_undefined ∨
                         r_can_be_undefined ∨
                         r_min ≤ 0 ≤ r_max

That is, `x` can be undefined if either input is undefined, or if there could
be division by zero.

If `r_min = 0 = r_max`, then:

    x_max = undefined
    x_min = undefined
    x_m = infinity
    x_n = undefined

Otherwise, the remaining parameters can be computed by parts, although for
`x_max` and `x_min` it is simpler to simply check all pairs of {`l_min`, `-1`,
`1`, `l_max`} // {`r_min`, `-1`, `1`, `r_max`} (removing zeroes from the
right-hand side, and removing `-1` and `1` if they do not fall between the
`min` and `max`).

`x_m` is:

    infinity      if l_m = r_m = infinity else
    GCD(l_m, r_n) if r_m = infinity       else
    1

`x_n` is

    l_n // r_n                     if l_m = r_m = infinity else
    (l_n // r_n) MOD GCD(l_m, r_n) if r_m = infinity       else
    0


#### Modulus

Modulus is somewhat simpler.

    x_can_be_undefined = l_can_be_undefined ∨
                         r_can_be_undefined ∨
                         r_min ≤ 0 ≤ r_max

If `l_m = r_m = infinity`, `x_m = infinity` and `x_min = x_max = x_n = l_n %
r_n`.

Otherwise:

    x_max = max(0, r_max - 1)
    x_min = min(0, r_min + 1)
    x_m = 1
    x_n = 0

Note that, as with some other bounds calculations in Emboss, there are some
special cases where `l` or `r` is a very small set where it is technically
possible to find a narrower bound: for example, if 6 ≤ l ≤ 7, l % 4 could have
the bounds `x_max = 3` and `x_min = 2`.  However, Emboss does not need to find
the absolute tightest bound; it only needs to find a reasonable bound.


## Other Notes

### `IsComplete()`

The *intention* of `IsComplete()` is that it should return `true` iff adding
more bytes cannot change the result of `Ok()` -- that is, iff the structure is
"complete" in the sense that there are enough bytes to hold the structure, even
if the structure is broken in some other way.

If the size of the structure is a dynamic value which involves division by
zero, the second definition of `IsComplete()` becomes ill-defined, in that it
becomes impossible to know if there are enough bytes for the structure:

    struct Foo:
      0 [+2]               UInt      divisor
      2 [+512 // divisor]  UInt:8[]  payload

If `divisor == 0`, the size of `payload` is undefined, so the structure's
completeness is undefined.

On the other hand, if `divisor == 0`, then the structure can never be `Ok()`,
so in that sense it is 'complete': there is no way to add more bytes and get a
structure that is functional.  There may be another way for the client software
to recover, such as scanning an input stream for a new start-of-message marker.

I (bolms@) think that the best option is:

1.  Add a new method `Maybe<bool> IsUndefined()` to virtual field views (and
    maybe to `UIntView`, `IntView`, and `FlagView`).
2.  If `IntrinsicSizeInBytes().IsUndefined()`, `IsComplete()` should return
    `true`.  (Note that `IntrinsicSizeInBytes()` is just the way the
    `$size_in_bytes` implicit virtual field is spelled in C++.)
    *   This will require a bunch of plumbing into the whole expression
        generation logic -- probably changing `Maybe<T>` to have a 'why not'
        reason when there is no `T`.
3.  Otherwise, proceed with the current `IsComplete()` logic.
4.  Update the documentation for `IntrinsicSizeInBytes()` and `IsComplete()` to
    note this caveat.

In practice, it is rare to have a dynamic value that could be zero as a divisor
in a field position or length: such divisions are almost always either division
by a constant or division by one of a small set of known divisors, often powers
of 2 (and in many of those cases, a shift operation would fit better).
