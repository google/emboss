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

#include "integration/googletest/emboss_test_util.h"

#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "testdata/complex_structure.emb.h"

namespace emboss {
namespace test {
namespace {

class EmbossTestUtilTest : public ::testing::Test {
 protected:
  EmbossTestUtilTest() { b_.s().Write(1); }
  ::std::array</**/ ::std::uint8_t, 64> buf_a_{};
  ::emboss_test::ComplexWriter a_{&buf_a_};
  ::std::array<char, 64> buf_b_{};
  ::emboss_test::ComplexWriter b_{&buf_b_};
};

TEST_F(EmbossTestUtilTest, EqualsEmb) {
  EXPECT_THAT(a_, EqualsEmb(a_));
  EXPECT_THAT(b_, EqualsEmb(b_));

  EXPECT_THAT(a_, ::testing::Not(EqualsEmb(b_)));
  EXPECT_THAT(b_, ::testing::Not(EqualsEmb(a_)));
}

TEST_F(EmbossTestUtilTest, NotOkView) {
  auto null_view = ::emboss_test::ComplexView(nullptr);
  EXPECT_THAT(a_, ::testing::Not(EqualsEmb(null_view)));
  EXPECT_THAT(b_, ::testing::Not(EqualsEmb(null_view)));
  EXPECT_THAT(null_view, ::testing::Not(EqualsEmb(null_view)));
  EXPECT_THAT(null_view, ::testing::Not(EqualsEmb(a_)));
  EXPECT_THAT(null_view, ::testing::Not(EqualsEmb(b_)));
}

TEST_F(EmbossTestUtilTest, NotOkViewMatcherDescribe) {
  auto null_view = ::emboss_test::ComplexView(nullptr);

  ::testing::StringMatchResultListener listener;
  EqualsEmb(a_).impl().MatchAndExplain(null_view, &listener);
  EXPECT_EQ(listener.str(), "View for comparison from is not OK.");

  listener.Clear();
  EqualsEmb(null_view).impl().MatchAndExplain(a_, &listener);
  EXPECT_EQ(listener.str(), "View for comparison to is not OK.");
}

TEST_F(EmbossTestUtilTest, MatcherDescribeEquivalent) {
  ::std::stringstream ss;
  EqualsEmb(a_).impl().DescribeTo(&ss);
  EXPECT_EQ(ss.str(), "are equal");
}

TEST_F(EmbossTestUtilTest, MatcherDescribeNotEquivalent) {
  ::std::stringstream ss;
  EqualsEmb(a_).impl().DescribeNegationTo(&ss);
  EXPECT_EQ(ss.str(), "are NOT equal");
}

TEST_F(EmbossTestUtilTest, MatcherExplainEquivalent) {
  ::testing::StringMatchResultListener listener;

  EqualsEmb(a_).impl().MatchAndExplain(a_, &listener);
  EXPECT_EQ(listener.str(), "");

  EqualsEmb(b_).impl().MatchAndExplain(b_, &listener);
  EXPECT_EQ(listener.str(), "");
}

TEST_F(EmbossTestUtilTest, MatcherExplainNotEquivalent) {
  ::testing::StringMatchResultListener listener;
  EqualsEmb(a_).impl().MatchAndExplain(b_, &listener);
  EXPECT_EQ(listener.str(), R"(
@@ -1,3 +1,3 @@
-  s: 0  # 0x0
+  s: 1  # 0x1
   u: 0  # 0x0
   i: 0  # 0x0
@@ +4,34 @@
   b: 0  # 0x0
   a: {
+    [0]: {
+      [0]: {
+        a: {
+          x: 0  # 0x0
+          l: 0  # 0x0
+          h: 0  # 0x0
+        }
+      }
+      [1]: {
+        a: {
+          x: 0  # 0x0
+          l: 0  # 0x0
+          h: 0  # 0x0
+        }
+      }
+      [2]: {
+        a: {
+          x: 0  # 0x0
+          l: 0  # 0x0
+          h: 0  # 0x0
+        }
+      }
+      [3]: {
+        a: {
+          x: 0  # 0x0
+          l: 0  # 0x0
+          h: 0  # 0x0
+        }
+      }
+    }
   }
   a0: 0  # 0x0
)");
}

}  // namespace
}  // namespace test
}  // namespace emboss
