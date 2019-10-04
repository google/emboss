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

inline constexpr bool AllKnown() { return true; }

template <typename T, typename... RestT>
inline constexpr bool AllKnown(T value, RestT... rest) {
  return value.Known() && AllKnown(rest...);
}

// MaybeDo implements the logic of checking for known values, unwrapping the
// known values, passing the unwrapped values to OperatorT, and then rewrapping
// the result.
template <typename IntermediateT, typename ResultT, typename OperatorT,
          typename... ArgsT>
inline constexpr Maybe<ResultT> MaybeDo(Maybe<ArgsT>... args) {
  return AllKnown(args...)
             ? Maybe<ResultT>(static_cast<ResultT>(OperatorT::template Do(
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
  template <typename T>
  static inline constexpr T Do(T arg) {
    // Base case for recursive template.
    return arg;
  }

  // Ideally, this would only use template<typename T>, but C++11 requires a
  // full variadic template or C-style variadic function in order to accept a
  // variable number of arguments.  C-style variadic functions have no intrinsic
  // way of figuring out how many arguments they receive, so we have to use a
  // variadic template.
  //
  // The static_assert ensures that all arguments are actually the same type.
  template <typename T1, typename T2, typename... T>
  static inline constexpr T1 Do(T1 l, T2 r, T... rest) {
    // C++11 std::max is not constexpr, so we can't just call it.
    static_assert(::std::is_same<T1, T2>::value,
                  "Expected Do to be called with a proper intermediate type.");
    return Do(l < r ? r : l, rest...);
  }
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
