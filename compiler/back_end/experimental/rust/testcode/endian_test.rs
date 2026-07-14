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

use emboss_runtime::Error;

#[test]
fn reads_endian_values_correctly() {
    let container: &[u8] = &[
        0x78, 0x56, 0x34, 0x12, // 0:4 little_uint32 == 0x12345678 (Little Endian)
        0x12, 0x34, 0x56, 0x78, // 4:8 big_uint32 == 0x12345678 (Big Endian)
        0xAB, // 8:9 single_byte == 0xAB
    ];

    let view = endian_emb_rs::Message::new(container);

    let little_val: u32 = view.little_uint32().try_read().unwrap();
    assert_eq!(little_val, 0x12345678);

    let big_val: u32 = view.big_uint32().try_read().unwrap();
    assert_eq!(big_val, 0x12345678);

    let byte_val: u8 = view.single_byte().try_read().unwrap();
    assert_eq!(byte_val, 0xAB);
}

#[test]
fn handles_endian_out_of_bounds() {
    let container: &[u8] = &[
        0x78, 0x56, 0x34, 0x12, // 0:4 little_uint32 == 0x12345678
        0x12, 0x34, 0x56, // TRUNCATED 4:7
    ];

    let view = endian_emb_rs::Message::new(container);

    let little_val: u32 = view.little_uint32().try_read().unwrap();
    assert_eq!(little_val, 0x12345678);

    assert_eq!(view.big_uint32().try_read(), Err(Error::OutOfBounds));
    assert_eq!(view.single_byte().try_read(), Err(Error::OutOfBounds));
}

#[test]
fn writes_endian_values_correctly() {
    let mut container: [u8; 9] = [0; 9];
    {
        let mut view = endian_emb_rs::MessageMut::new(&mut container[..]);
        view.little_uint32().try_write(0x12345678).unwrap();
        view.big_uint32().try_write(0x12345678).unwrap();
        view.single_byte().try_write(0xAB).unwrap();
    }
    let expected: &[u8] = &[
        0x78, 0x56, 0x34, 0x12, // 0:4 little_uint32 == 0x12345678 (Little Endian)
        0x12, 0x34, 0x56, 0x78, // 4:8 big_uint32 == 0x12345678 (Big Endian)
        0xAB, // 8:9 single_byte == 0xAB
    ];
    assert_eq!(&container[..], expected);
}

#[test]
fn handles_endian_write_out_of_bounds() {
    let mut container: [u8; 7] = [0; 7];
    let mut view = endian_emb_rs::MessageMut::new(&mut container[..]);

    assert!(view.little_uint32().try_write(0x12345678).is_ok());
    assert_eq!(view.big_uint32().try_write(0x12345678), Err(Error::OutOfBounds));
    assert_eq!(view.single_byte().try_write(0xAB), Err(Error::OutOfBounds));
}
