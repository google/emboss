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

//! Compile-time typestate markers and traits for Emboss views and writers.

/// Unchecked view or field state. Requires runtime-checked `try_` accessors.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Default)]
pub struct UncheckedState;

/// Complete view state. All fields in the current layout are infallible.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Default)]
pub struct CompleteState;

/// Typestate transition trait for layout and validation mutations.
pub trait State {
    type OnLayoutMutation: State;
    type OnValidMutation: State;
}

impl State for UncheckedState {
    type OnLayoutMutation = UncheckedState;
    type OnValidMutation = UncheckedState;
}

impl State for CompleteState {
    type OnLayoutMutation = UncheckedState;
    type OnValidMutation = CompleteState;
}

/// Marker trait for states that guarantee full layout completeness.
pub trait IsComplete: State {}
impl IsComplete for CompleteState {}

/// Infallible read operation for views in a verified typestate (`IsComplete`).
pub trait InfallibleRead {
    type ReadValue;
    fn read(&self) -> Self::ReadValue;
}

/// Infallible write operation for views in a verified typestate (`IsComplete`), consuming self and transitioning to the mutated state.
pub trait InfallibleWrite {
    type WriteValue;
    type Output;
    fn write(self, val: Self::WriteValue) -> Self::Output;
}

/// Trait for verifying dynamic layout completeness at runtime, upgrading the typestate to `CompleteState`.
pub trait CheckComplete {
    type Completed;
    fn check_complete(self) -> Result<Self::Completed, crate::Error>;
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{LittleEndian, Storage, UInt};

    const TEST_VALUE: u32 = 0x12345678;

    fn assert_state<S: State>() {}
    fn assert_complete<S: IsComplete>() {}
    #[test]
    fn test_state_marker_traits() {
        assert_state::<UncheckedState>();
        assert_state::<CompleteState>();

        assert_complete::<CompleteState>();
    }

    #[test]
    fn test_on_layout_mutation_transitions() {
        fn assert_is_unchecked<S: Storage>(_view: &UInt<32, LittleEndian, S, UncheckedState>) {}

        let mut buf = [0u8; 4];
        let complete_view =
            UInt::<32, LittleEndian, &mut [u8; 4], CompleteState>::new(&mut buf);
        assert_eq!(complete_view.read(), 0);

        // Performing a write consumes the CompleteState view and degrades its state to UncheckedState.
        let mutated_view = complete_view.write(TEST_VALUE);
        assert_is_unchecked(&mutated_view);

        // The degraded view in UncheckedState must use checked reading.
        assert_eq!(mutated_view.try_read().expect("valid read"), TEST_VALUE);
    }

    #[test]
    fn test_infallible_uint_read_write() {
        let mut buf = [0u8; 4];
        let uint_view = UInt::<32, LittleEndian, &mut [u8; 4], CompleteState>::new(&mut buf);
        let _ = uint_view.write(TEST_VALUE);
        let read_view = UInt::<32, LittleEndian, &[u8; 4], CompleteState>::new(&buf);
        assert_eq!(read_view.read(), TEST_VALUE);
    }
}
