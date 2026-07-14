use emboss_runtime::{prelude::*, Error};

#[test]
fn container_field_values_are_correct() {
    let container: &[u8] = &[
        0x28, 0x00, 0x00, 0x00, // 0:4    weight == 40
        0x78, 0x56, 0x34, 0x12, // 4:8    important_box.id == 0x12345678
        0x03, 0x02, 0x01, 0x00, // 8:12   important_box.count == 0x010203
        0x21, 0x43, 0x65, 0x87, // 12:16  other_box.id == 0x87654321
        0xcc, 0xbb, 0xaa, 0x00, // 16:20  other_box.count == 0xaabbcc
    ];

    let view = nested_structure_emb_rs::Container::new(container);

    // Static explicit typing assertions
    let weight: u32 = view.weight().try_read().unwrap();
    assert_eq!(weight, 40);

    let important_box = view.important_box();
    let important_box_id: u32 = important_box.id().try_read().unwrap();
    assert_eq!(important_box_id, 0x12345678);
    let important_box_count: u32 = important_box.count().try_read().unwrap();
    assert_eq!(important_box_count, 0x010203);

    let other_box = view.other_box();
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

    let view = nested_structure_emb_rs::Container::new(container);

    // weight and important_box can still be read successfully cleanly over the bounds organically
    assert_eq!(view.weight().try_read().unwrap(), 40);
    let important_box = view.important_box();
    assert_eq!(important_box.id().try_read().unwrap(), 0x12345678);
    assert_eq!(important_box.count().try_read().unwrap(), 0x010203);

    // structurally other_box cleanly passes the Slice but natively aborts safely during Read because of OutOfBounds bounds over exactly its byte size safely propagating Error organically natively
    let other_box = view.other_box();
    assert_eq!(other_box.id().try_read(), Err(Error::OutOfBounds));
    assert_eq!(other_box.count().try_read(), Err(Error::OutOfBounds));
}
