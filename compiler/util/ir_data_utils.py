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

"""Provides a helpers for working with IR data elements.

Historical note: At one point protocol buffers were used for IR data. The
codebase still expects the IR data classes to behave similarly, particularly
with respect to "autovivification" where accessing an undefined field will
create it temporarily and add it if assigned to. Though, perhaps not fully
following the Pythonic ethos, we provide this behavior via the `builder` and
`reader` helpers to remain compatible with the rest of the codebase.

builder
-------
Instead of:
```
def set_function_name_end(function: Function):
  if not function.function_name:
    function.function_name = Word()
  if not function.function_name.source_location:
    function.function_name.source_location = Location()
  word.source_location.end = Position(line=1,column=2)
```

We can do:
```
def set_function_name_end(function: Function):
  builder(function).function_name.source_location.end = Position(line=1,
  column=2)
```

reader
------
Instead of:
```
def is_leaf_synthetic(data):
  if data:
    if data.attribute:
      if data.attribute.value:
        if data.attribute.value.is_synthetic is not None:
          return data.attribute.value.is_synthetic
  return False
```
We can do:
```
def is_leaf_synthetic(data):
  return reader(data).attribute.value.is_synthetic
```

IrDataSerializer
----------------
Provides methods for serializing and deserializing an IR data object.
"""
import enum
import json
from typing import (
    Any,
    Callable,
    Generic,
    MutableMapping,
    MutableSequence,
    Optional,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from compiler.util import ir_data
from compiler.util import ir_data_fields


MessageT = TypeVar("MessageT", bound=ir_data.Message)


def field_specs(ir: Union[MessageT, type[MessageT]]):
    """Retrieves the field specs for the IR data class"""
    data_type = ir if isinstance(ir, type) else type(ir)
    return ir_data_fields.IrDataclassSpecs.get_specs(data_type).all_field_specs


class IrDataSerializer:
    """Provides methods for serializing IR data objects."""

    def __init__(self, ir: MessageT):
        assert ir is not None
        self.ir = ir

    def _to_dict(
        self,
        ir: MessageT,
        field_func: Callable[[MessageT], list[Tuple[ir_data_fields.FieldSpec, Any]]],
    ) -> MutableMapping[str, Any]:
        """Translates the IR to a standard Python `dict`."""
        assert ir is not None
        values: MutableMapping[str, Any] = {}
        for spec, value in field_func(ir):
            if value is not None and spec.is_dataclass:
                if spec.is_sequence:
                    value = [self._to_dict(v, field_func) for v in value]
                else:
                    value = self._to_dict(value, field_func)
            values[spec.name] = value
        return values

    def to_dict(self, exclude_none: bool = False):
        """Converts the IR data class to a dictionary."""

        def non_empty(ir):
            return _fields_and_values(
                ir, lambda v: v is not None and (not isinstance(v, list) or len(v))
            )

        def all_fields(ir):
            return _fields_and_values(ir)

        # It's tempting to use `dataclasses.asdict` here, but that does a deep
        # copy which is overkill for the current usage; mainly as an intermediary
        # for `to_json` and `repr`.
        return self._to_dict(self.ir, non_empty if exclude_none else all_fields)

    def to_json(self, *args, **kwargs):
        """Converts the IR data class to a JSON string."""
        return json.dumps(self.to_dict(exclude_none=True), *args, **kwargs)

    @staticmethod
    def from_json(data_cls, data):
        """Constructs an IR data class from the given JSON string."""
        as_dict = json.loads(data)
        return IrDataSerializer.from_dict(data_cls, as_dict)

    def copy_from_dict(self, data):
        """Deserializes the data and overwrites the IR data class with it."""
        cls = type(self.ir)
        data_copy = IrDataSerializer.from_dict(cls, data)
        for k in field_specs(cls):
            setattr(self.ir, k, getattr(data_copy, k))

    @staticmethod
    def _enum_type_converter(enum_cls: type[enum.Enum], val: Any) -> enum.Enum:
        """Converts `val` to an instance of `enum_cls`."""
        if isinstance(val, str):
            return getattr(enum_cls, val)
        return enum_cls(val)

    @staticmethod
    def _enum_type_hook(enum_cls: type[enum.Enum]):
        return lambda val: IrDataSerializer._enum_type_converter(enum_cls, val)

    @staticmethod
    def _from_dict(data_cls: type[MessageT], data):
        """Translates the given `data` dict to an instance of `data_cls`."""
        class_fields: MutableMapping[str, Any] = {}
        for name, spec in ir_data_fields.field_specs(data_cls).items():
            if (value := data.get(name)) is not None:
                if spec.is_dataclass:
                    if spec.is_sequence:
                        class_fields[name] = [
                            IrDataSerializer._from_dict(spec.data_type, v)
                            for v in value
                        ]
                    else:
                        class_fields[name] = IrDataSerializer._from_dict(
                            spec.data_type, value
                        )
                else:
                    if spec.data_type in (
                        ir_data.FunctionMapping,
                        ir_data.AddressableUnit,
                    ):
                        class_fields[name] = IrDataSerializer._enum_type_converter(
                            spec.data_type, value
                        )
                    else:
                        if spec.is_sequence:
                            class_fields[name] = value
                        else:
                            class_fields[name] = spec.data_type(value)
        return data_cls(**class_fields)

    @staticmethod
    def from_dict(data_cls: type[MessageT], data):
        """Creates a new IR data instance from a serialized dict."""
        return IrDataSerializer._from_dict(data_cls, data)


class _IrDataSequenceBuilder(MutableSequence[MessageT]):
    """Wrapper for a list of IR elements.

    Simply wraps the returned values during indexed access and iteration with
    IrDataBuilders.
    """

    def __init__(self, target: MutableSequence[MessageT]):
        self._target = target

    def __delitem__(self, key):
        del self._target[key]

    def __getitem__(self, key):
        return _IrDataBuilder(self._target.__getitem__(key))

    def __setitem__(self, key, value):
        self._target[key] = value

    def __iter__(self):
        itr = iter(self._target)
        for i in itr:
            yield _IrDataBuilder(i)

    def __repr__(self):
        return repr(self._target)

    def __len__(self):
        return len(self._target)

    def __eq__(self, other):
        return self._target == other

    def __ne__(self, other):
        return self._target != other

    def insert(self, index, value):
        self._target.insert(index, value)

    def extend(self, values):
        self._target.extend(values)


class _IrDataBuilder(Generic[MessageT]):
    """Wrapper for an IR element."""

    def __init__(self, ir: MessageT) -> None:
        assert ir is not None
        self.ir: MessageT = ir

    def __setattr__(self, __name: str, __value: Any) -> None:
        if __name == "ir":
            # This our proxy object
            object.__setattr__(self, __name, __value)
        else:
            # Passthrough to the proxy object
            ir: MessageT = object.__getattribute__(self, "ir")
            setattr(ir, __name, __value)

    def __getattribute__(self, name: str) -> Any:
        """Hook for `getattr` that handles adding missing fields.

        If the field is missing inserts it, and then returns either the raw
        value for basic types or a new IrBuilder wrapping the field to handle
        the next field access in a longer chain.

        Arguments:
            name: the name of the attribute to set/retrieve

        Returns:
            The value of the attribute `name`.
        """

        # Check if getting one of the builder attributes
        if name in ("CopyFrom", "ir"):
            return object.__getattribute__(self, name)

        # Get our target object by bypassing our getattr hook
        ir: MessageT = object.__getattribute__(self, "ir")
        if ir is None:
            return object.__getattribute__(self, name)

        if name in ("HasField", "WhichOneof"):
            return getattr(ir, name)

        field_spec = field_specs(ir).get(name)
        if field_spec is None:
            raise AttributeError(
                f"No field {name} on {type(ir).__module__}.{type(ir).__name__}."
            )

        obj = getattr(ir, name, None)
        if obj is None:
            # Create a default and store it
            obj = ir_data_fields.build_default(field_spec)
            setattr(ir, name, obj)

        if field_spec.is_dataclass:
            obj = (
                _IrDataSequenceBuilder(obj)
                if field_spec.is_sequence
                else _IrDataBuilder(obj)
            )

        return obj

    def CopyFrom(self, template: MessageT):  # pylint:disable=invalid-name
        """Updates the fields of this class with values set in the template."""
        update(cast(type[MessageT], self), template)


def builder(target: MessageT) -> MessageT:
    """Create a wrapper around the target to help build an IR Data structure."""
    # Check if the target is already a builder.
    if isinstance(target, (_IrDataBuilder, _IrDataSequenceBuilder)):
        return target

    # Builders are only valid for IR data classes.
    if not hasattr(type(target), "IR_DATACLASS"):
        raise TypeError(f"Builder target {type(target)} is not an ir_data.message")

    # Create a builder and cast it to the target type to expose type hinting for
    # the wrapped type.
    return cast(MessageT, _IrDataBuilder(target))


def _field_checker_from_spec(spec: ir_data_fields.FieldSpec):
    """Helper that builds an FieldChecker that pretends to be an IR class."""
    if spec.is_sequence:
        return []
    if spec.is_dataclass:
        return _ReadOnlyFieldChecker(spec)
    return ir_data_fields.build_default(spec)


def _field_type(ir_or_spec: Union[MessageT, ir_data_fields.FieldSpec]) -> type[Any]:
    """Returns the Python type of the given field."""
    if isinstance(ir_or_spec, ir_data_fields.FieldSpec):
        return ir_or_spec.data_type
    return type(ir_or_spec)


class _ReadOnlyFieldChecker:
    """Class used to chain calls to fields that aren't set."""

    def __init__(self, ir_or_spec: Union[MessageT, ir_data_fields.FieldSpec]) -> None:
        self.ir_or_spec = ir_or_spec

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "ir_or_spec":
            return object.__setattr__(self, name, value)

        raise AttributeError(f"Cannot set {name} on read-only wrapper")

    def __getattribute__(
        self, name: str
    ) -> Any:  # pylint:disable=too-many-return-statements
        ir_or_spec = object.__getattribute__(self, "ir_or_spec")
        if name == "ir_or_spec":
            return ir_or_spec

        field_type = _field_type(ir_or_spec)
        spec = field_specs(field_type).get(name)
        if not spec:
            if isinstance(ir_or_spec, ir_data_fields.FieldSpec):
                if name == "HasField":
                    return lambda x: False
                if name == "WhichOneof":
                    return lambda x: None
            return object.__getattribute__(ir_or_spec, name)

        if isinstance(ir_or_spec, ir_data_fields.FieldSpec):
            # Just pretending
            return _field_checker_from_spec(spec)

        value = getattr(ir_or_spec, name)
        if value is None:
            return _field_checker_from_spec(spec)

        if spec.is_dataclass:
            if spec.is_sequence:
                return [_ReadOnlyFieldChecker(i) for i in value]
            return _ReadOnlyFieldChecker(value)

        return value

    def __eq__(self, other):
        if isinstance(other, _ReadOnlyFieldChecker):
            other = other.ir_or_spec
        return self.ir_or_spec == other

    def __ne__(self, other):
        return not self == other


def reader(obj: Union[MessageT, _ReadOnlyFieldChecker]) -> MessageT:
    """Builds a wrapper that can be used to read chains of possibly unset fields.

    This wrapper explicitly does not alter the wrapped object and is only
    intended for reading contents.

    For example, a `reader` lets you do:
    ```
    def get_function_name_end_column(function: ir_data.Function):
        return reader(function).function_name.source_location.end.column
    ```

    Instead of:
    ```
    def get_function_name_end_column(function: ir_data.Function):
        if function.function_name:
            if function.function_name.source_location:
                if function.function_name.source_location.end:
                    return function.function_name.source_location.end.column
        return 0
    ```

    Arguments:
        obj: The IR node to wrap.

    Returns:
        An object whose attributes return either:

        The value of `obj.attr` if `attr` is an atomic type and is set on
        `obj`.

        A default value for `obj.attr` if `obj.attr` is not set, but is of an
        atomic type.

        A read-only wrapper around `obj.attr` if `obj.attr` is set and is an IR
        node type.

        A read-only wrapper around an empty IR node object if `obj.attr` is not
        set, and is of an IR node type.
    """
    # Create a read-only wrapper if it's not already one.
    if not isinstance(obj, _ReadOnlyFieldChecker):
        obj = _ReadOnlyFieldChecker(obj)

    # Cast it back to the original type.
    return cast(MessageT, obj)


def _extract_ir(
    ir_or_wrapper: Union[MessageT, _ReadOnlyFieldChecker, _IrDataBuilder, None],
) -> Optional[ir_data_fields.IrDataclassInstance]:
    if isinstance(ir_or_wrapper, _ReadOnlyFieldChecker):
        ir_or_spec = ir_or_wrapper.ir_or_spec
        if isinstance(ir_or_spec, ir_data_fields.FieldSpec):
            # This is a placeholder entry, no fields are set.
            return None
        ir_or_wrapper = ir_or_spec
    elif isinstance(ir_or_wrapper, _IrDataBuilder):
        ir_or_wrapper = ir_or_wrapper.ir
    return cast(ir_data_fields.IrDataclassInstance, ir_or_wrapper)


def _fields_and_values(
    ir_wrapper: Union[MessageT, _ReadOnlyFieldChecker],
    value_filt: Optional[Callable[[Any], bool]] = None,
) -> list[Tuple[ir_data_fields.FieldSpec, Any]]:
    """Retrieves the fields and their values for a given IR data class.

    Args:
        ir: The IR data class or a read-only wrapper of an IR data class.
        value_filt: Optional filter used to exclude values.

    Returns:
        Fields and their values for the IR held by `ir_wrapper`, optionally
        filtered by `value_filt`.
    """
    if (ir := _extract_ir(ir_wrapper)) is None:
        return []

    return ir_data_fields.fields_and_values(ir, value_filt)


def get_set_fields(ir: MessageT):
    """Retrieves the field specs and values of fields that are set in `ir`.

    A value is considered "set" if it is not None.

    Arguments:
        ir: The IR node to operate on.

    Returns:
        The field specs and values of fields that are set in the given IR data
        class.
    """
    return _fields_and_values(ir, lambda v: v is not None)


def copy(ir_wrapper: Optional[MessageT]) -> Optional[MessageT]:
    """Creates a copy of the given IR data class."""
    if (ir := _extract_ir(ir_wrapper)) is None:
        return None
    ir_copy = ir_data_fields.copy(ir)
    return cast(MessageT, ir_copy)


def update(ir: MessageT, template: MessageT):
    """Updates `ir`s fields with all set fields in the template."""
    if not (template_ir := _extract_ir(template)):
        return

    ir_data_fields.update(cast(ir_data_fields.IrDataclassInstance, ir), template_ir)
