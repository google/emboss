use emboss_runtime::Error;
use testdata_next_keyword_emb::*;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_next_keyword_fields_are_correctly_located() {
        let values: [u8; 11] = [1, 0, 0, 0, 2, 0, 3, 5, 6, 7, 4];

        let view = NextKeyword::new(&values[..]);

        // Native reading
        let val32: u32 = view.value32().try_read().unwrap();
        assert_eq!(val32, 1);

        let val16: u16 = view.value16().try_read().unwrap();
        assert_eq!(val16, 2);

        let val8: u8 = view.value8().try_read().unwrap();
        assert_eq!(val8, 3);

        let val8_off: u8 = view.value8_offset().try_read().unwrap();
        assert_eq!(val8_off, 4);
    }

    #[test]
    fn test_out_of_bounds() {
        let values: [u8; 2] = [1, 0]; // Too short
        let view = NextKeyword::new(&values[..]);
        assert_eq!(view.value32().try_read(), Err(Error::OutOfBounds));
    }
}
