#include <gtest/gtest.h>

#include <cstddef>
#include <vector>

#include "runtime/cpp/test/util/noncontiguous_container.h"
#include "testdata/alignments.emb.h"
#include "testdata/condition.emb.h"
#include "testdata/dynamic_size.emb.h"
#include "testdata/uint_sizes.emb.h"
#include "testdata/virtual_field.emb.h"

namespace emboss {
namespace test {
namespace {

template <typename CharT>
void TestMakeAlignmentsViewIntegration() {
  using ByteT = typename std::remove_const<CharT>::type;

  std::vector<std::vector<ByteT>> chunks = {
      {ByteT(0x11), ByteT(0x22)},
      {ByteT(0x33), ByteT(0x44), ByteT(0x55)},
      {ByteT(0x66), ByteT(0x77), ByteT(0x88)},
      {ByteT(0x00), ByteT(0x00), ByteT(0x00), ByteT(0x00)},
      {ByteT(0x00), ByteT(0x00), ByteT(0x00), ByteT(0x00)},
      {ByteT(0x00), ByteT(0x00), ByteT(0x00), ByteT(0x00)},
      {ByteT(0x00), ByteT(0x00), ByteT(0x00), ByteT(0x00)},
      {ByteT(0x00), ByteT(0x00), ByteT(0x00), ByteT(0x00)}};

  ::emboss::support::test::NoncontiguousContainer<ByteT> container(chunks);

  auto view = MakeAlignmentsView(container);
  EXPECT_TRUE(view.Ok());
  EXPECT_EQ(view.SizeInBytes(), 28U);

  EXPECT_EQ(view.zero_offset().dummy().Read(), 0x11223344U);
  EXPECT_EQ(view.three_offset().dummy().Read(), 0x44556677U);
  EXPECT_EQ(view.four_offset().dummy().Read(), 0x55667788U);
}

TEST(IteratorViewIntegrationTest, MakeAlignmentsView) {
  TestMakeAlignmentsViewIntegration<const char>();
  TestMakeAlignmentsViewIntegration<char>();
  TestMakeAlignmentsViewIntegration<const unsigned char>();
  TestMakeAlignmentsViewIntegration<unsigned char>();
#if __cplusplus >= 201703L
  TestMakeAlignmentsViewIntegration<const std::byte>();
  TestMakeAlignmentsViewIntegration<std::byte>();
#endif
}

// ---------------------------------------------------------
// BasicConditional from condition.emb (LittleEndian)
// 0 [+1] UInt x; if x == 0: 1 [+1] UInt xc
// ---------------------------------------------------------

template <typename CharT>
void TestBasicConditionalViewIntegration() {
  using ByteT = typename std::remove_const<CharT>::type;

  std::vector<std::vector<ByteT>> chunks = {
      {ByteT(0x00)},  // x == 0
      {ByteT(0xAA)}   // xc == 0xAA
  };
  ::emboss::support::test::NoncontiguousContainer<ByteT> container(chunks);

  auto view = MakeBasicConditionalView(container);
  EXPECT_TRUE(view.Ok());
  EXPECT_EQ(view.SizeInBytes(), 2U);
  EXPECT_EQ(view.x().Read(), 0U);
  EXPECT_EQ(view.xc().Read(), 0xAAU);

  std::vector<std::vector<ByteT>> chunks2 = {
      {ByteT(0x01)},  // x == 1
  };
  ::emboss::support::test::NoncontiguousContainer<ByteT> container2(chunks2);
  auto view2 = MakeBasicConditionalView(container2);
  EXPECT_TRUE(view2.Ok());
  EXPECT_EQ(view2.SizeInBytes(), 1U);

  std::vector<std::vector<ByteT>> chunks_fail = {
      {ByteT(0x00)},  // x == 0
  };
  ::emboss::support::test::NoncontiguousContainer<ByteT> container_fail(
      chunks_fail);
  auto view_fail = MakeBasicConditionalView(container_fail);
  EXPECT_FALSE(view_fail.IsComplete());
}

TEST(IteratorViewIntegrationTest, BasicConditional) {
  TestBasicConditionalViewIntegration<char>();
  TestBasicConditionalViewIntegration<const char>();
  TestBasicConditionalViewIntegration<unsigned char>();
  TestBasicConditionalViewIntegration<const unsigned char>();
#if __cplusplus >= 201703L
  TestBasicConditionalViewIntegration<std::byte>();
  TestBasicConditionalViewIntegration<const std::byte>();
#endif
}

// ---------------------------------------------------------
// AlternatingEndianSizes from uint_sizes.emb
// Mixture of LittleEndian and BigEndian
// ---------------------------------------------------------
template <typename CharT>
void TestAlternatingEndianSizesViewIntegration() {
  using ByteT = typename std::remove_const<CharT>::type;

  std::vector<std::vector<ByteT>> chunks = {
      {ByteT(0x11)},               // one_byte (BigEndian)
      {ByteT(0x22), ByteT(0x33)},  // two_byte (LittleEndian) = 0x3322
      {ByteT(0x44)},               // split...
      {ByteT(0x55), ByteT(0x66)},  // three_byte (BigEndian) = 0x445566
      {ByteT(0x77), ByteT(0x88), ByteT(0x99),
       ByteT(0xAA)}  // four_byte (LittleEndian) = 0xAA998877
  };

  // Adding the rest to reach 36 bytes (8 fields)
  chunks.push_back(std::vector<ByteT>(26));

  ::emboss::support::test::NoncontiguousContainer<ByteT> container(chunks);

  auto view = MakeAlternatingEndianSizesView(container);
  EXPECT_TRUE(view.Ok());
  EXPECT_EQ(view.one_byte().Read(), 0x11U);
  EXPECT_EQ(view.two_byte().Read(), 0x3322U);
  EXPECT_EQ(view.three_byte().Read(), 0x445566U);
  EXPECT_EQ(view.four_byte().Read(), 0xAA998877U);
}

TEST(IteratorViewIntegrationTest, AlternatingEndianSizes) {
  TestAlternatingEndianSizesViewIntegration<char>();
  TestAlternatingEndianSizesViewIntegration<const char>();
  TestAlternatingEndianSizesViewIntegration<unsigned char>();
  TestAlternatingEndianSizesViewIntegration<const unsigned char>();
#if __cplusplus >= 201703L
  TestAlternatingEndianSizesViewIntegration<std::byte>();
  TestAlternatingEndianSizesViewIntegration<const std::byte>();
#endif
}

// ---------------------------------------------------------
// Message from dynamic_size.emb
// struct Message:
//   0   [+1]    UInt         header_length (h)
//   1   [+1]    UInt         message_length (m)
//   2   [+h-2]  UInt:8[h-2]  padding
//   h   [+m]    UInt:8[m]    message
//   h+m [+4]    UInt         crc32
// ---------------------------------------------------------
template <typename CharT>
void TestMessageDynamicSizeIntegration() {
  using ByteT = typename std::remove_const<CharT>::type;

  // h = 4, m = 3
  std::vector<std::vector<ByteT>> chunks = {
      {ByteT(4)},                                           // header_length
      {ByteT(3)},                                           // message_length
      {ByteT(0x00), ByteT(0x00)},                           // padding
      {ByteT(0xAA), ByteT(0xBB)},                           // message byte 0, 1
      {ByteT(0xCC)},                                        // message byte 2
      {ByteT(0x11), ByteT(0x22), ByteT(0x33), ByteT(0x44)}  // crc32
  };

  ::emboss::support::test::NoncontiguousContainer<ByteT> container(chunks);

  auto view = MakeMessageView(container);
  EXPECT_TRUE(view.Ok());
  EXPECT_EQ(view.SizeInBytes(), 11U);
  EXPECT_EQ(view.header_length().Read(), 4U);
  EXPECT_EQ(view.message_length().Read(), 3U);

  EXPECT_EQ(view.message()[0].Read(), 0xAAU);
  EXPECT_EQ(view.message()[1].Read(), 0xBBU);
  EXPECT_EQ(view.message()[2].Read(), 0xCCU);

  EXPECT_EQ(view.crc32().Read(), 0x44332211U);  // Little endian
}

TEST(IteratorViewIntegrationTest, MessageDynamicSize) {
  TestMessageDynamicSizeIntegration<char>();
  TestMessageDynamicSizeIntegration<const char>();
  TestMessageDynamicSizeIntegration<unsigned char>();
  TestMessageDynamicSizeIntegration<const unsigned char>();
#if __cplusplus >= 201703L
  TestMessageDynamicSizeIntegration<std::byte>();
  TestMessageDynamicSizeIntegration<const std::byte>();
#endif
}

// ---------------------------------------------------------
// UsesExternalSize
// ---------------------------------------------------------
template <typename CharT>
void TestUsesExternalSizeIntegration() {
  using ByteT = typename std::remove_const<CharT>::type;

  std::vector<std::vector<ByteT>> chunks = {
      {ByteT(0x11), ByteT(0x22), ByteT(0x33), ByteT(0x44)},
      {ByteT(0x55), ByteT(0x66), ByteT(0x77), ByteT(0x88)},
  };

  ::emboss::support::test::NoncontiguousContainer<ByteT> container(chunks);

  auto view = MakeUsesExternalSizeView(container);
  EXPECT_TRUE(view.Ok());
  EXPECT_EQ(view.x().value().Read(), 0x44332211U);
  EXPECT_EQ(view.y().value().Read(), 0x88776655U);
}

TEST(IteratorViewIntegrationTest, UsesExternalSize) {
  TestUsesExternalSizeIntegration<char>();
  TestUsesExternalSizeIntegration<const char>();
  TestUsesExternalSizeIntegration<unsigned char>();
  TestUsesExternalSizeIntegration<const unsigned char>();
#if __cplusplus >= 201703L
  TestUsesExternalSizeIntegration<std::byte>();
  TestUsesExternalSizeIntegration<const std::byte>();
#endif
}

}  // namespace
}  // namespace test
}  // namespace emboss
