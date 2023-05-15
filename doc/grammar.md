This is the context-free grammar for Emboss.  Terminal symbols are in `"quotes"`
or are named in `CamelCase`; nonterminal symbols are named in `snake_case`.  The
term `<empty>` to the right of the `->` indicates an empty production (a rule
where the left-hand-side may be parsed from an empty string).

This listing is auto-generated from the grammar defined in `module_ir.py`.

Note that, unlike in many languages, comments are included in the grammar.  This
is so that comments can be handled more easily by the autoformatter; comments
are ignored by the compiler.  This is distinct from *documentation*, which is
included in the IR for use by documentation generators.

```shell
module                                 -> comment-line* doc-line* import-line*
                                          attribute-line* type-definition*
type-definition                        -> bits
                                        | enum
                                        | external
                                        | struct
struct                                 -> "struct" type-name
                                          delimited-parameter-definition-list?
                                          ":" Comment? eol struct-body
struct-body                            -> Indent doc-line* attribute-line*
                                          type-definition* struct-field-block
                                          Dedent
struct-field-block                     -> <empty>
                                        | conditional-struct-field-block
                                          struct-field-block
                                        | unconditional-struct-field
                                          struct-field-block
unconditional-struct-field             -> anonymous-bits-field-definition
                                        | field
                                        | inline-bits-field-definition
                                        | inline-enum-field-definition
                                        | inline-struct-field-definition
                                        | virtual-field
virtual-field                          -> "let" snake-name "=" expression
                                          Comment? eol field-body?
field-body                             -> Indent doc-line* attribute-line* Dedent
expression                             -> choice-expression
choice-expression                      -> logical-expression
                                        | logical-expression "?"
                                          logical-expression ":"
                                          logical-expression
logical-expression                     -> and-expression
                                        | comparison-expression
                                        | or-expression
or-expression                          -> comparison-expression
                                          or-expression-right+
or-expression-right                    -> or-operator comparison-expression
or-operator                            -> "||"
comparison-expression                  -> additive-expression
                                        | additive-expression
                                          equality-expression-right+
                                        | additive-expression
                                          greater-expression-right-list
                                        | additive-expression inequality-operator
                                          additive-expression
                                        | additive-expression
                                          less-expression-right-list
less-expression-right-list             -> equality-expression-right*
                                          less-expression-right
                                          equality-or-less-expression-right*
equality-or-less-expression-right      -> equality-expression-right
                                        | less-expression-right
less-expression-right                  -> less-operator additive-expression
less-operator                          -> "<"
                                        | "<="
inequality-operator                    -> "!="
greater-expression-right-list          -> equality-expression-right*
                                          greater-expression-right
                                          equality-or-greater-expression-right*
equality-or-greater-expression-right   -> equality-expression-right
                                        | greater-expression-right
greater-expression-right               -> greater-operator additive-expression
greater-operator                       -> ">"
                                        | ">="
equality-expression-right              -> equality-operator additive-expression
equality-operator                      -> "=="
additive-expression                    -> times-expression
                                          additive-expression-right*
additive-expression-right              -> additive-operator times-expression
additive-operator                      -> "+"
                                        | "-"
times-expression                       -> negation-expression
                                          times-expression-right*
times-expression-right                 -> multiplicative-operator
                                          negation-expression
multiplicative-operator                -> "*"
negation-expression                    -> additive-operator bottom-expression
                                        | bottom-expression
bottom-expression                      -> "(" expression ")"
                                        | boolean-constant
                                        | builtin-reference
                                        | constant-reference
                                        | field-reference
                                        | function-name "(" argument-list ")"
                                        | numeric-constant
numeric-constant                       -> Number
argument-list                          -> <empty>
                                        | expression comma-then-expression*
comma-then-expression                  -> "," expression
function-name                          -> "$lower_bound"
                                        | "$max"
                                        | "$present"
                                        | "$upper_bound"
field-reference                        -> snake-reference field-reference-tail*
field-reference-tail                   -> "." snake-reference
snake-reference                        -> builtin-field-word
                                        | snake-word
snake-word                             -> SnakeWord
builtin-field-word                     -> "$max_size_in_bits"
                                        | "$max_size_in_bytes"
                                        | "$min_size_in_bits"
                                        | "$min_size_in_bytes"
                                        | "$size_in_bits"
                                        | "$size_in_bytes"
constant-reference                     -> constant-reference-tail
                                        | snake-reference "."
                                          constant-reference-tail
constant-reference-tail                -> constant-word
                                        | type-word "." constant-reference-tail
                                        | type-word "." snake-reference
type-word                              -> CamelWord
constant-word                          -> ShoutyWord
builtin-reference                      -> builtin-word
builtin-word                           -> "$is_statically_sized"
                                        | "$next"
                                        | "$static_size_in_bits"
boolean-constant                       -> BooleanConstant
and-expression                         -> comparison-expression
                                          and-expression-right+
and-expression-right                   -> and-operator comparison-expression
and-operator                           -> "&&"
snake-name                             -> snake-word
inline-struct-field-definition         -> field-location "struct" snake-name
                                          abbreviation? ":" Comment? eol
                                          struct-body
abbreviation                           -> "(" snake-word ")"
field-location                         -> expression "[" "+" expression "]"
inline-enum-field-definition           -> field-location "enum" snake-name
                                          abbreviation? ":" Comment? eol
                                          enum-body
enum-body                              -> Indent doc-line* attribute-line*
                                          enum-value+ Dedent
enum-value                             -> constant-name "=" expression attribute*
                                          doc? Comment? eol enum-value-body?
enum-value-body                        -> Indent doc-line* attribute-line* Dedent
doc                                    -> Documentation
attribute                              -> "[" attribute-context? "$default"?
                                          snake-word ":" attribute-value "]"
attribute-value                        -> expression
                                        | string-constant
string-constant                        -> String
attribute-context                      -> "(" snake-word ")"
constant-name                          -> constant-word
inline-bits-field-definition           -> field-location "bits" snake-name
                                          abbreviation? ":" Comment? eol
                                          bits-body
bits-body                              -> Indent doc-line* attribute-line*
                                          type-definition* bits-field-block
                                          Dedent
bits-field-block                       -> <empty>
                                        | conditional-bits-field-block
                                          bits-field-block
                                        | unconditional-bits-field
                                          bits-field-block
unconditional-bits-field               -> unconditional-anonymous-bits-field
                                        | virtual-field
unconditional-anonymous-bits-field     -> field
                                        | inline-bits-field-definition
                                        | inline-enum-field-definition
conditional-bits-field-block           -> "if" expression ":" Comment? eol Indent
                                          unconditional-bits-field+ Dedent
field                                  -> field-location type snake-name
                                          abbreviation? attribute* doc? Comment?
                                          eol field-body?
type                                   -> type-reference delimited-argument-list?
                                          type-size-specifier?
                                          array-length-specifier*
array-length-specifier                 -> "[" "]"
                                        | "[" expression "]"
type-size-specifier                    -> ":" numeric-constant
delimited-argument-list                -> "(" argument-list ")"
type-reference                         -> snake-word "." type-reference-tail
                                        | type-reference-tail
type-reference-tail                    -> type-word
                                        | type-word "." type-reference-tail
anonymous-bits-field-definition        -> field-location "bits" ":" Comment? eol
                                          anonymous-bits-body
anonymous-bits-body                    -> Indent attribute-line*
                                          anonymous-bits-field-block Dedent
anonymous-bits-field-block             -> <empty>
                                        | conditional-anonymous-bits-field-block
                                          anonymous-bits-field-block
                                        | unconditional-anonymous-bits-field
                                          anonymous-bits-field-block
conditional-anonymous-bits-field-block -> "if" expression ":" Comment? eol Indent
                                          unconditional-anonymous-bits-field+
                                          Dedent
conditional-struct-field-block         -> "if" expression ":" Comment? eol Indent
                                          unconditional-struct-field+ Dedent
eol                                    -> "\n" comment-line*
delimited-parameter-definition-list    -> "(" parameter-definition-list ")"
parameter-definition-list              -> <empty>
                                        | parameter-definition
                                          parameter-definition-list-tail*
parameter-definition-list-tail         -> "," parameter-definition
parameter-definition                   -> snake-name ":" type
type-name                              -> type-word
external                               -> "external" type-name ":" Comment? eol
                                          external-body
external-body                          -> Indent doc-line* attribute-line* Dedent
enum                                   -> "enum" type-name ":" Comment? eol
                                          enum-body
bits                                   -> "bits" type-name
                                          delimited-parameter-definition-list?
                                          ":" Comment? eol bits-body
attribute-line                         -> attribute Comment? eol
import-line                            -> "import" string-constant "as"
                                          snake-word Comment? eol
doc-line                               -> doc Comment? eol
comment-line                           -> Comment? "\n"
```

The following productions are automatically generated to handle zero-or-more,
one-or-more, and zero-or-one repeated lists (`foo*`, `foo+`, and `foo?`
nonterminals) in LR(1).  They are included for completeness, but may be ignored
if you just want to understand the grammar.

```shell
"$default"?                           -> <empty>
                                       | "$default"
Comment?                              -> <empty>
                                       | Comment
abbreviation?                         -> <empty>
                                       | abbreviation
additive-expression-right*            -> <empty>
                                       | additive-expression-right
                                         additive-expression-right*
and-expression-right*                 -> <empty>
                                       | and-expression-right
                                         and-expression-right*
and-expression-right+                 -> and-expression-right
                                         and-expression-right*
array-length-specifier*               -> <empty>
                                       | array-length-specifier
                                         array-length-specifier*
attribute*                            -> <empty>
                                       | attribute attribute*
attribute-context?                    -> <empty>
                                       | attribute-context
attribute-line*                       -> <empty>
                                       | attribute-line attribute-line*
comma-then-expression*                -> <empty>
                                       | comma-then-expression
                                         comma-then-expression*
comment-line*                         -> <empty>
                                       | comment-line comment-line*
delimited-argument-list?              -> <empty>
                                       | delimited-argument-list
delimited-parameter-definition-list?  -> <empty>
                                       | delimited-parameter-definition-list
doc-line*                             -> <empty>
                                       | doc-line doc-line*
doc?                                  -> <empty>
                                       | doc
enum-value*                           -> <empty>
                                       | enum-value enum-value*
enum-value+                           -> enum-value enum-value*
enum-value-body?                      -> <empty>
                                       | enum-value-body
equality-expression-right*            -> <empty>
                                       | equality-expression-right
                                         equality-expression-right*
equality-expression-right+            -> equality-expression-right
                                         equality-expression-right*
equality-or-greater-expression-right* -> <empty>
                                       | equality-or-greater-expression-right
                                         equality-or-greater-expression-right*
equality-or-less-expression-right*    -> <empty>
                                       | equality-or-less-expression-right
                                         equality-or-less-expression-right*
field-body?                           -> <empty>
                                       | field-body
field-reference-tail*                 -> <empty>
                                       | field-reference-tail
                                         field-reference-tail*
import-line*                          -> <empty>
                                       | import-line import-line*
or-expression-right*                  -> <empty>
                                       | or-expression-right or-expression-right*
or-expression-right+                  -> or-expression-right or-expression-right*
parameter-definition-list-tail*       -> <empty>
                                       | parameter-definition-list-tail
                                         parameter-definition-list-tail*
times-expression-right*               -> <empty>
                                       | times-expression-right
                                         times-expression-right*
type-definition*                      -> <empty>
                                       | type-definition type-definition*
type-size-specifier?                  -> <empty>
                                       | type-size-specifier
unconditional-anonymous-bits-field*   -> <empty>
                                       | unconditional-anonymous-bits-field
                                         unconditional-anonymous-bits-field*
unconditional-anonymous-bits-field+   -> unconditional-anonymous-bits-field
                                         unconditional-anonymous-bits-field*
unconditional-bits-field*             -> <empty>
                                       | unconditional-bits-field
                                         unconditional-bits-field*
unconditional-bits-field+             -> unconditional-bits-field
                                         unconditional-bits-field*
unconditional-struct-field*           -> <empty>
                                       | unconditional-struct-field
                                         unconditional-struct-field*
unconditional-struct-field+           -> unconditional-struct-field
                                         unconditional-struct-field*
```

The following regexes are used to tokenize input into the corresponding symbols.
Note that the `Indent`, `Dedent`, and `EndOfLine` symbols are generated using
separate logic.

Pattern                                    | Symbol
------------------------------------------ | ------------------------------
`\[`                                       | `"["`
`\]`                                       | `"]"`
`\(`                                       | `"("`
`\)`                                       | `")"`
`\:`                                       | `":"`
`\=`                                       | `"="`
`\+`                                       | `"+"`
`\-`                                       | `"-"`
`\*`                                       | `"*"`
`\.`                                       | `"."`
`\?`                                       | `"?"`
`\=\=`                                     | `"=="`
`\!\=`                                     | `"!="`
`\&\&`                                     | `"&&"`
`\|\|`                                     | `"||"`
`\<`                                       | `"<"`
`\>`                                       | `">"`
`\<\=`                                     | `"<="`
`\>\=`                                     | `">="`
`\,`                                       | `","`
`\$static_size_in_bits`                    | `"$static_size_in_bits"`
`\$is_statically_sized`                    | `"$is_statically_sized"`
`\$max`                                    | `"$max"`
`\$present`                                | `"$present"`
`\$upper_bound`                            | `"$upper_bound"`
`\$lower_bound`                            | `"$lower_bound"`
`\$next`                                   | `"$next"`
`\$size_in_bits`                           | `"$size_in_bits"`
`\$size_in_bytes`                          | `"$size_in_bytes"`
`\$max_size_in_bits`                       | `"$max_size_in_bits"`
`\$max_size_in_bytes`                      | `"$max_size_in_bytes"`
`\$min_size_in_bits`                       | `"$min_size_in_bits"`
`\$min_size_in_bytes`                      | `"$min_size_in_bytes"`
`\$default`                                | `"$default"`
`struct`                                   | `"struct"`
`bits`                                     | `"bits"`
`enum`                                     | `"enum"`
`external`                                 | `"external"`
`import`                                   | `"import"`
`as`                                       | `"as"`
`if`                                       | `"if"`
`let`                                      | `"let"`
`EmbossReserved[A-Za-z0-9]*`               | `BadWord`
`emboss_reserved[_a-z0-9]*`                | `BadWord`
`EMBOSS_RESERVED[_A-Z0-9]*`                | `BadWord`
`"(?:[^"\n\\]\|\\[n\\"])*"`                | `String`
`[0-9]+`                                   | `Number`
`[0-9]{1,3}(?:_[0-9]{3})*`                 | `Number`
`0x[0-9a-fA-F]+`                           | `Number`
`0x_?[0-9a-fA-F]{1,4}(?:_[0-9a-fA-F]{4})*` | `Number`
`0x_?[0-9a-fA-F]{1,8}(?:_[0-9a-fA-F]{8})*` | `Number`
`0b[01]+`                                  | `Number`
`0b_?[01]{1,4}(?:_[01]{4})*`               | `Number`
`0b_?[01]{1,8}(?:_[01]{8})*`               | `Number`
`true\|false`                              | `BooleanConstant`
`[a-z][a-z_0-9]*`                          | `SnakeWord`
`[A-Z][A-Z_0-9]*[A-Z_][A-Z_0-9]*`          | `ShoutyWord`
`[A-Z][a-zA-Z0-9]*[a-z][a-zA-Z0-9]*`       | `CamelWord`
`-- .*`                                    | `Documentation`
`--$`                                      | `Documentation`
`--.*`                                     | `BadDocumentation`
`\s+`                                      | *no symbol emitted*
`#.*`                                      | `Comment`
`[0-9][bxBX]?[0-9a-fA-F_]*`                | `BadNumber`
`[a-zA-Z_$0-9]+`                           | `BadWord`

The following 534 keywords are reserved, but not used, by Emboss.  They may not
be used as field, type, or enum value names.

`ATOMIC_BOOL_LOCK_FREE` `ATOMIC_CHAR16_T_LOCK_FREE` `ATOMIC_CHAR32_T_LOCK_FREE`
`ATOMIC_CHAR_LOCK_FREE` `ATOMIC_FLAG_INIT` `ATOMIC_INT_LOCK_FREE`
`ATOMIC_LLONG_LOCK_FREE` `ATOMIC_LONG_LOCK_FREE` `ATOMIC_POINTER_LOCK_FREE`
`ATOMIC_SHORT_LOCK_FREE` `ATOMIC_VAR_INIT` `ATOMIC_WCHAR_T_LOCK_FREE` `BUFSIZ`
`CGFloat` `CHAR_BIT` `CHAR_MAX` `CHAR_MIN` `CLOCKS_PER_SEC` `CMPLX` `CMPLXF`
`CMPLXL` `DBL_DECIMAL_DIG` `DBL_DIG` `DBL_EPSILON` `DBL_HAS_SUBNORM`
`DBL_MANT_DIG` `DBL_MAX` `DBL_MAX_10_EXP` `DBL_MAX_EXP` `DBL_MIN`
`DBL_MIN_10_EXP` `DBL_MIN_EXP` `DBL_TRUE_MIN` `DECIMAL_DIG` `DOMAIN` `EDOM`
`EILSEQ` `EOF` `ERANGE` `EXIT_FAILURE` `EXIT_SUCCESS` `FE_ALL_EXCEPT`
`FE_DFL_ENV` `FE_DIVBYZERO` `FE_DOWNWARD` `FE_INEXACT` `FE_INVALID`
`FE_OVERFLOW` `FE_TONEAREST` `FE_TOWARDZERO` `FE_UNDERFLOW` `FE_UPWARD`
`FILENAME_MAX` `FLT_DECIMAL_DIG` `FLT_DIG` `FLT_EPSILON` `FLT_EVAL_METHOD`
`FLT_HAS_SUBNORM` `FLT_MANT_DIG` `FLT_MAX` `FLT_MAX_10_EXP` `FLT_MAX_EXP`
`FLT_MIN` `FLT_MIN_10_EXP` `FLT_MIN_EXP` `FLT_RADIX` `FLT_ROUNDS` `FLT_TRUE_MIN`
`FOPEN_MAX` `FP_FAST_FMA` `FP_FAST_FMAF` `FP_FAST_FMAL` `FP_ILOGB0`
`FP_ILOGBNAN` `FP_INFINITE` `FP_NAN` `FP_NORMAL` `FP_SUBNORMAL` `FP_ZERO`
`False` `HUGE_VAL` `HUGE_VALF` `HUGE_VALL` `INFINITY` `INT16_C` `INT16_MAX`
`INT16_MIN` `INT32_C` `INT32_MAX` `INT32_MIN` `INT64_C` `INT64_MAX` `INT64_MIN`
`INT8_C` `INT8_MAX` `INT8_MIN` `INTMAX_C` `INTMAX_MAX` `INTMAX_MIN` `INTPTR_MAX`
`INTPTR_MIN` `INT_FAST16_MAX` `INT_FAST16_MIN` `INT_FAST32_MAX` `INT_FAST32_MIN`
`INT_FAST64_MAX` `INT_FAST64_MIN` `INT_FAST8_MAX` `INT_FAST8_MIN`
`INT_LEAST16_MAX` `INT_LEAST16_MIN` `INT_LEAST32_MAX` `INT_LEAST32_MIN`
`INT_LEAST64_MAX` `INT_LEAST64_MIN` `INT_LEAST8_MAX` `INT_LEAST8_MIN` `INT_MAX`
`INT_MIN` `LC_ALL` `LC_COLLATE` `LC_CTYPE` `LC_MONETARY` `LC_NUMERIC` `LC_TIME`
`LDBL_DECIMAL_DIG` `LDBL_DIG` `LDBL_EPSILON` `LDBL_HAS_SUBNORM` `LDBL_MANT_DIG`
`LDBL_MAX` `LDBL_MAX_10_EXP` `LDBL_MAX_EXP` `LDBL_MIN` `LDBL_MIN_10_EXP`
`LDBL_MIN_EXP` `LDBL_TRUE_MIN` `LLONG_MAX` `LLONG_MIN` `LONG_MAX` `LONG_MIN`
`MATH_ERREXCEPT` `MATH_ERRNO` `MAXFLOAT` `MB_CUR_MAX` `MB_LEN_MAX` `M_1_PI`
`M_2_PI` `M_2_SQRTPI` `M_3PI_4` `M_E` `M_INVLN2` `M_IVLN10` `M_LN10` `M_LN2`
`M_LN2HI` `M_LN2LO` `M_LOG10E` `M_LOG2E` `M_LOG2_E` `M_PI` `M_PI_2` `M_PI_4`
`M_SQRT1_2` `M_SQRT2` `M_SQRT3` `M_SQRTPI` `M_TWOPI` `NAN` `NDEBUG` `NSInteger`
`NSNumber` `NSObject` `NULL` `None` `ONCE_FLAG_INIT` `OVERFLOW` `PLOSS`
`PTRDIFF_MAX` `PTRDIFF_MIN` `RAND_MAX` `SCHAR_MAX` `SCHAR_MIN` `SEEK_CUR`
`SEEK_END` `SEEK_SET` `SHRT_MAX` `SHRT_MIN` `SIGABRT` `SIGFPE` `SIGILL` `SIGINT`
`SIGSEGV` `SIGTERM` `SIG_ATOMIC_MAX` `SIG_ATOMIC_MIN` `SIG_DFL` `SIG_ERR`
`SIG_IGN` `SING` `SIZE_MAX` `Self` `TIME_UTC` `TLOSS` `TMP_MAX` `TMP_MAX_S`
`TSS_DTOR_ITERATIONS` `True` `UCHAR_MAX` `UINT16_C` `UINT16_MAX` `UINT32_C`
`UINT32_MAX` `UINT64_C` `UINT64_MAX` `UINT8_C` `UINT8_MAX` `UINTMAX_C`
`UINTMAX_MAX` `UINTPTR_MAX` `UINT_FAST16_MAX` `UINT_FAST32_MAX`
`UINT_FAST64_MAX` `UINT_FAST8_MAX` `UINT_LEAST16_MAX` `UINT_LEAST32_MAX`
`UINT_LEAST64_MAX` `UINT_LEAST8_MAX` `UINT_MAX` `ULLONG_MAX` `ULONG_MAX`
`UNDERFLOW` `USHRT_MAX` `WCHAR_MAX` `WCHAR_MIN` `WEOF` `WINT_MAX` `WINT_MIN`
`abstract` `acos` `acosh` `after` `alignas` `alignof` `and` `and_eq` `andalso`
`asin` `asinh` `asm` `assert` `atan` `atan2` `atanh`
`atomic_compare_exchange_strong` `atomic_compare_exchange_strong_explicit`
`atomic_compare_exchange_weak` `atomic_compare_exchange_weak_explicit`
`atomic_exchange` `atomic_exchange_explicit` `atomic_fetch_add`
`atomic_fetch_add_explicit` `atomic_fetch_and` `atomic_fetch_and_explicit`
`atomic_fetch_or` `atomic_fetch_or_explicit` `atomic_fetch_sub`
`atomic_fetch_sub_explicit` `atomic_fetch_xor` `atomic_fetch_xor_explicit`
`atomic_init` `atomic_is_lock_free` `atomic_load` `atomic_load_explicit`
`atomic_store` `atomic_store_explicit` `auto` `band` `become` `begin` `bitand`
`bitor` `bnot` `bool` `boolean` `bor` `box` `break` `bsl` `bsr` `bxor` `byte`
`carg` `case` `catch` `cbrt` `ceil` `chan` `char` `char16_t` `char32_t` `cimag`
`class` `classdef` `compl` `complex` `concept` `cond` `conj` `const`
`const_cast` `constexpr` `continue` `copysign` `cos` `cosh` `cproj` `crate`
`creal` `decltype` `def` `default` `defer` `del` `delete` `div` `do` `double`
`dynamic_cast` `elif` `else` `elseif` `end` `erf` `erfc` `errno` `except` `exec`
`exp` `exp2` `explicit` `expm1` `export` `extends` `extern` `fabs` `fallthrough`
`fdim` `final` `finally` `float` `floor` `fma` `fmax` `fmin` `fmod` `fn` `for`
`fortran` `fpclassify` `frexp` `friend` `from` `fun` `func` `function` `global`
`go` `goto` `hypot` `ilogb` `imaginary` `impl` `implementation` `implements`
`in` `inline` `instanceof` `int` `interface` `is` `isfinite` `isgreater`
`isgreaterequal` `isinf` `isless` `islessequal` `islessgreater` `isnan`
`isnormal` `isunordered` `kill_dependency` `lambda` `ldexp` `lgamma` `llrint`
`llround` `log` `log10` `log1p` `log2` `logb` `long` `loop` `lrint` `lround`
`macro` `map` `match` `math_errhandling` `mod` `move` `mut` `mutable`
`namespace` `native` `nearbyint` `new` `nextafter` `nexttoward` `noexcept`
`nonatomic` `nonlocal` `noreturn` `not` `not_eq` `null` `nullptr` `of`
`offsetof` `operator` `or` `or_eq` `orelse` `otherwise` `override` `package`
`parfor` `pass` `persistent` `pow` `print` `priv` `private` `proc` `property`
`protected` `protocol` `pub` `public` `pure` `raise` `range` `readonly`
`readwrite` `receive` `ref` `register` `reinterpret_cast` `rem` `remainder`
`remquo` `requires` `restrict` `retain` `rethrow` `return` `rint` `round`
`scalbln` `scalbn` `select` `self` `setjmp` `short` `signbit` `signed` `sin`
`sinh` `sizeof` `spmd` `sqrt` `static` `static_assert` `static_cast` `stderr`
`stdin` `stdout` `strictfp` `strong` `super` `switch` `synchronized` `tan`
`tanh` `template` `tgamma` `this` `thread_local` `throw` `throws` `trait`
`transient` `trunc` `try` `type` `typedef` `typeid` `typename` `typeof` `union`
`unsafe` `unsafe_unretained` `unsigned` `unsized` `use` `using` `va_arg`
`va_copy` `va_end` `va_start` `var` `virtual` `void` `volatile` `wchar_t` `weak`
