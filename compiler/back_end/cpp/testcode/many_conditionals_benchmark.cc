#include <gtest/gtest.h>

#include <chrono>
#include <iostream>
#include <vector>

#include "testdata/many_conditionals.emb.h"

// A simple test that acts as a benchmark/sanity check.
// Since this file is in compiler/back_end/cpp/testcode/, it will be built as a
// cc_test. We can use GoogleTest macros.

namespace emboss {
namespace test {
namespace {

TEST(ComplexConditionals, PerformanceBenchmark) {
  std::vector<char> buffer(100, 0);
  auto view = emboss::test::MakeLargeConditionalsView(&buffer);

  auto start = std::chrono::high_resolution_clock::now();
  int iterations = 10000;
  volatile bool result = false;
  for (int i = 0; i < iterations; ++i) {
    for (int tag = 0; tag < 100; ++tag) {
      view.tag().Write(tag);
      result = view.Ok();
    }
  }
  auto end = std::chrono::high_resolution_clock::now();

  std::chrono::duration<double> elapsed = end - start;
  // We don't strictly fail on time, but we print it.
  // In a real CI system we might assert upper bounds.
  std::cout << "Time for " << iterations
            << " iterations (x100 tags): " << elapsed.count() << "s"
            << std::endl;

  EXPECT_TRUE(result);
  EXPECT_TRUE(view.Ok());
}

TEST(ComplexConditionals, DuplicateCaseValueFallthrough) {
  std::vector<char> buffer(8, 0);
  auto view = emboss::test::MakeLargeConditionalsView(&buffer);
  view.tag().Write(0);
  EXPECT_FALSE(view.Ok());
}

TEST(DisjunctionConditionals, OkAcrossTagSpace) {
  // Exercises the disjunction-of-equality matching path: each conditional
  // field is guarded by an `||` chain over the same discriminant, so the
  // generator should produce one multi-label switch arm per group rather
  // than a chain of redundant per-disjunct if-statements.
  std::vector<char> buffer(8, 0);
  auto view = emboss::test::MakeDisjunctionConditionalsView(&buffer);
  auto start = std::chrono::high_resolution_clock::now();
  int iterations = 10000;
  volatile bool result = false;
  for (int i = 0; i < iterations; ++i) {
    for (int tag : {0, 1, 2, 10, 11, 100, 200, 300, 7, 50, 999}) {
      view.tag().Write(tag);
      result = view.Ok();
    }
  }
  auto end = std::chrono::high_resolution_clock::now();
  std::chrono::duration<double> elapsed = end - start;
  std::cout << "DisjunctionConditionals: " << iterations
            << " iterations (x11 tags): " << elapsed.count() << "s"
            << std::endl;
  EXPECT_TRUE(result);
}

}  // namespace
}  // namespace test
}  // namespace emboss
