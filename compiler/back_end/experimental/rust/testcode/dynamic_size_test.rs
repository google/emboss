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

pub use testdata_dynamic_size_emb::*;
use emboss_runtime::{CheckComplete, CheckOk, InfallibleRead};

#[test]
fn test_chained_size_in_order() {
    let bytes = [0x01, 0x02, 0x03, 0x04];
    let view = ChainedSize::new(&bytes[..]);
    
    // a is at 0 -> 1
    assert_eq!(view.a().try_read(), Ok(1));
    // b is at a (1) -> 2
    assert_eq!(view.b().try_read(), Ok(2));
    // c is at b (2) -> 3
    assert_eq!(view.c().try_read(), Ok(3));
    // d is at c (3) -> 4
    assert_eq!(view.d().try_read(), Ok(4));
}

#[test]
fn test_chained_size_mut() {
    let mut bytes = [0x01, 0x02, 0x03, 0x04];
    let mut view = ChainedSizeMut::new(&mut bytes[..]);
    
    assert_eq!(view.a().try_read(), Ok(1));
    view.b().try_write(5).unwrap();
    
    assert_eq!(bytes[1], 5);
}

#[test]
fn test_negative_term_in_location_valid() {
    let mut bytes = [0u8; 16];
    bytes[0] = 5; // a = 5
    bytes[5] = 42; // b at 10 - 5 = 5
    
    let view = NegativeTermInLocation::new(&bytes[..]);
    assert_eq!(view.a().try_read(), Ok(5));
    assert_eq!(view.b().try_read(), Ok(42));
}

#[test]
fn test_dynamic_overlap() {
    let mut bytes = [0u8; 16];
    bytes[0] = 4; // a = 4
    bytes[9] = 2; // b = 2
    bytes[4] = 7; // c at 4
    bytes[5] = 8; // d at a+1 = 5
    
    let view = DynamicFinalFieldOverlaps::new(&bytes[..]);
    assert_eq!(view.a().try_read(), Ok(4));
    assert_eq!(view.b().try_read(), Ok(2));
    assert_eq!(view.d().try_read(), Ok(8));
}

#[test]
fn test_chained_size_writer_typestates() {
    let mut bytes = [0x01, 0x02, 0x03, 0x04];
    let writer = ChainedSizeMut::new(&mut bytes[..])
        .into_writer()
        .check_ok()
        .expect("ok writer");

    // Mutating `d` (non-layout dependency) invalidates OkState to CompleteState
    let complete_writer = writer.write_d(42);
    assert_eq!(complete_writer.as_view().d().try_read(), Ok(42));

    // Re-checking ok upgrades CompleteState back to OkState, re-enabling infallible read
    let ok_writer = complete_writer.check_ok().expect("re-checked ok");
    assert_eq!(ok_writer.into_view().d().read(), 42);

    let writer = ChainedSizeMut::new(&mut bytes[..])
        .into_writer()
        .check_ok()
        .expect("ok writer");

    // Mutating `a` (layout dependency) degrades state to UncheckedState
    let unchecked_writer = writer.write_a(1);
    let ok_writer = unchecked_writer.check_ok().expect("re-checked ok");
    assert_eq!(ok_writer.into_view().a().read(), 1);
}

#[test]
fn test_ok_state_infallible_read() {
    let mut bytes = vec![0u8; 14];
    bytes[0] = 4; // h = 4
    bytes[1] = 6; // m = 6

    let view = message::View::new(&bytes[..]);
    // CompleteState: complete layout, but not Ok, so infallible read is not exposed; try_read works
    let complete_view = view.check_complete().expect("should be complete");
    assert_eq!(complete_view.header_length().try_read().unwrap(), 4);

    // OkState: check_ok produces an Ok view with infallible read exposed!
    let ok_view = complete_view.check_ok().expect("should be ok");
    assert_eq!(ok_view.header_length().read(), 4);
    assert_eq!(ok_view.message_length().read(), 6);

    // Can also check_ok directly from unchecked view:
    let ok_view_direct = message::View::new(&bytes[..]).check_ok().expect("should be ok");
    assert_eq!(ok_view_direct.header_length().read(), 4);
}

#[test]
fn test_dynamic_size_bounds_and_view() {
    use testdata_dynamic_size_emb::message;
    use emboss_runtime::View;

    assert_eq!(message::MIN_SIZE_IN_BYTES, 4);
    assert_eq!(message::MAX_SIZE_IN_BYTES, 514);

    // Message layout:
    // 0: header_length (h)
    // 1: message_length (m)
    // 2..h: padding (h - 2)
    // h..h+m: message (m)
    // h+m..h+m+4: crc32 (4)
    // Total size = h + m + 4
    let mut bytes = vec![0u8; 14];
    bytes[0] = 4; // h = 4
    bytes[1] = 6; // m = 6

    let view = message::View::new(&bytes[..]);
    assert_eq!(view.size_in_bytes().unwrap(), 14);

    // check_complete succeeds when buffer length >= 14
    let complete = view.check_complete().expect("should be complete");
    assert_eq!(complete.size_in_bytes().unwrap(), 14);

    // Truncated buffer: only 10 bytes available
    let truncated_view = message::View::new(&bytes[..10]);
    assert_eq!(truncated_view.size_in_bytes().unwrap(), 14);
    assert!(truncated_view.check_complete().is_err());
}
