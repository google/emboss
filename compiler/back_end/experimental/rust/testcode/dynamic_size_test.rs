pub use dynamic_size_emb_rs::*;
use emboss_runtime::{prelude::*, Error};

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
