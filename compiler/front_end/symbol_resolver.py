# Copyright 2019 Google LLC
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

"""Symbol resolver for Emboss IR.

The resolve_symbols function should be used to generate canonical resolutions
for all symbol references in an Emboss IR.
"""

import collections

from compiler.util import error
from compiler.util import ir_data
from compiler.util import ir_data_utils
from compiler.util import ir_util
from compiler.util import traverse_ir

# TODO(bolms): Symbol resolution raises an exception at the first error, but
# this is one place where it can make sense to report multiple errors.

FileLocation = collections.namedtuple("FileLocation", ["file", "location"])


def ambiguous_name_error(file_name, location, name, candidate_locations):
    """A name cannot be resolved because there are two or more candidates."""
    result = [error.error(file_name, location, "Ambiguous name '{}'".format(name))]
    for location in sorted(candidate_locations):
        result.append(
            error.note(location.file, location.location, "Possible resolution")
        )
    return result


def duplicate_name_error(file_name, location, name, original_location):
    """A name is defined two or more times."""
    return [
        error.error(file_name, location, "Duplicate name '{}'".format(name)),
        error.note(
            original_location.file, original_location.location, "Original definition"
        ),
    ]


def missing_name_error(file_name, location, name):
    return [error.error(file_name, location, "No candidate for '{}'".format(name))]


def array_subfield_error(file_name, location, name):
    return [
        error.error(
            file_name, location, "Cannot access member of array '{}'".format(name)
        )
    ]


def noncomposite_subfield_error(file_name, location, name):
    return [
        error.error(
            file_name,
            location,
            "Cannot access member of noncomposite field '{}'".format(name),
        )
    ]


def _nested_name(canonical_name, name):
    """Creates a new CanonicalName with name appended to the object_path."""
    return ir_data.CanonicalName(
        module_file=canonical_name.module_file,
        object_path=list(canonical_name.object_path) + [name],
    )


class _Scope(dict):
    """A _Scope holds data for a symbol.

    A _Scope is a dict with some additional attributes.  Lexically nested names
    are kept in the dict, and bookkeeping is kept in the additional attributes.

    For example, each module should have a child _Scope for each type contained in
    the module.  `struct` and `bits` types should have nested _Scopes for each
    field; `enum` types should have nested scopes for each enumerated name.

    Attributes:
      canonical_name: The absolute name of this symbol; e.g. ("file.emb",
        "TypeName", "SubTypeName", "field_name")
      source_location: The ir_data.SourceLocation where this symbol is defined.
      visibility: LOCAL, PRIVATE, or SEARCHABLE; see below.
      alias: If set, this name is merely a pointer to another name.
    """

    __slots__ = ("canonical_name", "source_location", "visibility", "alias")

    # A LOCAL name is visible outside of its enclosing scope, but should not be
    # found when searching for a name.  That is, this name should be matched in
    # the tail of a qualified reference (the 'bar' in 'foo.bar'), but not when
    # searching for names (the 'foo' in 'foo.bar' should not match outside of
    # 'foo's scope).  This applies to public field names.
    LOCAL = object()

    # A PRIVATE name is similar to LOCAL except that it is never visible outside
    # its enclosing scope.  This applies to abbreviations of field names: if 'a'
    # is an abbreviation for field 'apple', then 'foo.a' is not a valid reference;
    # instead it should be 'foo.apple'.
    PRIVATE = object()

    # A SEARCHABLE name is visible as long as it is in a scope in the search list.
    # This applies to type names ('Foo'), which may be found from many scopes.
    SEARCHABLE = object()

    def __init__(self, canonical_name, source_location, visibility, alias=None):
        super(_Scope, self).__init__()
        self.canonical_name = canonical_name
        self.source_location = source_location
        self.visibility = visibility
        self.alias = alias


def _add_name_to_scope(name_ir, scope, canonical_name, visibility, errors):
    """Adds the given name_ir to the given scope."""
    name = name_ir.text
    new_scope = _Scope(canonical_name, name_ir.source_location, visibility)
    if name in scope:
        errors.append(
            duplicate_name_error(
                scope.canonical_name.module_file,
                name_ir.source_location,
                name,
                FileLocation(
                    scope[name].canonical_name.module_file, scope[name].source_location
                ),
            )
        )
    else:
        scope[name] = new_scope
    return new_scope


def _add_name_to_scope_and_normalize(name_ir, scope, visibility, errors):
    """Adds the given name_ir to scope and sets its canonical_name."""
    name = name_ir.name.text
    canonical_name = _nested_name(scope.canonical_name, name)
    ir_data_utils.builder(name_ir).canonical_name.CopyFrom(canonical_name)
    return _add_name_to_scope(name_ir.name, scope, canonical_name, visibility, errors)


def _add_struct_field_to_scope(field, scope, errors):
    """Adds the name of the given field to the scope."""
    new_scope = _add_name_to_scope_and_normalize(
        field.name, scope, _Scope.LOCAL, errors
    )
    if field.HasField("abbreviation"):
        _add_name_to_scope(
            field.abbreviation, scope, new_scope.canonical_name, _Scope.PRIVATE, errors
        )

    value_builtin_name = ir_data.Word(
        text="this",
        source_location=ir_data.Location(is_synthetic=True),
    )
    # In "inside field" scope, the name `this` maps back to the field itself.
    # This is important for attributes like `[requires]`.
    _add_name_to_scope(
        value_builtin_name, new_scope, field.name.canonical_name, _Scope.PRIVATE, errors
    )


def _add_parameter_name_to_scope(parameter, scope, errors):
    """Adds the name of the given parameter to the scope."""
    _add_name_to_scope_and_normalize(parameter.name, scope, _Scope.LOCAL, errors)


def _add_enum_value_to_scope(value, scope, errors):
    """Adds the name of the enum value to scope."""
    _add_name_to_scope_and_normalize(value.name, scope, _Scope.LOCAL, errors)


def _add_type_name_to_scope(type_definition, scope, errors):
    """Adds the name of type_definition to the given scope."""
    new_scope = _add_name_to_scope_and_normalize(
        type_definition.name, scope, _Scope.SEARCHABLE, errors
    )
    return {"scope": new_scope}


def _set_scope_for_type_definition(type_definition, scope):
    """Sets the current scope for an ir_data.AddressableUnit."""
    return {"scope": scope[type_definition.name.name.text]}


def _add_module_to_scope(module, scope):
    """Adds the name of the module to the given scope."""
    module_symbol_table = _Scope(
        ir_data.CanonicalName(module_file=module.source_file_name, object_path=[]),
        None,
        _Scope.SEARCHABLE,
    )
    scope[module.source_file_name] = module_symbol_table
    return {"scope": scope[module.source_file_name]}


def _set_scope_for_module(module, scope):
    """Adds the name of the module to the given scope."""
    return {"scope": scope[module.source_file_name]}


def _add_import_to_scope(foreign_import, table, module, errors):
    if not foreign_import.local_name.text:
        # This is the prelude import; ignore it.
        return
    _add_alias_to_scope(
        foreign_import.local_name,
        table,
        module.canonical_name,
        [foreign_import.file_name.text],
        _Scope.SEARCHABLE,
        errors,
    )


def _construct_symbol_tables(ir):
    """Constructs per-module symbol tables for each module in ir."""
    symbol_tables = {}
    errors = []
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.Module],
        _add_module_to_scope,
        parameters={"errors": errors, "scope": symbol_tables},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.TypeDefinition],
        _add_type_name_to_scope,
        incidental_actions={ir_data.Module: _set_scope_for_module},
        parameters={"errors": errors, "scope": symbol_tables},
    )
    if errors:
        # Ideally, we would find duplicate field names elsewhere in the module, even
        # if there are duplicate type names, but field/enum names in the colliding
        # types also end up colliding, leading to spurious errors.  E.g., if you
        # have two `struct Foo`s, then the field check will also discover a
        # collision for `$size_in_bytes`, since there are two `Foo.$size_in_bytes`.
        return symbol_tables, errors

    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.EnumValue],
        _add_enum_value_to_scope,
        incidental_actions={
            ir_data.Module: _set_scope_for_module,
            ir_data.TypeDefinition: _set_scope_for_type_definition,
        },
        parameters={"errors": errors, "scope": symbol_tables},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.Field],
        _add_struct_field_to_scope,
        incidental_actions={
            ir_data.Module: _set_scope_for_module,
            ir_data.TypeDefinition: _set_scope_for_type_definition,
        },
        parameters={"errors": errors, "scope": symbol_tables},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.RuntimeParameter],
        _add_parameter_name_to_scope,
        incidental_actions={
            ir_data.Module: _set_scope_for_module,
            ir_data.TypeDefinition: _set_scope_for_type_definition,
        },
        parameters={"errors": errors, "scope": symbol_tables},
    )
    return symbol_tables, errors


def _add_alias_to_scope(name_ir, table, scope, alias, visibility, errors):
    """Adds the given name to the scope as an alias."""
    name = name_ir.text
    new_scope = _Scope(
        _nested_name(scope, name), name_ir.source_location, visibility, alias
    )
    scoped_table = table[scope.module_file]
    for path_element in scope.object_path:
        scoped_table = scoped_table[path_element]
    if name in scoped_table:
        errors.append(
            duplicate_name_error(
                scoped_table.canonical_name.module_file,
                name_ir.source_location,
                name,
                FileLocation(
                    scoped_table[name].canonical_name.module_file,
                    scoped_table[name].source_location,
                ),
            )
        )
    else:
        scoped_table[name] = new_scope
    return new_scope


def _resolve_head_of_field_reference(
    field_reference, table, current_scope, visible_scopes, source_file_name, errors
):
    return _resolve_reference(
        field_reference.path[0],
        table,
        current_scope,
        visible_scopes,
        source_file_name,
        errors,
    )


def _resolve_reference(
    reference, table, current_scope, visible_scopes, source_file_name, errors
):
    """Sets the canonical name of the given reference."""
    if reference.HasField("canonical_name"):
        # This reference has already been resolved by the _resolve_field_reference
        # pass.
        return
    target = _find_target_of_reference(
        reference, table, current_scope, visible_scopes, source_file_name, errors
    )
    if target is not None:
        assert not target.alias
        ir_data_utils.builder(reference).canonical_name.CopyFrom(target.canonical_name)


def _find_target_of_reference(
    reference, table, current_scope, visible_scopes, source_file_name, errors
):
    """Returns the resolved name of the given reference."""
    found_in_table = None
    name = reference.source_name[0].text
    for scope in visible_scopes:
        scoped_table = table[scope.module_file]
        for path_element in scope.object_path or []:
            scoped_table = scoped_table[path_element]
        if name in scoped_table and (
            scope == current_scope or scoped_table[name].visibility == _Scope.SEARCHABLE
        ):
            # Prelude is "", so explicitly check for None.
            if found_in_table is not None:
                # TODO(bolms): Currently, this catches the case where a module tries to
                # use a name that is defined (at the same scope) in two different
                # modules.  It may make sense to raise duplicate_name_error whenever two
                # modules define the same name (whether it is used or not), and reserve
                # ambiguous_name_error for cases where a name is found in multiple
                # scopes.
                errors.append(
                    ambiguous_name_error(
                        source_file_name,
                        reference.source_location,
                        name,
                        [
                            FileLocation(
                                found_in_table[name].canonical_name.module_file,
                                found_in_table[name].source_location,
                            ),
                            FileLocation(
                                scoped_table[name].canonical_name.module_file,
                                scoped_table[name].source_location,
                            ),
                        ],
                    )
                )
                continue
            found_in_table = scoped_table
            if reference.is_local_name:
                # This is a little hacky.  When "is_local_name" is True, the name refers
                # to a type that was defined inline.  In many cases, the type should be
                # found at the same scope as the field; e.g.:
                #
                #     struct Foo:
                #       0 [+1]  enum  bar:
                #         BAZ = 1
                #
                # In this case, `Foo.bar` has type `Foo.Bar`.  Unfortunately, things
                # break down a little bit when there is an inline type in an anonymous
                # `bits`:
                #
                #     struct Foo:
                #       0 [+1]  bits:
                #         0 [+7]  enum  bar:
                #           BAZ = 1
                #
                # Types inside of anonymous `bits` are hoisted into their parent type,
                # so instead of `Foo.EmbossReservedAnonymous1.Bar`, `bar`'s type is just
                # `Foo.Bar`.  Unfortunately, the field is still
                # `Foo.EmbossReservedAnonymous1.bar`, so `bar`'s type won't be found in
                # `bar`'s `current_scope`.
                #
                # (The name `bar` is exposed from `Foo` as an alias virtual field, so
                # perhaps the correct answer is to allow type aliases, so that `Bar` can
                # be found in both `Foo` and `Foo.EmbossReservedAnonymous1`.  That would
                # involve an entirely new feature, though.)
                #
                # The workaround here is to search scopes from the innermost outward,
                # and just stop as soon as a match is found.  This isn't ideal, because
                # it relies on other bits of the front end having correctly added the
                # inline type to the correct scope before symbol resolution, but it does
                # work.  Names with False `is_local_name` will still be checked for
                # ambiguity.
                break
    if found_in_table is None:
        errors.append(
            missing_name_error(
                source_file_name, reference.source_name[0].source_location, name
            )
        )
    if not errors:
        for subname in reference.source_name:
            if subname.text not in found_in_table:
                errors.append(
                    missing_name_error(
                        source_file_name, subname.source_location, subname.text
                    )
                )
                return None
            found_in_table = found_in_table[subname.text]
            while found_in_table.alias:
                referenced_table = table
                for name in found_in_table.alias:
                    referenced_table = referenced_table[name]
                    # TODO(bolms): This section should really be a recursive lookup
                    # function, which would be able to handle arbitrary aliases through
                    # other aliases.
                    #
                    # This should be fine for now, since the only aliases here should be
                    # imports, which can't refer to other imports.
                    assert not referenced_table.alias, "Alias found to contain alias."
                found_in_table = referenced_table
        return found_in_table
    return None


def _resolve_field_reference(field_reference, source_file_name, errors, ir):
    """Resolves the References inside of a FieldReference."""
    if field_reference.path[-1].HasField("canonical_name"):
        # Already done.
        return
    previous_field = ir_util.find_object_or_none(field_reference.path[0], ir)
    previous_reference = field_reference.path[0]
    for ref in field_reference.path[1:]:
        while ir_util.field_is_virtual(previous_field):
            if (
                previous_field.read_transform.WhichOneof("expression")
                == "field_reference"
            ):
                # Pass a separate error list into the recursive _resolve_field_reference
                # call so that only one copy of the error for a particular reference
                # will actually surface: in particular, the one that results from a
                # direct call from traverse_ir_top_down into _resolve_field_reference.
                new_errors = []
                _resolve_field_reference(
                    previous_field.read_transform.field_reference,
                    previous_field.name.canonical_name.module_file,
                    new_errors,
                    ir,
                )
                # If the recursive _resolve_field_reference was unable to resolve the
                # field, then bail.  Otherwise we get a cascade of errors, where an
                # error in `x` leads to errors in anything trying to reach a member of
                # `x`.
                if not previous_field.read_transform.field_reference.path[-1].HasField(
                    "canonical_name"
                ):
                    return
                previous_field = ir_util.find_object(
                    previous_field.read_transform.field_reference.path[-1], ir
                )
            else:
                errors.append(
                    noncomposite_subfield_error(
                        source_file_name,
                        previous_reference.source_location,
                        previous_reference.source_name[0].text,
                    )
                )
                return
        if previous_field.type.WhichOneof("type") == "array_type":
            errors.append(
                array_subfield_error(
                    source_file_name,
                    previous_reference.source_location,
                    previous_reference.source_name[0].text,
                )
            )
            return
        assert previous_field.type.WhichOneof("type") == "atomic_type"
        member_name = ir_data_utils.copy(
            previous_field.type.atomic_type.reference.canonical_name
        )
        ir_data_utils.builder(member_name).object_path.extend([ref.source_name[0].text])
        previous_field = ir_util.find_object_or_none(member_name, ir)
        if previous_field is None:
            errors.append(
                missing_name_error(
                    source_file_name,
                    ref.source_name[0].source_location,
                    ref.source_name[0].text,
                )
            )
            return
        ir_data_utils.builder(ref).canonical_name.CopyFrom(member_name)
        previous_reference = ref


def _set_visible_scopes_for_type_definition(type_definition, visible_scopes):
    """Sets current_scope and visible_scopes for the given type_definition."""
    return {
        "current_scope": type_definition.name.canonical_name,
        # In order to ensure that the iteration through scopes in
        # _find_target_of_reference will go from innermost to outermost, it is
        # important that the current scope (type_definition.name.canonical_name)
        # precedes the previous visible_scopes here.
        "visible_scopes": (type_definition.name.canonical_name,) + visible_scopes,
    }


def _set_visible_scopes_for_module(module):
    """Sets visible_scopes for the given module."""
    self_scope = ir_data.CanonicalName(module_file=module.source_file_name)
    extra_visible_scopes = []
    for foreign_import in module.foreign_import:
        # Anonymous imports are searched for top-level names; named imports are not.
        # As of right now, only the prelude should be imported anonymously; other
        # modules must be imported with names.
        if not foreign_import.local_name.text:
            extra_visible_scopes.append(
                ir_data.CanonicalName(module_file=foreign_import.file_name.text)
            )
    return {"visible_scopes": (self_scope,) + tuple(extra_visible_scopes)}


def _set_visible_scopes_for_attribute(attribute, field, visible_scopes):
    """Sets current_scope and visible_scopes for the attribute."""
    del attribute  # Unused
    if field is None:
        return
    return {
        "current_scope": field.name.canonical_name,
        "visible_scopes": (field.name.canonical_name,) + visible_scopes,
    }


def _module_source_from_table_action(m, table):
    return {"module": table[m.source_file_name]}


def _resolve_symbols_from_table(ir, table):
    """Resolves all references in the given IR, given the constructed table."""
    errors = []
    # Symbol resolution is broken into five passes.  First, this code resolves any
    # imports, and adds import aliases to modules.
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.Import],
        _add_import_to_scope,
        incidental_actions={
            ir_data.Module: _module_source_from_table_action,
        },
        parameters={"errors": errors, "table": table},
    )
    if errors:
        return errors
    # Next, this resolves all absolute references (e.g., it resolves "UInt" in
    # "0:1  UInt  field" to [prelude]::UInt).
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.Reference],
        _resolve_reference,
        skip_descendants_of=(ir_data.FieldReference,),
        incidental_actions={
            ir_data.TypeDefinition: _set_visible_scopes_for_type_definition,
            ir_data.Module: _set_visible_scopes_for_module,
            ir_data.Attribute: _set_visible_scopes_for_attribute,
        },
        parameters={"table": table, "errors": errors, "field": None},
    )
    # Lastly, head References to fields (e.g., the `a` of `a.b.c`) are resolved.
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.FieldReference],
        _resolve_head_of_field_reference,
        incidental_actions={
            ir_data.TypeDefinition: _set_visible_scopes_for_type_definition,
            ir_data.Module: _set_visible_scopes_for_module,
            ir_data.Attribute: _set_visible_scopes_for_attribute,
        },
        parameters={"table": table, "errors": errors, "field": None},
    )
    return errors


def resolve_field_references(ir):
    """Resolves structure member accesses ("field.subfield") in ir."""
    errors = []
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.FieldReference],
        _resolve_field_reference,
        incidental_actions={
            ir_data.TypeDefinition: _set_visible_scopes_for_type_definition,
            ir_data.Module: _set_visible_scopes_for_module,
            ir_data.Attribute: _set_visible_scopes_for_attribute,
        },
        parameters={"errors": errors, "field": None},
    )
    return errors


def resolve_symbols(ir):
    """Resolves the symbols in all modules in ir."""
    symbol_tables, errors = _construct_symbol_tables(ir)
    if errors:
        return errors
    return _resolve_symbols_from_table(ir, symbol_tables)
