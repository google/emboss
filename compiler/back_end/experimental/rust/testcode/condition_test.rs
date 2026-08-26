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

use emboss_runtime::{CheckComplete, CheckOk};
pub use testdata_condition_emb::*;

#[test]
fn test_conditional_on_flag_size_and_read() {
    // When enabled is false (bit 0 is 0):
    // Size required is 1 byte.
    let bytes_disabled = [0x00];
    let view_disabled = ConditionalOnFlag::new(&bytes_disabled[..]);

    assert_eq!(view_disabled.enabled().try_read(), Ok(false));
    assert_eq!(view_disabled.size_in_bytes(), Ok(1));

    let ok_disabled = view_disabled.check_ok().expect("ok view");
    let enabled_val: bool = ok_disabled.enabled().read();
    assert!(!enabled_val);

    // When enabled is true (bit 0 is 1):
    // Size required is 2 bytes (offset 1 + size 1 for value).
    let bytes_enabled = [0x01, 0x42];
    let view_enabled = ConditionalOnFlag::new(&bytes_enabled[..]);

    assert_eq!(view_enabled.enabled().try_read(), Ok(true));
    assert_eq!(view_enabled.size_in_bytes(), Ok(2));

    let ok_enabled = view_enabled.check_ok().expect("ok view");
    let enabled_val: bool = ok_enabled.enabled().read();
    assert!(enabled_val);

    // If buffer only has 1 byte but flag is enabled, size check fails:
    let bytes_truncated = [0x01];
    let view_truncated = ConditionalOnFlag::new(&bytes_truncated[..]);
    assert_eq!(view_truncated.size_in_bytes(), Ok(2));
    assert!(view_truncated.check_complete().is_err());

    // Module size constants:
    assert_eq!(conditional_on_flag::MIN_SIZE_IN_BYTES, 1);
    assert_eq!(conditional_on_flag::MAX_SIZE_IN_BYTES, 2);
}
