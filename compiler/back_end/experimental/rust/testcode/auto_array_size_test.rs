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
use testdata_auto_array_size_emb::*;

#[test]
fn test_array_access() {
    let mut storage = vec![0u8; 22]; // Large enough for all arrays with a=3
    
    // Set array_size to something valid, e.g., 3
    storage[0] = 3; // a = 3 => array_size = 3
    
    let view = AutoSize::new(&storage[..]);
    // Validate the dynamic struct array size offsets
    // array_size is 'a' which is 3
    // byte_offset = 13 + 3 = 16
    // byte_length = a * 2 = 6
    // element_size = 2. element_count = byte_length / 2 = 3.
    assert_eq!(view.array_size().try_read().unwrap(), 3);
    
    let dyn_struct_array = view.dynamic_struct_array().unwrap();
    assert_eq!(dyn_struct_array.element_count(), 3); // 6 bytes / 2 bytes per struct = 3 structs!
    let cloned_array = dyn_struct_array.clone();
    assert_eq!(cloned_array.element_count(), 3);
    
    // let's try getting index 0
    let element0 = dyn_struct_array.get(0).unwrap();
    assert_eq!(element0.a().try_read().unwrap(), 0);
    let element0_cloned = cloned_array.get(0).unwrap();
    assert_eq!(element0_cloned.a().try_read().unwrap(), 0);
    
    // get index 3 which is OutOfBounds because count is 3 (valid indices are 0, 1, 2)
    let res = dyn_struct_array.get(3);
    assert!(res.is_err());
}
/// ```compile_fail
/// use emboss_runtime::CheckComplete;
/// use testdata_auto_array_size_emb::*;
///
/// let mut storage = [0u8; 22];
/// let writer = AutoSizeMut::new(&mut storage[..])
///     .into_writer()
///     .check_complete()
///     .unwrap();
///
/// let writer = writer.write_array_size(3);
/// // Fails at compile-time: write methods are not available on UncheckedState.
/// writer.write_array_size(3);
/// ```
#[test]
fn test_auto_size_writer_degrades_on_dynamic_field() {
    let mut storage = vec![0u8; 22];
    let writer = AutoSizeMut::new(&mut storage[..])
        .into_writer()
        .check_complete()
        .expect("complete auto size writer");

    // Writing array_size (layout dependency) degrades writer to UncheckedState
    let unchecked_writer = writer.write_array_size(3);
    let _complete_writer = unchecked_writer.check_complete().expect("re-checked complete");

    let view = AutoSize::new(&storage[..]);
    assert_eq!(view.array_size().try_read().unwrap(), 3);
    let dyn_struct_array = view.dynamic_struct_array().unwrap();
    assert_eq!(dyn_struct_array.element_count(), 3);
}
