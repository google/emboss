// Copyright 2019 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// Implementations for the operations and builtin functions in the Emboss
// expression language.
#ifndef EMBOSS_RUNTIME_CPP_EMBOSS_ARITHMETIC_H_
#define EMBOSS_RUNTIME_CPP_EMBOSS_ARITHMETIC_H_

#include <cstdint>
#include <type_traits>

#include "runtime/cpp/emboss_bit_util.h"
#include "runtime/cpp/emboss_maybe.h"

namespace emboss {
namespace support {

// Arithmetic operations
//
// Emboss arithmetic is performed by special-purpose functions, not (directly)
// using C++ operators.  This allows Emboss to handle the minor differences
// between the ways that Emboss operations are defined and the way that C++
// operations are defined, and provides a convenient way to handle arithmetic on
// values that might not be readable.
//
// The biggest differences are:
//
// Emboss's And and Or are defined to return false or true, respectively, if at
// least one operand is false or true, respectively, even if the other operand
// is not Known().  This is similar to C/C++ shortcut evaluation, except that it
// is symmetric.
//
// Emboss's expression type system uses (notionally) infinite-size integers, but
// it is an error in Emboss if the full range of any subexpression cannot fit in
// either [-(2**63), 2**63 - 1] or [0, 2**64 - 1].  Additionally, either all
// arguments to and the return type of an operation, if integers, must fit in
// int64_t, or they must all fit in uin64_t.  This means that C++ integer types
// can be used directly for each operation, but casting may be required in
// between operations.


// AllKnown(...) returns true if all of its arguments are Known().  The base
// case is no arguments.
inline constexpr bool AllKnown() { return true; }

// The rest of AllKnown() could be:
//
// template <typename T, typename... RestT>
// inline constexpr bool AllKnown(T v, RestT... rest) {
//   return v.Known() && AllKnown(rest...);
// }
//
// ... unfortunately, some compilers do not optimize this well, and it ends
// up using linear stack space instead of constant stack space; for complex
// structs on systems with limited stack (such as typical microcontrollers),
// this can cause methods like Ok() to blow the stack.
//
// The C++14 solution would be to use a std::initializer_list and iterate over
// the arguments.  Unfortunately, C++11 std::initializer_list is not
// constexpr, and C++11 constexpr does not allow iteration.
//
// Instead, for "small" numbers of arguments (up to 64, at time of writing,
// controlled by OVERLOADS in generators/all_known.py), we have generated
// overloads of the form:
//
// template <typename T0, ... typename TN>
// inline constexpr bool AllKnown(T0 v0, ... TN vN) {
//   return v0.Known() && ... && vN.Known();
// }
//
// This reduces stack frames by ~64x.
#include "emboss_arithmetic_all_known_generated.h"

// MaybeDo implements the logic of checking for known values, unwrapping the
// known values, passing the unwrapped values to OperatorT, and then rewrapping
// the result.
template <typename IntermediateT, typename ResultT, typename OperatorT,
          typename... ArgsT>
inline constexpr Maybe<ResultT> MaybeDo(Maybe<ArgsT>... args) {
  return AllKnown(args...)
             ? Maybe<ResultT>(static_cast<ResultT>(OperatorT::template Do<>(
                   static_cast<IntermediateT>(args.ValueOrDefault())...)))
             : Maybe<ResultT>();
}

//// Operations intended to be passed to MaybeDo:

struct SumOperation {
  template <typename T>
  static inline constexpr T Do(T l, T r) {
    return l + r;
  }
};

struct DifferenceOperation {
  template <typename T>
  static inline constexpr T Do(T l, T r) {
    return l - r;
  }
};

struct ProductOperation {
  template <typename T>
  static inline constexpr T Do(T l, T r) {
    return l * r;
  }
};

// Assertions for the template types of comparisons.
template <typename ResultT, typename LeftT, typename RightT>
inline constexpr bool AssertComparisonInPartsTypes() {
  static_assert(::std::is_same<ResultT, bool>::value,
                "EMBOSS BUG: Comparisons must return bool.");
  static_assert(
      ::std::is_signed<LeftT>::value || ::std::is_signed<RightT>::value,
      "EMBOSS BUG: Comparisons in parts expect one side to be signed.");
  static_assert(
      ::std::is_unsigned<LeftT>::value || ::std::is_unsigned<RightT>::value,
      "EMBOSS BUG: Comparisons in parts expect one side to be unsigned.");
  return true;  // A literal return type is required for a constexpr function.
}

struct EqualOperation {
  template <typename T>
  static inline constexpr bool Do(T l, T r) {
    return l == r;
  }
};

struct NotEqualOperation {
  template <typename T>
  static inline constexpr bool Do(T l, T r) {
    return l != r;
  }
};

struct LessThanOperation {
  template <typename T>
  static inline constexpr bool Do(T l, T r) {
    return l < r;
  }
};

struct LessThanOrEqualOperation {
  template <typename T>
  static inline constexpr bool Do(T l, T r) {
    return l <= r;
  }
};

struct GreaterThanOperation {
  template <typename T>
  static inline constexpr bool Do(T l, T r) {
    return l > r;
  }
};

struct GreaterThanOrEqualOperation {
  template <typename T>
  static inline constexpr bool Do(T l, T r) {
    return l >= r;
  }
};

// MaximumOperation is a bit more complex, in order to handle the variable
// number of parameters.
struct MaximumOperation {
  // Maximum of 1 element is just itself.
  template <typename T>
  static inline constexpr T Do(T arg) {
    return arg;
  }

  // The rest of MaximumOperation::Do could be:
  //
  // template <typename T, typename... RestT>
  // static inline constexpr T Do(T v0, T v1, RestT... rest) {
  //   return Do(v0 < v1 ? v1 : v0, rest...);
  // }
  //
  // ... unfortunately, some compilers do not optimize this well, and it ends
  // up using linear stack space instead of constant stack space; for complex
  // structs on systems with limited stack (such as typical microcontrollers),
  // this can cause methods like Ok() to blow the stack.
  //
  // The C++14 solution would be to use a std::initializer_list and iterate over
  // the arguments.  Unfortunately, C++11 std::initializer_list is not
  // constexpr, and C++11 constexpr does not allow iteration.
  //
  // Instead, we have a small number of hand-written overloads and a large
  // number (59, at time of writing, controlled by OVERLOADS in
  // generators/maximum_operation_do.py) of generated overloads, which use
  // O(lg(N)) stack for "small" numbers of arguments (128 or fewer, at time of
  // writing), and O(N) stack for more arguments, but with a much, much smaller
  // constant multiplier: one additional stack frame per 64 arguments, instead
  // of one per argument.

  // Maximum of 2-4 elements are special-cased.
  template <typename T>
  static inline constexpr T Do(T v0, T v1) {
    // C++11 std::max is not constexpr, so we can't just call it.
    return v0 < v1 ? v1 : v0;
  }

  template <typename T>
  static inline constexpr T Do(T v0, T v1, T v2) {
    return Do(v0 < v1 ? v1 : v0, v2);
  }

  template <typename T>
  static inline constexpr T Do(T v0, T v1, T v2, T v3) {
    return Do(v0 < v1 ? v1 : v0, v2 < v3 ? v3 : v2);
  }

  // The remaining overloads (5+ arguments) are generated by a script and
  // #included, so that they do not clutter the hand-written code.
  //
  // They are of the form:
  //
  // template <typename T>
  // static inline constexpr Do(T v0, ... T vN, T vN_plus_1, ... T v2N) {
  //   return Do(Do(v0, ... vN), Do(vN_plus_1, ... v2N));
  // }
  //
  // In each case, they cut their argument lists in half, calling Do(Do(first
  // half), Do(second half)).
  //
  // Note that, if there are enough arguments, this still falls back onto
  // linear-stack-space recursion.
#include "emboss_arithmetic_maximum_operation_generated.h"
};

//// Special operations, where either un-Known() operands do not always result
//// in un-Known() results, or where Known() operands do not always result in
//// Known() results.

// Assertions for And and Or.
template <typename IntermediateT, typename ResultT, typename LeftT,
          typename RightT>
inline constexpr bool AssertBooleanOperationTypes() {
  // And and Or are templates so that the Emboss code generator
  // doesn't have to special case AND, but they should only be instantiated with
  // <bool, bool, bool>.  This pushes a bit of extra work onto the C++ compiler.
  static_assert(::std::is_same<IntermediateT, bool>::value,
                "EMBOSS BUG: Boolean operations must have bool IntermediateT.");
  static_assert(::std::is_same<ResultT, bool>::value,
                "EMBOSS BUG: Boolean operations must return bool.");
  static_assert(::std::is_same<LeftT, bool>::value,
                "EMBOSS BUG: Boolean operations require boolean operands.");
  static_assert(::std::is_same<RightT, bool>::value,
                "EMBOSS BUG: Boolean operations require boolean operands.");
  return true;  // A literal return type is required for a constexpr function.
}

template <typename IntermediateT, typename ResultT, typename LeftT,
          typename RightT>
inline constexpr Maybe<ResultT> And(Maybe<LeftT> l, Maybe<RightT> r) {
  // If either value is false, the result is false, even if the other value is
  // unknown.  Otherwise, if either value is unknown, the result is unknown.
  // Otherwise, both values are true, and the result is true.
  return AssertBooleanOperationTypes<IntermediateT, ResultT, LeftT, RightT>(),
         !l.ValueOr(true) || !r.ValueOr(true)
             ? Maybe<ResultT>(false)
             : (!l.Known() || !r.Known() ? Maybe<ResultT>()
                                         : Maybe<ResultT>(true));
}

template <typename IntermediateT, typename ResultT, typename LeftT,
          typename RightT>
inline constexpr Maybe<ResultT> Or(Maybe<LeftT> l, Maybe<RightT> r) {
  // If either value is true, the result is true, even if the other value is
  // unknown.  Otherwise, if either value is unknown, the result is unknown.
  // Otherwise, both values are false, and the result is false.
  return AssertBooleanOperationTypes<IntermediateT, ResultT, LeftT, RightT>(),
         l.ValueOr(false) || r.ValueOr(false)
             ? Maybe<ResultT>(true)
             : (!l.Known() || !r.Known() ? Maybe<ResultT>()
                                         : Maybe<ResultT>(false));
}

template <typename ResultT, typename ValueT>
inline constexpr Maybe<ResultT> MaybeStaticCast(Maybe<ValueT> value) {
  return value.Known()
             ? Maybe<ResultT>(static_cast<ResultT>(value.ValueOrDefault()))
             : Maybe<ResultT>();
}

template <typename IntermediateT, typename ResultT, typename ConditionT,
          typename TrueT, typename FalseT>
inline constexpr Maybe<ResultT> Choice(Maybe<ConditionT> condition,
                                       Maybe<TrueT> if_true,
                                       Maybe<FalseT> if_false) {
  // Since the result of a condition could be any value from either if_true or
  // if_false, it should be the same type as IntermediateT.
  static_assert(::std::is_same<IntermediateT, ResultT>::value,
                "Choice's IntermediateT should be the same as ResultT.");
  static_assert(::std::is_same<ConditionT, bool>::value,
                "Choice operation requires a boolean condition.");
  // If the condition is un-Known(), then the result is un-Known().  Otherwise,
  // the result is if_true if condition, or if_false if not condition.  For
  // integral types, ResultT may differ from TrueT or FalseT, so Known() results
  // must be unwrapped, cast to ResultT, and re-wrapped in Maybe<ResultT>.  For
  // non-integral TrueT/FalseT/ResultT, the cast is unnecessary, but safe.
  return condition.Known() ? condition.ValueOrDefault()
                                 ? MaybeStaticCast<ResultT, TrueT>(if_true)
                                 : MaybeStaticCast<ResultT, FalseT>(if_false)
                           : Maybe<ResultT>();
}

//// From here down: boilerplate instantiations of the various operations, which
//// only forward to MaybeDo:

template <typename IntermediateT, typename ResultT, typename LeftT,
          typename RightT>
inline constexpr Maybe<ResultT> Sum(Maybe<LeftT> l, Maybe<RightT> r) {
  return MaybeDo<IntermediateT, ResultT, SumOperation, LeftT, RightT>(l, r);
}

template <typename IntermediateT, typename ResultT, typename LeftT,
          typename RightT>
inline constexpr Maybe<ResultT> Difference(Maybe<LeftT> l, Maybe<RightT> r) {
  return MaybeDo<IntermediateT, ResultT, DifferenceOperation, LeftT, RightT>(l,
                                                                             r);
}

template <typename IntermediateT, typename ResultT, typename LeftT,
          typename RightT>
inline constexpr Maybe<ResultT> Product(Maybe<LeftT> l, Maybe<RightT> r) {
  return MaybeDo<IntermediateT, ResultT, ProductOperation, LeftT, RightT>(l, r);
}

template <typename IntermediateT, typename ResultT, typename LeftT,
          typename RightT>
inline constexpr Maybe<ResultT> Equal(Maybe<LeftT> l, Maybe<RightT> r) {
  return MaybeDo<IntermediateT, ResultT, EqualOperation, LeftT, RightT>(l, r);
}

template <typename IntermediateT, typename ResultT, typename LeftT,
          typename RightT>
inline constexpr Maybe<ResultT> NotEqual(Maybe<LeftT> l, Maybe<RightT> r) {
  return MaybeDo<IntermediateT, ResultT, NotEqualOperation, LeftT, RightT>(l,
                                                                           r);
}

template <typename IntermediateT, typename ResultT, typename LeftT,
          typename RightT>
inline constexpr Maybe<ResultT> LessThan(Maybe<LeftT> l, Maybe<RightT> r) {
  return MaybeDo<IntermediateT, ResultT, LessThanOperation, LeftT, RightT>(l,
                                                                           r);
}

template <typename IntermediateT, typename ResultT, typename LeftT,
          typename RightT>
inline constexpr Maybe<ResultT> LessThanOrEqual(Maybe<LeftT> l,
                                                Maybe<RightT> r) {
  return MaybeDo<IntermediateT, ResultT, LessThanOrEqualOperation, LeftT,
                 RightT>(l, r);
}

template <typename IntermediateT, typename ResultT, typename LeftT,
          typename RightT>
inline constexpr Maybe<ResultT> GreaterThan(Maybe<LeftT> l, Maybe<RightT> r) {
  return MaybeDo<IntermediateT, ResultT, GreaterThanOperation, LeftT, RightT>(
      l, r);
}

template <typename IntermediateT, typename ResultT, typename LeftT,
          typename RightT>
inline constexpr Maybe<ResultT> GreaterThanOrEqual(Maybe<LeftT> l,
                                                   Maybe<RightT> r) {
  return MaybeDo<IntermediateT, ResultT, GreaterThanOrEqualOperation, LeftT,
                 RightT>(l, r);
}

template <typename IntermediateT, typename ResultT, typename... ArgsT>
inline constexpr Maybe<ResultT> Maximum(Maybe<ArgsT>... args) {
  return MaybeDo<IntermediateT, ResultT, MaximumOperation, ArgsT...>(args...);
}

}  // namespace support
}  // namespace emboss

#endif  // EMBOSS_RUNTIME_CPP_EMBOSS_ARITHMETIC_H_
