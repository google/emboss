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

"""Routines for fully traversing an IR."""

import inspect

from compiler.util import ir_data
from compiler.util import ir_data_fields
from compiler.util import ir_data_utils
from compiler.util import simple_memoizer


class _FunctionCaller:
    """Provides a template for setting up a generic call to a function.

    The function parameters are inspected at run-time to build up a set of valid
    and required arguments. When invoking the function unnecessary parameters
    will be trimmed out. If arguments are missing an assertion will be
    triggered.

    This is currently limited to functions that have at least one positional
    parameter.

    Example usage:
    ```
    def func_1(a, b, c=2): pass
    def func_2(a, d): pass
    caller_1 = _FunctionCaller(func_1)
    caller_2 = _FunctionCaller(func_2)
    generic_params = {"b": 2, "c": 3, "d": 4}

    # Equivalent of: func_1(a, b=2, c=3)
    caller_1.invoke(a, generic_params)

    # Equivalent of: func_2(a, d=4)
    caller_2.invoke(a, generic_params)
    """

    def __init__(self, function):
        self.function = function
        self.needs_filtering = True
        self.valid_arg_names = set()
        self.required_arg_names = set()

        argspec = inspect.getfullargspec(function)
        if argspec.varkw:
            # If the function accepts a kwargs parameter, then it will accept all
            # arguments.
            # Note: this isn't technically true if one of the keyword arguments has the
            # same name as one of the positional arguments.
            self.needs_filtering = False
        else:
            # argspec.args is a list of all parameter names excluding keyword only
            # args. The first element is our required positional_arg and should be
            # ignored.
            args = argspec.args[1:]
            self.valid_arg_names.update(args)

            # args.kwonlyargs gives us the list of keyword only args which are
            # also valid.
            self.valid_arg_names.update(argspec.kwonlyargs)

            # Required args are positional arguments that don't have defaults.
            # Keyword only args are always optional and can be ignored. Args with
            # defaults are the last elements of the argsepec.args list and should
            # be ignored.
            if argspec.defaults:
                # Trim the arguments with defaults.
                args = args[: -len(argspec.defaults)]
            self.required_arg_names.update(args)

    def invoke(self, positional_arg, keyword_args):
        """Invokes the function with the given args."""
        if self.needs_filtering:
            # Trim to just recognized args.
            matched_args = {
                k: v for k, v in keyword_args.items() if k in self.valid_arg_names
            }
            # Check if any required args are missing.
            missing_args = self.required_arg_names.difference(matched_args.keys())
            assert not missing_args, (
                f"Attempting to call '{self.function.__name__}'; "
                f"missing {missing_args} (have {set(keyword_args.keys())})"
            )
            keyword_args = matched_args

        return self.function(positional_arg, **keyword_args)


@simple_memoizer.memoize
def _memoized_caller(function):
    default_lambda_name = (lambda: None).__name__
    assert (
        callable(function) and function.__name__ != default_lambda_name
    ), "For performance reasons actions must be defined as static functions"
    return _FunctionCaller(function)


def _call_with_optional_args(function, positional_arg, keyword_args):
    """Calls function with whatever keyword_args it will accept."""
    caller = _memoized_caller(function)
    return caller.invoke(positional_arg, keyword_args)


def _fast_traverse_proto_top_down(
    proto, incidental_actions, pattern, skip_descendants_of, action, parameters
):
    """Traverses an IR, calling `action` on some nodes."""

    # Parameters are scoped to the branch of the tree, so make a copy here, before
    # any action or incidental_action can update them.
    parameters = parameters.copy()

    # If there is an incidental action for this node type, run it.
    if type(proto) in incidental_actions:  # pylint: disable=unidiomatic-typecheck
        for incidental_action in incidental_actions[type(proto)]:
            parameters.update(
                _call_with_optional_args(incidental_action, proto, parameters) or {}
            )

    # If we are at the end of pattern, check to see if we should call action.
    if len(pattern) == 1:
        new_pattern = pattern
        if pattern[0] == type(proto):
            parameters.update(_call_with_optional_args(action, proto, parameters) or {})
    else:
        # Otherwise, if this node's type matches the head of pattern, recurse with
        # the tail of the pattern.
        if pattern[0] == type(proto):
            new_pattern = pattern[1:]
        else:
            new_pattern = pattern

    # If the current node's type is one of the types whose branch should be
    # skipped, then bail.  This has to happen after `action` is called, because
    # clients rely on being able to, e.g., get a callback for the "root"
    # Expression without getting callbacks for every sub-Expression.
    # pylint: disable=unidiomatic-typecheck
    if type(proto) in skip_descendants_of:
        return

    # Otherwise, recurse.  _FIELDS_TO_SCAN_BY_CURRENT_AND_TARGET tells us, given
    # the current node's type and the current target type, which fields to check.
    singular_fields, repeated_fields = _FIELDS_TO_SCAN_BY_CURRENT_AND_TARGET[
        type(proto), new_pattern[0]
    ]
    for member_name in singular_fields:
        if proto.HasField(member_name):
            _fast_traverse_proto_top_down(
                getattr(proto, member_name),
                incidental_actions,
                new_pattern,
                skip_descendants_of,
                action,
                parameters,
            )
    for member_name in repeated_fields:
        for array_element in getattr(proto, member_name) or []:
            _fast_traverse_proto_top_down(
                array_element,
                incidental_actions,
                new_pattern,
                skip_descendants_of,
                action,
                parameters,
            )


def _fields_to_scan_by_current_and_target():
    """Generates _FIELDS_TO_SCAN_BY_CURRENT_AND_TARGET."""
    # In order to avoid spending a *lot* of time just walking the IR, this
    # function sets up a dict that allows `_fast_traverse_proto_top_down()` to
    # skip traversing large portions of the IR, depending on what node types it is
    # targeting.
    #
    # Without this branch culling scheme, the Emboss front end (at time of
    # writing) spends roughly 70% (19s out of 31s) of its time just walking the
    # IR.  With branch culling, that goes down to 6% (0.7s out of 12.2s).

    # type_to_fields is a map of types to maps of field names to field types.
    # That is, type_to_fields[ir_data.Module]["type"] == ir_data.AddressableUnit.
    type_to_fields = {}

    # Later, we need to know which fields are singular and which are repeated,
    # because the access methods are not uniform.  This maps (type, field_name)
    # tuples to descriptor labels: type_fields_to_cardinality[ir_data.Module,
    # "type"] == ir_data.Repeated.
    type_fields_to_cardinality = {}

    # Fill out the above maps by recursively walking the IR type tree, starting
    # from the root.
    types_to_check = [ir_data.EmbossIr]
    while types_to_check:
        type_to_check = types_to_check.pop()
        if type_to_check in type_to_fields:
            continue
        fields = {}
        for field_name, field_type in ir_data_utils.field_specs(type_to_check).items():
            if field_type.is_dataclass:
                fields[field_name] = field_type.data_type
                types_to_check.append(field_type.data_type)
                type_fields_to_cardinality[type_to_check, field_name] = (
                    field_type.container
                )
        type_to_fields[type_to_check] = fields

    # type_to_descendant_types is a map of all types that can be reached from a
    # particular type.  After the setup, type_to_descendant_types[ir_data.EmbossIr]
    # == set(<all types>) and type_to_descendant_types[ir_data.Reference] ==
    # {ir_data.CanonicalName, ir_data.Word, ir_data.Location} and
    # type_to_descendant_types[ir_data.Word] == set().
    #
    # The while loop basically ors in the known descendants of each known
    # descendant of each type until the dict stops changing, which is a bit
    # brute-force, but in practice only iterates a few times.
    type_to_descendant_types = {}
    for parent_type, field_map in type_to_fields.items():
        type_to_descendant_types[parent_type] = set(field_map.values())
    previous_map = {}
    while type_to_descendant_types != previous_map:
        # In order to check the previous iteration against the current iteration, it
        # is necessary to make a two-level copy.  Otherwise, the updates to the
        # values will also update previous_map's values, which causes the loop to
        # exit prematurely.
        previous_map = {k: set(v) for k, v in type_to_descendant_types.items()}
        for ancestor_type, descendents in previous_map.items():
            for descendent in descendents:
                type_to_descendant_types[ancestor_type] |= previous_map[descendent]

    # Finally, we have all of the information we need to make the map we really
    # want: given a current node type and a target node type, which fields should
    # be checked?  (This implicitly skips fields that *can't* contain the target
    # type.)
    fields_to_scan_by_current_and_target = {}
    for current_node_type in type_to_fields:
        for target_node_type in type_to_fields:
            singular_fields_to_scan = []
            repeated_fields_to_scan = []
            for field_name, field_type in type_to_fields[current_node_type].items():
                # If the target node type cannot contain another instance of itself, it
                # is still necessary to scan fields that have the actual target type.
                if (
                    target_node_type == field_type
                    or target_node_type in type_to_descendant_types[field_type]
                ):
                    # Singular and repeated fields go to different lists, so that they can
                    # be handled separately.
                    if (
                        type_fields_to_cardinality[current_node_type, field_name]
                        is not ir_data_fields.FieldContainer.LIST
                    ):
                        singular_fields_to_scan.append(field_name)
                    else:
                        repeated_fields_to_scan.append(field_name)
            fields_to_scan_by_current_and_target[
                current_node_type, target_node_type
            ] = (singular_fields_to_scan, repeated_fields_to_scan)
    return fields_to_scan_by_current_and_target


_FIELDS_TO_SCAN_BY_CURRENT_AND_TARGET = _fields_to_scan_by_current_and_target()


def _emboss_ir_action(ir):
    return {"ir": ir}


def _module_action(m):
    return {"source_file_name": m.source_file_name}


def _type_definition_action(t):
    return {"type_definition": t}


def _field_action(f):
    return {"field": f}


def fast_traverse_ir_top_down(
    ir,
    pattern,
    action,
    incidental_actions=None,
    skip_descendants_of=(),
    parameters=None,
):
    """Traverses an IR from the top down, executing the given actions.

    `fast_traverse_ir_top_down` walks the given IR in preorder traversal,
    specifically looking for nodes whose path from the root of the tree matches
    `pattern`.  For every node which matches `pattern`, `action` will be called.

    `pattern` is just a list of node types.  For example, to execute `print` on
    every `ir_data.Word` in the IR:

        fast_traverse_ir_top_down(ir, [ir_data.Word], print)

    If more than one type is specified, then each one must be found inside the
    previous.  For example, to print only the Words inside of import statements:

        fast_traverse_ir_top_down(ir, [ir_data.Import, ir_data.Word], print)

    The optional arguments provide additional control.

    `skip_descendants_of` is a list of types that should be treated as if they are
    leaf nodes when they are encountered.  That is, traversal will skip any
    nodes with any ancestor node whose type is in `skip_descendants_of`.  For
    example, to `do_something` only on outermost `Expression`s:

        fast_traverse_ir_top_down(ir, [ir_data.Expression], do_something,
                                  skip_descendants_of={ir_data.Expression})

    `parameters` specifies a dictionary of initial parameters which can be passed
    as arguments to `action` and `incidental_actions`.  Note that the parameters
    can be overridden for parts of the tree by `action` and `incidental_actions`.
    Parameters can be used to set an object which may be updated by `action`, such
    as a list of errors generated by some check in `action`:

        def check_structure(structure, errors):
          if structure_is_bad(structure):
            errors.append(error_for_structure(structure))

        errors = []
        fast_traverse_ir_top_down(ir, [ir_data.Structure], check_structure,
                                  parameters={"errors": errors})
        if errors:
          print("Errors: {}".format(errors))
          sys.exit(1)

    `incidental_actions` is a map from node types to functions (or tuples of
    functions or lists of functions) which should be called on those nodes.
    Because `fast_traverse_ir_top_down` may skip branches that can't contain
    `pattern`, functions in `incidental_actions` should generally not have any
    side effects: instead, they may return a dictionary, which will be used to
    override `parameters` for any children of the node they were called on.  For
    example:

        def do_something(expression, field_name=None):
          if field_name:
            print("Found {} inside {}".format(expression, field_name))
          else:
            print("Found {} not in any field".format(expression))

        fast_traverse_ir_top_down(
            ir, [ir_data.Expression], do_something,
            incidental_actions={ir_data.Field: lambda f: {"field_name": f.name}})

    (The `action` may also return a dict in the same way.)

    A few `incidental_actions` are built into `fast_traverse_ir_top_down`, so
    that certain parameters are contextually available with well-known names:

        ir: The complete IR (the root ir_data.EmbossIr node).
        source_file_name: The file name from which the current node was sourced.
        type_definition: The most-immediate ancestor type definition.
        field: The field containing the current node, if any.

    Arguments:
      ir: An ir_data.Ir object to walk.
      pattern: A list of node types to match.
      action: A callable, which will be called on nodes matching `pattern`.
      incidental_actions: A dict of node types to callables, which can be used to
          set new parameters for `action` for part of the IR tree.
      skip_descendants_of: A list of types whose children should be skipped when
          traversing `ir`.
      parameters: A list of top-level parameters.

    Returns:
      None
    """
    all_incidental_actions = {
        ir_data.EmbossIr: [_emboss_ir_action],
        ir_data.Module: [_module_action],
        ir_data.TypeDefinition: [_type_definition_action],
        ir_data.Field: [_field_action],
    }
    if incidental_actions:
        for key, incidental_action in incidental_actions.items():
            if not isinstance(incidental_action, (list, tuple)):
                incidental_action = [incidental_action]
            all_incidental_actions.setdefault(key, []).extend(incidental_action)
    _fast_traverse_proto_top_down(
        ir,
        all_incidental_actions,
        pattern,
        skip_descendants_of,
        action,
        parameters or {},
    )


def fast_traverse_node_top_down(
    node,
    pattern,
    action,
    incidental_actions=None,
    skip_descendants_of=(),
    parameters=None,
):
    """Traverse a subtree of an IR, executing the given actions.

    fast_traverse_node_top_down is like fast_traverse_ir_top_down, except that:

    It may be called on a subtree, instead of the top of the IR.

    It does not have any built-in incidental actions.

    Arguments:
      node: An ir_data.Ir object to walk.
      pattern: A list of node types to match.
      action: A callable, which will be called on nodes matching `pattern`.
      incidental_actions: A dict of node types to callables, which can be used to
          set new parameters for `action` for part of the IR tree.
      skip_descendants_of: A list of types whose children should be skipped when
          traversing `node`.
      parameters: A list of top-level parameters.

    Returns:
      None
    """
    _fast_traverse_proto_top_down(
        node,
        incidental_actions or {},
        pattern,
        skip_descendants_of or {},
        action,
        parameters or {},
    )
