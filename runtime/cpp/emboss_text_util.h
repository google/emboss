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

// This header contains functionality related to Emboss text output.
#ifndef EMBOSS_RUNTIME_CPP_EMBOSS_TEXT_UTIL_H_
#define EMBOSS_RUNTIME_CPP_EMBOSS_TEXT_UTIL_H_

#include <array>
#include <climits>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <limits>
#include <sstream>
#include <string>
#include <vector>

#include "runtime/cpp/emboss_defines.h"

namespace emboss {

// TextOutputOptions are used to configure text output.  Typically, one can just
// use a default TextOutputOptions() (for compact output) or MultilineText()
// (for reasonable formatted output).
class TextOutputOptions final {
 public:
  TextOutputOptions() = default;

  TextOutputOptions PlusOneIndent() const {
    TextOutputOptions result = *this;
    result.current_indent_ += indent();
    return result;
  }

  TextOutputOptions Multiline(bool new_value) const {
    TextOutputOptions result = *this;
    result.multiline_ = new_value;
    return result;
  }

  TextOutputOptions WithIndent(::std::string new_value) const {
    TextOutputOptions result = *this;
    result.indent_ = ::std::move(new_value);
    return result;
  }

  TextOutputOptions WithComments(bool new_value) const {
    TextOutputOptions result = *this;
    result.comments_ = new_value;
    return result;
  }

  TextOutputOptions WithDigitGrouping(bool new_value) const {
    TextOutputOptions result = *this;
    result.digit_grouping_ = new_value;
    return result;
  }

  TextOutputOptions WithNumericBase(uint8_t new_value) const {
    TextOutputOptions result = *this;
    result.numeric_base_ = new_value;
    return result;
  }

  TextOutputOptions WithAllowPartialOutput(bool new_value) const {
    TextOutputOptions result = *this;
    result.allow_partial_output_ = new_value;
    return result;
  }

  ::std::string current_indent() const { return current_indent_; }
  ::std::string indent() const { return indent_; }
  bool multiline() const { return multiline_; }
  bool digit_grouping() const { return digit_grouping_; }
  bool comments() const { return comments_; }
  ::std::uint8_t numeric_base() const { return numeric_base_; }
  bool allow_partial_output() const { return allow_partial_output_; }

 private:
  ::std::string indent_;
  ::std::string current_indent_;
  bool comments_ = false;
  bool multiline_ = false;
  bool digit_grouping_ = false;
  bool allow_partial_output_ = false;
  ::std::uint8_t numeric_base_ = 10;
};

namespace support {

// TextOutputStream puts a stream-like interface onto a std::string, for use by
// DumpToTextStream.  It is used by UpdateFromText().
class TextOutputStream final {
 public:
  inline explicit TextOutputStream() = default;

  inline void Write(const ::std::string &text) {
    text_.write(text.data(), text.size());
  }

  inline void Write(const char *text) { text_.write(text, strlen(text)); }

  inline void Write(const char c) { text_.put(c); }

  inline ::std::string Result() { return text_.str(); }

 private:
  ::std::ostringstream text_;
};

// DecodeInteger decodes an integer from a string.  This is very similar to the
// many, many existing integer decode routines in the world, except that a) it
// accepts integers in any Emboss format, and b) it can run in environments that
// do not support std::istream or Google's number conversion routines.
//
// Ideally, this would be replaced by someone else's code.
template <class IntType>
bool DecodeInteger(const ::std::string &text, IntType *result) {
  IntType accumulator = 0;
  IntType base = 10;
  bool negative = false;
  unsigned offset = 0;
  if (::std::is_signed<IntType>::value && text.size() >= 1 + offset &&
      text[offset] == '-') {
    negative = true;
    offset += 1;
  }
  if (text.size() >= 2 + offset && text[offset] == '0') {
    if (text[offset + 1] == 'x' || text[offset + 1] == 'X') {
      base = 16;
      offset += 2;
    } else if (text[offset + 1] == 'b' || text[offset + 1] == 'B') {
      base = 2;
      offset += 2;
    }
  }
  // "", "0x", "0b", "-", "-0x", and "-0b" are not valid numbers.
  if (offset == text.size()) return false;
  for (; offset < text.size(); ++offset) {
    char c = text[offset];
    IntType digit = 0;
    if (c == '_') {
      if (offset == 0) {
        return false;
      }
      continue;
    } else if (c >= '0' && c <= '9') {
      digit = c - '0';
    } else if (c >= 'A' && c <= 'F') {
      digit = c - 'A' + 10;
    } else if (c >= 'a' && c <= 'f') {
      digit = c - 'a' + 10;
    } else {
      return false;
    }
    if (digit >= base) {
      return false;
    }
    if (negative) {
      if (accumulator <
          (::std::numeric_limits<IntType>::min() + digit) / base) {
        return false;
      }
      accumulator = accumulator * base - digit;
    } else {
      if (accumulator >
          (::std::numeric_limits<IntType>::max() - digit) / base) {
        return false;
      }
      accumulator = accumulator * base + digit;
    }
  }
  *result = accumulator;
  return true;
}

template <class Stream>
bool DiscardWhitespace(Stream *stream) {
  char c;
  bool in_comment = false;
  do {
    if (!stream->Read(&c)) return true;
    if (c == '#') in_comment = true;
    if (c == '\r' || c == '\n') in_comment = false;
  } while (in_comment || c == ' ' || c == '\t' || c == '\n' || c == '\r');
  return stream->Unread(c);
}

template <class Stream>
bool ReadToken(Stream *stream, ::std::string *token) {
  ::std::vector<char> result;
  char c;
  if (!DiscardWhitespace(stream)) return false;
  if (!stream->Read(&c)) {
    *token = "";
    return true;
  }

  const char *const punctuation = ":{}[],";
  if (strchr(punctuation, c) != nullptr) {
    *token = ::std::string(1, c);
    return true;
  } else {
    // TODO(bolms): Only allow alphanumeric characters here?
    do {
      result.push_back(c);
      if (!stream->Read(&c)) {
        *token = ::std::string(&result[0], result.size());
        return true;
      }
    } while (c != ' ' && c != '\t' && c != '\n' && c != '\r' && c != '#' &&
             strchr(punctuation, c) == nullptr);
    if (!stream->Unread(c)) return false;
    *token = ::std::string(&result[0], result.size());
    return true;
  }
}

template <class Stream, class View>
bool ReadIntegerFromTextStream(View *view, Stream *stream) {
  ::std::string token;
  if (!::emboss::support::ReadToken(stream, &token)) return false;
  if (token.empty()) return false;
  typename View::ValueType value;
  if (!::emboss::support::DecodeInteger(token, &value)) return false;
  return view->TryToWrite(value);
}

// WriteIntegerToTextStream encodes the given value in base 2, 10, or 16, with
// or without digit group separators ('_'), and then calls stream->Write() with
// a char * argument that is a C-style null-terminated string of the encoded
// number.
//
// As with DecodeInteger, above, it would be nice to be able to replace this
// with someone else's code, but I (bolms@) was unable to find anything in
// standard C++ that would encode numbers in binary, nothing that would add
// digit separators to hex numbers, and nothing that would use '_' for digit
// separators.
template <class Stream, typename IntegralType>
void WriteIntegerToTextStream(IntegralType value, Stream *stream,
                              ::std::uint8_t base, bool digit_grouping) {
  static_assert(::std::numeric_limits<
                    typename ::std::remove_cv<IntegralType>::type>::is_integer,
                "WriteIntegerToTextStream only supports integer types.");
  static_assert(
      !::std::is_same<bool,
                      typename ::std::remove_cv<IntegralType>::type>::value,
      "WriteIntegerToTextStream only supports integer types.");
  EMBOSS_CHECK(base == 10 || base == 2 || base == 16);
  const char *const digits = "0123456789abcdef";
  const int grouping = base == 10 ? 3 : base == 16 ? 4 : 8;
  // The maximum size 32-bit number is -2**31, which is:
  //
  // -0b10000000_00000000_00000000_00000000  (38 chars)
  // -2_147_483_648  (14 chars)
  // -0x8000_0000  (12 chars)
  //
  // Likewise, the maximum size 8-bit number is -128, which is:
  // -0b10000000  (11 chars)
  // -128  (4 chars)
  // -0x80  (5 chars)
  //
  // Binary with separators is always the longest value: 9 chars per 8 bits,
  // minus 1 char for the '_' that does not appear at the front of the number,
  // plus 2 chars for "0b", plus 1 char for '-', plus 1 extra char for the
  // trailing '\0', which is (sizeof value) * CHAR_BIT * 9 / 8 - 1 + 2 + 1 + 1.
  const int buffer_size = (sizeof value) * CHAR_BIT * 9 / 8 + 3;
  char buffer[buffer_size];
  buffer[buffer_size - 1] = '\0';
  int next_char = buffer_size - 2;
  if (value == 0) {
    EMBOSS_DCHECK_GE(next_char, 0);
    buffer[next_char] = digits[0];
    --next_char;
  }
  int sign = value < 0 ? -1 : 1;
  int digit_count = 0;
  auto buffer_char = [&](char c) {
    EMBOSS_DCHECK_GE(next_char, 0);
    buffer[next_char] = c;
    --next_char;
  };
  if (value < 0) {
    if (value == ::std::numeric_limits<decltype(value)>::lowest()) {
      // The minimum negative two's-complement value has no corresponding
      // positive value, so 'value = -value' is not useful in that case.
      // Instead, we do some trickery to buffer the lowest-order digit here.
      auto digit = -(value + 1) % base + 1;
      value = -(value + 1) / base;
      if (digit == base) {
        digit = 0;
        ++value;
      }
      buffer_char(digits[digit]);
      ++digit_count;
    } else {
      value = -value;
    }
  }
  while (value > 0) {
    if (digit_count && digit_count % grouping == 0 && digit_grouping) {
      buffer_char('_');
    }
    buffer_char(digits[value % base]);
    value /= base;
    ++digit_count;
  }
  if (base == 16) {
    buffer_char('x');
    buffer_char('0');
  } else if (base == 2) {
    buffer_char('b');
    buffer_char('0');
  }
  if (sign < 0) {
    buffer_char('-');
  }

  stream->Write(buffer + 1 + next_char);
}

// Writes an integer value in the base given in options, plus an optional
// comment with the same value in a second base.  This is used for the common
// output format of IntView, UIntView, and BcdView.
template <class Stream, class View>
void WriteIntegerViewToTextStream(View *view, Stream *stream,
                                  const TextOutputOptions &options) {
  WriteIntegerToTextStream(view->Read(), stream, options.numeric_base(),
                           options.digit_grouping());
  if (options.comments()) {
    stream->Write("  # ");
    WriteIntegerToTextStream(view->Read(), stream,
                             options.numeric_base() == 10 ? 16 : 10,
                             options.digit_grouping());
  }
}

template <class Stream, class View>
bool ReadBooleanFromTextStream(View *view, Stream *stream) {
  ::std::string token;
  if (!::emboss::support::ReadToken(stream, &token)) return false;
  if (token == "true") {
    return view->TryToWrite(true);
  } else if (token == "false") {
    return view->TryToWrite(false);
  }
  // TODO(bolms): Provide a way to get an error message on parse failure.
  return false;
}

// The TextOutputOptions parameter is present so that it can be passed in by
// generated code that uses the same form for WriteBooleanViewToTextStream,
// WriteIntegerViewToTextStream, and WriteEnumViewToTextStream.
template <class Stream, class View>
void WriteBooleanViewToTextStream(View *view, Stream *stream,
                                  const TextOutputOptions &) {
  if (view->Read()) {
    stream->Write("true");
  } else {
    stream->Write("false");
  }
}

// FloatConstants holds various masks for working with IEEE754-compatible
// floating-point values at a bit level.  These are mostly used here to
// implement text format for NaNs, preserving the NaN payload so that the text
// format can (in theory) provide a bit-exact round-trip through the text
// format.
template <class Float>
struct FloatConstants;

template <>
struct FloatConstants<float> {
  static_assert(sizeof(float) == 4, "Emboss requires 32-bit float.");
  using MatchingIntegerType = ::std::uint32_t;
  static constexpr MatchingIntegerType kMantissaMask() { return 0x7fffffU; }
  static constexpr MatchingIntegerType kExponentMask() { return 0x7f800000U; }
  static constexpr MatchingIntegerType kSignMask() { return 0x80000000U; }
  static constexpr int kPrintfPrecision() { return 9; }
  static constexpr const char *kScanfFormat() { return "%f%n"; }
};

template <>
struct FloatConstants<double> {
  static_assert(sizeof(double) == 8, "Emboss requires 64-bit double.");
  using MatchingIntegerType = ::std::uint64_t;
  static constexpr MatchingIntegerType kMantissaMask() {
    return 0xfffffffffffffUL;
  }
  static constexpr MatchingIntegerType kExponentMask() {
    return 0x7ff0000000000000UL;
  }
  static constexpr MatchingIntegerType kSignMask() {
    return 0x8000000000000000UL;
  }
  static constexpr int kPrintfPrecision() { return 17; }
  static constexpr const char *kScanfFormat() { return "%lf%n"; }
};

// Decodes a floating-point number from text.
template <class Float>
bool DecodeFloat(const ::std::string &token, Float *result) {
  // The state of the world for reading floating-point values is somewhat better
  // than the situation for writing them, but there are still a few bits that
  // are underspecified.  This function is the mirror of WriteFloatToTextStream,
  // below, so it specifically decodes infinities and NaNs in the formats that
  // Emboss uses.
  //
  // Because of the use of scanf here, this function accepts hex floating-point
  // values (0xh.hhhhpeee) *on some systems*.  TODO(bolms): make hex float
  // support universal.

  using UInt = typename FloatConstants<Float>::MatchingIntegerType;

  if (token.empty()) return false;

  // First, check for negative.
  bool negative = token[0] == '-';

  // Second, check for NaN.
  ::std::size_t i = token[0] == '-' || token[0] == '+' ? 1 : 0;
  if (token.size() >= i + 3 && (token[i] == 'N' || token[i] == 'n') &&
      (token[i + 1] == 'A' || token[i + 1] == 'a') &&
      (token[i + 2] == 'N' || token[i + 2] == 'n')) {
    UInt nan_payload;
    if (token.size() >= i + 4) {
      if (token[i + 3] == '(' && token[token.size() - 1] == ')') {
        if (!DecodeInteger(token.substr(i + 4, token.size() - i - 5),
                           &nan_payload)) {
          return false;
        }
      } else {
        // NaN may not be followed by trailing characters other than a
        // ()-enclosed payload.
        return false;
      }
    } else {
      // If no specific NaN was given, take a default NaN from the C++ standard
      // library.  Technically, a conformant C++ implementation might not have
      // quiet_NaN(), but any IEEE754-based implementation should.
      //
      // It is tempting to just write the default NaN directly into the view and
      // return success, but "-NaN" should be have its sign bit set, and there
      // is no direct way to set the sign bit of a NaN, so there are fewer code
      // paths if we extract the default NaN payload, then use it in the
      // reconstruction step, below.
      Float default_nan = ::std::numeric_limits<Float>::quiet_NaN();
      UInt bits;
      ::std::memcpy(&bits, &default_nan, sizeof(bits));
      nan_payload = bits & FloatConstants<Float>::kMantissaMask();
    }
    if (nan_payload == 0) {
      // "NaN" with a payload of zero is actually the bit pattern for infinity;
      // "NaN(0)" should not be an alias for "Inf".
      return false;
    }
    if (nan_payload & (FloatConstants<Float>::kExponentMask() |
                       FloatConstants<Float>::kSignMask())) {
      // The payload must be small enough to fit in the payload space; it must
      // not overflow into the exponent or sign bits.
      //
      // Note that the DecodeInteger call which decoded the payload will return
      // false if the payload would overflow the `UInt` type, so cases like
      // "NaN(0x10000000000000000000000000000)" -- which are so big that they no
      // longer interfere with the sign or exponent -- are caught above.
      return false;
    }
    UInt bits = FloatConstants<Float>::kExponentMask();
    bits |= nan_payload;
    if (negative) {
      bits |= FloatConstants<Float>::kSignMask();
    }
    ::std::memcpy(result, &bits, sizeof(bits));
    return true;
  }

  // If the value is not NaN, check for infinity.
  if (token.size() >= i + 3 && (token[i] == 'I' || token[i] == 'i') &&
      (token[i + 1] == 'N' || token[i + 1] == 'n') &&
      (token[i + 2] == 'F' || token[i + 2] == 'f')) {
    if (token.size() > i + 3) {
      // Infinity must be exactly "Inf" or "-Inf" (case insensitive).  There
      // must not be trailing characters.
      return false;
    }
    // As with quiet_NaN(), a conforming C++ implementation might not have
    // infinity(), but an IEEE 754-based implementation should.
    if (negative) {
      *result = -::std::numeric_limits<Float>::infinity();
      return true;
    } else {
      *result = ::std::numeric_limits<Float>::infinity();
      return true;
    }
  }

  // For non-NaN, non-Inf values, use the C scanf function, mirroring the use of
  // printf for writing the value, below.
  int chars_used = -1;
  if (::std::sscanf(token.c_str(), FloatConstants<Float>::kScanfFormat(),
                    result, &chars_used) < 1) {
    return false;
  }
  if (chars_used < 0 ||
      static_cast</**/ ::std::size_t>(chars_used) < token.size()) {
    return false;
  }
  return true;
}

// Decodes a floating-point number from a text stream and writes it to the
// specified view.
template <class Stream, class View>
bool ReadFloatFromTextStream(View *view, Stream *stream) {
  ::std::string token;
  if (!ReadToken(stream, &token)) return false;
  typename View::ValueType value;
  if (!DecodeFloat(token, &value)) return false;
  return view->TryToWrite(value);
}

template <class Stream, class Float>
void WriteFloatToTextStream(Float n, Stream *stream,
                            const TextOutputOptions &options) {
  static_assert(::std::is_same<Float, float>::value ||
                    ::std::is_same<Float, double>::value,
                "WriteFloatToTextStream can only write float or double.");
  // The state of the world w.r.t. rendering floating-points as decimal text is,
  // ca. 2018, less than ideal.
  //
  // In C++ land, there is actually no stable facility in the standard library
  // until to_chars() in C++17 -- which is not actually implemented yet in
  // libc++.  to_string(), the printf() family, and the iostreams system all
  // respect the current locale.  In most programs, the locale is permanently
  // left on "C", but this is not guaranteed.  to_string() also uses a fixed and
  // rather unfortunate format.
  //
  // For integers, I (bolms@) chose to just implement custom read and write
  // routines, but those routines are quite small and straightforward compared
  // to floating point conversion.  Even writing correct output is difficult,
  // and writing correct and minimal output is the subject of a number of
  // academic papers.
  //
  // For the moment, I'm just using snprintf("%.*g", 17, n), which is guaranteed
  // to be read back as the same number, but can be longer than strictly
  // necessary.
  //
  // TODO(bolms): Import a modified version of the double-to-string conversion
  // from Swift's standard library, which appears to be best implementation
  // currently available.

  if (::std::isnan(n)) {
    // The printf format for NaN is just "NaN".  In the interests of keeping
    // things bit-exact, Emboss prints the exact NaN.
    typename FloatConstants<Float>::MatchingIntegerType bits;
    ::std::memcpy(&bits, &n, sizeof(bits));
    ::std::uint64_t nan_payload = bits & FloatConstants<Float>::kMantissaMask();
    ::std::uint64_t nan_sign = bits & FloatConstants<Float>::kSignMask();
    if (nan_sign) {
      // NaN still has a sign bit, which is generally treated differently from
      // the payload.  There is no real "standard" text format for NaNs, but
      // "-NaN" appears to be a common way of indicating a NaN with the sign bit
      // set.
      stream->Write("-NaN(");
    } else {
      stream->Write("NaN(");
    }
    // NaN payloads are always dumped in hex.  Note that Emboss is treating the
    // is_quiet/is_signal bit as just another bit in the payload.
    WriteIntegerToTextStream(nan_payload, stream, 16, options.digit_grouping());
    stream->Write(")");
    return;
  }

  if (::std::isinf(n)) {
    if (n < 0.0) {
      stream->Write("-Inf");
    } else {
      stream->Write("Inf");
    }
    return;
  }

  // TODO(bolms): Should the current numeric base be honored here?  Should there
  // be a separate Float numeric base?
  ::std::array<char, 30> buffer;
  // TODO(bolms): Figure out how to get ::std::snprintf to work on
  // microcontroller builds.
  ::std::size_t snprintf_result = static_cast</**/ ::std::size_t>(::snprintf(
      &(buffer[0]), buffer.size(), "%.*g",
      FloatConstants<Float>::kPrintfPrecision(), static_cast<double>(n)));
  (void)snprintf_result;  // Unused if EMBOSS_CHECK_LE is compiled out.
  EMBOSS_CHECK_LE(snprintf_result, buffer.size());
  stream->Write(&buffer[0]);

  // TODO(bolms): Support digit grouping.
}

template <class Stream, class View>
bool ReadEnumViewFromTextStream(View *view, Stream *stream) {
  ::std::string token;
  if (!ReadToken(stream, &token)) return false;
  if (token.empty()) return false;
  if (::std::isdigit(token[0])) {
    ::std::uint64_t value;
    if (!DecodeInteger(token, &value)) return false;
    // TODO(bolms): Fix the static_cast<ValueType> for signed ValueType.
    // TODO(bolms): Should values between 2**63 and 2**64-1 actually be
    // allowed in the text format when ValueType is signed?
    return view->TryToWrite(static_cast<typename View::ValueType>(value));
  } else if (token[0] == '-') {
    ::std::int64_t value;
    if (!DecodeInteger(token, &value)) return false;
    return view->TryToWrite(static_cast<typename View::ValueType>(value));
  } else {
    typename View::ValueType value;
    if (!TryToGetEnumFromName(token.c_str(), &value)) return false;
    return view->TryToWrite(value);
  }
}

template <class Stream, class View>
void WriteEnumViewToTextStream(View *view, Stream *stream,
                               const TextOutputOptions &options) {
  const char *name = TryToGetNameFromEnum(view->Read());
  if (name != nullptr) {
    stream->Write(name);
  }
  // If the enum value has no known name, then write its numeric value
  // instead.  If it does have a known name, and comments are enabled on the
  // output, then write the numeric value as a comment.
  if (name == nullptr || options.comments()) {
    if (name != nullptr) stream->Write("  # ");
    WriteIntegerToTextStream(
        static_cast<
            typename ::std::underlying_type<typename View::ValueType>::type>(
            view->Read()),
        stream, options.numeric_base(), options.digit_grouping());
  }
}

// Updates an array from a text stream.  For an array of integers, the most
// basic form of the text format looks like:
//
// { 0, 1, 2 }
//
// However, the following are all acceptable and equivalent:
//
// { 0, 1, 2, }
// {0 1 2}
// { [2]: 2, [1]: 1, [0]: 0 }
// {[2]:2, [0]:0, 1}
//
// Formally, the array must be contained within braces ("{}").  Elements are
// represented as an optional index surrounded by brackets ("[]") followed by
// the text format of the element, followed by a single optional comma (",").
// If no index is present for the first element, the index 0 will be used.  If
// no index is present for any elements after the first, the index one greater
// than the previous index will be used.
template <class Array, class Stream>
bool ReadArrayFromTextStream(Array *array, Stream *stream) {
  // The text format allows any given index to be set more than once.  In
  // theory, this function could track indices and fail if an index were
  // double-set, but doing so would require quite a bit of overhead, and
  // O(array->ElementCount()) extra space in the worst case.  It does not seem
  // worth it to impose the runtime cost here.
  ::std::size_t index = 0;
  ::std::string brace;
  // Read out the opening brace.
  if (!ReadToken(stream, &brace)) return false;
  if (brace != "{") return false;
  for (;;) {
    char c;
    // Check for a closing brace; if present, success.
    if (!DiscardWhitespace(stream)) return false;
    if (!stream->Read(&c)) return false;
    if (c == '}') return true;

    // If the element has an index, read it.
    if (c == '[') {
      ::std::string index_text;
      if (!ReadToken(stream, &index_text)) return false;
      if (!::emboss::support::DecodeInteger(index_text, &index)) return false;
      ::std::string closing_bracket;
      if (!ReadToken(stream, &closing_bracket)) return false;
      if (closing_bracket != "]") return false;
      ::std::string colon;
      if (!ReadToken(stream, &colon)) return false;
      if (colon != ":") return false;
    } else {
      if (!stream->Unread(c)) return false;
    }

    // Read the element.
    if (index >= array->ElementCount()) return false;
    if (!(*array)[index].UpdateFromTextStream(stream)) return false;
    ++index;

    // If there is a trailing comma, discard it.
    if (!DiscardWhitespace(stream)) return false;
    if (!stream->Read(&c)) return false;
    if (c != ',') {
      if (c != '}') return false;
      if (!stream->Unread(c)) return false;
    }
  }
}

// Prints out the elements of an 8-bit Int or UInt array as characters.
template <class Array, class Stream>
void WriteShorthandAsciiArrayCommentToTextStream(
    const Array *array, Stream *stream, const TextOutputOptions &options) {
  if (!options.multiline()) return;
  if (!options.comments()) return;
  if (array->ElementCount() == 0) return;
  static constexpr int kCharsPerBlock = 64;
  static constexpr char kStandInForNonPrintableChar = '.';
  auto start_new_line = [&]() {
    stream->Write("\n");
    stream->Write(options.current_indent());
    stream->Write("# ");
  };
  for (int i = 0, n = array->ElementCount(); i < n; ++i) {
    const int c = (*array)[i].Read();
    const bool c_is_printable = (c >= 32 && c <= 126);
    const bool starting_new_block = ((i % kCharsPerBlock) == 0);
    if (starting_new_block) start_new_line();
    stream->Write(c_is_printable ? static_cast<char>(c)
                                 : kStandInForNonPrintableChar);
  }
}

// Writes an array to a text stream.  This writes the array in a format
// compatible with ReadArrayFromTextStream, above.  For multiline output, writes
// one element per line.
//
// TODO(bolms): Make the output for arrays of small elements (like bytes) much
// more compact.
//
// This will require several support functions like `MaxTextLength` on every
// view type, and will substantially increase the number of tests required for
// this function, but will make arrays of small elements much more readable.
template <class Array, class Stream>
void WriteArrayToTextStream(Array *array, Stream *stream,
                            const TextOutputOptions &options) {
  TextOutputOptions element_options = options.PlusOneIndent();
  if (options.multiline()) {
    stream->Write("{");
    WriteShorthandArrayCommentToTextStream(array, stream, element_options);
    for (::std::size_t i = 0; i < array->ElementCount(); ++i) {
      if (!options.allow_partial_output() || (*array)[i].IsAggregate() ||
          (*array)[i].Ok()) {
        stream->Write("\n");
        stream->Write(element_options.current_indent());
        stream->Write("[");
        // TODO(bolms): Put padding in here so that array elements start at the
        // same column.
        //
        // TODO(bolms): (Maybe) figure out how to get padding to work so that
        // elements with comments can have their comments align to the same
        // column.
        WriteIntegerToTextStream(i, stream, options.numeric_base(),
                                 options.digit_grouping());
        stream->Write("]: ");
        (*array)[i].WriteToTextStream(stream, element_options);
      } else if (element_options.comments()) {
        stream->Write("\n");
        stream->Write(element_options.current_indent());
        stream->Write("# [");
        WriteIntegerToTextStream(i, stream, options.numeric_base(),
                                 options.digit_grouping());
        stream->Write("]: UNREADABLE");
      }
    }
    stream->Write("\n");
    stream->Write(options.current_indent());
    stream->Write("}");
  } else {
    stream->Write("{");
    bool skipped_unreadable = false;
    for (::std::size_t i = 0; i < array->ElementCount(); ++i) {
      if (!options.allow_partial_output() || (*array)[i].IsAggregate() ||
          (*array)[i].Ok()) {
        stream->Write(" ");
        if (i % 8 == 0 || skipped_unreadable) {
          stream->Write("[");
          WriteIntegerToTextStream(i, stream, options.numeric_base(),
                                   options.digit_grouping());
          stream->Write("]: ");
        }
        (*array)[i].WriteToTextStream(stream, element_options);
        if (i < array->ElementCount() - 1) {
          stream->Write(",");
        }
        skipped_unreadable = false;
      } else {
        if (element_options.comments()) {
          stream->Write(" # ");
          if (i % 8 == 0) {
            stream->Write("[");
            WriteIntegerToTextStream(i, stream, options.numeric_base(),
                                     options.digit_grouping());
            stream->Write("]: ");
          }
          stream->Write("UNREADABLE\n");
        }
        skipped_unreadable = true;
      }
    }
    stream->Write(" }");
  }
}

// TextStream puts a stream-like interface onto a std::string, for use by
// UpdateFromTextStream.  It is used by UpdateFromText().
class TextStream final {
 public:
  // This template handles std::string, std::string_view, and absl::string_view.
  template <class String>
  inline explicit TextStream(const String &text)
      : text_(text.data()), length_(text.size()) {}

  inline explicit TextStream(const char *text)
      : text_(text), length_(strlen(text)) {}

  inline TextStream(const char *text, ::std::size_t length)
      : text_(text), length_(length) {}

  inline bool Read(char *result) {
    if (index_ >= length_) return false;
    *result = text_[index_];
    ++index_;
    return true;
  }

  inline bool Unread(char c) {
    if (index_ < 1) return false;
    if (text_[index_ - 1] != c) return false;
    --index_;
    return true;
  }

 private:
  // It would be nice to use string_view here, but that's not available until
  // C++17.
  const char *text_ = nullptr;
  ::std::size_t length_ = 0;
  ::std::size_t index_ = 0;
};

}  // namespace support

// Returns a TextOutputOptions set for reasonable multi-line text output.
static inline TextOutputOptions MultilineText() {
  return TextOutputOptions()
      .Multiline(true)
      .WithIndent("  ")
      .WithComments(true)
      .WithDigitGrouping(true);
}

// TODO(bolms): Add corresponding ReadFromText*() verbs which enforce the
// constraint that all of a field's dependencies must be present in the text
// before the field itself is set.
template <typename EmbossViewType>
inline bool UpdateFromText(const EmbossViewType &view,
                           const ::std::string &text) {
  auto text_stream = support::TextStream{text};
  return view.UpdateFromTextStream(&text_stream);
}

template <typename EmbossViewType>
inline ::std::string WriteToString(const EmbossViewType &view,
                                   TextOutputOptions options) {
  support::TextOutputStream text_stream;
  view.WriteToTextStream(&text_stream, options);
  return text_stream.Result();
}

template <typename EmbossViewType>
inline ::std::string WriteToString(const EmbossViewType &view) {
  return WriteToString(view, TextOutputOptions());
}

}  // namespace emboss

#endif  // EMBOSS_RUNTIME_CPP_EMBOSS_TEXT_UTIL_H_
