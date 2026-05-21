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

#include "runtime/cpp/test/util/noncontiguous_container.h"

#include <algorithm>
#include <list>
#include <string>
#include <type_traits>
#include <vector>

#include "gtest/gtest.h"

namespace emboss {
namespace support {
namespace test {
namespace {

template <typename Container>
bool IsNoncontiguous(const Container& container) {
  if (container.size() <= 1) return false;
  auto it = container.begin();
  auto prev = it++;
  for (; it != container.end(); ++it, ++prev) {
    if (std::addressof(*it) != std::addressof(*prev) + 1) {
      return true;
    }
  }
  return false;
}

TEST(NoncontiguousContainer, BasicStringChunkIteration) {
  NoncontiguousContainer<char, std::basic_string> container(
      {"12", "", "3", "456"});
  EXPECT_TRUE(IsNoncontiguous(container));

  std::string result;
  for (auto it = container.cbegin(); it != container.cend(); ++it) {
    result += *it;
  }
  EXPECT_EQ("123456", result);
}

TEST(NoncontiguousContainer, GenericVectorIteration) {
  NoncontiguousContainer<int> container({{1, 2}, {}, {3}, {4, 5, 6}});
  EXPECT_TRUE(IsNoncontiguous(container));

  int sum = 0;
  for (int v : container) {
    sum += v;
  }
  EXPECT_EQ(21, sum);
}

TEST(NoncontiguousContainer, StdListStorageIteration) {
  NoncontiguousContainer<int, std::vector, std::list> container(
      {{10, 20}, {30}});
  EXPECT_TRUE(IsNoncontiguous(container));

  int sum = 0;
  for (int v : container) {
    sum += v;
  }
  EXPECT_EQ(60, sum);
}

TEST(NoncontiguousContainer, RandomAccessAdvance) {
  NoncontiguousContainer<char> container({{'1', '2'}, {'3'}, {'4', '5', '6'}});
  EXPECT_TRUE(IsNoncontiguous(container));

  auto it = container.begin();
  EXPECT_EQ('1', *it);

  it += 2;
  EXPECT_EQ('3', *it);

  it += 3;
  EXPECT_EQ('6', *it);

  it -= 4;
  EXPECT_EQ('2', *it);
}

TEST(NoncontiguousContainer, DistanceOperator) {
  NoncontiguousContainer<char> container(
      {{'a', 'b', 'c'}, {'d', 'e', 'f'}, {'g', 'h', 'i'}});
  EXPECT_TRUE(IsNoncontiguous(container));

  auto begin = container.begin();
  auto end = container.end();

  EXPECT_EQ(9, end - begin);
  EXPECT_EQ(-9, begin - end);

  auto mid = begin + 4;
  EXPECT_EQ('e', *mid);
  EXPECT_EQ(4, mid - begin);
  EXPECT_EQ(-4, begin - mid);
  EXPECT_EQ(5, end - mid);
  EXPECT_EQ(-5, mid - end);
}

TEST(NoncontiguousContainer, RelationalOperators) {
  NoncontiguousContainer<int> container({{1, 2}, {3, 4}});
  EXPECT_TRUE(IsNoncontiguous(container));

  auto it1 = container.begin();
  auto it2 = container.begin() + 1;
  auto it3 = container.begin() + 2;

  EXPECT_TRUE(it1 == it1);
  EXPECT_TRUE(it1 != it2);

  EXPECT_TRUE(it1 < it2);
  EXPECT_TRUE(it2 > it1);
  EXPECT_TRUE(it1 <= it2);
  EXPECT_TRUE(it1 <= it1);
  EXPECT_TRUE(it2 >= it1);
  EXPECT_TRUE(it2 >= it2);

  EXPECT_TRUE(it1 < it3);
  EXPECT_TRUE(it2 < it3);
}

TEST(NoncontiguousContainer, DecrementFromEnd) {
  NoncontiguousContainer<int> container({{1, 2}, {3}});
  EXPECT_TRUE(IsNoncontiguous(container));

  auto it = container.end();
  --it;
  EXPECT_EQ(3, *it);
  it -= 2;
  EXPECT_EQ(1, *it);
}

TEST(NoncontiguousContainer, ContiguousOrEmpty) {
  NoncontiguousContainer<int> empty({});
  EXPECT_EQ(empty.begin(), empty.end());
  EXPECT_EQ(0U, empty.size());

  NoncontiguousContainer<int> single({{42}});
  EXPECT_FALSE(IsNoncontiguous(single));
  EXPECT_EQ(1U, single.size());
  EXPECT_EQ(42, *single.begin());

  auto it = single.begin();
  ++it;
  EXPECT_EQ(it, single.end());

  NoncontiguousContainer<int> contiguous({{1, 2, 3, 4, 5}});
  EXPECT_FALSE(IsNoncontiguous(contiguous));
  EXPECT_EQ(5U, contiguous.size());

  int sum = 0;
  for (int v : contiguous) {
    sum += v;
  }
  EXPECT_EQ(15, sum);
}

TEST(NoncontiguousContainer, StdCopyAcrossChunks) {
  NoncontiguousContainer<char> container({{'a', 'b'}, {'c', 'd'}, {'e', 'f'}});
  EXPECT_TRUE(IsNoncontiguous(container));

  {
    std::string dest = "    ";
    auto start = container.begin() + 1;
    auto dest_it = dest.begin();
    for (int i = 0; i < 4; ++i) {
      *dest_it++ = *start++;
    }
    EXPECT_EQ("bcde", dest);
  }

  {
    std::string dest;
    dest.resize(3);
    std::copy_n(container.begin(), 3, dest.begin());
    EXPECT_EQ("abc", dest);
  }

  {
    std::string dest;
    std::copy(container.begin() + 2, container.end(), std::back_inserter(dest));
    EXPECT_EQ("cdef", dest);
  }

  {
    std::string dest;
    std::copy(container.begin(), container.end(), std::back_inserter(dest));
    EXPECT_EQ("abcdef", dest);
  }

  {
    std::string src = "123456";
    std::copy(src.begin(), src.end(), container.begin());

    std::string dest;
    std::copy(container.begin(), container.end(), std::back_inserter(dest));
    EXPECT_EQ(src, dest);
  }
}

TEST(NoncontiguousContainer, ConsecutiveEmptyChunks) {
  NoncontiguousContainer<char> container({{'a'}, {}, {}, {'b'}, {}});
  EXPECT_TRUE(IsNoncontiguous(container));

  auto begin = container.begin();
  auto end = container.end();

  EXPECT_EQ(2, end - begin);
  EXPECT_EQ('a', *begin);

  auto second = begin + 1;
  EXPECT_EQ('b', *second);

  auto after_second = second + 1;
  EXPECT_TRUE(after_second == end);
}

TEST(NoncontiguousContainer, IteratorTraitsAndConstValidation) {
  using ContainerT = NoncontiguousContainer<int>;

  using CatT = typename ContainerT::iterator::iterator_category;
  using IsRandomCat = std::is_same<CatT, std::random_access_iterator_tag>;
  EXPECT_TRUE(IsRandomCat::value);

  using ValT = typename ContainerT::iterator::value_type;
  using IsIntVal = std::is_same<ValT, int>;
  EXPECT_TRUE(IsIntVal::value);

  const ContainerT container({{1}, {2, 3}});
  EXPECT_TRUE(IsNoncontiguous(container));

  int sum = 0;
  for (ContainerT::const_iterator it = container.cbegin();
       it != container.cend(); ++it) {
    sum += *it;
  }
  EXPECT_EQ(6, sum);
}

}  // namespace
}  // namespace test
}  // namespace support
}  // namespace emboss
