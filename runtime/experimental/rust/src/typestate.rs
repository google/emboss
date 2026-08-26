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

/// Complete view state. All fields in the current layout fit within storage.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Default)]
pub struct CompleteState;

/// Ok view state. All fields in the current layout fit within storage and are valid.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Default)]
pub struct OkState;

/// Alias for `OkState`.
pub type Ok = OkState;

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

impl State for OkState {
    type OnLayoutMutation = UncheckedState;
    type OnValidMutation = CompleteState;
}

/// Marker trait for states that guarantee full layout completeness.
pub trait IsComplete: State {}
impl IsComplete for CompleteState {}
impl IsComplete for OkState {}

/// Marker trait for states that guarantee layout completeness and validity.
pub trait IsOk: IsComplete {}
impl IsOk for OkState {}

/// Infallible read operation for views in a verified typestate (`IsOk`).
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

/// Trait for verifying validity at runtime, upgrading the typestate to `OkState`.
pub trait CheckOk {
    type Ok;
    fn check_ok(self) -> Result<Self::Ok, crate::Error>;
}

/// Trait for converting a mutable view or storage into a self-consuming typestate Writer.
pub trait IntoWriter {
    type Writer;
    fn into_writer(self) -> Self::Writer;
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{LittleEndian, Storage, UInt};

    const TEST_VALUE: u32 = 0x12345678;

    fn assert_state<S: State>() {}
    fn assert_complete<S: IsComplete>() {}
    fn assert_ok<S: IsOk>() {}

    #[test]
    fn test_state_marker_traits() {
        assert_state::<UncheckedState>();
        assert_state::<CompleteState>();
        assert_state::<OkState>();

        assert_complete::<CompleteState>();
        assert_complete::<OkState>();

        assert_ok::<OkState>();
    }

    #[test]
    fn test_on_layout_mutation_transitions() {
        fn assert_is_unchecked<S: Storage>(_view: &UInt<32, LittleEndian, S, UncheckedState>) {}

        let mut buf = [0u8; 4];
        let ok_view =
            UInt::<32, LittleEndian, &mut [u8; 4], OkState>::new(&mut buf);
        assert_eq!(ok_view.read(), 0);

        // Performing a write consumes the OkState view and degrades its state to UncheckedState.
        let mutated_view = ok_view.write(TEST_VALUE);
        assert_is_unchecked(&mutated_view);

        // The degraded view in UncheckedState must use checked reading.
        assert_eq!(mutated_view.try_read().expect("valid read"), TEST_VALUE);
    }

    #[test]
    fn test_infallible_uint_read_write() {
        let mut buf = [0u8; 4];
        let uint_view = UInt::<32, LittleEndian, &mut [u8; 4], OkState>::new(&mut buf);
        let _ = uint_view.write(TEST_VALUE);
        let read_view = UInt::<32, LittleEndian, &[u8; 4], OkState>::new(&buf);
        assert_eq!(read_view.read(), TEST_VALUE);
    }

    #[test]
    fn test_into_writer_conversion() {
        struct MockMut<S>(S);
        struct MockWriter<S, ST: State>(S, core::marker::PhantomData<ST>);

        impl<S> IntoWriter for MockMut<S> {
            type Writer = MockWriter<S, UncheckedState>;
            fn into_writer(self) -> Self::Writer {
                MockWriter(self.0, core::marker::PhantomData)
            }
        }

        impl<S> CheckComplete for MockWriter<S, UncheckedState> {
            type Completed = MockWriter<S, CompleteState>;
            fn check_complete(self) -> Result<Self::Completed, crate::Error> {
                Ok(MockWriter(self.0, core::marker::PhantomData))
            }
        }

        impl<S> CheckOk for MockWriter<S, UncheckedState> {
            type Ok = MockWriter<S, OkState>;
            fn check_ok(self) -> Result<Self::Ok, crate::Error> {
                Ok(MockWriter(self.0, core::marker::PhantomData))
            }
        }

        let mut buf = [0u8; 4];
        let mock_mut = MockMut(&mut buf);
        let _complete_writer: MockWriter<&mut [u8; 4], CompleteState> =
            mock_mut.into_writer().check_complete().expect("complete writer");

        let mock_mut2 = MockMut(&mut buf);
        let _ok_writer: MockWriter<&mut [u8; 4], OkState> =
            mock_mut2.into_writer().check_ok().expect("ok writer");
    }
}
