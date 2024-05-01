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

// View class template for enums.
#ifndef EMBOSS_RUNTIME_CPP_EMBOSS_ENUM_VIEW_H_
#define EMBOSS_RUNTIME_CPP_EMBOSS_ENUM_VIEW_H_

#include <cctype>
#include <cstdint>
#include <string>
#include <utility>

#include "runtime/cpp/emboss_defines.h"
#include "runtime/cpp/emboss_view_parameters.h"

// Forward declarations for optional text processing helpers.
namespace emboss {
class TextOutputOptions;
namespace support {
template <class Stream, class View>
bool ReadEnumViewFromTextStream(View *view, Stream *stream);
template <class Stream, class View>
void WriteEnumViewToTextStream(View *view, Stream *stream,
                               const TextOutputOptions &options);
}  // namespace support
}  // namespace emboss

namespace emboss {
namespace support {

// EnumView is a view for Enums inside of bitfields.
template <class Enum, class Parameters, class BitViewType>
class EnumView final {
 public:
  using ValueType = typename ::std::remove_cv<Enum>::type;
  static_assert(
      Parameters::kBits <= sizeof(ValueType) * 8,
      "EnumView requires sizeof(ValueType) * 8 >= Parameters::kBits.");
  template <typename... Args>
  explicit EnumView(Args &&...args) : buffer_{::std::forward<Args>(args)...} {}
  EnumView() : buffer_() {}
  EnumView(const EnumView &) = default;
  EnumView(EnumView &&) = default;
  EnumView &operator=(const EnumView &) = default;
  EnumView &operator=(EnumView &&) = default;
  ~EnumView() = default;

  // TODO(bolms): Here and in CouldWriteValue(), the static_casts to ValueType
  // rely on implementation-defined behavior when ValueType is signed.
  ValueType Read() const {
    ValueType result = static_cast<ValueType>(buffer_.ReadUInt());
    EMBOSS_CHECK(Parameters::ValueIsOk(result));
    return result;
  }
  ValueType UncheckedRead() const {
    return static_cast<ValueType>(buffer_.UncheckedReadUInt());
  }
  void Write(ValueType value) const {
    const bool result = TryToWrite(value);
    (void)result;
    EMBOSS_CHECK(result);
  }
  bool TryToWrite(ValueType value) const {
    if (!CouldWriteValue(value)) return false;
    if (!IsComplete()) return false;
    buffer_.WriteUInt(static_cast<typename BitViewType::ValueType>(value));
    return true;
  }
  static constexpr bool CouldWriteValue(ValueType value) {
    // The value can be written if:
    //
    // a) it can fit in BitViewType::ValueType (verified by casting to
    //    BitViewType::ValueType and back, and making sure that the value is
    //    unchanged)
    //
    // and either:
    //
    // b1) the field size is large enough to hold all values, or
    // b2) the value is less than 2**(field size in bits)
    return value == static_cast<ValueType>(
                        static_cast<typename BitViewType::ValueType>(value)) &&
           ((Parameters::kBits ==
             sizeof(typename BitViewType::ValueType) * 8) ||
            (static_cast<typename BitViewType::ValueType>(value) <
             ((static_cast<typename BitViewType::ValueType>(1)
               << (Parameters::kBits - 1))
              << 1))) &&
           Parameters::ValueIsOk(value);
  }
  void UncheckedWrite(ValueType value) const {
    buffer_.UncheckedWriteUInt(
        static_cast<typename BitViewType::ValueType>(value));
  }

  template <typename OtherView>
  void CopyFrom(const OtherView &other) const {
    Write(other.Read());
  }
  template <typename OtherView>
  void UncheckedCopyFrom(const OtherView &other) const {
    UncheckedWrite(other.UncheckedRead());
  }
  template <typename OtherView>
  bool TryToCopyFrom(const OtherView &other) const {
    return other.Ok() && TryToWrite(other.Read());
  }

  // All bit patterns in the underlying buffer are valid, so Ok() is always
  // true if IsComplete() is true.
  bool Ok() const {
    return IsComplete() && Parameters::ValueIsOk(UncheckedRead());
  }
  template <class OtherBitViewType>
  bool Equals(const EnumView<Enum, Parameters, OtherBitViewType> &other) const {
    return Read() == other.Read();
  }
  template <class OtherBitViewType>
  bool UncheckedEquals(
      const EnumView<Enum, Parameters, OtherBitViewType> &other) const {
    return UncheckedRead() == other.UncheckedRead();
  }
  bool IsComplete() const {
    return buffer_.Ok() && buffer_.SizeInBits() >= Parameters::kBits;
  }

  template <class Stream>
  bool UpdateFromTextStream(Stream *stream) const {
    return ::emboss::support::ReadEnumViewFromTextStream(this, stream);
  }

  template <class Stream>
  void WriteToTextStream(Stream *stream,
                         const TextOutputOptions &options) const {
    ::emboss::support::WriteEnumViewToTextStream(this, stream, options);
  }

  static constexpr bool IsAggregate() { return false; }

  static constexpr int SizeInBits() { return Parameters::kBits; }

 private:
  BitViewType buffer_;
};

}  // namespace support
}  // namespace emboss

#endif  // EMBOSS_RUNTIME_CPP_EMBOSS_ENUM_VIEW_H_
