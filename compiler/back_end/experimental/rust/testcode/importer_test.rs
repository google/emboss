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

#[test]
fn test_importer_nested_writer() {
    let mut buf = [0u8; 16];
    let inner_writer = testdata_imported_emb::InnerMut::new(&mut buf[..8])
        .into_writer()
        .check_complete()
        .expect("complete inner writer");
    let _ = inner_writer.write_value(1234);

    let importer_ro = Outer::new(&buf[..]);
    assert_eq!(importer_ro.inner().value().try_read().unwrap(), 1234);
}
