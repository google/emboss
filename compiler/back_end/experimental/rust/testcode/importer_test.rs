use testdata_importer_emb::{Outer, OuterMut};

#[test]
fn test_importer() {
    let mut buf = [0u8; 16];
    let mut importer = OuterMut::new(&mut buf[..]);
    
    // We should be able to access the nested imported inner struct.
    let mut inner = importer.inner();
    let mut value = inner.value();
    value.try_write(1234).unwrap();
    
    let importer_ro = Outer::new(&buf[..]);
    assert_eq!(importer_ro.inner().value().try_read().unwrap(), 1234);
}
