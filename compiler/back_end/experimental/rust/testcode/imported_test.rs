use emboss_runtime::{prelude::*, Error};
use testdata_imported_emb::*;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_imported_inner_field_read() {
        let values: [u8; 8] = [42, 0, 0, 0, 0, 0, 0, 0];

        let view = Inner::new(&values[..]);
        let _value_type_check: Result<u64, Error> = view.value().try_read();

        assert_eq!(view.value().try_read().unwrap(), 42);
    }

    #[test]
    fn test_out_of_bounds() {
        let values: [u8; 1] = [42]; // Too short
        let view = Inner::new(&values[..]);
        assert_eq!(view.value().try_read(), Err(Error::OutOfBounds));
    }
}
