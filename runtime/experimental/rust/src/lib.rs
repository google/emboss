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
    fn len(&self) -> usize;
    fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

pub trait MutStorage: Storage {
    type SlicedMut<'a>: MutStorage where Self: 'a;
    fn slice_mut(&mut self, offset: usize, length: usize) -> Result<Self::SlicedMut<'_>, Error>;
    fn try_write_byte(&mut self, offset: usize, val: u8) -> Result<(), Error>;
}

impl<'a, T: ?Sized + AsRef<[u8]>> Storage for &'a T {
    type Sliced<'b> = &'b [u8] where Self: 'b;
    fn slice(&self, offset: usize, length: usize) -> Result<Self::Sliced<'_>, Error> {
        let bytes = (*self).as_ref();
        bytes.get(offset..offset + length).ok_or(Error::OutOfBounds)
    }
    fn try_read_byte(&self, offset: usize) -> Result<u8, Error> {
        let bytes = self.as_ref();
        bytes.get(offset).copied().ok_or(Error::OutOfBounds)
    }
    fn len(&self) -> usize {
        (*self).as_ref().len()
    }
}

impl<'a, T: ?Sized + AsRef<[u8]>> Storage for &'a mut T {
    type Sliced<'b> = &'b [u8] where Self: 'b;
    fn slice(&self, offset: usize, length: usize) -> Result<Self::Sliced<'_>, Error> {
        let bytes = (*self).as_ref();
        bytes.get(offset..offset + length).ok_or(Error::OutOfBounds)
    }
    fn try_read_byte(&self, offset: usize) -> Result<u8, Error> {
        let bytes = self.as_ref();
        bytes.get(offset).copied().ok_or(Error::OutOfBounds)
    }
    fn len(&self) -> usize {
        (*self).as_ref().len()
    }
}

impl<'a, T: ?Sized + AsMut<[u8]> + AsRef<[u8]>> MutStorage for &'a mut T {
    type SlicedMut<'b> = &'b mut [u8] where Self: 'b;
    fn slice_mut(&mut self, offset: usize, length: usize) -> Result<Self::SlicedMut<'_>, Error> {
        let bytes = self.as_mut();
        bytes.get_mut(offset..offset + length).ok_or(Error::OutOfBounds)
    }
    fn try_write_byte(&mut self, offset: usize, val: u8) -> Result<(), Error> {
        let bytes = self.as_mut();
        let b = bytes.get_mut(offset).ok_or(Error::OutOfBounds)?;
        *b = val;
        Ok(())
    }
}

impl<T: Storage> Storage for Result<T, Error> {
    type Sliced<'a> = T::Sliced<'a> where Self: 'a;
    fn slice(&self, offset: usize, length: usize) -> Result<Self::Sliced<'_>, Error> {
        match self {
            Ok(s) => s.slice(offset, length),
            Err(e) => Err(*e),
        }
    }
    fn try_read_byte(&self, offset: usize) -> Result<u8, Error> {
        match self {
            Ok(s) => s.try_read_byte(offset),
            Err(e) => Err(*e),
        }
    }
    fn len(&self) -> usize {
        match self {
            Ok(s) => s.len(),
            Err(_) => 0,
        }
    }
}

impl<T: MutStorage> MutStorage for Result<T, Error> {
    type SlicedMut<'a> = T::SlicedMut<'a> where Self: 'a;
    fn slice_mut(&mut self, offset: usize, length: usize) -> Result<Self::SlicedMut<'_>, Error> {
        match self {
            Ok(s) => s.slice_mut(offset, length),
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

pub trait IsComplete {
    fn is_complete(&self) -> bool;
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
    fn from_u64(val: u64) -> Self::T;
}
pub struct SizeSelector<const BITS: usize>;

macro_rules! impl_smallest_uint {
    ($type:ty, $($bits:expr),+) => {
        $(
            impl SmallestUInt for SizeSelector<$bits> {
                type T = $type;
                #[inline]
                fn from_u64(val: u64) -> Self::T { val as $type }
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
    pub fn is_complete(&self) -> bool {
        self.storage.len() >= BITS.div_ceil(8)
    }
}

impl<const BITS: usize, E: ByteOrder, S: Storage> IsComplete for UInt<BITS, E, S> {
    fn is_complete(&self) -> bool {
        self.is_complete()
    }
}

impl<const BITS: usize, E: ByteOrder, S: Storage> UInt<BITS, E, S>
where
    SizeSelector<BITS>: SmallestUInt,
    <SizeSelector<BITS> as SmallestUInt>::T: DecodeFromStorage<E>,
{
    pub fn try_read(&self) -> Result<<SizeSelector<BITS> as SmallestUInt>::T, Error> {
        let size_in_bytes = BITS.div_ceil(8);
        <<SizeSelector<BITS> as SmallestUInt>::T as DecodeFromStorage<E>>::decode(
            &self.storage,
            size_in_bytes,
        )
    }
    /// # Safety
    /// Calling this function requires that the view is complete.
    pub unsafe fn read_unchecked(&self) -> <SizeSelector<BITS> as SmallestUInt>::T {
        self.try_read().unwrap()
    }
}

impl<const BITS: usize, E: ByteOrder, S: MutStorage> UInt<BITS, E, S>
where
    SizeSelector<BITS>: SmallestUInt,
    <SizeSelector<BITS> as SmallestUInt>::T: EncodeToStorage<E>,
{
    pub fn try_write(&mut self, val: <SizeSelector<BITS> as SmallestUInt>::T) -> Result<(), Error> {
        let size_in_bytes = BITS.div_ceil(8);
        val.encode(&mut self.storage, size_in_bytes)
    }
    /// # Safety
    /// Calling this function requires that the view is complete.
    pub unsafe fn write_unchecked(&mut self, val: <SizeSelector<BITS> as SmallestUInt>::T) {
        self.try_write(val).unwrap();
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
    pub fn is_complete(&self) -> bool {
        self.storage.len() >= BITS.div_ceil(8)
    }
}

impl<const BITS: usize, E: ByteOrder, S: Storage> IsComplete for Int<BITS, E, S> {
    fn is_complete(&self) -> bool {
        self.is_complete()
    }
}

impl<const BITS: usize, E: ByteOrder, S: Storage> Int<BITS, E, S>
where
    SizeSelector<BITS>: SmallestUInt + SmallestInt<U = <SizeSelector<BITS> as SmallestUInt>::T>,
    <SizeSelector<BITS> as SmallestUInt>::T: DecodeFromStorage<E>,
{
    pub fn try_read(&self) -> Result<<SizeSelector<BITS> as SmallestInt>::T, Error> {
        let size_in_bytes = BITS.div_ceil(8);
        let slice = self.storage.slice(0, size_in_bytes)?;
        let raw = UInt::<BITS, E, S::Sliced<'_>>::new(slice).try_read()?;
        Ok(<SizeSelector<BITS> as SmallestInt>::sign_extend(raw, BITS))
    }
    /// # Safety
    /// Calling this function requires that the view is complete.
    pub unsafe fn read_unchecked(&self) -> <SizeSelector<BITS> as SmallestInt>::T {
        self.try_read().unwrap()
    }
}

impl<const BITS: usize, E: ByteOrder, S: MutStorage> Int<BITS, E, S>
where
    SizeSelector<BITS>: SmallestUInt + SmallestInt<U = <SizeSelector<BITS> as SmallestUInt>::T>,
    <SizeSelector<BITS> as SmallestUInt>::T: EncodeToStorage<E>,
{
    pub fn try_write(&mut self, val: <SizeSelector<BITS> as SmallestInt>::T) -> Result<(), Error> {
        let unsigned = <SizeSelector<BITS> as SmallestInt>::mask_to_unsigned(val, BITS);
        let mut uint_view = UInt::<BITS, E, S::SlicedMut<'_>>::new(self.storage.slice_mut(0, BITS.div_ceil(8))?);
        uint_view.try_write(unsigned)
    }
    /// # Safety
    /// Calling this function requires that the view is complete.
    pub unsafe fn write_unchecked(&mut self, val: <SizeSelector<BITS> as SmallestInt>::T) {
        self.try_write(val).unwrap();
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

impl<T, Inner: IsComplete> EnumView<T, Inner> {
    pub fn is_complete(&self) -> bool {
        self.inner.is_complete()
    }
}

impl<T, Inner: IsComplete> IsComplete for EnumView<T, Inner> {
    fn is_complete(&self) -> bool {
        self.inner.is_complete()
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

impl<T, Inner: IsComplete> EnumViewMut<T, Inner> {
    pub fn is_complete(&self) -> bool {
        self.inner.is_complete()
    }
}

impl<T, Inner: IsComplete> IsComplete for EnumViewMut<T, Inner> {
    fn is_complete(&self) -> bool {
        self.inner.is_complete()
    }
}

pub trait TryRead {
    type ReadValue;
    fn try_read(&self) -> Result<Self::ReadValue, Error>;
    /// # Safety
    /// Calling this function requires that the view is complete.
    unsafe fn read_unchecked(&self) -> Self::ReadValue {
        match self.try_read() {
            Ok(val) => val,
            Err(_) => panic!("read_unchecked called on incomplete view"),
        }
    }
}

pub trait TryWrite {
    type WriteValue;
    fn try_write(&mut self, val: Self::WriteValue) -> Result<(), Error>;
    /// # Safety
    /// Calling this function requires that the view is complete.
    unsafe fn write_unchecked(&mut self, val: Self::WriteValue) {
        if self.try_write(val).is_err() {
            panic!("write_unchecked called on incomplete view");
        }
    }
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
    /// # Safety
    /// Calling this function requires that the view is complete.
    pub unsafe fn read_unchecked(&self) -> T {
        match self.try_read() {
            Ok(val) => val,
            Err(_) => panic!("read_unchecked called on incomplete view"),
        }
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
    /// # Safety
    /// Calling this function requires that the view is complete.
    pub unsafe fn write_unchecked(&mut self, val: T) {
        if self.try_write(val).is_err() {
            panic!("write_unchecked called on incomplete view");
        }
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
    /// # Safety
    /// Calling this function requires that the view is complete.
    pub unsafe fn read_unchecked(&self) -> T {
        match self.try_read() {
            Ok(val) => val,
            Err(_) => panic!("read_unchecked called on incomplete view"),
        }
    }
}

pub struct BitUInt<const BITS: usize, const BIT_OFFSET: usize, E: ByteOrder, S: Storage> {
    storage: S,
    _marker: core::marker::PhantomData<E>,
}

impl<const BITS: usize, const BIT_OFFSET: usize, E: ByteOrder, S: Storage> BitUInt<BITS, BIT_OFFSET, E, S> {
    pub fn new(storage: S) -> Self {
        Self {
            storage,
            _marker: core::marker::PhantomData,
        }
    }
    pub fn is_complete(&self) -> bool {
        self.storage.len() >= (BIT_OFFSET + BITS).div_ceil(8)
    }
}

impl<const BITS: usize, const BIT_OFFSET: usize, E: ByteOrder, S: Storage> IsComplete for BitUInt<BITS, BIT_OFFSET, E, S> {
    fn is_complete(&self) -> bool {
        self.is_complete()
    }
}

impl<const BITS: usize, const BIT_OFFSET: usize, E: ByteOrder, S: Storage> BitUInt<BITS, BIT_OFFSET, E, S>
where
    SizeSelector<BITS>: SmallestUInt,
{
    pub fn try_read(&self) -> Result<<SizeSelector<BITS> as SmallestUInt>::T, Error> {
        let mut val: u64 = 0;
        let first_byte = BIT_OFFSET / 8;
        let last_byte = (BIT_OFFSET + BITS - 1) / 8;

        for i in first_byte..=last_byte {
            let byte_val = self.storage.try_read_byte(i)? as u64;
            let bits_from_byte_offset = i * 8;

            if bits_from_byte_offset >= BIT_OFFSET {
                let shift = bits_from_byte_offset - BIT_OFFSET;
                if shift < 64 {
                    val |= byte_val << shift;
                }
            } else {
                let shift = BIT_OFFSET - bits_from_byte_offset;
                val |= byte_val >> shift;
            }
        }

        let mask = if BITS == 64 { !0 } else { (1 << BITS) - 1 };
        Ok(<SizeSelector<BITS> as SmallestUInt>::from_u64(val & mask))
    }
    /// # Safety
    /// Calling this function requires that the view is complete.
    pub unsafe fn read_unchecked(&self) -> <SizeSelector<BITS> as SmallestUInt>::T {
        match self.try_read() {
            Ok(val) => val,
            Err(_) => panic!("read_unchecked called on incomplete view"),
        }
    }
}

pub struct BitInt<const BITS: usize, const BIT_OFFSET: usize, E: ByteOrder, S: Storage> {
    storage: S,
    _marker: core::marker::PhantomData<E>,
}

impl<const BITS: usize, const BIT_OFFSET: usize, E: ByteOrder, S: Storage> BitInt<BITS, BIT_OFFSET, E, S> {
    pub fn new(storage: S) -> Self {
        Self {
            storage,
            _marker: core::marker::PhantomData,
        }
    }
    pub fn is_complete(&self) -> bool {
        self.storage.len() >= (BIT_OFFSET + BITS).div_ceil(8)
    }
}

impl<const BITS: usize, const BIT_OFFSET: usize, E: ByteOrder, S: Storage> IsComplete for BitInt<BITS, BIT_OFFSET, E, S> {
    fn is_complete(&self) -> bool {
        self.is_complete()
    }
}

impl<const BITS: usize, const BIT_OFFSET: usize, E: ByteOrder, S: Storage> BitInt<BITS, BIT_OFFSET, E, S>
where
    SizeSelector<BITS>: SmallestUInt + SmallestInt<U = <SizeSelector<BITS> as SmallestUInt>::T>,
{
    pub fn try_read(&self) -> Result<<SizeSelector<BITS> as SmallestInt>::T, Error> {
        let uint_view = BitUInt::<BITS, BIT_OFFSET, E, S::Sliced<'_>>::new(self.storage.slice(0, (BIT_OFFSET + BITS).div_ceil(8))?);
        let raw = uint_view.try_read()?;
        Ok(<SizeSelector<BITS> as SmallestInt>::sign_extend(raw, BITS))
    }
    /// # Safety
    /// Calling this function requires that the view is complete.
    pub unsafe fn read_unchecked(&self) -> <SizeSelector<BITS> as SmallestInt>::T {
        match self.try_read() {
            Ok(val) => val,
            Err(_) => panic!("read_unchecked called on incomplete view"),
        }
    }
}

impl<const BITS: usize, const BIT_OFFSET: usize, E: ByteOrder, S: Storage> TryRead for BitUInt<BITS, BIT_OFFSET, E, S>
where
    SizeSelector<BITS>: SmallestUInt,
{
    type ReadValue = <SizeSelector<BITS> as SmallestUInt>::T;
    fn try_read(&self) -> Result<Self::ReadValue, Error> {
        self.try_read()
    }
}

impl<const BITS: usize, const BIT_OFFSET: usize, E: ByteOrder, S: Storage> TryRead for BitInt<BITS, BIT_OFFSET, E, S>
where
    SizeSelector<BITS>: SmallestUInt + SmallestInt<U = <SizeSelector<BITS> as SmallestUInt>::T>,
{
    type ReadValue = <SizeSelector<BITS> as SmallestInt>::T;
    fn try_read(&self) -> Result<Self::ReadValue, Error> {
        self.try_read()
    }
}

#[derive(Clone, Copy, Debug)]
pub struct VirtualField<T> {
    pub value: core::result::Result<T, Error>,
}

impl<T> VirtualField<T> {
    pub const fn new(value: core::result::Result<T, Error>) -> Self {
        Self { value }
    }
    pub fn is_complete(&self) -> bool {
        self.value.is_ok()
    }
}

impl<T> IsComplete for VirtualField<T> {
    fn is_complete(&self) -> bool {
        self.is_complete()
    }
}

impl<T: Copy> VirtualField<T> {
    pub fn try_read(&self) -> core::result::Result<T, Error> {
        self.value
    }
    /// # Safety
    /// Calling this function requires that the view is complete.
    pub unsafe fn read_unchecked(&self) -> T {
        match self.try_read() {
            Ok(val) => val,
            Err(_) => panic!("read_unchecked called on incomplete view"),
        }
    }
}

impl<T: Copy> TryRead for VirtualField<T> {
    type ReadValue = T;
    fn try_read(&self) -> core::result::Result<T, Error> {
        self.value
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_uint_is_complete_and_read_write() {
        let mut buffer = [0x12, 0x34];
        let uint_view = UInt::<16, LittleEndian, _>::new(&buffer[..]);
        assert!(uint_view.is_complete());
        assert_eq!(unsafe { uint_view.read_unchecked() }, 0x3412);

        let incomplete_view = UInt::<16, LittleEndian, _>::new(&buffer[..1]);
        assert!(!incomplete_view.is_complete());

        let mut uint_mut = UInt::<16, LittleEndian, _>::new(&mut buffer[..]);
        unsafe { uint_mut.write_unchecked(0x5678) };
        assert_eq!(buffer, [0x78, 0x56]);
    }

    #[test]
    #[should_panic]
    fn test_uint_read_panic_on_error() {
        let buffer = [0x12];
        let incomplete_view = UInt::<16, LittleEndian, _>::new(&buffer[..]);
        let _ = unsafe { incomplete_view.read_unchecked() };
    }

    #[test]
    #[should_panic]
    fn test_uint_write_panic_on_error() {
        let mut buffer = [0x12];
        let mut incomplete_view = UInt::<16, LittleEndian, _>::new(&mut buffer[..]);
        unsafe { incomplete_view.write_unchecked(0x1234) };
    }

    #[test]
    fn test_int_is_complete_and_read_write() {
        let mut buffer = [0xfe, 0xff]; // -2 in i16 LE
        let int_view = Int::<16, LittleEndian, _>::new(&buffer[..]);
        assert!(int_view.is_complete());
        assert_eq!(unsafe { int_view.read_unchecked() }, -2i16);

        let mut int_mut = Int::<16, LittleEndian, _>::new(&mut buffer[..]);
        unsafe { int_mut.write_unchecked(-5i16) };
        assert_eq!(unsafe { int_mut.read_unchecked() }, -5i16);
    }

    #[test]
    fn test_virtual_field_is_complete_and_read() {
        let vf_ok = VirtualField::new(Ok(42u32));
        assert!(vf_ok.is_complete());
        assert_eq!(unsafe { vf_ok.read_unchecked() }, 42);

        let vf_err: VirtualField<u32> = VirtualField::new(Err(Error::OutOfBounds));
        assert!(!vf_err.is_complete());
    }
}


