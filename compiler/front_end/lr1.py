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

"""LR(1) parser generator.

The primary class in this module, Grammar, takes a list of context-free grammar
productions, and produces the corresponding LR(1) shift-reduce parser.  This is
an implementation of the algorithm on pages 221 and 261-265 of "Compilers:
Principles, Techniques, & Tools" (Second Edition) by Aho, Lam, Sethi, and
Ullman, also known as "The Dragon Book," hereafter referred to as "ALSU."

This module only implements the LR(1) algorithms; unlike tools such as yacc, it
does not implement the various bits of glue necessary to actually use a parser.
Clients are expected to provide their own tokenizers and handle turning a raw
parse tree into an intermediate representation on their own.
"""

import collections

from compiler.util import parser_types


class Item(
    collections.namedtuple("Item", ["production", "dot", "terminal", "next_symbol"])
):
    """An Item is an LR(1) Item: a production, a cursor location, and a terminal.

    An Item represents a partially-parsed production, and a lookahead symbol.
    The position of the dot indicates what portion of the production has been
    parsed.  Generally, Items are an internal implementation detail, but they
    can be useful elsewhere, particularly for debugging.

    Attributes:
        production: The Production this Item covers.
        dot: The index of the "dot" in production's rhs.
        terminal: The terminal lookahead symbol that follows the production in
            the input stream.
        next_symbol: The lookahead symbol.
    """

    def __str__(self):
        """__str__ generates ASLU notation."""
        return (
            str(self.production.lhs)
            + " -> "
            + " ".join(
                [
                    str(r)
                    for r in self.production.rhs[0 : self.dot]
                    + (".",)
                    + self.production.rhs[self.dot :]
                ]
            )
            + ", "
            + str(self.terminal)
        )

    @staticmethod
    def parse(text):
        """Parses an Item in ALSU notation.

        Parses an Item from notation like:

           symbol -> foo . bar baz, qux

        where "symbol -> foo bar baz" will be taken as the production, the position
        of the "." is taken as "dot" (in this case 1), and the symbol after "," is
        taken as the "terminal".  The following are also valid items:

           sym -> ., foo
           sym -> . foo bar, baz
           sym -> foo bar ., baz

        Symbols on the right-hand side of the production should be separated by
        whitespace.

        Arguments:
          text: The text to parse into an Item.

        Returns:
          An Item.
        """
        production, terminal = text.split(",")
        terminal = terminal.strip()
        if terminal == "$":
            terminal = END_OF_INPUT
        lhs, rhs = production.split("->")
        lhs = lhs.strip()
        if lhs == "S'":
            lhs = START_PRIME
        before_dot, after_dot = rhs.split(".")
        handle = before_dot.split()
        tail = after_dot.split()
        return make_item(
            parser_types.Production(lhs, tuple(handle + tail)), len(handle), terminal
        )


def make_item(production, dot, symbol):
    return Item(
        production,
        dot,
        symbol,
        None if dot >= len(production.rhs) else production.rhs[dot],
    )


class Conflict(collections.namedtuple("Conflict", ["state", "symbol", "actions"])):
    """Conflict represents a parse conflict."""

    def __str__(self):
        return "Conflict for {} in state {}: ".format(
            self.symbol, self.state
        ) + " vs ".join([str(a) for a in self.actions])


Shift = collections.namedtuple("Shift", ["state", "items"])
Reduce = collections.namedtuple("Reduce", ["rule"])
Accept = collections.namedtuple("Accept", [])
Error = collections.namedtuple("Error", ["code"])

Symbol = collections.namedtuple("Symbol", ["symbol"])

# START_PRIME is the implicit 'real' root symbol for the grammar.
START_PRIME = "S'"

# END_OF_INPUT is the implicit symbol at the end of input.
END_OF_INPUT = "$"

# ANY_TOKEN is used by mark_error as a "wildcard" token that should be replaced
# by every other token.
ANY_TOKEN = parser_types.Token(object(), "*", parser_types.parse_location("0:0-0:0"))


class Reduction(
    collections.namedtuple(
        "Reduction", ["symbol", "children", "production", "source_location"]
    )
):
    """A Reduction is a non-leaf node in a parse tree.

    Attributes:
      symbol: The name of this element in the parse.
      children: The child elements of this parse.
      production: The grammar production to which this reduction corresponds.
      source_location: If known, the range in the source text corresponding to the
        tokens from which this reduction was parsed.  May be 'None' if this
        reduction was produced from no symbols, or if the tokens fed to `parse`
        did not include source_location.
    """

    pass


class Grammar(object):
    """Grammar is an LR(1) context-free grammar.

    Attributes:
      start: The start symbol for the grammar.
      productions: A list of productions in the grammar, including the S' -> start
        production.
      symbols: A set of all symbols in the grammar, including $ and S'.
      nonterminals: A set of all nonterminal symbols in the grammar, including S'.
      terminals: A set of all terminal symbols in the grammar, including $.
    """

    def __init__(self, start_symbol, productions):
        """Constructs a Grammar object.

        Arguments:
          start_symbol: The start symbol for the grammar.
          productions: A list of productions (not including the "S' -> start_symbol"
              production).
        """
        object.__init__(self)
        self.start = start_symbol
        self._seed_production = parser_types.Production(START_PRIME, (self.start,))
        self.productions = productions + [self._seed_production]

        self._single_level_closure_of_item_cache = {}
        self._closure_of_item_cache = {}
        self._compute_symbols()
        self._compute_seed_firsts()
        self._set_productions_by_lhs()
        self._populate_item_cache()

    def _set_productions_by_lhs(self):
        # Prepopulating _productions_by_lhs speeds up _closure_of_item by about 30%,
        # which is significant on medium-to-large grammars.
        self._productions_by_lhs = {}
        for production in self.productions:
            self._productions_by_lhs.setdefault(production.lhs, list()).append(
                production
            )

    def _populate_item_cache(self):
        # There are a relatively small number of possible Items for a grammar, and
        # the algorithm needs to get Items from their constituent components very
        # frequently.  As it turns out, pre-caching all possible Items results in a
        # ~35% overall speedup to Grammar.parser().
        self._item_cache = {}
        for symbol in self.terminals:
            for production in self.productions:
                for dot in range(len(production.rhs) + 1):
                    self._item_cache[production, dot, symbol] = make_item(
                        production, dot, symbol
                    )

    def _compute_symbols(self):
        """Finds all grammar symbols, and sorts them into terminal and non-terminal.

        Nonterminal symbols are those which appear on the left side of any
        production.  Terminal symbols are those which do not.

        _compute_symbols is used during __init__.
        """
        self.symbols = {END_OF_INPUT}
        self.nonterminals = set()
        for production in self.productions:
            self.symbols.add(production.lhs)
            self.nonterminals.add(production.lhs)
            for symbol in production.rhs:
                self.symbols.add(symbol)
        self.terminals = self.symbols - self.nonterminals

    def _compute_seed_firsts(self):
        """Computes FIRST (ALSU p221) for all terminal and nonterminal symbols.

        The algorithm for computing FIRST is an iterative one that terminates when
        it reaches a fixed point (that is, when further iterations stop changing
        state).  _compute_seed_firsts computes the fixed point for all single-symbol
        strings, by repeatedly calling _first and updating the internal _firsts
        table with the results.

        Once _compute_seed_firsts has completed, _first will return correct results
        for both single- and multi-symbol strings.

        _compute_seed_firsts is used during __init__.
        """
        self.firsts = {}
        # FIRST for a terminal symbol is always just that terminal symbol.
        for terminal in self.terminals:
            self.firsts[terminal] = set([terminal])
        for nonterminal in self.nonterminals:
            self.firsts[nonterminal] = set()
        while True:
            # The first iteration picks up all the productions that start with
            # terminal symbols.  The second iteration picks up productions that start
            # with nonterminals that the first iteration picked up.  The third
            # iteration picks up nonterminals that the first and second picked up, and
            # so on.
            #
            # This is guaranteed to end, in the worst case, when every terminal
            # symbol and epsilon has been added to the _firsts set for every
            # nonterminal symbol.  This would be slow, but requires a pathological
            # grammar; useful grammars should complete in only a few iterations.
            firsts_to_add = {}
            for production in self.productions:
                for first in self._first(production.rhs):
                    if first not in self.firsts[production.lhs]:
                        if production.lhs not in firsts_to_add:
                            firsts_to_add[production.lhs] = set()
                        firsts_to_add[production.lhs].add(first)
            if not firsts_to_add:
                break
            for symbol in firsts_to_add:
                self.firsts[symbol].update(firsts_to_add[symbol])

    def _first(self, symbols):
        """The FIRST function from ALSU p221.

        _first takes a string of symbols (both terminals and nonterminals) and
        returns the set of terminal symbols which could be the first terminal symbol
        of a string produced by the given list of symbols.

        _first will not give fully-correct results until _compute_seed_firsts
        finishes, but is called by _compute_seed_firsts, and must provide partial
        results during that method's execution.

        Args:
          symbols: A list of symbols.

        Returns:
          A set of terminals which could be the first terminal in "symbols."
        """
        result = set()
        all_contain_epsilon = True
        for symbol in symbols:
            for first in self.firsts[symbol]:
                if first:
                    result.add(first)
            if None not in self.firsts[symbol]:
                all_contain_epsilon = False
                break
        if all_contain_epsilon:
            # "None" seems like a Pythonic way of representing epsilon (no symbol).
            result.add(None)
        return result

    def _closure_of_item(self, root_item):
        """Modified implementation of CLOSURE from ALSU p261.

        _closure_of_item performs the CLOSURE function with a single seed item, with
        memoization.  In the algorithm as presented in ALSU, CLOSURE is called with
        a different set of items every time, which is unhelpful for memoization.
        Instead, we let _parallel_goto merge the sets returned by _closure_of_item,
        which results in a ~40% speedup.

        CLOSURE, roughly, computes the set of LR(1) Items which might be active when
        a "seed" set of Items is active.

        Technically, it is the epsilon-closure of the NFA states represented by
        "items," where an epsilon transition (a transition that does not consume any
        symbols) occurs from a->Z.bY,q to b->.X,p when p is in FIRST(Yq).  (a and b
        are nonterminals, X, Y, and Z are arbitrary strings of symbols, and p and q
        are terminals.)  That is, it is the set of all NFA states which can be
        reached from "items" without consuming any input.  This set corresponds to a
        single DFA state.

        Args:
          root_item: The initial LR(1) Item.

        Returns:
          A set of LR(1) items which may be active at the time when the provided
          item is active.
        """
        if root_item in self._closure_of_item_cache:
            return self._closure_of_item_cache[root_item]
        item_set = set([root_item])
        item_list = [root_item]
        i = 0
        # Each newly-added Item may trigger the addition of further Items, so
        # iterate until no new Items are added.  In the worst case, a new Item will
        # be added for each production.
        #
        # This algorithm is really looking for "next" nonterminals in the existing
        # items, and adding new items corresponding to their productions.
        while i < len(item_list):
            item = item_list[i]
            i += 1
            if not item.next_symbol:
                continue
            # If _closure_of_item_cache contains the full closure of item, then we can
            # add its full closure to the result set, and skip checking any of its
            # items: any item that would be added by any item in the cached result
            # will already be in the _closure_of_item_cache entry.
            if item in self._closure_of_item_cache:
                item_set |= self._closure_of_item_cache[item]
                continue
            # Even if we don't have the full closure of item, we may have the
            # immediate closure of item.  It turns out that memoizing just this step
            # speeds up this function by about 50%, even after the
            # _closure_of_item_cache check.
            if item not in self._single_level_closure_of_item_cache:
                new_items = set()
                for production in self._productions_by_lhs.get(item.next_symbol, []):
                    for terminal in self._first(
                        item.production.rhs[item.dot + 1 :] + (item.terminal,)
                    ):
                        new_items.add(self._item_cache[production, 0, terminal])
                self._single_level_closure_of_item_cache[item] = new_items
            for new_item in self._single_level_closure_of_item_cache[item]:
                if new_item not in item_set:
                    item_set.add(new_item)
                    item_list.append(new_item)
        self._closure_of_item_cache[root_item] = item_set
        # Typically, _closure_of_item() will be called on items whose closures
        # bring in the greatest number of additional items, then on items which
        # close over fewer and fewer other items.  Since items are not added to
        # _closure_of_item_cache unless _closure_of_item() is called directly on
        # them, this means that it is unlikely that items brought in will (without
        # intervention) have entries in _closure_of_item_cache, which slows down the
        # computation of the larger closures.
        #
        # Although it is not guaranteed, items added to item_list last will tend to
        # close over fewer items, and therefore be easier to compute.  By forcibly
        # re-calculating closures from last to first, and adding the results to
        # _closure_of_item_cache at each step, we get a modest performance
        # improvement: roughly 50% less time spent in _closure_of_item, which
        # translates to about 5% less time in parser().
        for item in item_list[::-1]:
            self._closure_of_item(item)
        return item_set

    def _parallel_goto(self, items):
        """The GOTO function from ALSU p261, executed on all symbols.

        _parallel_goto takes a set of Items, and returns a dict from every symbol in
        self.symbols to the set of Items that would be active after a shift
        operation (if symbol is a terminal) or after a reduction operation (if
        symbol is a nonterminal).

        _parallel_goto is used in lieu of the single-symbol GOTO from ALSU because
        it eliminates the outer loop over self.terminals, and thereby reduces the
        number of next_symbol calls by a factor of len(self.terminals).

        Args:
          items: The set of items representing the initial DFA state.

        Returns:
          A dict from symbols to sets of items representing the new DFA states.
        """
        results = collections.defaultdict(set)
        for item in items:
            next_symbol = item.next_symbol
            if next_symbol is None:
                continue
            item = self._item_cache[item.production, item.dot + 1, item.terminal]
            # Inlining the cache check results in a ~25% speedup in this function, and
            # about 10% overall speedup to parser().
            if item in self._closure_of_item_cache:
                closure = self._closure_of_item_cache[item]
            else:
                closure = self._closure_of_item(item)
            # _closure will add newly-started Items (Items with dot=0) to the result
            # set.  After this operation, the result set will correspond to the new
            # state.
            results[next_symbol].update(closure)
        return results

    def _items(self):
        """The items function from ALSU p261.

        _items computes the set of sets of LR(1) items for a shift-reduce parser
        that matches the grammar.  Each set of LR(1) items corresponds to a single
        DFA state.

        Returns:
          A tuple.

          The first element of the tuple is a list of sets of LR(1) items (each set
          corresponding to a DFA state).

          The second element of the tuple is a dictionary from (int, symbol) pairs
          to ints, where all the ints are indexes into the list of sets of LR(1)
          items.  This dictionary is based on the results of the _Goto function,
          where item_sets[dict[i, sym]] == self._Goto(item_sets[i], sym).
        """
        # The list of states is seeded with the marker S' production.
        item_list = [
            frozenset(
                self._closure_of_item(
                    self._item_cache[self._seed_production, 0, END_OF_INPUT]
                )
            )
        ]
        items = {item_list[0]: 0}
        goto_table = {}
        i = 0
        # For each state, figure out what the new state when each symbol is added to
        # the top of the parsing stack (see the comments in parser._parse).  See
        # _Goto for an explanation of how that is actually computed.
        while i < len(item_list):
            item_set = item_list[i]
            gotos = self._parallel_goto(item_set)
            for symbol, goto in gotos.items():
                goto = frozenset(goto)
                if goto not in items:
                    items[goto] = len(item_list)
                    item_list.append(goto)
                goto_table[i, symbol] = items[goto]
            i += 1
        return item_list, goto_table

    def parser(self):
        """parser returns an LR(1) parser for the Grammar.

        This implements the Canonical LR(1) ("LR(1)") parser algorithm ("Algorithm
        4.56", ALSU p265), rather than the more common Lookahead LR(1) ("LALR(1)")
        algorithm.  LALR(1) produces smaller tables, but is more complex and does
        not cover all LR(1) grammars.  When the LR(1) and LALR(1) algorithms were
        invented, table sizes were an important consideration; now, the difference
        between a few hundred and a few thousand entries is unlikely to matter.

        At this time, Grammar does not handle ambiguous grammars, which are commonly
        used to handle precedence, associativity, and the "dangling else" problem.
        Formally, these can always be handled by an unambiguous grammar, though
        doing so can be cumbersome, particularly for expression languages with many
        levels of precedence.  ALSU section 4.8 (pp278-287) contains some techniques
        for handling these kinds of ambiguity.

        Returns:
          A Parser.
        """
        item_sets, goto = self._items()
        action = {}
        conflicts = set()
        end_item = self._item_cache[self._seed_production, 1, END_OF_INPUT]
        for i in range(len(item_sets)):
            for item in item_sets[i]:
                new_action = None
                if (
                    item.next_symbol is None
                    and item.production != self._seed_production
                ):
                    terminal = item.terminal
                    new_action = Reduce(item.production)
                elif item.next_symbol in self.terminals:
                    terminal = item.next_symbol
                    assert goto[i, terminal] is not None
                    new_action = Shift(goto[i, terminal], item_sets[goto[i, terminal]])
                if new_action:
                    if (i, terminal) in action and action[i, terminal] != new_action:
                        conflicts.add(
                            Conflict(
                                i,
                                terminal,
                                frozenset([action[i, terminal], new_action]),
                            )
                        )
                    action[i, terminal] = new_action
                if item == end_item:
                    new_action = Accept()
                    assert (i, END_OF_INPUT) not in action or action[
                        i, END_OF_INPUT
                    ] == new_action
                    action[i, END_OF_INPUT] = new_action
        trimmed_goto = {}
        for k in goto:
            if k[1] in self.nonterminals:
                trimmed_goto[k] = goto[k]
        expected = {}
        for state, terminal in action:
            if state not in expected:
                expected[state] = set()
            expected[state].add(terminal)
        return Parser(
            item_sets,
            trimmed_goto,
            action,
            expected,
            conflicts,
            self.terminals,
            self.nonterminals,
            self.productions,
        )


ParseError = collections.namedtuple(
    "ParseError", ["code", "index", "token", "state", "expected_tokens"]
)
ParseResult = collections.namedtuple("ParseResult", ["parse_tree", "error"])


class Parser(object):
    """Parser is a shift-reduce LR(1) parser.

    Generally, clients will want to get a Parser from a Grammar, rather than
    directly instantiating one.

    Parser exposes the raw tables needed to feed into a Shift-Reduce parser,
    but can also be used directly for parsing.

    Attributes:
      item_sets: A list of item sets which correspond to the state numbers in
        the action and goto tables.  This is not necessary for parsing, but is
        useful for debugging parsers.
      goto: The GOTO table for this parser.
      action: The ACTION table for this parser.
      expected: A table of terminal symbols that are expected (that is, that
        have a non-Error action) for each state.  This can be used to provide
        more helpful error messages for parse errors.
      conflicts: A set of unresolved conflicts found during table generation.
      terminals: A set of terminal symbols in the grammar.
      nonterminals: A set of nonterminal symbols in the grammar.
      productions: A list of productions in the grammar.
      default_errors: A dict of states to default error codes to use when
        encountering an error in that state, when a more-specific Error for the
        state/terminal pair has not been set.
    """

    def __init__(
        self,
        item_sets,
        goto,
        action,
        expected,
        conflicts,
        terminals,
        nonterminals,
        productions,
    ):
        super(Parser, self).__init__()
        self.item_sets = item_sets
        self.goto = goto
        self.action = action
        self.expected = expected
        self.conflicts = conflicts
        self.terminals = terminals
        self.nonterminals = nonterminals
        self.productions = productions
        self.default_errors = {}

    def _parse(self, tokens):
        """_parse implements Shift-Reduce parsing algorithm.

        _parse implements the standard shift-reduce algorithm outlined on ASLU
        pp236-237.

        Arguments:
          tokens: the list of token objects to parse.

        Returns:
          A ParseResult.
        """
        # The END_OF_INPUT token is explicitly added to avoid explicit "cursor <
        # len(tokens)" checks.
        tokens = list(tokens) + [Symbol(END_OF_INPUT)]

        # Each element of stack is a parse state and a (possibly partial) parse
        # tree.  The state at the top of the stack encodes which productions are
        # "active" (that is, which ones the parser has seen partial input which
        # matches some prefix of the production, in a place where that production
        # might be valid), and, for each active production, how much of the
        # production has been completed.
        stack = [(0, None)]

        def state():
            return stack[-1][0]

        cursor = 0

        # On each iteration, look at the next symbol and the current state, and
        # perform the corresponding action.
        while True:
            if (state(), tokens[cursor].symbol) not in self.action:
                # Most state/symbol entries would be Errors, so rather than exhaustively
                # adding error entries, we just check here.
                if state() in self.default_errors:
                    next_action = Error(self.default_errors[state()])
                else:
                    next_action = Error(None)
            else:
                next_action = self.action[state(), tokens[cursor].symbol]

            if isinstance(next_action, Shift):
                # Shift means that there are no "complete" productions on the stack,
                # and so the current token should be shifted onto the stack, with a new
                # state indicating the new set of "active" productions.
                stack.append((next_action.state, tokens[cursor]))
                cursor += 1
            elif isinstance(next_action, Accept):
                # Accept means that parsing is over, successfully.
                assert len(stack) == 2, "Accepted incompletely-reduced input."
                assert tokens[cursor].symbol == END_OF_INPUT, (
                    "Accepted parse before " "end of input."
                )
                return ParseResult(stack[-1][1], None)
            elif isinstance(next_action, Reduce):
                # Reduce means that there is a complete production on the stack, and
                # that the next symbol implies that the completed production is the
                # correct production.
                #
                # Per ALSU, we would simply pop an element off the state stack for each
                # symbol on the rhs of the production, and then push a new state by
                # looking up the (post-pop) current state and the lhs of the production
                # in GOTO.  The GOTO table, in some sense, is equivalent to shift
                # actions for nonterminal symbols.
                #
                # Here, we attach a new partial parse tree, with the production lhs as
                # the "name" of the tree, and the popped trees as the "children" of the
                # new tree.
                children = [
                    item[1] for item in stack[len(stack) - len(next_action.rule.rhs) :]
                ]
                # Attach source_location, if known.  The source location will not be
                # known if the reduction consumes no symbols (empty rhs) or if the
                # client did not specify source_locations for tokens.
                #
                # It is necessary to loop in order to handle cases like:
                #
                # C -> c D
                # D ->
                #
                # The D child of the C reduction will not have a source location
                # (because it is not produced from any source), so it is necessary to
                # scan backwards through C's children to find the end position.  The
                # opposite is required in the case where initial children have no
                # source.
                #
                # These loops implicitly handle the case where the reduction has no
                # children, setting the source_location to None in that case.
                start_position = None
                end_position = None
                for child in children:
                    if (
                        hasattr(child, "source_location")
                        and child.source_location is not None
                    ):
                        start_position = child.source_location.start
                        break
                for child in reversed(children):
                    if (
                        hasattr(child, "source_location")
                        and child.source_location is not None
                    ):
                        end_position = child.source_location.end
                        break
                if start_position is None:
                    source_location = None
                else:
                    source_location = parser_types.make_location(
                        start_position, end_position
                    )
                reduction = Reduction(
                    next_action.rule.lhs, children, next_action.rule, source_location
                )
                del stack[len(stack) - len(next_action.rule.rhs) :]
                stack.append((self.goto[state(), next_action.rule.lhs], reduction))
            elif isinstance(next_action, Error):
                # Error means that the parse is impossible.  For typical grammars and
                # texts, this usually happens within a few tokens after the mistake in
                # the input stream, which is convenient (though imperfect) for error
                # reporting.
                return ParseResult(
                    None,
                    ParseError(
                        next_action.code,
                        cursor,
                        tokens[cursor],
                        state(),
                        self.expected[state()],
                    ),
                )
            else:
                assert False, "Shouldn't be here."

    def mark_error(self, tokens, error_token, error_code):
        """Marks an error state with the given error code.

        mark_error implements the equivalent of the "Merr" system presented in
        "Generating LR Syntax error Messages from Examples" (Jeffery, 2003).
        This system has limitations, but has the primary advantage that error
        messages can be specified by giving an example of the error and the
        message itself.

        Arguments:
          tokens: a list of tokens to parse.
          error_token: the token where the parse should fail, or None if the parse
            should fail at the implicit end-of-input token.

            If the error_token is the special ANY_TOKEN, then the error will be
            recorded as the default error for the error state.
          error_code: a value to record for the error state reached by parsing
            tokens.

        Returns:
          None if error_code was successfully recorded, or an error message if there
          was a problem.
        """
        result = self._parse(tokens)

        # There is no error state to mark on a successful parse.
        if not result.error:
            return "Input successfully parsed."

        # Check if the error occurred at the specified token; if not, then this was
        # not the expected error.
        if error_token is None:
            error_symbol = END_OF_INPUT
            if result.error.token.symbol != END_OF_INPUT:
                return "error occurred on {} token, not end of input.".format(
                    result.error.token.symbol
                )
        else:
            error_symbol = error_token.symbol
            if result.error.token != error_token:
                return "error occurred on {} token, not {} token.".format(
                    result.error.token.symbol, error_token.symbol
                )

        # If the expected error was found, attempt to mark it.  It is acceptable if
        # the given error_code is already set as the error code for the given parse,
        # but not if a different code is set.
        if result.error.token == ANY_TOKEN:
            # For ANY_TOKEN, mark it as a default error.
            if result.error.state in self.default_errors:
                if self.default_errors[result.error.state] == error_code:
                    return None
                else:
                    return (
                        "Attempted to overwrite existing default error code {!r} "
                        "with new error code {!r} for state {}".format(
                            self.default_errors[result.error.state],
                            error_code,
                            result.error.state,
                        )
                    )
            else:
                self.default_errors[result.error.state] = error_code
                return None
        else:
            if (result.error.state, error_symbol) in self.action:
                existing_error = self.action[result.error.state, error_symbol]
                assert isinstance(existing_error, Error), "Bug"
                if existing_error.code == error_code:
                    return None
                else:
                    return (
                        "Attempted to overwrite existing error code {!r} with new "
                        "error code {!r} for state {}, terminal {}".format(
                            existing_error.code,
                            error_code,
                            result.error.state,
                            error_symbol,
                        )
                    )
            else:
                self.action[result.error.state, error_symbol] = Error(error_code)
                return None
        assert False, "All other paths should lead to return."

    def parse(self, tokens):
        """Parses a list of tokens.

        Arguments:
          tokens: a list of tokens to parse.

        Returns:
          A ParseResult.
        """
        result = self._parse(tokens)
        return result
