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

use emboss_runtime::Error;
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
