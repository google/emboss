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
pub enum Error<T = ()> {
    OutOfBounds,
    UnknownEnum(T),
}

impl<T> Error<T> {
    pub fn map_type<U>(self) -> Error<U> {
        match self {
            Error::OutOfBounds => Error::OutOfBounds,
            Error::UnknownEnum(_) => unreachable!("Cannot map UnknownEnum across unmodified types"),
        }
    }
}

pub trait Storage {
    type Sliced<'a>: Storage where Self: 'a;
    fn slice(&self, offset: usize, length: usize) -> Result<Self::Sliced<'_>, Error>;
    fn try_read_byte(&self, offset: usize) -> Result<u8, Error>;
}

pub trait MutStorage: Storage {
    type SlicedMut<'a>: MutStorage where Self: 'a;
    fn slice_mut(&mut self, offset: usize, length: usize) -> Result<Self::SlicedMut<'_>, Error>;
    fn try_write_byte(&mut self, offset: usize, val: u8) -> Result<(), Error>;
}

impl<'a, T: ?Sized + AsRef<[u8]>> Storage for &'a mut T {
    type Sliced<'b> = Result<&'b [u8], Error> where Self: 'b;
    fn slice(&self, offset: usize, length: usize) -> Result<Self::Sliced<'_>, Error> {
        let bytes = self.as_ref();
        Ok(bytes.get(offset..offset + length).ok_or(Error::OutOfBounds))
    }
    fn try_read_byte(&self, offset: usize) -> Result<u8, Error> {
        let bytes = self.as_ref();
        bytes.get(offset).copied().ok_or(Error::OutOfBounds)
    }
}

impl<'a, T: ?Sized + AsRef<[u8]>> Storage for &'a T {
    type Sliced<'b> = Result<&'b [u8], Error> where Self: 'b;
    fn slice(&self, offset: usize, length: usize) -> Result<Self::Sliced<'_>, Error> {
        let bytes = (*self).as_ref();
        Ok(bytes.get(offset..offset + length).ok_or(Error::OutOfBounds))
    }
    fn try_read_byte(&self, offset: usize) -> Result<u8, Error> {
        let bytes = self.as_ref();
        bytes.get(offset).copied().ok_or(Error::OutOfBounds)
    }
}

impl<'a, T: ?Sized + AsMut<[u8]> + AsRef<[u8]>> MutStorage for &'a mut T {
    type SlicedMut<'b> = Result<&'b mut [u8], Error> where Self: 'b;
    fn slice_mut(&mut self, offset: usize, length: usize) -> Result<Self::SlicedMut<'_>, Error> {
        let bytes = self.as_mut();
        Ok(bytes.get_mut(offset..offset + length).ok_or(Error::OutOfBounds))
    }
    fn try_write_byte(&mut self, offset: usize, val: u8) -> Result<(), Error> {
        let bytes = self.as_mut();
        let b = bytes.get_mut(offset).ok_or(Error::OutOfBounds)?;
        *b = val;
        Ok(())
    }
}

impl<T: Storage> Storage for Result<T, Error> {
    type Sliced<'a> = Result<T::Sliced<'a>, Error> where Self: 'a;
    fn slice(&self, offset: usize, length: usize) -> Result<Self::Sliced<'_>, Error> {
        match self {
            Ok(s) => match s.slice(offset, length) {
                Ok(sliced) => Ok(Ok(sliced)),
                Err(e) => Err(e),
            },
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

impl<T: MutStorage> MutStorage for Result<T, Error> {
    type SlicedMut<'a> = Result<T::SlicedMut<'a>, Error> where Self: 'a;
    fn slice_mut(&mut self, offset: usize, length: usize) -> Result<Self::SlicedMut<'_>, Error> {
        match self {
            Ok(s) => match s.slice_mut(offset, length) {
                Ok(sliced) => Ok(Ok(sliced)),
                Err(e) => Err(e),
            },
            Err(e) => Err(*e),
        }
    }
    fn try_write_byte(&mut self, offset: usize, val: u8) -> Result<(), Error> {
        match self {
            Ok(s) => s.try_write_byte(offset, val),
            Err(e) => Err(*e),
        }
    }
}

pub trait ByteOrder {
    fn shift(i: usize, size_in_bytes: usize) -> usize;
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct LittleEndian;
impl ByteOrder for LittleEndian {
    #[inline(always)]
    fn shift(i: usize, _size_in_bytes: usize) -> usize {
        i * 8
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct BigEndian;
impl ByteOrder for BigEndian {
    #[inline(always)]
    fn shift(i: usize, size_in_bytes: usize) -> usize {
        (size_in_bytes - 1 - i) * 8
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Null;
impl ByteOrder for Null {
    #[inline(always)]
    fn shift(_i: usize, _size_in_bytes: usize) -> usize {
        0
    }
}

pub trait DecodeFromStorage<E: ByteOrder>: Sized {
    fn decode<S: Storage>(storage: &S, size_in_bytes: usize) -> Result<Self, Error>;
}

pub trait EncodeToStorage<E: ByteOrder>: Sized {
    fn encode<S: MutStorage>(&self, storage: &mut S, size_in_bytes: usize) -> Result<(), Error>;
}

macro_rules! impl_decode_uint {
    ($type:ty) => {
        impl<E: ByteOrder> DecodeFromStorage<E> for $type {
            fn decode<S: Storage>(storage: &S, size_in_bytes: usize) -> Result<Self, Error> {
                let mut val: $type = 0;
                for i in 0..size_in_bytes {
                    val |= (storage.try_read_byte(i)? as $type) << E::shift(i, size_in_bytes);
                }
                Ok(val)
            }
        }
        impl<E: ByteOrder> EncodeToStorage<E> for $type {
            fn encode<S: MutStorage>(&self, storage: &mut S, size_in_bytes: usize) -> Result<(), Error> {
                for i in 0..size_in_bytes {
                    storage.try_write_byte(i, ((*self) >> E::shift(i, size_in_bytes)) as u8)?;
                }
                Ok(())
            }
        }
    };
}
impl_decode_uint!(u8);
impl_decode_uint!(u16);
impl_decode_uint!(u32);
impl_decode_uint!(u64);

pub trait SmallestUInt {
    type T;
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

pub struct UInt<const BITS: usize, E: ByteOrder, S: Storage> {
    storage: S,
    _marker: core::marker::PhantomData<E>,
}

impl<const BITS: usize, E: ByteOrder, S: Storage> UInt<BITS, E, S> {
    pub fn new(storage: S) -> Self {
        Self {
            storage,
            _marker: core::marker::PhantomData,
        }
    }
}

impl<const BITS: usize, E: ByteOrder, S: Storage> UInt<BITS, E, S>
where
    SizeSelector<BITS>: SmallestUInt,
    <SizeSelector<BITS> as SmallestUInt>::T: DecodeFromStorage<E>,
{
    pub fn try_read(&self) -> Result<<SizeSelector<BITS> as SmallestUInt>::T, Error> {
        let size_in_bytes = (BITS + 7) / 8;
        <<SizeSelector<BITS> as SmallestUInt>::T as DecodeFromStorage<E>>::decode(
            &self.storage,
            size_in_bytes,
        )
    }
}

impl<const BITS: usize, E: ByteOrder, S: MutStorage> UInt<BITS, E, S>
where
    SizeSelector<BITS>: SmallestUInt,
    <SizeSelector<BITS> as SmallestUInt>::T: EncodeToStorage<E>,
{
    pub fn try_write(&mut self, val: <SizeSelector<BITS> as SmallestUInt>::T) -> Result<(), Error> {
        let size_in_bytes = (BITS + 7) / 8;
        val.encode(&mut self.storage, size_in_bytes)
    }
}

pub trait SmallestInt {
    type T;
    type U;
    fn sign_extend(raw: Self::U, bits: usize) -> Self::T;
    fn mask_to_unsigned(val: Self::T, bits: usize) -> Self::U;
}

macro_rules! impl_smallest_int {
    ($type:ty, $utype:ty, $($bits:expr),+) => {
        $(
            impl SmallestInt for SizeSelector<$bits> {
                type T = $type;
                type U = $utype;
                #[inline]
                fn sign_extend(raw: Self::U, bits: usize) -> Self::T {
                    let shift_amount = (core::mem::size_of::<$type>() * 8) - bits;
                    let sign_extended = (raw as $type) << shift_amount;
                    sign_extended >> shift_amount
                }
                #[inline]
                fn mask_to_unsigned(val: Self::T, bits: usize) -> Self::U {
                    let mask = if bits == core::mem::size_of::<$utype>() * 8 {
                        !0
                    } else {
                        (1 << bits) - 1
                    };
                    (val as Self::U) & mask
                }
            }
        )+
    };
}

impl_smallest_int!(i8, u8, 1, 2, 3, 4, 5, 6, 7, 8);
impl_smallest_int!(i16, u16, 9, 10, 11, 12, 13, 14, 15, 16);
impl_smallest_int!(
    i32, u32, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32
);
impl_smallest_int!(
    i64, u64, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48
);
impl_smallest_int!(
    i64, u64, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64
);

pub struct Int<const BITS: usize, E: ByteOrder, S: Storage> {
    storage: S,
    _marker: core::marker::PhantomData<E>,
}

impl<const BITS: usize, E: ByteOrder, S: Storage> Int<BITS, E, S> {
    pub fn new(storage: S) -> Self {
        Self {
            storage,
            _marker: core::marker::PhantomData,
        }
    }
}

impl<const BITS: usize, E: ByteOrder, S: Storage> Int<BITS, E, S>
where
    SizeSelector<BITS>: SmallestUInt + SmallestInt<U = <SizeSelector<BITS> as SmallestUInt>::T>,
    <SizeSelector<BITS> as SmallestUInt>::T: DecodeFromStorage<E>,
{
    pub fn try_read(&self) -> Result<<SizeSelector<BITS> as SmallestInt>::T, Error> {
        let size_in_bytes = (BITS + 7) / 8;
        let slice = self.storage.slice(0, size_in_bytes)?;
        let raw = UInt::<BITS, E, S::Sliced<'_>>::new(slice).try_read()?;
        Ok(<SizeSelector<BITS> as SmallestInt>::sign_extend(raw, BITS))
    }
}

impl<const BITS: usize, E: ByteOrder, S: MutStorage> Int<BITS, E, S>
where
    SizeSelector<BITS>: SmallestUInt + SmallestInt<U = <SizeSelector<BITS> as SmallestUInt>::T>,
    <SizeSelector<BITS> as SmallestUInt>::T: EncodeToStorage<E>,
{
    pub fn try_write(&mut self, val: <SizeSelector<BITS> as SmallestInt>::T) -> Result<(), Error> {
        let unsigned = <SizeSelector<BITS> as SmallestInt>::mask_to_unsigned(val, BITS);
        let mut uint_view = UInt::<BITS, E, S::SlicedMut<'_>>::new(self.storage.slice_mut(0, (BITS + 7) / 8)?);
        uint_view.try_write(unsigned)
    }
}

pub trait TryFromRaw<T> {
    fn try_from_raw(val: T) -> Result<Self, Error<T>>
    where
        Self: Sized;
}

pub struct EnumView<T, Inner> {
    pub inner: Inner,
    _phantom: core::marker::PhantomData<T>,
}

impl<T, Inner> EnumView<T, Inner> {
    pub fn new(inner: Inner) -> Self {
        Self {
            inner,
            _phantom: core::marker::PhantomData,
        }
    }
}

pub struct EnumViewMut<T, Inner> {
    pub inner: Inner,
    _phantom: core::marker::PhantomData<T>,
}

impl<T, Inner> EnumViewMut<T, Inner> {
    pub fn new(inner: Inner) -> Self {
        Self {
            inner,
            _phantom: core::marker::PhantomData,
        }
    }
}

pub trait TryRead {
    type ReadValue;
    fn try_read(&self) -> Result<Self::ReadValue, Error>;
}

pub trait TryWrite {
    type WriteValue;
    fn try_write(&mut self, val: Self::WriteValue) -> Result<(), Error>;
}

impl<const BITS: usize, E: ByteOrder, S: Storage> TryRead for UInt<BITS, E, S>
where
    SizeSelector<BITS>: SmallestUInt,
    <SizeSelector<BITS> as SmallestUInt>::T: DecodeFromStorage<E>,
{
    type ReadValue = <SizeSelector<BITS> as SmallestUInt>::T;
    fn try_read(&self) -> Result<Self::ReadValue, Error> {
        self.try_read()
    }
}

impl<const BITS: usize, E: ByteOrder, S: MutStorage> TryWrite for UInt<BITS, E, S>
where
    SizeSelector<BITS>: SmallestUInt,
    <SizeSelector<BITS> as SmallestUInt>::T: EncodeToStorage<E>,
{
    type WriteValue = <SizeSelector<BITS> as SmallestUInt>::T;
    fn try_write(&mut self, val: Self::WriteValue) -> Result<(), Error> {
        self.try_write(val)
    }
}

impl<const BITS: usize, E: ByteOrder, S: Storage> TryRead for Int<BITS, E, S>
where
    SizeSelector<BITS>: SmallestUInt + SmallestInt<U = <SizeSelector<BITS> as SmallestUInt>::T>,
    <SizeSelector<BITS> as SmallestUInt>::T: DecodeFromStorage<E>,
{
    type ReadValue = <SizeSelector<BITS> as SmallestInt>::T;
    fn try_read(&self) -> Result<Self::ReadValue, Error> {
        self.try_read()
    }
}

impl<const BITS: usize, E: ByteOrder, S: MutStorage> TryWrite for Int<BITS, E, S>
where
    SizeSelector<BITS>: SmallestUInt + SmallestInt<U = <SizeSelector<BITS> as SmallestUInt>::T>,
    <SizeSelector<BITS> as SmallestUInt>::T: EncodeToStorage<E>,
{
    type WriteValue = <SizeSelector<BITS> as SmallestInt>::T;
    fn try_write(&mut self, val: Self::WriteValue) -> Result<(), Error> {
        self.try_write(val)
    }
}

impl<T, Inner> EnumView<T, Inner>
where
    Inner: TryRead,
    T: TryFromRaw<Inner::ReadValue>,
{
    pub fn try_read(&self) -> Result<T, Error<Inner::ReadValue>> {
        let raw = self.inner.try_read().map_err(|e| e.map_type())?;
        T::try_from_raw(raw)
    }
}

impl<T, Inner> EnumViewMut<T, Inner>
where
    Inner: TryWrite,
    Inner::WriteValue: From<T>,
{
    pub fn try_write(&mut self, val: T) -> Result<(), Error> {
        self.inner.try_write(Inner::WriteValue::from(val))
    }
}

impl<T, Inner> EnumViewMut<T, Inner>
where
    Inner: TryRead,
    T: TryFromRaw<Inner::ReadValue>,
{
    pub fn try_read(&self) -> Result<T, Error<Inner::ReadValue>> {
        let raw = self.inner.try_read().map_err(|e| e.map_type())?;
        T::try_from_raw(raw)
    }
}
