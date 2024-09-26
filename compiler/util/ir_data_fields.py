# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Provides helpers for defining and working with the fields of IR data classes.

Field specs
-----------
Various utilities are provided for working with `dataclasses.Field`s:
  - Classes:
    - `FieldSpec` - used to track data about an IR data field
    - `FieldContainer` - used to track the field container type
  - Functions that work with `FieldSpec`s:
    - `make_field_spec`, `build_default`
  - Functions for retrieving a set of `FieldSpec`s for a given class:
    - `field_specs`
  - Functions for retrieving fields and their values:
    - `fields_and_values`
  - Functions for copying and updating IR data classes
    - `copy`, `update`
  - Functions to help defining IR data fields
    - `oneof_field`, `list_field`, `str_field`
"""

import dataclasses
import enum
import sys
from typing import (
    Any,
    Callable,
    ClassVar,
    ForwardRef,
    Iterable,
    Mapping,
    MutableMapping,
    NamedTuple,
    Optional,
    Protocol,
    SupportsIndex,
    Tuple,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
)


class IrDataclassInstance(Protocol):
    """Type bound for an IR dataclass instance."""

    __dataclass_fields__: ClassVar[dict[str, dataclasses.Field[Any]]]
    IR_DATACLASS: ClassVar[object]
    field_specs: ClassVar["FilteredIrFieldSpecs"]


IrDataT = TypeVar("IrDataT", bound=IrDataclassInstance)

CopyValuesListT = TypeVar("CopyValuesListT", bound=type)

_IR_DATACLASSS_ATTR = "IR_DATACLASS"


def _is_ir_dataclass(obj):
    return hasattr(obj, _IR_DATACLASSS_ATTR)


class CopyValuesList(list[CopyValuesListT]):
    """A list that makes copies of any value that is inserted."""

    def __init__(
        self, value_type: CopyValuesListT, iterable: Optional[Iterable[Any]] = None
    ):
        if iterable:
            super().__init__(iterable)
        else:
            super().__init__()
        self.value_type = value_type

    def _copy(self, obj: Any):
        if _is_ir_dataclass(obj):
            return copy(obj)
        return self.value_type(obj)

    def extend(self, iterable: Iterable) -> None:
        return super().extend([self._copy(i) for i in iterable])

    def shallow_copy(self, iterable: Iterable) -> None:
        """Explicitly performs a shallow copy of the provided list."""
        return super().extend(iterable)

    def append(self, obj: Any) -> None:
        return super().append(self._copy(obj))

    def insert(self, index: SupportsIndex, obj: Any) -> None:
        return super().insert(index, self._copy(obj))


class TemporaryCopyValuesList(NamedTuple):
    """Holder for a CopyValuesList while copying/constructing an IR dataclass."""

    temp_list: CopyValuesList


class FieldContainer(enum.Enum):
    """Indicates a fields container type."""

    NONE = 0
    OPTIONAL = 1
    LIST = 2


class FieldSpec(NamedTuple):
    """Indicates the container and type of a field.

    `FieldSpec` objects are accessed millions of times during runs so we cache
    as many operations as possible.
      - `is_dataclass`: `dataclasses.is_dataclass(data_type)`
      - `is_sequence`: `container is FieldContainer.LIST`
      - `is_enum`: `issubclass(data_type, enum.Enum)`
      - `is_oneof`: `oneof is not None`

    Use `make_field_spec` to automatically fill in the cached operations.
    """

    name: str
    data_type: type
    container: FieldContainer
    oneof: Optional[str]
    is_dataclass: bool
    is_sequence: bool
    is_enum: bool
    is_oneof: bool


def make_field_spec(
    name: str, data_type: type, container: FieldContainer, oneof: Optional[str]
):
    """Builds a field spec with cached type queries."""
    return FieldSpec(
        name,
        data_type,
        container,
        oneof,
        is_dataclass=_is_ir_dataclass(data_type),
        is_sequence=container is FieldContainer.LIST,
        is_enum=issubclass(data_type, enum.Enum),
        is_oneof=oneof is not None,
    )


def build_default(field_spec: FieldSpec):
    """Builds a default instance of the given field."""
    if field_spec.is_sequence:
        return CopyValuesList(field_spec.data_type)
    if field_spec.is_enum:
        return field_spec.data_type(int())
    return field_spec.data_type()


class FilteredIrFieldSpecs:
    """Provides cached views of an IR dataclass' fields."""

    def __init__(self, specs: Mapping[str, FieldSpec]):
        self.all_field_specs = specs
        self.field_specs = tuple(specs.values())
        self.dataclass_field_specs = {k: v for k, v in specs.items() if v.is_dataclass}
        self.oneof_field_specs = {k: v for k, v in specs.items() if v.is_oneof}
        self.sequence_field_specs = tuple(v for v in specs.values() if v.is_sequence)
        self.oneof_mappings = tuple(
            (k, v.oneof) for k, v in self.oneof_field_specs.items() if v.oneof
        )


def all_ir_classes(mod):
    """Retrieves a list of all IR dataclass definitions in the given module."""
    return (
        v
        for v in mod.__dict__.values()
        if isinstance(type, v.__class__) and _is_ir_dataclass(v)
    )


class IrDataclassSpecs:
    """Maintains a cache of all IR dataclass specs."""

    spec_cache: MutableMapping[type, FilteredIrFieldSpecs] = {}

    @classmethod
    def get_mod_specs(cls, mod):
        """Gets the IR dataclass specs for the given module."""
        return {
            ir_class: FilteredIrFieldSpecs(_field_specs(ir_class))
            for ir_class in all_ir_classes(mod)
        }

    @classmethod
    def get_specs(cls, data_class):
        """Gets the field specs for the given class. The specs will be cached."""
        if data_class not in cls.spec_cache:
            mod = sys.modules[data_class.__module__]
            cls.spec_cache.update(cls.get_mod_specs(mod))
        return cls.spec_cache[data_class]


def cache_message_specs(mod, cls):
    """Adds `field_specs` to `mod`, excluding `cls`.

    Adds a cached `field_specs` attribute to IR dataclasses in module `mod`
    excluding the given base class `cls`.

    This needs to be done after the dataclass decorators run and create the
    wrapped classes.

    Arguments:
        mod: The module to process.
        cls: The base class to exclude.

    Returns:
        None
    """
    for data_class in all_ir_classes(mod):
        if data_class is not cls:
            data_class.field_specs = IrDataclassSpecs.get_specs(data_class)


def _field_specs(cls: type[IrDataT]) -> Mapping[str, FieldSpec]:
    """Gets the IR data field names and types for the given IR data class."""
    # Get the dataclass fields
    class_fields = dataclasses.fields(cast(Any, cls))

    # Pre-python 3.11 (maybe pre 3.10) `get_type_hints` will substitute
    # `builtins.Expression` for 'Expression' rather than `ir_data.Expression`.
    # Instead we manually substitute the type by extracting the list of classes
    # from the class' module and manually substituting.
    mod_ns = {
        k: v
        for k, v in sys.modules[cls.__module__].__dict__.items()
        if isinstance(type, v.__class__)
    }

    # Now extract the concrete type out of optionals
    result: MutableMapping[str, FieldSpec] = {}
    for class_field in class_fields:
        if class_field.name.startswith("_"):
            continue
        container_type = FieldContainer.NONE
        type_hint = class_field.type
        oneof = class_field.metadata.get("oneof")

        # Check if this type is wrapped
        origin = get_origin(type_hint)
        # Get the wrapped types if there are any
        args = get_args(type_hint)
        if origin is not None:
            # Extract the type.
            type_hint = args[0]

            # Underneath the hood `typing.Optional` is just a `Union[T, None]` so we
            # have to check if it's a `Union` instead of just using `Optional`.
            if origin == Union:
                # Make sure this is an `Optional` and not another `Union` type.
                assert len(args) == 2 and args[1] == type(None)
                container_type = FieldContainer.OPTIONAL
            elif origin == list:
                container_type = FieldContainer.LIST
            else:
                raise TypeError(f"Field has invalid container type: {origin}")

        # Resolve any forward references.
        if isinstance(type_hint, str):
            type_hint = mod_ns[type_hint]
        if isinstance(type_hint, ForwardRef):
            type_hint = mod_ns[type_hint.__forward_arg__]

        result[class_field.name] = make_field_spec(
            class_field.name, type_hint, container_type, oneof
        )

    return result


def field_specs(obj: Union[IrDataT, type[IrDataT]]) -> Mapping[str, FieldSpec]:
    """Retrieves the fields specs for the give data type.

    The results of this method are cached to reduce lookup overhead.

    Arguments:
        obj: Either an IR dataclass type, or an instance of such a type.

    Returns:
        The field specs for `obj`.
    """
    cls = obj if isinstance(obj, type) else type(obj)
    if cls is type(None):
        raise TypeError("field_specs called with invalid type: NoneType")
    return IrDataclassSpecs.get_specs(cls).all_field_specs


def fields_and_values(
    ir: IrDataT,
    value_filt: Optional[Callable[[Any], bool]] = None,
):
    """Retrieves the fields and their values for a given IR data class.

    Args:
        ir: The IR data class or a read-only wrapper of an IR data class.
        value_filt: Optional filter used to exclude values.

    Returns:
        None
    """
    set_fields: list[Tuple[FieldSpec, Any]] = []
    specs: FilteredIrFieldSpecs = ir.field_specs
    for spec in specs.field_specs:
        value = getattr(ir, spec.name)
        if not value_filt or value_filt(value):
            set_fields.append((spec, value))
    return set_fields


# `copy` is one of the hottest paths of embossc. We've taken steps to
# optimize this path at the expense of code clarity and modularization.
#
# 1. `FilteredFieldSpecs` are cached on in the class definition for IR
#    dataclasses under the `ir_data.Message.field_specs` class attribute. We
#    just assume the passed in object has that attribute.
# 2. We cache a `field_specs` entry that is just the `values()` of the
#    `all_field_specs` dict.
# 3. Copied lists are wrapped in a `TemporaryCopyValuesList`. This is used to
#    signal to consumers that they can take ownership of the contained list
#    rather than copying it again. See `ir_data.Message()` and `update()` for
#    where this is used.
# 4. `FieldSpec` checks are cached including `is_dataclass` and `is_sequence`.
# 5. None checks are only done in `copy()`, `_copy_set_fields` only
#    references `_copy()` to avoid this step.
def _copy_set_fields(ir: IrDataT):
    """Deep copies fields from IR node `ir`."""
    values: MutableMapping[str, Any] = {}

    specs: FilteredIrFieldSpecs = ir.field_specs
    for spec in specs.field_specs:
        value = getattr(ir, spec.name)
        if value is not None:
            if spec.is_sequence:
                if spec.is_dataclass:
                    copy_value = CopyValuesList(
                        spec.data_type, (_copy(v) for v in value)
                    )
                    value = TemporaryCopyValuesList(copy_value)
                else:
                    copy_value = CopyValuesList(spec.data_type, value)
                    value = TemporaryCopyValuesList(copy_value)
            elif spec.is_dataclass:
                value = _copy(value)
            values[spec.name] = value
    return values


def _copy(ir: IrDataT) -> IrDataT:
    return type(ir)(**_copy_set_fields(ir))  # type: ignore[misc]


def copy(ir: IrDataT) -> Optional[IrDataT]:
    """Creates a copy of the given IR data class."""
    if not ir:
        return None
    return _copy(ir)


def update(ir: IrDataT, template: IrDataT):
    """Updates `ir`s fields with all set fields in the template."""
    for k, v in _copy_set_fields(template).items():
        if isinstance(v, TemporaryCopyValuesList):
            v = v.temp_list
        setattr(ir, k, v)


class OneOfField:
    """Decorator for a "oneof" field.

    Tracks when the field is set and will unset othe fields in the associated
    oneof group.

    Note: Decorators only work if dataclass slots aren't used.
    """

    def __init__(self, oneof: str) -> None:
        super().__init__()
        self.oneof = oneof
        self.owner_type = None
        self.proxy_name: str = ""
        self.name: str = ""

    def __set_name__(self, owner, name):
        self.name = name
        self.proxy_name = f"_{name}"
        self.owner_type = owner
        # Add our empty proxy field to the class.
        setattr(owner, self.proxy_name, None)

    def __get__(self, obj, objtype=None):
        return getattr(obj, self.proxy_name)

    def __set__(self, obj, value):
        if value is self:
            # This will happen if the dataclass uses the default value, we just
            # default to None.
            value = None

        if value is not None:
            # Clear the others
            for name, oneof in IrDataclassSpecs.get_specs(
                self.owner_type
            ).oneof_mappings:
                if oneof == self.oneof and name != self.name:
                    setattr(obj, name, None)

        setattr(obj, self.proxy_name, value)


def oneof_field(name: str):
    """Alternative for `datclasses.field` that sets up a oneof variable."""
    return dataclasses.field(  # pylint:disable=invalid-field-call
        default=OneOfField(name), metadata={"oneof": name}, init=True
    )


def str_field():
    """Helper used to define a defaulted str field."""
    return dataclasses.field(default_factory=str)  # pylint:disable=invalid-field-call


def list_field(cls_or_fn):
    """Helper used to define a defaulted list field.

    A lambda can be used to defer resolution of a field type that references its
    container type, for example:
    ```
    class Foo:
      subtypes: list['Foo'] = list_field(lambda: Foo)
      names: list[str] = list_field(str)
    ```

    Args:
        cls_or_fn: The class type or a function that resolves to the class type.

    Returns:
        A field with a `default_factory` that produces an appropriate list.
    """

    def list_factory(c):
        return CopyValuesList(c if isinstance(c, type) else c())

    return dataclasses.field(  # pylint:disable=invalid-field-call
        default_factory=lambda: list_factory(cls_or_fn)
    )
