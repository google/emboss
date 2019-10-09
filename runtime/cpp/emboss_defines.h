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

// This header contains #defines that are used to control Emboss's generated
// code.
//
// These #defines are global, and *must* be defined the same way in every
// translation unit.  In particular, if you use `-D` (or your compiler's
// equivalent) to define some of them on the command line, you *must* pass the
// *exact* same definition when compiling *every* file that #includes any
// Emboss-generated or Emboss-related file, directly or indirectly.  Failure to
// do so will lead to ODR violations and strange behavior.
//
// Rather than using the command line, the Emboss authors recommend that you
// insert an #include of a custom site_defines.h between the two markers below.
//
// If you are using [Copybara][1] to import Emboss into your environment, you
// can use a transform like:
//
//     core.replace(
//         before = '${start_of_line}// #include "MY_SITE_DEFINES.h"',
//         after = '${start_of_line}#include "MY_SITE_DEFINES.h"',
//         paths = ['public/emboss_defines.h'],
//         regex_groups = {
//             'start_of_line': '^',
//         },
//     ),
//
// [1]: https://github.com/google/copybara
//
// If you are using [Bazel][2], be sure to add a dependency from the
// //public:cpp_utils target to a target exporting your custom header:
//
//     core.replace(
//         before = '${leading_whitespace}# "//MY_SITE_DEFINES:TARGET",',
//         after = '${leading_whitespace}"//MY_SITE_DEFINES:TARGET",',
//         paths = ['public/BUILD'],
//         regex_groups = {
//             'leading_whitespace': '^ *',
//         },
//     ),
//
// [2]: https://bazel.build
#ifndef EMBOSS_RUNTIME_CPP_EMBOSS_DEFINES_H_
#define EMBOSS_RUNTIME_CPP_EMBOSS_DEFINES_H_

#include <cassert>

// START INSERT_INCLUDE_SITE_DEFINES_HERE
// #include "MY_SITE_DEFINES.h"
// END INSERT_INCLUDE_SITE_DEFINES_HERE

// EMBOSS_CHECK should abort the program if the given expression evaluates to
// false.
//
// By default, checks are only enabled on non-NDEBUG builds.  (Note that all
// translation units MUST be built with the same value of NDEBUG!)
#if !defined(EMBOSS_CHECK)
#define EMBOSS_CHECK(x) assert((x))
#define EMBOSS_CHECK_ABORTS (!(NDEBUG))
#endif  // !defined(EMBOSS_CHECK)

#if !defined(EMBOSS_CHECK_ABORTS)
#error "Custom EMBOSS_CHECK without EMBOSS_CHECK_ABORTS."
#endif  // !defined(EMBOSS_CHECK_ABORTS)

#if !defined(EMBOSS_CHECK_LE)
#define EMBOSS_CHECK_LE(x, y) EMBOSS_CHECK((x) <= (y))
#endif  // !defined(EMBOSS_CHECK_LE)

#if !defined(EMBOSS_CHECK_LT)
#define EMBOSS_CHECK_LT(x, y) EMBOSS_CHECK((x) < (y))
#endif  // !defined(EMBOSS_CHECK_LT)

#if !defined(EMBOSS_CHECK_GE)
#define EMBOSS_CHECK_GE(x, y) EMBOSS_CHECK((x) >= (y))
#endif  // !defined(EMBOSS_CHECK_GE)

#if !defined(EMBOSS_CHECK_GT)
#define EMBOSS_CHECK_GT(x, y) EMBOSS_CHECK((x) > (y))
#endif  // !defined(EMBOSS_CHECK_GT)

#if !defined(EMBOSS_CHECK_EQ)
#define EMBOSS_CHECK_EQ(x, y) EMBOSS_CHECK((x) == (y))
#endif  // !defined(EMBOSS_CHECK_EQ)

#if !defined(EMBOSS_CHECK_NE)
#define EMBOSS_CHECK_NE(x, y) EMBOSS_CHECK((x) == (y))
#endif  // !defined(EMBOSS_CHECK_NE)

// The EMBOSS_DCHECK macros, by default, work the same way as EMBOSS_CHECK;
// EMBOSS_DCHECK is used as an assert() for logic embedded in Emboss, where
// EMBOSS_CHECK is used to check preconditions on application logic.  Depending
// on how much you trust the correctness of Emboss itself, you may wish to
// disable EMBOSS_DCHECK in situations where you do not disable EMBOSS_CHECK.
#if !defined(EMBOSS_DCHECK)
#define EMBOSS_DCHECK(x) assert((x))
#define EMBOSS_DCHECK_ABORTS (!(NDEBUG))
#endif  // !defined(EMBOSS_DCHECK)

#if !defined(EMBOSS_DCHECK_ABORTS)
#error "Custom EMBOSS_DCHECK without EMBOSS_DCHECK_ABORTS."
#endif  // !defined(EMBOSS_DCHECK_ABORTS)

#if !defined(EMBOSS_DCHECK_LE)
#define EMBOSS_DCHECK_LE(x, y) EMBOSS_DCHECK((x) <= (y))
#endif  // !defined(EMBOSS_DCHECK_LE)

#if !defined(EMBOSS_DCHECK_LT)
#define EMBOSS_DCHECK_LT(x, y) EMBOSS_DCHECK((x) < (y))
#endif  // !defined(EMBOSS_DCHECK_LT)

#if !defined(EMBOSS_DCHECK_GE)
#define EMBOSS_DCHECK_GE(x, y) EMBOSS_DCHECK((x) >= (y))
#endif  // !defined(EMBOSS_DCHECK_GE)

#if !defined(EMBOSS_DCHECK_GT)
#define EMBOSS_DCHECK_GT(x, y) EMBOSS_DCHECK((x) > (y))
#endif  // !defined(EMBOSS_DCHECK_GT)

#if !defined(EMBOSS_DCHECK_EQ)
#define EMBOSS_DCHECK_EQ(x, y) EMBOSS_DCHECK((x) == (y))
#endif  // !defined(EMBOSS_DCHECK_EQ)

#if !defined(EMBOSS_DCHECK_NE)
#define EMBOSS_DCHECK_NE(x, y) EMBOSS_DCHECK((x) == (y))
#endif  // !defined(EMBOSS_DCHECK_NE)

// Technically, the mapping from pointers to integers is implementation-defined,
// but the standard states "[ Note: It is intended to be unsurprising to those
// who know the addressing structure of the underlying machine. - end note ],"
// so this should be a reasonably safe way to check that a pointer is aligned.
#if !defined(EMBOSS_DCHECK_POINTER_ALIGNMENT)
#define EMBOSS_DCHECK_POINTER_ALIGNMENT(p, align, offset)                  \
  EMBOSS_DCHECK_EQ(reinterpret_cast</**/ ::std::uintptr_t>((p)) % (align), \
                   (static_cast</**/ ::std::uintptr_t>((offset))))
#endif  // !defined(EMBOSS_DCHECK_POINTER_ALIGNMENT)

#if !defined(EMBOSS_CHECK_POINTER_ALIGNMENT)
#define EMBOSS_CHECK_POINTER_ALIGNMENT(p, align, offset)                  \
  EMBOSS_CHECK_EQ(reinterpret_cast</**/ ::std::uintptr_t>((p)) % (align), \
                  static_cast</**/ ::std::uintptr_t>((offset)))
#endif  // !defined(EMBOSS_CHECK_POINTER_ALIGNMENT)

// EMBOSS_NO_OPTIMIZATIONS is used to turn off all system-specific
// optimizations.  This is mostly intended for testing, but could be used if
// optimizations are causing problems.
#if !defined(EMBOSS_NO_OPTIMIZATIONS)
#if defined(__GNUC__)  // GCC and "compatible" compilers, such as Clang.

// GCC, Clang, and ICC only support two's-complement systems, so it is safe to
// assume two's-complement for those systems.  In particular, this means that
// static_cast<int>() will treat its argument as a two's-complement bit pattern,
// which means that it is reasonable to static_cast<int>(some_unsigned_value).
//
// TODO(bolms): Are there actually any non-archaic systems that use any integer
// types other than 2's-complement?
#if !defined(EMBOSS_SYSTEM_IS_TWOS_COMPLEMENT)
#define EMBOSS_SYSTEM_IS_TWOS_COMPLEMENT 1
#endif  // !defined(EMBOSS_SYSTEM_IS_TWOS_COMPLEMENT)

#if !defined(__INTEL_COMPILER)
// On systems with known host byte order, Emboss can always use memcpy to safely
// and relatively efficiently read and write values from and to memory.
// However, memcpy cannot assume that its pointers are aligned.  On common
// platforms, particularly x86, this almost never matters; however, on some
// systems this can add considerable overhead, as memcpy must either perform
// byte-by-byte copies or perform tests to determine pointer alignment and then
// dispatch to alignment-specific code.
//
// Platforms with no alignment restrictions:
//
// * x86 (except for a few SSE instructions like movdqa: see
//   http://pzemtsov.github.io/2016/11/06/bug-story-alignment-on-x86.html)
// * ARM systems with ARMv6 and later ISAs
// * High-end POWER-based systems
// * POWER-based systems with an alignment exception handler installed (but note
//   that emulated unaligned reads are *very* slow)
//
// Platforms with alignment restrictions:
//
// * MicroBlaze
// * Emscripten
// * Low-end bare-metal POWER-based systems
// * ARM systems with ARMv5 and earlier ISAs
// * x86 with the AC bit of EEFLAGS enabled (but note that this is never enabled
//   on any normal system, and, e.g., you will get crashes in glibc if you try
//   to enable it)
//
// The naive solution is to reinterpret_cast to a type like uint32_t, then read
// or write through that pointer; however, this can easily run afoul of C++'s
// type aliasing rules and result in undefined behavior.
//
// On GCC, there is a solution to this: use the "__may_alias__" type attribute,
// which essentially forces the type to have the same aliasing rules as char;
// i.e., it is safe to read and write through a pointer derived from
// reinterpret_cast<T __attribute__((__may_alias__)) *>, just as it is safe to
// read and write through a pointer derived from reinterpret_cast<char *>.
//
// Note that even though ICC pretends to be compatible with GCC by defining
// __GNUC__, it does *not* appear to support the __may_alias__ attribute.
// (TODO(bolms): verify this if/when Emboss explicitly supports ICC.)
//
// Note the lack of parentheses around 't' in the expansion: unfortunately,
// GCC's attribute syntax disallows parentheses in that particular position.
#if !defined(EMBOSS_ALIAS_SAFE_POINTER_CAST)
#define EMBOSS_ALIAS_SAFE_POINTER_CAST(t, x) \
  reinterpret_cast<t __attribute__((__may_alias__)) *>((x))
#endif  // !defined(EMBOSS_LITTLE_ENDIAN_TO_NATIVE)
#endif  // !defined(__INTEL_COMPILER)

// GCC supports __BYTE_ORDER__ of __ORDER_LITTLE_ENDIAN__, __ORDER_BIG_ENDIAN__,
// and __ORDER_PDP_ENDIAN__.  Since all available test systems are
// __ORDER_LITTLE_ENDIAN__, only little-endian hosts get optimized code paths;
// however, big-endian support ought to be trivial to add.
//
// There are no plans to support PDP-endian systems.
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
// EMBOSS_LITTLE_ENDIAN_TO_NATIVE and EMBOSS_BIG_ENDIAN_TO_NATIVE can be used to
// fix up integers after a little- or big-endian value has been memcpy'ed into
// them.
//
// On little-endian systems, no fixup is needed for little-endian sources, but
// big-endian sources require a byte swap.
#if !defined(EMBOSS_LITTLE_ENDIAN_TO_NATIVE)
#define EMBOSS_LITTLE_ENDIAN_TO_NATIVE(x) (x)
#endif  // !defined(EMBOSS_LITTLE_ENDIAN_TO_NATIVE)

#if !defined(EMBOSS_NATIVE_TO_LITTLE_ENDIAN)
#define EMBOSS_NATIVE_TO_LITTLE_ENDIAN(x) (x)
#endif  // !defined(EMBOSS_NATIVE_TO_LITTLE_ENDIAN)

#if !defined(EMBOSS_BIG_ENDIAN_TO_NATIVE)
#define EMBOSS_BIG_ENDIAN_TO_NATIVE(x) (::emboss::support::ByteSwap((x)))
#endif  // !defined(EMBOSS_BIG_ENDIAN_TO_NATIVE)

#if !defined(EMBOSS_NATIVE_TO_BIG_ENDIAN)
#define EMBOSS_NATIVE_TO_BIG_ENDIAN(x) (::emboss::support::ByteSwap((x)))
#endif  // !defined(EMBOSS_NATIVE_TO_BIG_ENDIAN)

// TODO(bolms): Find a way to test on a big-endian architecture, and add support
// for __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
#endif  // __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__

// Prior to version 4.8, __builtin_bswap16 was not available on all platforms.
// https://gcc.gnu.org/bugzilla/show_bug.cgi?id=52624
//
// Clang pretends to be an earlier GCC, but does support __builtin_bswap16.
// Clang recommends using __has_builtin(__builtin_bswap16), but unfortunately
// that fails to compile on GCC, even with defined(__has_builtin) &&
// __has_builtin(__builtin_bswap16), so instead Emboss just checks for
// defined(__clang__).
#if !defined(EMBOSS_BYTESWAP16)
#if __GNUC__ > 4 || (__GNUC__ == 4 && __GNUC_MINOR__ >= 8) || defined(__clang__)
#define EMBOSS_BYTESWAP16(x) __builtin_bswap16((x))
#endif  // __GNUC__ > 4 || (__GNUC__ == 4 && __GNUC_MINOR__ >= 8)
#endif  // !defined(EMBOSS_BYTESWAP16)

#if !defined(EMBOSS_BYTESWAP32)
#define EMBOSS_BYTESWAP32(x) __builtin_bswap32((x))
#endif  // !defined(EMBOSS_BYTESWAP32)

#if !defined(EMBOSS_BYTESWAP64)
#define EMBOSS_BYTESWAP64(x) __builtin_bswap64((x))
#endif  // !defined(EMBOSS_BYTESWAP64)

#endif  // defined(__GNUC__)
#endif  // !defined(EMBOSS_NO_OPTIMIZATIONS)

#if !defined(EMBOSS_SYSTEM_IS_TWOS_COMPLEMENT)
#define EMBOSS_SYSTEM_IS_TWOS_COMPLEMENT 0
#endif  // !defined(EMBOSS_SYSTEM_IS_TWOS_COMPLEMENT)

#endif  // EMBOSS_RUNTIME_CPP_EMBOSS_DEFINES_H_
