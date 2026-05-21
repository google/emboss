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

#ifndef EMBOSS_RUNTIME_CPP_TEST_UTIL_NONCONTIGUOUS_CONTAINER_H_
#define EMBOSS_RUNTIME_CPP_TEST_UTIL_NONCONTIGUOUS_CONTAINER_H_

#include <cstddef>
#include <initializer_list>
#include <iterator>
#include <list>
#include <string>
#include <vector>

namespace emboss {
namespace support {
namespace test {

// A mock non-contiguous container representing data fragmented across a storage
// collection of individual chunks.
template <typename T,
          template <typename, typename...> class ChunkT = std::vector,
          template <typename, typename...> class StorageT = std::vector>
class NoncontiguousContainer {
 public:
  using value_type = T;
  using Chunk = ChunkT<T>;
  using Storage = StorageT<Chunk>;
  using size_type = std::size_t;

  template <bool IsConst>
  class IteratorBase {
   public:
    using iterator_category = std::random_access_iterator_tag;
    using value_type = T;
    using difference_type = std::ptrdiff_t;
    using pointer = typename std::conditional<IsConst, const T*, T*>::type;
    using reference = typename std::conditional<IsConst, const T&, T&>::type;

   private:
    using StoragePtr =
        typename std::conditional<IsConst, const Storage*, Storage*>::type;
    using ChunkIterator =
        typename std::conditional<IsConst, typename Storage::const_iterator,
                                  typename Storage::iterator>::type;

    IteratorBase(StoragePtr storage, size_type chunk_idx,
                 difference_type byte_idx, ChunkIterator chunk_it)
        : storage_(storage),
          chunk_idx_(chunk_idx),
          byte_idx_(byte_idx),
          chunk_it_(chunk_it) {
      Normalize();
    }

    friend IteratorBase<!IsConst>;
    friend NoncontiguousContainer;

   public:
    IteratorBase() = default;

    // Allow implicit conversion from non-const to const iterator
    template <bool WasConst = IsConst,
              typename = typename std::enable_if<!WasConst>::type>
    operator IteratorBase<true>() const {
      return IteratorBase<true>(storage_, chunk_idx_, byte_idx_, chunk_it_);
    }

    reference operator*() const {
      auto element_it = chunk_it_->begin();
      std::advance(element_it, byte_idx_);
      return *element_it;
    }

    pointer operator->() const { return &(*(*this)); }

    reference operator[](difference_type n) const { return *(*this + n); }

    IteratorBase& operator++() {
      ++byte_idx_;
      Normalize();
      return *this;
    }

    IteratorBase operator++(int) {
      IteratorBase temp = *this;
      ++(*this);
      return temp;
    }

    IteratorBase& operator--() {
      --byte_idx_;
      Normalize();
      return *this;
    }

    IteratorBase operator--(int) {
      IteratorBase temp = *this;
      --(*this);
      return temp;
    }

    IteratorBase& operator+=(difference_type n) {
      byte_idx_ += n;
      Normalize();
      return *this;
    }

    IteratorBase operator+(difference_type n) const {
      IteratorBase temp = *this;
      return temp += n;
    }

    friend IteratorBase operator+(difference_type n, const IteratorBase& it) {
      return it + n;
    }

    IteratorBase& operator-=(difference_type n) {
      byte_idx_ -= n;
      Normalize();
      return *this;
    }

    IteratorBase operator-(difference_type n) const {
      IteratorBase temp = *this;
      return temp -= n;
    }

    template <bool OtherConst>
    difference_type operator-(const IteratorBase<OtherConst>& other) const {
      difference_type dist = 0;
      IteratorBase temp = other;

      // If other is ahead of us, compute distance and negate
      if (temp > *this) {
        return -(temp - *this);
      }

      while (temp != *this) {
        size_type temp_remaining = temp.chunk_it_->size() - temp.byte_idx_;

        if (temp.chunk_idx_ == this->chunk_idx_) {
          dist += (this->byte_idx_ - temp.byte_idx_);
          break;
        } else {
          dist += temp_remaining;
          ++temp.chunk_idx_;
          ++temp.chunk_it_;
          temp.byte_idx_ = 0;
          temp.Normalize();
        }
      }
      return dist;
    }

    template <bool OtherConst>
    bool operator==(const IteratorBase<OtherConst>& other) const {
      return storage_ == other.storage_ && chunk_idx_ == other.chunk_idx_ &&
             byte_idx_ == other.byte_idx_;
    }

    template <bool OtherConst>
    bool operator!=(const IteratorBase<OtherConst>& other) const {
      return !(*this == other);
    }

    template <bool OtherConst>
    bool operator<(const IteratorBase<OtherConst>& other) const {
      if (chunk_idx_ != other.chunk_idx_) return chunk_idx_ < other.chunk_idx_;
      return byte_idx_ < other.byte_idx_;
    }

    template <bool OtherConst>
    bool operator>(const IteratorBase<OtherConst>& other) const {
      return other < *this;
    }

    template <bool OtherConst>
    bool operator<=(const IteratorBase<OtherConst>& other) const {
      return !(other < *this);
    }

    template <bool OtherConst>
    bool operator>=(const IteratorBase<OtherConst>& other) const {
      return !(*this < other);
    }

   private:
    StoragePtr storage_ = nullptr;
    size_type chunk_idx_ = 0;
    difference_type byte_idx_ = 0;
    ChunkIterator chunk_it_ = {};

    void Normalize() {
      if (!storage_) return;

      // Handle backward normalization
      while (byte_idx_ < 0) {
        if (chunk_idx_ == 0) {
          // Invalid `byte_idx_`, but required for random_access_iterator.
          return;
        }
        --chunk_idx_;
        --chunk_it_;
        byte_idx_ += static_cast<difference_type>(chunk_it_->size());
      }

      // Handle forward normalization
      while (chunk_idx_ < storage_->size() &&
             byte_idx_ >= static_cast<difference_type>(chunk_it_->size())) {
        byte_idx_ -= static_cast<difference_type>(chunk_it_->size());
        ++chunk_idx_;
        ++chunk_it_;
      }
    }
  };

  using iterator = IteratorBase<false>;
  using const_iterator = IteratorBase<true>;

  explicit NoncontiguousContainer(Storage chunks) : chunks_(std::move(chunks)) {
    for (const auto& chunk : chunks_) {
      total_size_ += chunk.size();
    }
  }

  NoncontiguousContainer(
      std::initializer_list<typename Storage::value_type> init)
      : chunks_(init) {
    for (const auto& chunk : chunks_) {
      total_size_ += chunk.size();
    }
  }

  iterator begin() { return iterator(&chunks_, 0, 0, chunks_.begin()); }
  iterator end() {
    return iterator(&chunks_, chunks_.size(), 0, chunks_.end());
  }

  const_iterator begin() const {
    return const_iterator(&chunks_, 0, 0, chunks_.begin());
  }
  const_iterator end() const {
    return const_iterator(&chunks_, chunks_.size(), 0, chunks_.end());
  }

  const_iterator cbegin() const {
    return const_iterator(&chunks_, 0, 0, chunks_.begin());
  }
  const_iterator cend() const {
    return const_iterator(&chunks_, chunks_.size(), 0, chunks_.end());
  }

  size_type size() const { return total_size_; }

 private:
  Storage chunks_;
  size_type total_size_ = 0;
};

}  // namespace test
}  // namespace support
}  // namespace emboss

#endif  // EMBOSS_RUNTIME_CPP_TEST_UTIL_NONCONTIGUOUS_CONTAINER_H_
