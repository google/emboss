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

"""Checks for dependency cycles in Emboss IR."""

from compiler.util import error
from compiler.util import ir_data
from compiler.util import ir_util
from compiler.util import traverse_ir


def _add_reference_to_dependencies(
    reference, dependencies, name, source_file_name, errors
):
    """Adds the specified `reference` to the `dependencies` set."""
    if reference.canonical_name.object_path[0] in {
        "$is_statically_sized",
        "$static_size_in_bits",
        "$next",
    }:
        # This error is a bit opaque, but given that the compiler used to crash
        # on this case -- for a couple of years -- and no one complained, it
        # seems safe to assume that this is a rare error.
        errors.append(
            [
                error.error(
                    source_file_name,
                    reference.source_location,
                    "Keyword `"
                    + reference.canonical_name.object_path[0]
                    + "` may not be used in this context.",
                ),
            ]
        )
        return
    dependencies[name] |= {ir_util.hashable_form_of_reference(reference)}


def _add_field_reference_to_dependencies(reference, dependencies, name):
    dependencies[name] |= {ir_util.hashable_form_of_reference(reference.path[0])}


def _add_name_to_dependencies(proto, dependencies):
    name = ir_util.hashable_form_of_reference(proto.name)
    dependencies.setdefault(name, set())
    return {"name": name}


def _find_dependencies(ir):
    """Constructs a dependency graph for the entire IR."""
    dependencies = {}
    errors = []
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.Reference],
        _add_reference_to_dependencies,
        # TODO(bolms): Add handling for references inside of attributes, once
        # there are attributes with non-constant values.
        skip_descendants_of={
            ir_data.AtomicType,
            ir_data.Attribute,
            ir_data.FieldReference,
        },
        incidental_actions={
            ir_data.Field: _add_name_to_dependencies,
            ir_data.EnumValue: _add_name_to_dependencies,
            ir_data.RuntimeParameter: _add_name_to_dependencies,
        },
        parameters={
            "dependencies": dependencies,
            "errors": errors,
        },
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.FieldReference],
        _add_field_reference_to_dependencies,
        skip_descendants_of={ir_data.Attribute},
        incidental_actions={
            ir_data.Field: _add_name_to_dependencies,
            ir_data.EnumValue: _add_name_to_dependencies,
            ir_data.RuntimeParameter: _add_name_to_dependencies,
        },
        parameters={"dependencies": dependencies},
    )
    return dependencies, errors


def _find_dependency_ordering_for_fields_in_structure(
    structure, type_definition, dependencies
):
    """Populates structure.fields_in_dependency_order."""
    # For fields which appear before their dependencies in the original source
    # text, this algorithm moves them to immediately after their dependencies.
    #
    # This is one of many possible schemes for constructing a dependency ordering;
    # it has the advantage that all of the generated fields (e.g., $size_in_bytes)
    # stay at the end of the ordering, which makes testing easier.
    order = []
    added = set()
    for parameter in type_definition.runtime_parameter:
        added.add(ir_util.hashable_form_of_reference(parameter.name))
    needed = list(range(len(structure.field)))
    while True:
        for i in range(len(needed)):
            field_number = needed[i]
            field = ir_util.hashable_form_of_reference(
                structure.field[field_number].name
            )
            assert field in dependencies, "dependencies = {}".format(dependencies)
            if all(dependency in added for dependency in dependencies[field]):
                order.append(field_number)
                added.add(field)
                del needed[i]
                break
        else:
            break
    # If a non-local-field dependency were in dependencies[field], then not all
    # fields would be added to the dependency ordering.  This shouldn't happen.
    assert len(order) == len(
        structure.field
    ), "order: {}\nlen(structure.field: {})".format(order, len(structure.field))
    del structure.fields_in_dependency_order[:]
    structure.fields_in_dependency_order.extend(order)


def _find_dependency_ordering_for_fields(ir):
    """Populates the fields_in_dependency_order fields throughout ir."""
    dependencies = {}
    # TODO(bolms): This duplicates work in _find_dependencies that could be
    # shared.
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.FieldReference],
        _add_field_reference_to_dependencies,
        skip_descendants_of={ir_data.Attribute},
        incidental_actions={
            ir_data.Field: _add_name_to_dependencies,
            ir_data.EnumValue: _add_name_to_dependencies,
            ir_data.RuntimeParameter: _add_name_to_dependencies,
        },
        parameters={"dependencies": dependencies},
    )
    traverse_ir.fast_traverse_ir_top_down(
        ir,
        [ir_data.Structure],
        _find_dependency_ordering_for_fields_in_structure,
        parameters={"dependencies": dependencies},
    )


def _find_module_import_dependencies(ir):
    """Constructs a dependency graph of module imports."""
    dependencies = {}
    for module in ir.module:
        foreign_imports = set()
        for foreign_import in module.foreign_import:
            # The prelude gets an automatic self-import that shouldn't cause any
            # problems.  No other self-imports are allowed, however.
            if foreign_import.file_name.text or module.source_file_name:
                foreign_imports |= {(foreign_import.file_name.text,)}
        dependencies[module.source_file_name,] = foreign_imports
    return dependencies


def _find_cycles(graph):
    """Finds cycles in graph.

    The graph does not need to be fully connected.

    Arguments:
      graph: A dictionary whose keys are node labels.  Values are sets of node
        labels, representing edges from the key node to the value nodes.

    Returns:
      A set of sets of nodes which form strongly-connected components (subgraphs
      where every node is directly or indirectly reachable from every other node).
      No node will be included in more than one strongly-connected component, by
      definition.  Strongly-connected components of size 1, where the node in the
      component does not have a self-edge, are not included in the result.

      Note that a strongly-connected component may have a more complex structure
      than a single loop.  For example:

          +-- A <-+ +-> B --+
          |       | |       |
          v        C        v
          D       ^ ^       E
          |       | |       |
          +-> F --+ +-- G <-+
    """
    # This uses Tarjan's strongly-connected components algorithm, as described by
    # Wikipedia.  This is a depth-first traversal of the graph with a node stack
    # that is independent of the call stack; nodes are added to the stack when
    # they are first encountered, but not removed until all nodes they can reach
    # have been checked.
    next_index = [0]
    node_indices = {}
    node_lowlinks = {}
    nodes_on_stack = set()
    stack = []
    nontrivial_components = set()

    def strong_connect(node):
        """Implements the STRONGCONNECT routine of Tarjan's algorithm."""
        node_indices[node] = next_index[0]
        node_lowlinks[node] = next_index[0]
        next_index[0] += 1
        stack.append(node)
        nodes_on_stack.add(node)

        for destination_node in graph[node]:
            if destination_node not in node_indices:
                strong_connect(destination_node)
                node_lowlinks[node] = min(
                    node_lowlinks[node], node_lowlinks[destination_node]
                )
            elif destination_node in nodes_on_stack:
                node_lowlinks[node] = min(
                    node_lowlinks[node], node_indices[destination_node]
                )

        strongly_connected_component = []
        if node_lowlinks[node] == node_indices[node]:
            while True:
                popped_node = stack.pop()
                nodes_on_stack.remove(popped_node)
                strongly_connected_component.append(popped_node)
                if popped_node == node:
                    break
            if (
                len(strongly_connected_component) > 1
                or strongly_connected_component[0]
                in graph[strongly_connected_component[0]]
            ):
                nontrivial_components.add(frozenset(strongly_connected_component))

    for node in graph:
        if node not in node_indices:
            strong_connect(node)
    return nontrivial_components


def _find_object_dependency_cycles(ir):
    """Finds dependency cycles in types in the ir."""
    dependencies, find_dependency_errors = _find_dependencies(ir)
    if find_dependency_errors:
        return find_dependency_errors
    errors = []
    cycles = _find_cycles(dict(dependencies))
    for cycle in cycles:
        # TODO(bolms): This lists the entire strongly-connected component in a
        # fairly arbitrary order.  This is simple, and handles components that
        # aren't simple cycles, but may not be the most user-friendly way to
        # present this information.
        cycle_list = sorted(list(cycle))
        node_object = ir_util.find_object(cycle_list[0], ir)
        error_group = [
            error.error(
                cycle_list[0][0],
                node_object.source_location,
                "Dependency cycle\n" + node_object.name.name.text,
            )
        ]
        for node in cycle_list[1:]:
            node_object = ir_util.find_object(node, ir)
            error_group.append(
                error.note(
                    node[0], node_object.source_location, node_object.name.name.text
                )
            )
        errors.append(error_group)
    return errors


def _find_module_dependency_cycles(ir):
    """Finds dependency cycles in modules in the ir."""
    dependencies = _find_module_import_dependencies(ir)
    cycles = _find_cycles(dict(dependencies))
    errors = []
    for cycle in cycles:
        cycle_list = sorted(list(cycle))
        module = ir_util.find_object(cycle_list[0], ir)
        error_group = [
            error.error(
                cycle_list[0][0],
                module.source_location,
                "Import dependency cycle\n" + module.source_file_name,
            )
        ]
        for module_name in cycle_list[1:]:
            module = ir_util.find_object(module_name, ir)
            error_group.append(
                error.note(
                    module_name[0], module.source_location, module.source_file_name
                )
            )
        errors.append(error_group)
    return errors


def find_dependency_cycles(ir):
    """Finds any dependency cycles in the ir."""
    errors = _find_module_dependency_cycles(ir)
    return errors + _find_object_dependency_cycles(ir)


def set_dependency_order(ir):
    """Sets the fields_in_dependency_order member of Structures."""
    _find_dependency_ordering_for_fields(ir)
    return []
