use auto_array_size_emb_rs::*;

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
    
    // let's try getting index 0
    let element0 = dyn_struct_array.get(0).unwrap();
    assert_eq!(element0.a().try_read().unwrap(), 0);
    
    // get index 3 which is OutOfBounds because count is 3 (valid indices are 0, 1, 2)
    let res = dyn_struct_array.get(3);
    assert!(res.is_err());
}
