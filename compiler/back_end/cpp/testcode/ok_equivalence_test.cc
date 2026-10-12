// Copyright 2026 Google LLC
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

// Equivalence tests for the optimized structure Ok() method.
//
// When several conditional fields share a discriminant, the C++ back end
// emits their Ok() checks as a switch on that discriminant instead of a
// per-field sequence of has_${field}() tests, and an arm whose existence
// condition carries predicates beyond the discriminant equality gates its
// field check on those residual predicates alone.  There is no generator
// option to emit the unoptimized form, so these tests pin the optimized
// Ok() to an independent reference that follows the definition directly:
// the structure is complete, and for every field the existence condition is
// Known and, when the field is present, the field itself is Ok().
//
// Each structure is checked for every buffer length from zero up to its full
// size, so that a discriminant that lies beyond the end of the buffer, or
// that is itself absent, is exercised alongside the ordinary shapes.  The
// bytes that existence conditions read (the discriminant and any field in a
// residual) take every value; the remaining bytes belong to plain UInt
// fields, whose Ok() does not depend on their contents, and are set to two
// extreme fill patterns.  The four-byte discriminants in many_conditionals.emb
// are sampled as documented at each test; the sampling always covers every
// switch arm, values that match no arm, and every length.
#include <stdint.h>

#include <cstddef>
#include <sstream>
#include <string>

#include "gtest/gtest.h"
#include "testdata/condition.emb.h"
#include "testdata/many_conditionals.emb.h"

namespace emboss {
namespace test {
namespace {

// The reference condition for a single field, from the definition of Ok():
// an Unknown existence condition makes the structure not Ok(); a present
// field must be Ok(); an absent field does not matter.
#define EMBOSS_TEST_FIELD_OK(view, field) \
  ((view).has_##field().Known() &&        \
   (!(view).has_##field().ValueOrDefault() || (view).field().Ok()))

::std::string DescribeBuffer(const ::std::uint8_t* bytes,
                             ::std::size_t length) {
  ::std::ostringstream out;
  out << "length " << length << ", bytes {";
  for (::std::size_t i = 0; i < length; ++i) {
    out << (i == 0 ? "" : ", ") << static_cast<unsigned>(bytes[i]);
  }
  out << "}";
  return out.str();
}

// Compares Ok() against the reference for one buffer.  The first few
// mismatches are reported individually; the rest are only counted.
template <typename MakeView, typename Reference>
void CheckOneBuffer(const char* schema, MakeView make_view, Reference reference,
                    const ::std::uint8_t* bytes, ::std::size_t length,
                    ::std::uint64_t* checked, int* mismatches) {
  const auto view = make_view(bytes, length);
  const bool actual = view.Ok();
  const bool expected = reference(view);
  ++*checked;
  if (actual == expected) return;
  if (++*mismatches <= 10) {
    ADD_FAILURE() << schema << ": Ok() is " << actual
                  << " but the reference is " << expected << " for "
                  << DescribeBuffer(bytes, length);
  }
}

// Number of buffers enumerated by ForEveryBuffer<kSignificant, kMaxLength>.
constexpr ::std::uint64_t Pow256(::std::size_t n) {
  return n == 0 ? 1 : 256 * Pow256(n - 1);
}
constexpr ::std::uint64_t ExhaustivePrefixCount(::std::size_t significant) {
  return significant == 0
             ? 1
             : Pow256(significant) + ExhaustivePrefixCount(significant - 1);
}
constexpr ::std::size_t kFillPatternCount = 2;
constexpr ::std::uint64_t ExhaustiveBufferCount(::std::size_t significant,
                                                ::std::size_t max_length) {
  return ExhaustivePrefixCount(significant) +
         (max_length - significant) * kFillPatternCount * Pow256(significant);
}

// Fill values for bytes that do not take part in any existence condition.
// Those fields are plain UInts, whose Ok() does not depend on their value,
// so a pair of extreme patterns is enough to catch an accidental dependence.
constexpr ::std::uint8_t kFillPatterns[kFillPatternCount] = {0x00, 0xff};

// Checks every buffer of every length in [0, kMaxLength].  The first
// kSignificant bytes -- the ones that existence conditions read -- take
// every value: 256^length buffers for each length up to kSignificant.  For
// longer buffers the bytes past kSignificant are set to each fill pattern in
// turn, so every length is still checked against every significant prefix.
template <::std::size_t kSignificant, ::std::size_t kMaxLength,
          typename MakeView, typename Reference>
void ForEveryBuffer(const char* schema, MakeView make_view,
                    Reference reference) {
  static_assert(kSignificant <= kMaxLength, "prefix longer than buffer");
  ::std::uint8_t bytes[kMaxLength + 1] = {0};
  ::std::uint64_t checked = 0;
  int mismatches = 0;
  for (::std::size_t length = 0; length <= kMaxLength; ++length) {
    const ::std::size_t varied = length < kSignificant ? length : kSignificant;
    const ::std::size_t fills = length > kSignificant ? kFillPatternCount : 1;
    for (::std::size_t f = 0; f < fills; ++f) {
      for (::std::size_t i = 0; i < varied; ++i) bytes[i] = 0;
      for (::std::size_t i = varied; i < length; ++i) {
        bytes[i] = kFillPatterns[f];
      }
      for (;;) {
        CheckOneBuffer(schema, make_view, reference, bytes, length, &checked,
                       &mismatches);
        ::std::size_t i = 0;
        while (i < varied && ++bytes[i] == 0) ++i;
        if (i == varied) break;
      }
    }
  }
  EXPECT_EQ(0, mismatches) << schema;
  EXPECT_EQ(ExhaustiveBufferCount(kSignificant, kMaxLength), checked) << schema;
}

void WriteLittleEndian32(::std::uint8_t* bytes, ::std::uint32_t value) {
  for (int i = 0; i < 4; ++i)
    bytes[i] = static_cast<::std::uint8_t>(value >> (8 * i));
}

// Checks a prepared buffer at every length in [0, kSize].
template <::std::size_t kSize, typename MakeView, typename Reference>
void ForEveryLength(const char* schema, MakeView make_view, Reference reference,
                    const ::std::uint8_t* bytes, ::std::uint64_t* checked,
                    int* mismatches) {
  for (::std::size_t length = 0; length <= kSize; ++length) {
    CheckOneBuffer(schema, make_view, reference, bytes, length, checked,
                   mismatches);
  }
}

// Discriminant values for the four-byte `tag` fields in many_conditionals.emb.
// The low byte takes every value, which covers all 100 arms of
// LargeConditionals and OuterGuardedUnion, the gaps between arms, and the
// values just past the last arm.  The upper three bytes take zero (so the
// value is the low byte itself), one (a value above every arm whose low
// byte still collides with an arm) and all-ones (the top of the range).
constexpr ::std::uint32_t kTagHighParts[] = {0x00000000u, 0x00000100u,
                                             0xffffff00u};

// ---------------------------------------------------------------------------
// condition.emb: conditional discriminants.  Byte 0 is `outer` and byte 1 is
// `tag`; both are exhaustive.  The remaining bytes (`a`/`b`, and `tail` in
// DominatedBareDiscriminant) are payload and take the fill patterns.
// ---------------------------------------------------------------------------

// Every arm carries the residual `outer == 1`, so the switch is demoted to
// per-field checks.  A buffer with `outer != 1` is Ok() even though `tag` is
// absent, and a one-byte buffer with `outer == 1` is not Ok() because `tag`
// cannot be read.
TEST(OkEquivalence, ResidualConditionalDiscriminant) {
  ForEveryBuffer<2, 3>(
      "ResidualConditionalDiscriminant",
      [](const ::std::uint8_t* bytes, ::std::size_t length) {
        return MakeResidualConditionalDiscriminantView(bytes, length);
      },
      [](const ResidualConditionalDiscriminantView& view) {
        return view.IsComplete() && EMBOSS_TEST_FIELD_OK(view, outer) &&
               EMBOSS_TEST_FIELD_OK(view, tag) &&
               EMBOSS_TEST_FIELD_OK(view, a) && EMBOSS_TEST_FIELD_OK(view, b);
      });
}

// Bare arms on a conditional discriminant: when `tag` is absent, has_a() and
// has_b() are Unknown and the structure is not Ok().
TEST(OkEquivalence, BareConditionalDiscriminant) {
  ForEveryBuffer<2, 3>(
      "BareConditionalDiscriminant",
      [](const ::std::uint8_t* bytes, ::std::size_t length) {
        return MakeBareConditionalDiscriminantView(bytes, length);
      },
      [](const BareConditionalDiscriminantView& view) {
        return view.IsComplete() && EMBOSS_TEST_FIELD_OK(view, outer) &&
               EMBOSS_TEST_FIELD_OK(view, tag) &&
               EMBOSS_TEST_FIELD_OK(view, a) && EMBOSS_TEST_FIELD_OK(view, b);
      });
}

// Like BareConditionalDiscriminant with an unconditional `tail` that keeps
// the size Known, so IsComplete() can be true while Ok() is false.
TEST(OkEquivalence, DominatedBareDiscriminant) {
  ForEveryBuffer<2, 4>(
      "DominatedBareDiscriminant",
      [](const ::std::uint8_t* bytes, ::std::size_t length) {
        return MakeDominatedBareDiscriminantView(bytes, length);
      },
      [](const DominatedBareDiscriminantView& view) {
        return view.IsComplete() && EMBOSS_TEST_FIELD_OK(view, outer) &&
               EMBOSS_TEST_FIELD_OK(view, tag) &&
               EMBOSS_TEST_FIELD_OK(view, a) && EMBOSS_TEST_FIELD_OK(view, b) &&
               EMBOSS_TEST_FIELD_OK(view, tail);
      });
}

// Disjunction arms (`tag == 0 || tag == 1`) with a residual.
TEST(OkEquivalence, DisjunctionConditionalDiscriminant) {
  ForEveryBuffer<2, 3>(
      "DisjunctionConditionalDiscriminant",
      [](const ::std::uint8_t* bytes, ::std::size_t length) {
        return MakeDisjunctionConditionalDiscriminantView(bytes, length);
      },
      [](const DisjunctionConditionalDiscriminantView& view) {
        return view.IsComplete() && EMBOSS_TEST_FIELD_OK(view, outer) &&
               EMBOSS_TEST_FIELD_OK(view, tag) &&
               EMBOSS_TEST_FIELD_OK(view, a) && EMBOSS_TEST_FIELD_OK(view, b);
      });
}

// A single residual arm, which the generator demotes as too small for a
// switch.
TEST(OkEquivalence, SingleEntryConditionalDiscriminant) {
  ForEveryBuffer<2, 3>(
      "SingleEntryConditionalDiscriminant",
      [](const ::std::uint8_t* bytes, ::std::size_t length) {
        return MakeSingleEntryConditionalDiscriminantView(bytes, length);
      },
      [](const SingleEntryConditionalDiscriminantView& view) {
        return view.IsComplete() && EMBOSS_TEST_FIELD_OK(view, outer) &&
               EMBOSS_TEST_FIELD_OK(view, tag) && EMBOSS_TEST_FIELD_OK(view, a);
      });
}

// Enum-typed discriminant with residual arms.
TEST(OkEquivalence, EnumConditionalDiscriminant) {
  ForEveryBuffer<2, 3>(
      "EnumConditionalDiscriminant",
      [](const ::std::uint8_t* bytes, ::std::size_t length) {
        return MakeEnumConditionalDiscriminantView(bytes, length);
      },
      [](const EnumConditionalDiscriminantView& view) {
        return view.IsComplete() && EMBOSS_TEST_FIELD_OK(view, outer) &&
               EMBOSS_TEST_FIELD_OK(view, tag) &&
               EMBOSS_TEST_FIELD_OK(view, a) && EMBOSS_TEST_FIELD_OK(view, b);
      });
}

// `if false:` arms are never present and never make the structure not Ok().
// These structures have no discriminant; both bytes are enumerated anyway
// since they are cheap.
TEST(OkEquivalence, AlwaysFalseCondition) {
  ForEveryBuffer<2, 2>(
      "AlwaysFalseCondition",
      [](const ::std::uint8_t* bytes, ::std::size_t length) {
        return MakeAlwaysFalseConditionView(bytes, length);
      },
      [](const AlwaysFalseConditionView& view) {
        return view.IsComplete() && EMBOSS_TEST_FIELD_OK(view, x) &&
               EMBOSS_TEST_FIELD_OK(view, xc);
      });
}

TEST(OkEquivalence, OnlyAlwaysFalseCondition) {
  ForEveryBuffer<2, 2>(
      "OnlyAlwaysFalseCondition",
      [](const ::std::uint8_t* bytes, ::std::size_t length) {
        return MakeOnlyAlwaysFalseConditionView(bytes, length);
      },
      [](const OnlyAlwaysFalseConditionView& view) {
        return view.IsComplete() && EMBOSS_TEST_FIELD_OK(view, xc);
      });
}

// ---------------------------------------------------------------------------
// many_conditionals.emb: four-byte discriminants, sampled as documented
// above (kTagHighParts, kFillPatterns), every length.
// ---------------------------------------------------------------------------

// Expands X(n) for each of the 100 arms (tag == 0 through tag == 99) of
// LargeConditionals and OuterGuardedUnion.
// clang-format off
#define EMBOSS_TEST_FOR_EACH_ARM(X) \
  X(0) X(1) X(2) X(3) X(4) X(5) X(6) X(7) X(8) X(9) \
  X(10) X(11) X(12) X(13) X(14) X(15) X(16) X(17) X(18) X(19) \
  X(20) X(21) X(22) X(23) X(24) X(25) X(26) X(27) X(28) X(29) \
  X(30) X(31) X(32) X(33) X(34) X(35) X(36) X(37) X(38) X(39) \
  X(40) X(41) X(42) X(43) X(44) X(45) X(46) X(47) X(48) X(49) \
  X(50) X(51) X(52) X(53) X(54) X(55) X(56) X(57) X(58) X(59) \
  X(60) X(61) X(62) X(63) X(64) X(65) X(66) X(67) X(68) X(69) \
  X(70) X(71) X(72) X(73) X(74) X(75) X(76) X(77) X(78) X(79) \
  X(80) X(81) X(82) X(83) X(84) X(85) X(86) X(87) X(88) X(89) \
  X(90) X(91) X(92) X(93) X(94) X(95) X(96) X(97) X(98) X(99)
// clang-format on

template <typename View>
bool LargeConditionalsReference(const View& view) {
  if (!view.IsComplete() || !EMBOSS_TEST_FIELD_OK(view, tag)) return false;
#define EMBOSS_TEST_ARM(n) \
  if (!EMBOSS_TEST_FIELD_OK(view, f##n)) return false;
  EMBOSS_TEST_FOR_EACH_ARM(EMBOSS_TEST_ARM)
#undef EMBOSS_TEST_ARM
  return true;
}

template <typename View>
bool OuterGuardedUnionReference(const View& view) {
  if (!view.IsComplete() || !EMBOSS_TEST_FIELD_OK(view, outer) ||
      !EMBOSS_TEST_FIELD_OK(view, tag)) {
    return false;
  }
#define EMBOSS_TEST_ARM(n) \
  if (!EMBOSS_TEST_FIELD_OK(view, g##n)) return false;
  EMBOSS_TEST_FOR_EACH_ARM(EMBOSS_TEST_ARM)
#undef EMBOSS_TEST_ARM
  return true;
}

// A flat union with 100 bare arms: the control case, with no residuals.
// Buffer: tag (4 bytes), payload (4 bytes).
TEST(OkEquivalence, LargeConditionals) {
  const char* const schema = "LargeConditionals";
  const auto make_view = [](const ::std::uint8_t* bytes, ::std::size_t length) {
    return MakeLargeConditionalsView(bytes, length);
  };
  ::std::uint8_t bytes[8] = {0};
  ::std::uint64_t checked = 0;
  int mismatches = 0;
  for (::std::uint8_t fill : kFillPatterns) {
    for (int i = 4; i < 8; ++i) bytes[i] = fill;
    for (::std::uint32_t high : kTagHighParts) {
      for (::std::uint32_t low = 0; low < 256; ++low) {
        WriteLittleEndian32(bytes, high | low);
        ForEveryLength<8>(schema, make_view,
                          LargeConditionalsReference<LargeConditionalsView>,
                          bytes, &checked, &mismatches);
      }
    }
  }
  EXPECT_EQ(0, mismatches);
  EXPECT_EQ(kFillPatternCount * 3u * 256u * 9u, checked);
}

// Multi-label arms (`tag == 0 || tag == 1 || tag == 2`, up to `tag == 300`).
// The low two bytes of `tag` run over 0..1023, which covers every label and
// the gaps; the high two bytes take zero, one and all-ones.
TEST(OkEquivalence, DisjunctionConditionals) {
  const char* const schema = "DisjunctionConditionals";
  const auto make_view = [](const ::std::uint8_t* bytes, ::std::size_t length) {
    return MakeDisjunctionConditionalsView(bytes, length);
  };
  const auto reference = [](const DisjunctionConditionalsView& view) {
    return view.IsComplete() && EMBOSS_TEST_FIELD_OK(view, tag) &&
           EMBOSS_TEST_FIELD_OK(view, shared_low) &&
           EMBOSS_TEST_FIELD_OK(view, shared_high) &&
           EMBOSS_TEST_FIELD_OK(view, shared_far);
  };
  constexpr ::std::uint32_t kHighParts[] = {0x00000000u, 0x00010000u,
                                            0xffff0000u};
  ::std::uint8_t bytes[8] = {0};
  ::std::uint64_t checked = 0;
  int mismatches = 0;
  for (::std::uint8_t fill : kFillPatterns) {
    for (int i = 4; i < 8; ++i) bytes[i] = fill;
    for (::std::uint32_t high : kHighParts) {
      for (::std::uint32_t low = 0; low < 1024; ++low) {
        WriteLittleEndian32(bytes, high | low);
        ForEveryLength<8>(schema, make_view, reference, bytes, &checked,
                          &mismatches);
      }
    }
  }
  EXPECT_EQ(0, mismatches);
  EXPECT_EQ(kFillPatternCount * 3u * 1024u * 9u, checked);
}

// 100 arms that each carry the residual `outer == 1`, with an always-present
// `outer` so the discriminant is provably Known and the switch survives.
// Buffer: outer (4 bytes), tag (4 bytes), payload (4 bytes).  `outer` takes
// the residual's value, its neighbours, values whose low byte is 1 but which
// are not 1, and the top of the range.
TEST(OkEquivalence, OuterGuardedUnion) {
  const char* const schema = "OuterGuardedUnion";
  const auto make_view = [](const ::std::uint8_t* bytes, ::std::size_t length) {
    return MakeOuterGuardedUnionView(bytes, length);
  };
  constexpr ::std::uint32_t kOuterValues[] = {
      0u, 1u, 2u, 0x00000101u, 0x01000001u, 0xffffffffu};
  ::std::uint8_t bytes[12] = {0};
  ::std::uint64_t checked = 0;
  int mismatches = 0;
  for (::std::uint8_t fill : kFillPatterns) {
    for (int i = 8; i < 12; ++i) bytes[i] = fill;
    for (::std::uint32_t outer : kOuterValues) {
      WriteLittleEndian32(bytes, outer);
      for (::std::uint32_t high : kTagHighParts) {
        for (::std::uint32_t low = 0; low < 256; ++low) {
          WriteLittleEndian32(bytes + 4, high | low);
          ForEveryLength<12>(schema, make_view,
                             OuterGuardedUnionReference<OuterGuardedUnionView>,
                             bytes, &checked, &mismatches);
        }
      }
    }
  }
  EXPECT_EQ(0, mismatches);
  EXPECT_EQ(kFillPatternCount * 6u * 3u * 256u * 13u, checked);
}

#undef EMBOSS_TEST_FOR_EACH_ARM
#undef EMBOSS_TEST_FIELD_OK

}  // namespace
}  // namespace test
}  // namespace emboss
