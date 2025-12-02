"""Program to generate a list of parse error examples for Emboss.

This is a development aid; when new grammar productions are added, this tool
can run to generate new error examples.

This program's output should be exhaustive: it exploits knowledge of the
tokenizer (in particular, what tokens can possibly follow other tokens) and
deep inspection of the parser tables to quickly find traversals of the parser
state space that correspond to realizable sequences of tokens.
"""

from __future__ import print_function

import argparse
import collections
import pkgutil
import sys

from compiler.front_end import lr1
from compiler.front_end import parser
from compiler.front_end import tokenizer


def _parse_command_line(argv):
    """Parses the given command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generator of examples inputs for Emboss parser errors.",
        prog=argv[0],
    )
    parser.add_argument(
        "--find-examples-for-existing-errors",
        action="store_true",
        help="If set, find examples for errors that already have messages.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="If set, print periodic status messages to stderr.",
    )
    return parser.parse_args(argv[1:])


def _token_sequences_for_symbols(parser, next_terminals):
    # `boundaries` is a dict of symbols to dicts of (first terminal, last
    # terminal) pairs to [terminal lists].
    #
    # `boundaries[symbol][(first, last)]` is a list of terminals that reduce to
    # `symbol`, and which starts with `first` and ends with `last`.
    #
    # As a special case, if `symbol` can be reduced from the empty sequence
    # (`[]`) then `boundaries[symbol][(None, None)] == []`.
    #
    # This construction makes it possible to efficiently find terminal sequences
    # that can be added to an input stream in order to force a REDUCE action as
    # a transition to a new top-of-stack state.
    boundaries = {}

    # The boundary for a terminal symbol is always just that terminal symbol.
    for terminal in parser.terminals:
        boundaries[terminal] = {(terminal, terminal): [terminal]}
    for nonterminal in parser.nonterminals:
        boundaries[nonterminal] = {}

    def _boundary(symbols):
        # `symbols` is the right-hand side (RHS) of a production -- something
        # like `["aexpr", "+", "mexpr"]`.
        #
        # The possible boundary terminals are determined by starting with the
        # empty sequence, and iteratively tacking on every sequence for each
        # symbol.  So if "aexpr" can be "- NUM", "NUM", or "( NUM )", the first
        # iteration will tack each of those three sequences onto the empty
        # sequence.  (Note that "NUM + NUM" would not be recorded because it has
        # the same start and end terminals as "NUM".)
        #
        # Then "+" can only be "+", so after the second iteration, the prefix
        # sequences would be "- NUM +", "NUM +", and "( NUM ) + ".
        #
        # Then the last iteration would add "- NUM", "NUM", and "( NUM )" to
        # each of the three existing prefixes, resulting in:
        #
        #     - NUM + - NUM
        #     - NUM + NUM
        #     - NUM + ( NUM )
        #     NUM + - NUM
        #     NUM + NUM
        #     NUM + ( NUM )
        #     ( NUM ) + - NUM
        #     ( NUM ) + NUM
        #     ( NUM ) + ( NUM )
        #
        # Several of these have the same start and end terminals, so after
        # culling `_boundary()` would return:
        #
        #     {
        #         ("-", "NUM"): ["-", "NUM", "+", "-", "NUM"],
        #         ("-", ")"): ["-", "NUM", "+", "(", "NUM", ")"],
        #         ("NUM", "NUM"): ["NUM", "+", "-", "NUM",],
        #         ("NUM", ")"): ["(", "NUM", ")", "+", "(", "NUM", ")"],
        #         ("(", "NUM"): ["(", "NUM", ")", "+", "-", "NUM",],
        #         ("(", ")"): ["(", "NUM", ")", "+", "(", "NUM", ")"],
        #     }
        prefix_boundaries = {(None, None): []}
        for symbol in symbols:
            new_prefix_boundaries = {}
            for symbol_boundary, symbol_token_sequence in boundaries[symbol].items():
                first, last = symbol_boundary
                if first is None and last is None:
                    new_prefix_boundaries.update(prefix_boundaries)
                    continue
                for boundary, prefix_token_sequence in prefix_boundaries.items():
                    if boundary == (None, None):
                        new_prefix_boundaries[(first, last)] = symbol_token_sequence
                    elif first in next_terminals[boundary[1]]:
                        new_prefix_boundaries[(boundary[0], last)] = (
                            prefix_token_sequence + symbol_token_sequence
                        )
            prefix_boundaries = new_prefix_boundaries
        return prefix_boundaries

    while True:
        # The first iteration picks up all the productions that start with and
        # end with terminal symbols.  The second iteration picks up productions
        # that start with nonterminals that the first iteration picked up.  The
        # third iteration picks up nonterminals that the first and second
        # picked up, and so on.
        #
        # This is guaranteed to end, in the worst case, when every terminal
        # symbol and epsilon has been added to the boundary set for every
        # nonterminal symbol.  This could be slow (polynomial time), but
        # requires a pathological grammar; useful grammars should complete in
        # only a few iterations.
        boundaries_to_add = {}
        for production in parser.productions:
            for boundary, sequence in _boundary(production.rhs).items():
                if boundary not in boundaries[production.lhs]:
                    boundaries_to_add.setdefault(production.lhs, {})[
                        boundary
                    ] = sequence
        if not boundaries_to_add:
            break
        for symbol in boundaries_to_add:
            boundaries[symbol].update(boundaries_to_add[symbol])

    return boundaries


def _token_examples():
    """Builds a list of example tokens for each token defined by the tokenizer."""
    tokens = {}
    for token in tokenizer.LITERAL_TOKEN_PATTERNS:
        tokens['"' + token + '"'] = token
    for token in tokenizer.REGEX_TOKEN_PATTERNS:
        if token.symbol:  # Skip whitespace.
            tokens[token.symbol] = token.example
    return tokens


class _RenderError(Exception):
    def __init__(self, last_token, token):
        self.last_token = last_token
        self.token = token
        super().__init__()


def _render(
    token_strings,
    next_terminals,
    sequence,
    trailing_error_terminals,
    trailing_ok_terminals,
):
    """Renders a sequence of tokens as source text.

    Arguments:
      sequence: A list of terminal tokens.

    Returns:
      A string which should tokenize to the original sequence (possibly with
      trailing newline).
    """
    result = []
    indent = 0
    last_token = None
    for token in sequence + ("$END",):
        if token not in next_terminals[last_token] and token != "$END":
            raise _RenderError(last_token, token)
        if token == "Indent":
            indent += 2
        elif token == "Dedent":
            indent -= 2
            if indent < 0:
                return None
        elif token == '"\\n"':
            result.append("\n")
        elif token == lr1.END_OF_INPUT:
            break
        else:
            if last_token in ['"\\n"', "Indent", "Dedent"]:
                result.append(" " * indent)
            if token == "$END":
                result.append("$ERR $ANY\n# errors: ")
                result.append(" ".join(trailing_error_terminals))
                result.append("\n# allowed: ")
                result.append(" ".join(trailing_ok_terminals))
            else:
                result.append(token_strings[token])
            if last_token != '"\\n"':
                result.append(" ")
        last_token = token
    return "".join(result).replace(" \n", "\n")


def _next_terminals(parser):
    """Generates a table of terminals which can follow other terminals."""
    terminals = parser.terminals
    next_terminals = {}

    # Most terminals can follow most terminals.  Only a few specific terminals
    # require special handling.
    #
    # TODO(bolms): automatically check that _render's output actually tokenizes
    # back into the desired token stream, so that any future tokens similar to
    # the Documentation token don't cause problems.
    regular_terminals = terminals - {
        '"\\n"',
        "Indent",
        "Dedent",
        "Documentation",
        "Comment",
        lr1.END_OF_INPUT,
    }

    regular_terminal_successors = regular_terminals | {
        "Documentation",
        '"\\n"',
        "Comment",
    }

    # Regular terminals can all follow each other (and themselves), and can be
    # followed by Documentation, Comment, or end of line.
    for terminal in regular_terminals:
        next_terminals[terminal] = regular_terminal_successors

    # Indents and Dedents can only occur at the start of a new line.  Newlines
    # cannot immediately follow newlines: the tokenizer ignores blank lines, so
    # only one newline token will be generated, no matter how many newlines
    # appear consecutively in the source code.
    #
    # A final newline and zero-or-more Dedents will be generated at the end of
    # input, so END_OF_INPUT can only appear after newline or Dedent.
    next_terminals['"\\n"'] = regular_terminals | {
        "Indent",
        "Dedent",
        "Documentation",
        "Comment",
        lr1.END_OF_INPUT,
    }

    # Indents can be followed by any regular terminal, Documentation, or
    # Comment.  They cannot be immediately followed by a newline or Dedent,
    # because they are only generated when there is a non-whitespace character
    # on the line.
    next_terminals["Indent"] = regular_terminals | {"Documentation", "Comment"}

    # Dedents may appear multiple times in a row, or followed by Documentation
    # or Comment or end of input.
    next_terminals["Dedent"] = regular_terminals | {
        "Dedent",
        "Documentation",
        "Comment",
        lr1.END_OF_INPUT,
    }

    # The regexes for Documentation and Comment consume all input until end of
    # line, so the only token that can follow Documentation or Comment is a
    # newline.
    next_terminals["Documentation"] = next_terminals["Comment"] = {'"\\n"'}

    # Any regular terminal, Documentation, Comment, or end of input can appear
    # at the very start of a source file.  It is computationally convenient to
    # treat None as if it can follow None.
    next_terminals[None] = regular_terminals | {
        "Documentation",
        "Comment",
        lr1.END_OF_INPUT,
        None,
    }

    # No terminals may follow END_OF_INPUT, by definition.
    next_terminals[lr1.END_OF_INPUT] = set()

    return next_terminals


def _target_states(parser, next_terminals, flags):
    """Generates a list of states which should have associated error messages."""
    terminals = parser.terminals
    states = set(parser.action.keys())
    # A state can only have an associated error if it is the start state or it
    # can be reached via a Shift action.  If it can only be reached via Reduce
    # actions, it should be impossible to generate an error in that state: any
    # error should have been generated in the previous state, instead of
    # Reducing.
    #
    # Since a Shift consumes input, the Shifted-to state will examine new
    # input, and thus could discover an error.
    #
    # Furthermore, in the Emboss grammar it is impossible to generate certain
    # token sequences, such as Documentation (regex: /-- .*/) followed by
    # anything other than a newline.  The Shifted-to state must have an error
    # action which corresponds to a terminal which can follow the shifted
    # terminal.  For example: in the Emboss grammar, a Documentation token is
    # always followed by a '"\\n"' token.  When the parser encounters a
    # Documentation token (in a valid position), it will Shift a new state with
    # error actions for all tokens other than '"\\n"': if Documentation were
    # ever followed by anything other than newline, it would be a parse error.
    # However, since the Documentation regex consumes all input until the
    # newline, it is impossible to get a token other than '"\\n"' after
    # Documentation, and thus it is impossible to actually trigger the error.
    target_states = set()
    if flags.find_examples_for_existing_errors:
        target_states.add(0)
    elif 0 not in parser.default_errors:
        for terminal in next_terminals[None]:
            if terminal not in parser.action.get(0, {}):
                target_states.add(0)
                break
    for state in states:
        for terminal in terminals:
            action = parser.action.get(state, {}).get(terminal)
            if not isinstance(action, lr1.Shift):
                continue
            next_state = action.state
            # Check that there is a reachable error action in the Shifted-to
            # state; if so, add the state to target_states.
            if (
                not flags.find_examples_for_existing_errors
                and next_state in parser.default_errors
            ):
                continue
            for next_terminal in next_terminals[terminal]:
                if next_terminal not in parser.action.get(next_state, {}):
                    target_states.add(next_state)
                    break
                elif flags.find_examples_for_existing_errors and isinstance(
                    parser.action[next_state][next_terminal], lr1.Error
                ):
                    target_states.add(next_state)
                    break
    return target_states


def _errors_by_production_search(parser, next_terminals, flags):
    """Finds all reachable parser states without exhaustive error messages."""
    # We can treat the states of a shift-reduce parser as nodes on a graph,
    # with edges labeled by the *symbol* (either terminal or nonterminal) which
    # causes the new state to be pushed onto the parser's state stack.  For
    # terminal symbols, this is just the symbol with an associated SHIFT action
    # in the ACTION table.  For nonterminal symbols, it is a bit more subtle:
    # after processing some number of additional terminal symbols, the parser
    # can encounter a REDUCE action (in whatever state is at the top of the
    # stack at that point).  Each REDUCE specifies a grammar production: a
    # number of entries are popped off of the state stack (equal to the length
    # of the productions right hand side), and new top of the stack and the
    # (nonterminal) symbol on the left hand side of the production are used to
    # look up a new state in the GOTO table.  The
    # _token_sequences_for_symbols() function finds appropriate sequences of
    # terminal symbols that will REDUCE to a specified nonterminal symbol.
    #
    # When traversing this graph, it is straightforward to check each state as
    # it is visited to see if the state has no default error message, and there
    # is some terminal such that (state, terminal) does not have an entry in
    # ACTION.  If so, the state is need of at least one error message.
    #
    # All of the above is true, BUT there is one additional wrinkle due to the
    # structure of Emboss tokens: not every terminal can actual follow every
    # other terminal.  For example, Indent can only follow "\n", and
    # nothing other than "\n" can follow Documentation.
    #
    # In order to handle this wrinkle, yet still be exhaustive, we have to
    # traverse a "virtual" graph, where the nodes in the graph are (state,
    # final terminal) pairs, where the "final terminal" is the last terminal
    # seen when the state was reached.  Then the potential transitions are all
    # of the token_sequences that can follow the final terminal.
    #
    # Even this is technically not fully sound, since the simple "can follow"
    # rule does not account for some impossibilities: for example, there cannot
    # be more Dedents than Indents to the left of any point in the token
    # stream.  However, the "can follow" rule seems to work well enough in
    # practice, and it means that we aren't trying to take the cartesian
    # product of the state tables for two different grammars.
    found_states = {(0, None): [None]}
    states_to_check = [(0, [None])]
    terminals = parser.terminals
    target_states = _target_states(parser, next_terminals, flags)
    token_sequences = _token_sequences_for_symbols(parser, next_terminals)
    result = []
    while states_to_check:
        state_to_check, prefix = states_to_check[0]
        del states_to_check[0]
        for symbol, boundaries in token_sequences.items():
            next_state = None
            if symbol in terminals:
                action = parser.action.get(state_to_check, {}).get(symbol)
                if isinstance(action, lr1.Shift):
                    next_state = action.state
            else:
                goto = parser.goto.get(state_to_check, {}).get(symbol)
                if goto is not None:
                    next_state = goto
            if next_state is None:
                continue
            for boundary, tokens in boundaries.items():
                if (
                    boundary[0] is not None
                    and boundary[0] not in next_terminals[prefix[-1]]
                ):
                    continue
                if boundary[1] is None:
                    new_end = prefix[-1]
                else:
                    new_end = boundary[1]
                if (next_state, new_end) in found_states:
                    continue
                found_states[(next_state, new_end)] = prefix + tokens
                states_to_check.append((next_state, prefix + tokens))
                if next_state in target_states:
                    error_terminals = set()
                    non_error_terminals = set()
                    for t in terminals:
                        action = parser.action.get(next_state, {}).get(t)
                        if action is None:
                            error_terminals.add(t)
                        elif isinstance(action, lr1.Error):
                            error_terminals.add(t + "^")
                        else:
                            non_error_terminals.add(t)
                    none_count = 0
                    for i in prefix:
                        if i is not None:
                            break
                        none_count += 1
                    result.append(
                        (
                            next_state,
                            tuple(prefix[none_count:] + tokens),
                            sorted(error_terminals),
                            sorted(non_error_terminals),
                        )
                    )
                    if flags.verbose and len(result) % 1000 == 0:
                        print("Found", len(result), "examples", file=sys.stderr)
    if flags.verbose and len(result) % 1000 != 0:
        print("Found", len(result), "examples", file=sys.stderr)
    return result


def main(flags):
    next_terminals = _next_terminals(parser.module_parser())
    examples = _errors_by_production_search(
        parser.module_parser(), next_terminals, flags
    )
    successful_examples = 0
    for example in sorted(examples):
        try:
            rendered = _render(_token_examples(), next_terminals, *example[1:])
            print("=" * 80)
            print("DO NOT " "SUBMIT: State", example[0])
            print("-" * 80)
            print(rendered)
            successful_examples += 1
        except _RenderError as r:
            print("Failed:", r.last_token, r.token)
    if flags.verbose:
        print(
            "Found valid examples for",
            successful_examples,
            "out of",
            len(examples),
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(_parse_command_line(sys.argv)))
