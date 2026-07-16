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

pub use testdata_enum_emb::*;

#[test]
fn generates_correct_enum_variants() {
    assert_eq!(Kind::WIDGET as u64, 0);
    assert_eq!(Kind::SPROCKET as u64, 1);
    assert_eq!(Kind::GEEGAW as u64, 2);
    assert_eq!(
        Kind::COMPUTED as u64,
        Kind::GEEGAW as u64 + Kind::SPROCKET as u64
    );
    assert_eq!(Kind::MAX32BIT as u64, 4294967295);
    assert_eq!(Kind::LARGE_VALUE as u64, 2000);
    assert_eq!(Kind::DUPLICATE_LARGE_VALUE as u64, 2000);
}

#[test]
fn can_read_kind() {
    let k_manifest_entry: [u8; 14] = [
        0x01,                          // 0:1  Kind  kind == SPROCKET
        0x04, 0x00, 0x00, 0x00,        // 1:5  UInt  count == 4
        0x02, 0x00, 0x00, 0x00,        // 5:9  Kind  wide_kind == GEEGAW
        0x20, 0x00, 0x00, 0x00, 0x00,  // 9:14 Kind  wide_kind_in_bits == GEEGAW
    ];
    let view = ManifestEntry::new(&k_manifest_entry);
    
    assert_eq!(view.kind().try_read().unwrap(), Kind::SPROCKET);
    assert_eq!(view.count().try_read().unwrap(), 4);
    assert_eq!(view.wide_kind().try_read().unwrap(), Kind::GEEGAW);
}

#[test]
fn edge_cases_unknown_enum() {
    let k_manifest_entry_edge_cases: [u8; 14] = [
        0xff,                          // 0:1  Kind  kind == 0xff
        0x04, 0x00, 0x00, 0x00,        // 1:5  UInt  count == 4
        0xff, 0xff, 0xff, 0xff,        // 5:9  Kind  wide_kind == MAX32BIT
        0xf0, 0xff, 0xff, 0xff, 0x0f,  // 9:14 Kind  wide_kind_in_bits == GEEGAW
    ];
    let view = ManifestEntry::new(&k_manifest_entry_edge_cases);
    
    assert_eq!(view.kind().try_read().unwrap_err(), emboss_runtime::Error::UnknownEnum(255));
    assert_eq!(view.count().try_read().unwrap(), 4);
    assert_eq!(view.wide_kind().try_read().unwrap(), Kind::MAX32BIT);
}

#[test]
fn can_write_kind() {
    let mut buffer = [0u8; 14];
    let mut writer = ManifestEntryMut::new(&mut buffer);
    
    writer.kind().try_write(Kind::SPROCKET).unwrap();
    writer.count().try_write(4).unwrap();
    writer.wide_kind().try_write(Kind::GEEGAW).unwrap();
    
    let k_manifest_entry: [u8; 14] = [
        0x01,                          // 0:1  Kind  kind == SPROCKET
        0x04, 0x00, 0x00, 0x00,        // 1:5  UInt  count == 4
        0x02, 0x00, 0x00, 0x00,        // 5:9  Kind  wide_kind == GEEGAW
        0x00, 0x00, 0x00, 0x00, 0x00,  // wide_kind_in_bits unwritten
    ];
    assert_eq!(&buffer[..], &k_manifest_entry[..]);
}
