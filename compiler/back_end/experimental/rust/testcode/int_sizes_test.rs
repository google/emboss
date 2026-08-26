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

use emboss_runtime::CheckComplete;

#[test]
fn reads_int_sizes_correctly() {
    let container: &[u8] = &[
        0x02, // 0:1    one_byte == 2
        0xfc, 0xfe, // 1:3    two_byte == -260
        0x66, 0x55, 0x44, // 3:6    three_byte == 0x445566
        0xfa, 0xfa, 0xfb, 0xfc, // 6:10   four_byte == -0x03040506
        0x21, 0x43, 0x65, 0x87, // 10:14  five_byte
        0x29, // 14:15  five_byte == 0x2987654321
        0x44, 0x65, 0x87, 0xa9, // 15:19  six_byte
        0xcb, 0xed, // 19:21  six_byte == -0x123456789abc
        0x97, 0xa6, 0xb5, 0xc4, // 21:25  seven_byte
        0xd3, 0xe2, 0x71, // 25:28  seven_byte == 0x71e2d3c4b5a697
        0xfa, 0xfa, 0xfb, 0xfc, // 28:32  eight_byte
        0xfd, 0xfe, 0xff, 0x80, // 32:36  eight_byte == -0x7f00010203040506
    ];

    let view = testdata_int_sizes_emb::Sizes::new(container);

    assert_eq!(view.one_byte().try_read().unwrap(), 2i8);
    assert_eq!(view.two_byte().try_read().unwrap(), -260i16);
    assert_eq!(view.three_byte().try_read().unwrap(), 0x445566i32);
    assert_eq!(view.four_byte().try_read().unwrap(), -0x03040506i32);
    assert_eq!(view.five_byte().try_read().unwrap(), 0x2987654321i64);
    assert_eq!(view.six_byte().try_read().unwrap(), -0x123456789abci64);
    assert_eq!(view.seven_byte().try_read().unwrap(), 0x71e2d3c4b5a697i64);
    assert_eq!(
        view.eight_byte().try_read().unwrap(),
        -0x7f00010203040506i64
    );
}

#[test]
fn reads_negative_ones_correctly() {
    let container: &[u8] = &[0xff; 36];
    let view = testdata_int_sizes_emb::Sizes::new(container);

    assert_eq!(view.one_byte().try_read().unwrap(), -1i8);
    assert_eq!(view.two_byte().try_read().unwrap(), -1i16);
    assert_eq!(view.three_byte().try_read().unwrap(), -1i32);
    assert_eq!(view.four_byte().try_read().unwrap(), -1i32);
    assert_eq!(view.five_byte().try_read().unwrap(), -1i64);
    assert_eq!(view.six_byte().try_read().unwrap(), -1i64);
    assert_eq!(view.seven_byte().try_read().unwrap(), -1i64);
    assert_eq!(view.eight_byte().try_read().unwrap(), -1i64);
}

#[test]
fn owned_storage_and_clone() {
    let container = [0xffu8; 36];
    let view = testdata_int_sizes_emb::Sizes::new(container);
    let cloned_view = view.clone();

    assert_eq!(view.one_byte().try_read().unwrap(), -1i8);
    assert_eq!(cloned_view.one_byte().try_read().unwrap(), -1i8);

    let vec_container = vec![0xffu8; 36];
    let vec_view = testdata_int_sizes_emb::Sizes::new(vec_container);
    let cloned_vec_view = vec_view.clone();

    assert_eq!(vec_view.two_byte().try_read().unwrap(), -1i16);
    assert_eq!(cloned_vec_view.two_byte().try_read().unwrap(), -1i16);
}

#[test]
fn writes_int_sizes_with_writer() {
    let mut container = [0u8; 36];
    let writer = testdata_int_sizes_emb::SizesMut::new(&mut container[..])
        .into_writer()
        .check_complete()
        .expect("complete sizes writer");

    let _writer = writer
        .write_one_byte(2)
        .write_two_byte(-260)
        .write_three_byte(0x445566)
        .write_four_byte(-0x03040506)
        .write_five_byte(0x2987654321)
        .write_six_byte(-0x123456789abc)
        .write_seven_byte(0x71e2d3c4b5a697)
        .write_eight_byte(-0x7f00010203040506);

    let view = testdata_int_sizes_emb::Sizes::new(&container[..]);
    assert_eq!(view.one_byte().try_read().unwrap(), 2i8);
    assert_eq!(view.two_byte().try_read().unwrap(), -260i16);
    assert_eq!(view.three_byte().try_read().unwrap(), 0x445566i32);
    assert_eq!(view.four_byte().try_read().unwrap(), -0x03040506i32);
    assert_eq!(view.five_byte().try_read().unwrap(), 0x2987654321i64);
    assert_eq!(view.six_byte().try_read().unwrap(), -0x123456789abci64);
    assert_eq!(view.seven_byte().try_read().unwrap(), 0x71e2d3c4b5a697i64);
    assert_eq!(view.eight_byte().try_read().unwrap(), -0x7f00010203040506i64);
}

#[test]
fn test_sizes_metadata_and_view_trait() {
    use testdata_int_sizes_emb::sizes;
    use emboss_runtime::View;

    // Module constants
    assert_eq!(sizes::MIN_SIZE_IN_BYTES, 36);
    assert_eq!(sizes::MAX_SIZE_IN_BYTES, 36);
    assert_eq!(sizes::SIZE_IN_BYTES, 36);

    // Static buffer allocation with module constants
    let mut buf = [0u8; sizes::SIZE_IN_BYTES];

    // Aliased types in the module
    let view = sizes::View::new(&buf[..]);
    assert_eq!(view.size_in_bytes().unwrap(), 36);

    let view_mut = sizes::ViewMut::new(&mut buf[..]);
    assert_eq!(view_mut.size_in_bytes().unwrap(), 36);

    let writer = sizes::Writer::new(&mut buf[..]);
    assert_eq!(writer.size_in_bytes().unwrap(), 36);
}
