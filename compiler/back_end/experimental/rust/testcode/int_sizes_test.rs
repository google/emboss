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

use emboss_runtime::{IsComplete, TryRead, TryWrite};

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

    assert!(view.is_complete());
    assert!(view.one_byte().is_complete());
    assert_eq!(unsafe { view.one_byte().read_unchecked() }, 2i8);
    assert_eq!(unsafe { view.two_byte().read_unchecked() }, -260i16);
    assert_eq!(unsafe { view.three_byte().read_unchecked() }, 0x445566i32);
    assert_eq!(unsafe { view.four_byte().read_unchecked() }, -0x03040506i32);
    assert_eq!(unsafe { view.five_byte().read_unchecked() }, 0x2987654321i64);
    assert_eq!(unsafe { view.six_byte().read_unchecked() }, -0x123456789abci64);
    assert_eq!(unsafe { view.seven_byte().read_unchecked() }, 0x71e2d3c4b5a697i64);
    assert_eq!(
        unsafe { view.eight_byte().read_unchecked() },
        -0x7f00010203040506i64
    );

    let incomplete_view = testdata_int_sizes_emb::Sizes::new(&container[..10]);
    assert!(!incomplete_view.is_complete());
}

#[test]
fn writes_int_sizes_infallibly() {
    let mut container = vec![0u8; 36];
    let mut view = testdata_int_sizes_emb::SizesMut::new(&mut container[..]);

    assert!(view.is_complete());
    unsafe { view.one_byte().write_unchecked(42i8) };
    unsafe { view.two_byte().write_unchecked(-260i16) };

    assert_eq!(unsafe { view.one_byte().read_unchecked() }, 42i8);
    assert_eq!(unsafe { view.two_byte().read_unchecked() }, -260i16);
}

#[test]
fn reads_negative_ones_correctly() {
    let container: &[u8] = &[0xff; 36];
    let view = testdata_int_sizes_emb::Sizes::new(container);

    assert!(view.is_complete());
    assert_eq!(unsafe { view.one_byte().read_unchecked() }, -1i8);
    assert_eq!(unsafe { view.two_byte().read_unchecked() }, -1i16);
    assert_eq!(unsafe { view.three_byte().read_unchecked() }, -1i32);
    assert_eq!(unsafe { view.four_byte().read_unchecked() }, -1i32);
    assert_eq!(unsafe { view.five_byte().read_unchecked() }, -1i64);
    assert_eq!(unsafe { view.six_byte().read_unchecked() }, -1i64);
    assert_eq!(unsafe { view.seven_byte().read_unchecked() }, -1i64);
    assert_eq!(unsafe { view.eight_byte().read_unchecked() }, -1i64);
}

