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

pub mod prelude;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Error {
    OutOfBounds,
}

pub trait Storage: Clone {
    type Sliced: Storage;
    fn slice(&self, offset: usize, length: usize) -> Self::Sliced;
    fn try_read_byte(&self, offset: usize) -> Result<u8, Error>;
}

impl<'a, T: ?Sized + AsRef<[u8]>> Storage for &'a T {
    type Sliced = Result<&'a [u8], Error>;
    fn slice(&self, offset: usize, length: usize) -> Self::Sliced {
        let bytes = (*self).as_ref();
        bytes.get(offset..offset + length).ok_or(Error::OutOfBounds)
    }
    fn try_read_byte(&self, offset: usize) -> Result<u8, Error> {
        let bytes = (*self).as_ref();
        bytes.get(offset).copied().ok_or(Error::OutOfBounds)
    }
}

impl<T: Storage> Storage for Result<T, Error> {
    type Sliced = Result<T::Sliced, Error>;
    fn slice(&self, offset: usize, length: usize) -> Self::Sliced {
        match self {
            Ok(s) => Ok(s.slice(offset, length)),
            Err(e) => Err(*e),
        }
    }
    fn try_read_byte(&self, offset: usize) -> Result<u8, Error> {
        match self {
            Ok(s) => s.try_read_byte(offset),
            Err(e) => Err(*e),
        }
    }
}

pub trait DecodeFromStorage: Sized {
    fn decode<S: Storage>(storage: &S, size_in_bytes: usize) -> Result<Self, Error>;
}

macro_rules! impl_decode_uint {
    ($type:ty) => {
        impl DecodeFromStorage for $type {
            fn decode<S: Storage>(storage: &S, size_in_bytes: usize) -> Result<Self, Error> {
                let mut val: $type = 0;
                for i in 0..size_in_bytes {
                    val |= (storage.try_read_byte(i)? as $type) << (i * 8);
                }
                Ok(val)
            }
        }
    };
}
impl_decode_uint!(u8);
impl_decode_uint!(u16);
impl_decode_uint!(u32);
impl_decode_uint!(u64);

pub trait SmallestUInt {
    type T: DecodeFromStorage;
}
pub struct SizeSelector<const BITS: usize>;

macro_rules! impl_smallest_uint {
    ($type:ty, $($bits:expr),+) => {
        $(
            impl SmallestUInt for SizeSelector<$bits> {
                type T = $type;
            }
        )+
    };
}
impl_smallest_uint!(u8, 1, 2, 3, 4, 5, 6, 7, 8);
impl_smallest_uint!(u16, 9, 10, 11, 12, 13, 14, 15, 16);
impl_smallest_uint!(
    u32, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32
);
impl_smallest_uint!(
    u64, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48
);
impl_smallest_uint!(
    u64, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64
);

pub struct UInt<const BITS: usize, S: Storage> {
    storage: S,
}

impl<const BITS: usize, S: Storage> UInt<BITS, S>
where
    SizeSelector<BITS>: SmallestUInt,
{
    pub fn new(storage: S) -> Self {
        Self { storage }
    }

    pub fn try_read(&self) -> Result<<SizeSelector<BITS> as SmallestUInt>::T, Error> {
        let size_in_bytes = (BITS + 7) / 8;
        <<SizeSelector<BITS> as SmallestUInt>::T>::decode(&self.storage, size_in_bytes)
    }
}
