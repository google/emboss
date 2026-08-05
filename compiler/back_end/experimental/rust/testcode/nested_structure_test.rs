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

use emboss_runtime::{Error, IsComplete, TryRead, TryWrite};

#[test]
fn container_field_values_are_correct() {
    let container: &[u8] = &[
        0x28, 0x00, 0x00, 0x00, // 0:4    weight == 40
        0x78, 0x56, 0x34, 0x12, // 4:8    important_box.id == 0x12345678
        0x03, 0x02, 0x01, 0x00, // 8:12   important_box.count == 0x010203
        0x21, 0x43, 0x65, 0x87, // 12:16  other_box.id == 0x87654321
        0xcc, 0xbb, 0xaa, 0x00, // 16:20  other_box.count == 0xaabbcc
    ];

    let view = testdata_nested_structure_emb::Container::new(container);
    assert!(IsComplete::is_complete(&view));

    // Static explicit typing assertions
    let weight: u32 = view.weight().try_read().unwrap();
    assert_eq!(weight, 40);

    let important_box = view.important_box();
    assert!(IsComplete::is_complete(&important_box));
    let important_box_id: u32 = important_box.id().try_read().unwrap();
    assert_eq!(important_box_id, 0x12345678);
    let important_box_count: u32 = important_box.count().try_read().unwrap();
    assert_eq!(important_box_count, 0x010203);

    let other_box = view.other_box();
    assert!(IsComplete::is_complete(&other_box));
    let other_box_id: u32 = other_box.id().try_read().unwrap();
    assert_eq!(other_box_id, 0x87654321);
    let other_box_count: u32 = other_box.count().try_read().unwrap();
    assert_eq!(other_box_count, 0xaabbcc);
}

#[test]
fn nested_out_of_bounds_handles_cascading_reads_dynamically() {
    let container: &[u8] = &[
        0x28, 0x00, 0x00, 0x00, // 0:4    weight == 40
        0x78, 0x56, 0x34, 0x12, // 4:8    important_box.id == 0x12345678
        0x03, 0x02, 0x01, 0x00, // 8:12   important_box.count == 0x010203
    ]; // TRUNCATED struct! Missing the entire 8 bytes of other_box!

    let view = testdata_nested_structure_emb::Container::new(container);
    assert!(!IsComplete::is_complete(&view));

    assert_eq!(view.weight().try_read().unwrap(), 40);
    let important_box = view.important_box();
    assert!(IsComplete::is_complete(&important_box));
    assert_eq!(important_box.id().try_read().unwrap(), 0x12345678);
    assert_eq!(important_box.count().try_read().unwrap(), 0x010203);

    let other_box = view.other_box();
    assert!(!other_box.is_complete());
    assert_eq!(other_box.id().try_read(), Err(Error::OutOfBounds));
    assert_eq!(other_box.count().try_read(), Err(Error::OutOfBounds));
}

#[test]
fn method_syntax_and_mutation() {
    let mut container = vec![0u8; 20];
    let mut view = testdata_nested_structure_emb::ContainerMut::new(&mut container[..]);

    assert!(view.is_complete());

    let mut important_box = view.important_box();
    assert!(important_box.is_complete());
    unsafe { important_box.id().write_unchecked(0x12345678) };

    assert_eq!(unsafe { view.important_box().id().read_unchecked() }, 0x12345678);
}


