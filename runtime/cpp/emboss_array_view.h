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

// View classes for arrays and bit arrays.
#ifndef EMBOSS_RUNTIME_CPP_EMBOSS_ARRAY_VIEW_H_
#define EMBOSS_RUNTIME_CPP_EMBOSS_ARRAY_VIEW_H_

#include <cstddef>
#include <iterator>
#include <tuple>
#include <type_traits>

#include "runtime/cpp/emboss_arithmetic.h"

namespace emboss {

// Forward declarations for use by WriteShorthandArrayCommentToTextStream.
class TextOutputOptions;
namespace support {
template <class Array, class Stream>
void WriteShorthandAsciiArrayCommentToTextStream(
    const Array *array, Stream *stream, const TextOutputOptions &options);
}
namespace prelude {
template <class Parameters, class BitViewType>
class UIntView;
template <class Parameters, class BitViewType>
class IntView;
}  // namespace prelude

namespace support {

// Advance direction for ElementViewIterator.
enum class ElementViewIteratorDirection { kForward, kReverse };

// Iterator adapter for elements in a GenericArrayView.
template <class GenericArrayView, ElementViewIteratorDirection kDirection>
class ElementViewIterator {
 public:
  using iterator_category = ::std::random_access_iterator_tag;
  using value_type = typename GenericArrayView::ViewType;
  using difference_type = ::std::ptrdiff_t;
  using pointer = typename ::std::add_pointer<value_type>::type;
  using reference = typename ::std::add_lvalue_reference<value_type>::type;

  explicit ElementViewIterator(const GenericArrayView array_view,
                               ::std::ptrdiff_t index)
      : array_view_(array_view), view_(array_view[index]), index_(index) {}

  ElementViewIterator() = default;

  reference operator*() { return view_; }

  pointer operator->() { return &view_; }

  ElementViewIterator &operator+=(difference_type d) {
    index_ += (kDirection == ElementViewIteratorDirection::kForward ? d : -d);
    view_ = array_view_[index_];
    return *this;
  }

  ElementViewIterator &operator-=(difference_type d) { return *this += (-d); }

  ElementViewIterator &operator++() {
    *this += 1;
    return *this;
  }

  ElementViewIterator &operator--() {
    *this -= 1;
    return *this;
  }

  ElementViewIterator operator++(int) {
    auto copy = *this;
    ++(*this);
    return copy;
  }

  ElementViewIterator operator--(int) {
    auto copy = *this;
    --(*this);
    return copy;
  }

  ElementViewIterator operator+(difference_type d) const {
    auto copy = *this;
    copy += d;
    return copy;
  }

  ElementViewIterator operator-(difference_type d) const {
    return *this + (-d);
  }

  difference_type operator-(const ElementViewIterator &other) const {
    return kDirection == ElementViewIteratorDirection::kForward
               ? index_ - other.index_
               : other.index_ - index_;
  }

  bool operator==(const ElementViewIterator &other) const {
    return array_view_ == other.array_view_ && index_ == other.index_;
  }

  bool operator!=(const ElementViewIterator &other) const {
    return !(*this == other);
  }

  bool operator<(const ElementViewIterator &other) const {
    return kDirection == ElementViewIteratorDirection::kForward
               ? index_ < other.index_
               : other.index_ < index_;
  }

  bool operator<=(const ElementViewIterator &other) const {
    return kDirection == ElementViewIteratorDirection::kForward
               ? index_ <= other.index_
               : other.index_ <= index_;
  }

  bool operator>(const ElementViewIterator &other) const {
    return !(*this <= other);
  }

  bool operator>=(const ElementViewIterator &other) const {
    return !(*this < other);
  }

 private:
  const GenericArrayView array_view_;
  typename GenericArrayView::ViewType view_;
  ::std::ptrdiff_t index_;
};

// View for an array in a structure.
//
// ElementView should be the view class for a single array element (e.g.,
// UIntView<...> or ArrayView<...>).
//
// BufferType is the storage type that will be passed into the array.
//
// kElementSize is the fixed size of a single element, in addressable units.
//
// kAddressableUnitSize is the size of a single addressable unit.  It should be
// either 1 (one bit) or 8 (one byte).
//
// ElementViewParameterTypes is a list of the types of parameters which must be
// passed down to each element of the array.  ElementViewParameterTypes can be
// empty.
template <class ElementView, class BufferType, ::std::size_t kElementSize,
          ::std::size_t kAddressableUnitSize,
          typename... ElementViewParameterTypes>
class GenericArrayView final {
 public:
  using ViewType = ElementView;
  using ForwardIterator =
      ElementViewIterator<GenericArrayView,
                          ElementViewIteratorDirection::kForward>;
  using ReverseIterator =
      ElementViewIterator<GenericArrayView,
                          ElementViewIteratorDirection::kReverse>;

  GenericArrayView() : buffer_() {}
  explicit GenericArrayView(const ElementViewParameterTypes &...parameters,
                            BufferType buffer)
      : parameters_{parameters...}, buffer_{buffer} {}

  ElementView operator[](::std::size_t index) const {
    return IndexOperatorHelper<sizeof...(ElementViewParameterTypes) ==
                               0>::ConstructElement(parameters_, buffer_,
                                                    index);
  }

  ForwardIterator begin() const { return ForwardIterator(*this, 0); }
  ForwardIterator end() const { return ForwardIterator(*this, ElementCount()); }
  ReverseIterator rbegin() const {
    return ReverseIterator(*this, ElementCount() - 1);
  }
  ReverseIterator rend() const { return ReverseIterator(*this, -1); }

  // In order to selectively enable SizeInBytes and SizeInBits, it is
  // necessary to make them into templates.  Further, it is necessary for
  // ::std::enable_if to have a dependency on the template parameter, otherwise
  // SFINAE won't kick in.  Thus, these are templated on an int, and that int
  // is (spuriously) used as the left argument to `,` in the enable_if
  // condition.  The explicit cast to void is needed to silence GCC's
  // -Wunused-value.
  template <int N = 0>
  typename ::std::enable_if<((void)N, kAddressableUnitSize == 8),
                            ::std::size_t>::type
  SizeInBytes() const {
    return buffer_.SizeInBytes();
  }
  template <int N = 0>
  typename ::std::enable_if<((void)N, kAddressableUnitSize == 1),
                            ::std::size_t>::type
  SizeInBits() const {
    return buffer_.SizeInBits();
  }

  ::std::size_t ElementCount() const { return SizeOfBuffer() / kElementSize; }
  bool Ok() const {
    if (!buffer_.Ok()) return false;
    if (SizeOfBuffer() % kElementSize != 0) return false;
    for (::std::size_t i = 0; i < ElementCount(); ++i) {
      if (!(*this)[i].Ok()) return false;
    }
    return true;
  }
  template <class OtherElementView, class OtherBufferType>
  bool Equals(
      const GenericArrayView<OtherElementView, OtherBufferType, kElementSize,
                             kAddressableUnitSize> &other) const {
    if (ElementCount() != other.ElementCount()) return false;
    for (::std::size_t i = 0; i < ElementCount(); ++i) {
      if (!(*this)[i].Equals(other[i])) return false;
    }
    return true;
  }
  template <class OtherElementView, class OtherBufferType>
  bool UncheckedEquals(
      const GenericArrayView<OtherElementView, OtherBufferType, kElementSize,
                             kAddressableUnitSize> &other) const {
    if (ElementCount() != other.ElementCount()) return false;
    for (::std::size_t i = 0; i < ElementCount(); ++i) {
      if (!(*this)[i].UncheckedEquals(other[i])) return false;
    }
    return true;
  }
  bool IsComplete() const { return buffer_.Ok(); }

  template <class Stream>
  bool UpdateFromTextStream(Stream *stream) const {
    return ReadArrayFromTextStream(this, stream);
  }

  template <class Stream>
  void WriteToTextStream(Stream *stream,
                         const TextOutputOptions &options) const {
    WriteArrayToTextStream(this, stream, options);
  }

  static constexpr bool IsAggregate() { return true; }

  BufferType BackingStorage() const { return buffer_; }

  // Forwards to BufferType's ToString(), if any, but only if ElementView is a
  // 1-byte type.
  template <typename String>
  typename ::std::enable_if<kAddressableUnitSize == 8 && kElementSize == 1,
                            String>::type
  ToString() const {
    EMBOSS_CHECK(Ok());
    return BackingStorage().template ToString<String>();
  }

  bool operator==(const GenericArrayView &other) const {
    return parameters_ == other.parameters_ && buffer_ == other.buffer_;
  }

 private:
  // This uses the same technique to select the correct definition of
  // SizeOfBuffer() as in the SizeInBits()/SizeInBytes() selection above.
  template <int N = 0>
  typename ::std::enable_if<((void)N, kAddressableUnitSize == 8),
                            ::std::size_t>::type
  SizeOfBuffer() const {
    return SizeInBytes();
  }
  template <int N = 0>
  typename ::std::enable_if<((void)N, kAddressableUnitSize == 1),
                            ::std::size_t>::type
  SizeOfBuffer() const {
    return SizeInBits();
  }

  // This mess is needed to expand the parameters_ tuple into individual
  // arguments to the ElementView constructor.  If parameters_ has M elements,
  // then:
  //
  // IndexOperatorHelper<false>::ConstructElement() calls
  // IndexOperatorHelper<false, 0>::ConstructElement(), which calls
  // IndexOperatorHelper<false, 0, 1>::ConstructElement(), and so on, up to
  // IndexOperatorHelper<false, 0, 1, ..., M-1>::ConstructElement(), which calls
  // IndexOperatorHelper<true, 0, 1, ..., M>::ConstructElement()
  //
  // That last call will resolve to the second, specialized version of
  // IndexOperatorHelper.  That version's ConstructElement() uses
  // `std::get<N>(parameters)...`, which will be expanded into
  // `std::get<0>(parameters), std::get<1>(parameters), std::get<2>(parameters),
  // ..., std::get<M>(parameters)`.
  //
  // If there are 0 parameters, then operator[]() will call
  // IndexOperatorHelper<true>::ConstructElement(), which still works --
  // `std::get<N>(parameters)...,` will be replaced by ``.
  //
  // In C++14, a lot of this can be replaced by std::index_sequence_of, and in
  // C++17 it can be replaced with std::apply and a lambda.
  //
  // An alternate solution would be to force each parameterized view to have a
  // constructor that accepts a tuple, instead of individual parameters, but
  // that (further) complicates the matrix of constructors for view types.
  template <bool, ::std::size_t... N>
  struct IndexOperatorHelper {
    static ElementView ConstructElement(
        const ::std::tuple<ElementViewParameterTypes...> &parameters,
        BufferType buffer, ::std::size_t index) {
      return IndexOperatorHelper<
          sizeof...(ElementViewParameterTypes) == 1 + sizeof...(N), N...,
          sizeof...(N)>::ConstructElement(parameters, buffer, index);
    }
  };

  template </**/ ::std::size_t... N>
  struct IndexOperatorHelper<true, N...> {
    static ElementView ConstructElement(
        const ::std::tuple<ElementViewParameterTypes...> &parameters,
        BufferType buffer, ::std::size_t index) {
      return ElementView(::std::get<N>(parameters)...,
                         buffer.template GetOffsetStorage<kElementSize, 0>(
                             kElementSize * index, kElementSize));
    }
  };

  ::std::tuple<ElementViewParameterTypes...> parameters_;
  BufferType buffer_;
};

// Optionally prints a shorthand representation of a BitArray in a comment.
template <class ElementView, class BufferType, ::std::size_t kElementSize,
          ::std::size_t kAddressableUnitSize, class Stream>
void WriteShorthandArrayCommentToTextStream(
    const GenericArrayView<ElementView, BufferType, kElementSize,
                           kAddressableUnitSize> *array,
    Stream *stream, const TextOutputOptions &options) {
  // Intentionally empty.  Overload for specific element types.
  // Avoid unused parameters error:
  static_cast<void>(array);
  static_cast<void>(stream);
  static_cast<void>(options);
}

// Overload for arrays of UInt.
// Prints out the elements as ASCII characters for arrays of UInt:8.
template <class BufferType, class BitViewType, class Stream,
          ::std::size_t kElementSize, class Parameters,
          class = typename ::std::enable_if<Parameters::kBits == 8>::type>
void WriteShorthandArrayCommentToTextStream(
    const GenericArrayView<prelude::UIntView<Parameters, BitViewType>,
                           BufferType, kElementSize, 8> *array,
    Stream *stream, const TextOutputOptions &options) {
  WriteShorthandAsciiArrayCommentToTextStream(array, stream, options);
}

// Overload for arrays of UInt.
// Prints out the elements as ASCII characters for arrays of Int:8.
template <class BufferType, class BitViewType, class Stream,
          ::std::size_t kElementSize, class Parameters,
          class = typename ::std::enable_if<Parameters::kBits == 8>::type>
void WriteShorthandArrayCommentToTextStream(
    const GenericArrayView<prelude::IntView<Parameters, BitViewType>,
                           BufferType, kElementSize, 8> *array,
    Stream *stream, const TextOutputOptions &options) {
  WriteShorthandAsciiArrayCommentToTextStream(array, stream, options);
}

}  // namespace support
}  // namespace emboss

#endif  // EMBOSS_RUNTIME_CPP_EMBOSS_ARRAY_VIEW_H_
