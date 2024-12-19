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

"""Utilities for working with parse trees."""

from compiler.util import parser_types


def transform_parse_tree(
    parse_tree, token_handler, production_handlers, used_productions=None
):
    """Walks the provided parse_tree, calling handlers for each node.

    This function uses provided handlers to transform a parse tree into a new
    structure.  From the bottom up, calls a handler on each node, passing the
    node itself and the results of calling handlers on each child of the node
    (if any).

    This function avoids recursion, so it is suitable for very deep parse
    trees.

    Arguments:
        parse_tree: the tree to process
        token_handler: the handler to use for Token nodes.
        production_handlers: a map from productions to handlers for those
            productions.
        used_productions: an optional set; all encountered productions will be
            added to used_productions.

    Returns:
        The result of the production_handler for the top-level parse_tree node.
    """
    # The stack of entries to process.  Each entry is in one of two states,
    # depending on the 3rd element (children_completed):
    #
    # If False, the node's children have not been added, and the action is to
    # push the same node with children_completed=True, then push each an entry
    # for each of node's children with their children_completed=False.
    #
    # If True, the node's children have been added and (by the time the entry
    # is back on top of the stack) all of them have been processed.  In this
    # case, the action is to call the appropriate handler (token_handler() or
    # production_handlers[node.production]()) with the node and its transformed
    # children, then store the result in the node's parent's
    # transformed_children list.
    #
    # As an example, if we have:
    #
    #                                A
    #                               / \
    #                              B   C
    #                                 / \
    #                                D   E
    #
    # Then the steps are:
    #
    # Initialize:
    # 1.  Push (A, children_completed=False)
    #
    # Start handling A:
    # 2.  Pop (A, children_completed=False)
    # 3.  Push (A, children_completed=True)
    # 4.  Push (B, children_completed=False)
    # 5.  Push (C, children_completed=False)
    #
    # Start handling C:
    # 6.  Pop (C, children_completed=False)
    # 7.  Push (C, children_completed=True)
    # 8.  Push (D, children_completed=False)
    # 9.  Push (E, children_completed=False)
    #
    # Start handling E:
    # 10. Pop (E, children_completed=False)
    # 11. Push (E, children_completed=True)
    #
    # Finish handling E:
    # 12. Pop (E, children_completed=True)
    # 13. Insert token_handler(E) into C.transformed_children
    #
    # Start handling D:
    # 14. Pop (D, children_completed=False)
    # 15. Push (D, children_completed=True)
    #
    # Finish handling D:
    # 16. Pop (D, children_completed=True)
    # 17. Insert token_handler(D) into C.transformed_children
    #
    # Finish handling C:
    # 18. Pop (C, children_completed=True)
    # 19. Insert production_handlers[C.production](C, *C.transformed_children)
    #     into A.transformed_children
    #
    # Start handling B:
    # 20. Pop (B, children_completed=False)
    # 21. Push (B, children_completed=True)
    #
    # Finish handling B:
    # 22. Pop (B, children_completed=True)
    # 23. Insert token_handler(B) into A.transformed_children
    #
    # Finish handling A:
    # 24. Pop (A, children_completed=True)
    # 25. Return production_handlers[A.production](A, *A.transformed_children)
    #
    # It takes quite a few steps to handle even a small tree!
    stack = [(parse_tree, None, False, None)]
    while True:
        node, parent, children_completed, transformed_children = stack.pop()
        if not children_completed:
            parent_entry = []
            stack.append((node, parent, True, parent_entry))
            if hasattr(node, "children"):
                for child in node.children:
                    stack.append((child, parent_entry, False, None))
                if used_productions is not None:
                    used_productions.add(node.production)
        else:
            if isinstance(node, parser_types.Token):
                transformed_node = token_handler(node)
            else:
                transformed_node = production_handlers[node.production](
                    *([node] + transformed_children)
                )
            if parent is None:
                return transformed_node
            else:
                parent.insert(0, transformed_node)
