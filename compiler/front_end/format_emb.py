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

"""Formatter for Emboss source files.

This module exports a single function, format_emboss_parse_tree(), which
pretty-prints an Emboss parse tree.
"""

from __future__ import print_function

import collections
import itertools

from compiler.front_end import module_ir
from compiler.front_end import tokenizer
from compiler.util import parser_types


class Config(collections.namedtuple("Config", ["indent_width", "show_line_types"])):
    """Configuration for formatting."""

    def __new__(cls, indent_width=2, show_line_types=False):
        return super(cls, Config).__new__(cls, indent_width, show_line_types)


class _Row(collections.namedtuple("Row", ["name", "columns", "indent"])):
    """Structured contents of a single line."""

    def __new__(cls, name, columns=None, indent=0):
        return super(cls, _Row).__new__(cls, name, tuple(columns or []), indent)


class _Block(collections.namedtuple("Block", ["prefix", "header", "body"])):
    """Structured block of multiple lines."""

    def __new__(cls, prefix, header, body):
        assert header
        return super(cls, _Block).__new__(cls, prefix, header, body)


# Map of productions to their formatters.
_formatters = {}


def format_emboss_parse_tree(parse_tree, config, used_productions=None):
    """Formats Emboss source code.

    Arguments:
        parse_tree: A parse tree of an Emboss source file.
        config: A Config tuple with formatting options.
        used_productions: An optional set to which all used productions will be
            added.  Intended for use by test code to ensure full production
            coverage.

    Returns:
        A string of the reformatted source text.
    """
    if hasattr(parse_tree, "children"):
        parsed_children = [
            format_emboss_parse_tree(child, config, used_productions)
            for child in parse_tree.children
        ]
        args = parsed_children + [config]
        if used_productions is not None:
            used_productions.add(parse_tree.production)
        return _formatters[parse_tree.production](*args)
    else:
        assert isinstance(parse_tree, parser_types.Token), str(parse_tree)
        return parse_tree.text


def sanity_check_format_result(formatted_text, original_text):
    """Checks that the given texts are equivalent."""
    # The texts are considered equivalent if they tokenize to the same token
    # stream, except that:
    #
    # Multiple consecutive newline tokens are equivalent to a single newline
    # token.
    #
    # Extra newline tokens at the start of the stream should be ignored.
    #
    # Whitespace at the start or end of a token should be ignored.  This matters
    # for documentation and comment tokens, which may have had trailing whitespace
    # in the original text, and for indent tokens, which may contain a different
    # number of space and/or tab characters.
    original_tokens, errors = tokenizer.tokenize(original_text, "")
    if errors:
        return ["BUG: original text is not tokenizable: {!r}".format(errors)]

    formatted_tokens, errors = tokenizer.tokenize(formatted_text, "")
    if errors:
        return ["BUG: formatted text is not tokenizable: {!r}".format(errors)]

    o_tokens = _collapse_newline_tokens(original_tokens)
    f_tokens = _collapse_newline_tokens(formatted_tokens)
    for i in range(len(o_tokens)):
        if (
            o_tokens[i].symbol != f_tokens[i].symbol
            or o_tokens[i].text.strip() != f_tokens[i].text.strip()
        ):
            return [
                "BUG: Symbol {} differs: {!r} vs {!r}".format(
                    i, o_tokens[i], f_tokens[i]
                )
            ]
    return []


def _collapse_newline_tokens(token_list):
    r"""Collapses multiple consecutive "\\n" tokens into a single newline."""
    result = []
    for symbol, group in itertools.groupby(token_list, lambda x: x.symbol):
        if symbol == '"\\n"':
            # Skip all newlines if they are at the start, otherwise add a single
            # newline for each consecutive run of newlines.
            if result:
                result.append(list(group)[0])
        else:
            result.extend(group)
    return result


def _indent_row(row):
    """Adds one level of indent to the given row, returning a new row."""
    assert isinstance(row, _Row), repr(row)
    return _Row(name=row.name, columns=row.columns, indent=row.indent + 1)


def _indent_rows(rows):
    """Adds one level of indent to the given rows, returning a new list."""
    return list(map(_indent_row, rows))


def _indent_blocks(blocks):
    """Adds one level of indent to the given blocks, returning a new list."""
    return [
        _Block(
            prefix=_indent_rows(block.prefix),
            header=_indent_row(block.header),
            body=_indent_rows(block.body),
        )
        for block in blocks
    ]


def _intersperse(interspersed, sections):
    """Intersperses `interspersed` between non-empty `sections`."""
    result = []
    for section in sections:
        if section:
            if result:
                result.extend(interspersed)
            result.extend(section)
    return result


def _should_add_blank_lines(blocks):
    """Returns true if blank lines should be added between blocks."""
    other_non_empty_lines = 0
    last_non_empty_lines = 0
    for block in blocks:
        last_non_empty_lines = len(
            [line for line in block.body + block.prefix if line.columns]
        )
        other_non_empty_lines += last_non_empty_lines
    # Vertical spaces should be added if there are more interior
    # non-empty-non-header lines than header lines.
    return len(blocks) <= other_non_empty_lines - last_non_empty_lines


def _columnize(blocks, indent_width, indent_columns=1):
    """Aligns columns in the header rows of the given blocks.

    The `indent_columns` argument is used to determine how many columns should be
    indented.  With `indent_columns == 1`, the result would be:

    AA     BB  CC
      AAA  BBB  CCC
    A      B    C

    With `indent_columns == 2`:

    AA   BB     CC
      AAA  BBB  CCC
    A    B      C

    With `indent_columns == 1`, only the first column is indented compared to
    surrounding rows; with `indent_columns == 2`, both the first and second
    columns are indented.

    Arguments:
        blocks: A list of _Blocks to columnize.
        indent_width: The number of spaces per level of indent.
        indent_columns: The number of columns to indent.

    Returns:
        A list of _Rows of the prefix, header, and body _Rows of each block, where
        the header _Rows of each type have had their columns aligned.
    """
    single_width_separators = {"enum-value": {0, 1}, "field": {0}}
    # For each type of row, figure out how many characters each column needs.
    row_types = collections.defaultdict(lambda: collections.defaultdict(lambda: 0))
    for block in blocks:
        max_lengths = row_types[block.header.name]
        for i in range(len(block.header.columns)):
            if i == indent_columns - 1:
                adjustment = block.header.indent * indent_width
            else:
                adjustment = 0
            max_lengths[i] = max(
                max_lengths[i], len(block.header.columns[i]) + adjustment
            )

    assert len(row_types) < 3

    # Then, for each row, actually columnize it.
    result = []
    for block in blocks:
        columns = []
        for i in range(len(block.header.columns)):
            column_width = row_types[block.header.name][i]
            if column_width == 0:
                # Zero-width columns are entirely omitted, including their column
                # separators.
                pass
            else:
                if i == indent_columns - 1:
                    # This function only performs the right padding for each column.
                    # Since the left padding for indent will be added later, the
                    # corresponding space needs to be removed from the right padding of
                    # the first column.
                    column_width -= block.header.indent * indent_width
                if i in single_width_separators.get(block.header.name, []):
                    # Only one space around the "=" in enum values and between the start
                    # and size in field locations.
                    column_width += 1
                else:
                    column_width += 2
            columns.append(block.header.columns[i].ljust(column_width))
        result.append(
            block.prefix
            + [
                _Row(
                    block.header.name, ["".join(columns).rstrip()], block.header.indent
                )
            ]
            + block.body
        )
    return result


def _indent_blanks_and_comments(rows):
    """Indents blank and comment lines to match the next non-blank line."""
    result = []
    previous_indent = 0
    for row in reversed(rows):
        if not "".join(row.columns) or row.name == "comment":
            result.append(_Row(row.name, row.columns, previous_indent))
        else:
            result.append(row)
            previous_indent = row.indent
    return reversed(result)


def _add_blank_rows_on_dedent(rows):
    """Adds blank rows before dedented lines, where needed."""
    result = []
    previous_indent = 0
    previous_row_was_blank = True
    for row in rows:
        row_is_blank = not "".join(row.columns)
        found_dedent = previous_indent > row.indent
        if found_dedent and not previous_row_was_blank and not row_is_blank:
            result.append(_Row("dedent-space", [], row.indent))
        result.append(row)
        previous_indent = row.indent
        previous_row_was_blank = row_is_blank
    return result


def _render_row_to_text(row, indent_width):
    assert len(row.columns) < 2, "{!r}".format(row)
    text = " " * indent_width * row.indent
    text += "".join(row.columns)
    return text.rstrip()


def _render_rows_to_text(rows, indent_width, show_line_types):
    max_row_name_len = max([0] + [len(row.name) for row in rows])
    flattened_rows = []
    for row in rows:
        row_text = _render_row_to_text(row, indent_width)
        if show_line_types:
            row_text = row.name.ljust(max_row_name_len) + "|" + row_text
        flattened_rows.append(row_text)
    return "\n".join(flattened_rows + [""])


def _check_productions():
    """Asserts that the productions in this module match those in module_ir."""
    productions_ok = True
    for production in module_ir.PRODUCTIONS:
        if production not in _formatters:
            productions_ok = False
            print("@_formats({!r})".format(str(production)))

    for production in _formatters:
        if production not in module_ir.PRODUCTIONS:
            productions_ok = False
            print("not @_formats({!r})".format(str(production)))

    assert productions_ok, "Grammar mismatch."


def _formats_with_config(production_text):
    """Marks a function as a formatter requiring a config argument."""
    production = parser_types.Production.parse(production_text)

    def formats(f):
        assert production not in _formatters, production
        _formatters[production] = f
        return f

    return formats


def _formats(production_text):
    """Marks a function as the formatter for a particular production."""

    def strip_config_argument(f):
        _formats_with_config(production_text)(lambda *a, **kw: f(*a[:-1], **kw))
        return f

    return strip_config_argument


################################################################################
# From here to the end of the file are functions which recursively format an
# Emboss parse tree.
#
# The format_parse_tree() function will call formatters, bottom-up, for the
# entire parse tree.  Each formatter will be called with the results of the
# formatters for each child node.  (The "formatter" for leaf nodes is the
# original text of the token.)
#
# Formatters can be roughly divided into three types:
#
# The _module formatter is the top-level formatter.  It handles final rendering
# into text, and returns a string.
#
# Formatters for productions that are at least one full line return lists of
# _Rows.  The production 'attribute-line' falls into this category, but
# 'attribute' does not.  This form allows parallel constructs in separate lines
# to be lined up column-wise, even when there are intervening lines that should
# not be lined up -- for example, the types and names of struct fields will be
# aligned, even if there are documentation, comment, or attribute lines mixed
# in.
#
# Formatters for productions that are smaller than one full line just return
# strings.


@_formats_with_config(
    "module -> comment-line* doc-line* import-line*"
    "          attribute-line* type-definition*"
)
def _module(comments, docs, imports, attributes, types, config):
    """Performs top-level formatting for an Emboss source file."""

    # The top-level sections other than types should be separated by single lines.
    header_rows = _intersperse(
        [_Row("section-break")],
        [
            _strip_empty_leading_trailing_comment_lines(comments),
            docs,
            imports,
            attributes,
        ],
    )

    # Top-level types should be separated by double lines from themselves and from
    # the header rows.
    rows = _intersperse(
        [_Row("top-type-separator"), _Row("top-type-separator")], [header_rows] + types
    )

    # Final fixups.
    rows = _indent_blanks_and_comments(rows)
    rows = _add_blank_rows_on_dedent(rows)
    return _render_rows_to_text(rows, config.indent_width, config.show_line_types)


@_formats("doc-line -> doc Comment? eol")
def _doc_line(doc, comment, eol):
    assert not comment, "Comment should not be possible on the same line as doc."
    return [_Row("doc", [doc])] + eol


@_formats(
    'import-line -> "import" string-constant "as" snake-word Comment?'
    "               eol"
)
def _import_line(import_, filename, as_, name, comment, eol):
    return [
        _Row(
            "import", ["{} {} {} {}  {}".format(import_, filename, as_, name, comment)]
        )
    ] + eol


@_formats("attribute-line -> attribute Comment? eol")
def _attribute_line(attribute, comment, eol):
    return [_Row("attribute", ["{}  {}".format(attribute, comment)])] + eol


@_formats(
    'attribute -> "[" attribute-context? "$default"? snake-word ":"'
    '             attribute-value "]"'
)
def _attribute(open_, context, default, name, colon, value, close):
    return "".join(
        [open_, _concatenate_with_spaces(context, default, name + colon, value), close]
    )


@_formats('parameter-definition -> snake-name ":" type')
def _parameter_definition(name, colon, type_specifier):
    return "{}{} {}".format(name, colon, type_specifier)


@_formats("type-definition* -> type-definition type-definition*")
def _type_defitinions(definition, definitions):
    return [definition] + definitions


@_formats(
    'bits -> "bits" type-name delimited-parameter-definition-list? ":"'
    "        Comment? eol bits-body"
)
@_formats(
    'struct -> "struct" type-name delimited-parameter-definition-list?'
    '          ":" Comment? eol struct-body'
)
def _structure_type(struct, name, parameters, colon, comment, eol, body):
    return (
        [
            _Row(
                "type-header",
                ["{} {}{}{}  {}".format(struct, name, parameters, colon, comment)],
            )
        ]
        + eol
        + body
    )


@_formats('enum -> "enum" type-name ":" Comment? eol enum-body')
@_formats('external -> "external" type-name ":" Comment? eol external-body')
def _type(struct, name, colon, comment, eol, body):
    return (
        [_Row("type-header", ["{} {}{}  {}".format(struct, name, colon, comment)])]
        + eol
        + body
    )


@_formats_with_config(
    "bits-body -> Indent doc-line* attribute-line*"
    "             type-definition* bits-field-block Dedent"
)
@_formats_with_config(
    "struct-body -> Indent doc-line* attribute-line*"
    "               type-definition* struct-field-block Dedent"
)
def _structure_body(indent, docs, attributes, type_definitions, fields, dedent, config):
    """Formats a structure (`bits` or `struct`) body."""
    del indent, dedent  # Unused.
    spacing = [_Row("field-separator")] if _should_add_blank_lines(fields) else []
    columnized_fields = _columnize(fields, config.indent_width, indent_columns=2)
    return _indent_rows(
        _intersperse(spacing, [docs, attributes] + type_definitions + columnized_fields)
    )


@_formats('field-location -> expression "[" "+" expression "]"')
def _field_location(start, open_bracket, plus, size, close_bracket):
    return [start, open_bracket + plus + size + close_bracket]


@_formats(
    "anonymous-bits-field-block -> conditional-anonymous-bits-field-block"
    "                              anonymous-bits-field-block"
)
@_formats(
    "anonymous-bits-field-block -> unconditional-anonymous-bits-field"
    "                              anonymous-bits-field-block"
)
@_formats("bits-field-block -> conditional-bits-field-block bits-field-block")
@_formats("bits-field-block -> unconditional-bits-field bits-field-block")
@_formats(
    "struct-field-block -> conditional-struct-field-block"
    "                      struct-field-block"
)
@_formats("struct-field-block -> unconditional-struct-field struct-field-block")
@_formats(
    "unconditional-anonymous-bits-field* ->"
    "    unconditional-anonymous-bits-field"
    "    unconditional-anonymous-bits-field*"
)
@_formats(
    "unconditional-anonymous-bits-field+ ->"
    "    unconditional-anonymous-bits-field"
    "    unconditional-anonymous-bits-field*"
)
@_formats(
    "unconditional-bits-field* -> unconditional-bits-field"
    "                             unconditional-bits-field*"
)
@_formats(
    "unconditional-bits-field+ -> unconditional-bits-field"
    "                             unconditional-bits-field*"
)
@_formats(
    "unconditional-struct-field* -> unconditional-struct-field"
    "                               unconditional-struct-field*"
)
@_formats(
    "unconditional-struct-field+ -> unconditional-struct-field"
    "                               unconditional-struct-field*"
)
def _structure_block(field, block):
    """Prepends field to block."""
    return field + block


@_formats(
    'virtual-field -> "let" snake-name "=" expression Comment? eol'
    "                 field-body?"
)
def _virtual_field(let_keyword, name, equals, value, comment, eol, body):
    # This formatting doesn't look the best when there are blocks of several
    # virtual fields next to each other, but works pretty well when they're
    # intermixed with physical fields.  It's probably good enough for now, since
    # there aren't (yet) any virtual fields in real .embs, and will probably only
    # be a few in the near future.
    return [
        _Block(
            [],
            _Row(
                "virtual-field",
                [
                    _concatenate_with(
                        "  ",
                        _concatenate_with_spaces(let_keyword, name, equals, value),
                        comment,
                    )
                ],
            ),
            eol + body,
        )
    ]


@_formats(
    "field -> field-location type snake-name abbreviation?"
    "         attribute* doc? Comment? eol field-body?"
)
def _unconditional_field(
    location, type_, name, abbreviation, attributes, doc, comment, eol, body
):
    return [
        _Block(
            [],
            _Row(
                "field",
                location
                + [
                    type_,
                    _concatenate_with_spaces(name, abbreviation),
                    attributes,
                    doc,
                    comment,
                ],
            ),
            eol + body,
        )
    ]


@_formats("field-body -> Indent doc-line* attribute-line* Dedent")
def _field_body(indent, docs, attributes, dedent):
    del indent, dedent  # Unused
    return _indent_rows(docs + attributes)


@_formats(
    "anonymous-bits-field-definition ->"
    '    field-location "bits" ":" Comment? eol anonymous-bits-body'
)
def _inline_bits(location, bits, colon, comment, eol, body):
    """Formats an inline `bits` definition."""
    # Even though an anonymous bits field technically defines a new, anonymous
    # type, conceptually it's more like defining a bunch of fields on the
    # surrounding type, so it is treated as an inline list of blocks, instead of
    # being separately formatted.
    header_row = _Row(
        "field",
        [location[0], location[1] + "  " + bits + colon, "", "", "", "", comment],
    )
    return [_Block([], header_row, eol + body.header_lines)] + body.field_blocks


@_formats(
    "inline-enum-field-definition ->"
    '    field-location "enum" snake-name abbreviation? ":" Comment? eol'
    "    enum-body"
)
@_formats(
    "inline-struct-field-definition ->"
    '    field-location "struct" snake-name abbreviation? ":" Comment? eol'
    "    struct-body"
)
@_formats(
    "inline-bits-field-definition ->"
    '    field-location "bits" snake-name abbreviation? ":" Comment? eol'
    "    bits-body"
)
def _inline_type(location, keyword, name, abbreviation, colon, comment, eol, body):
    """Formats an inline type in a struct or bits."""
    header_row = _Row(
        "field",
        location
        + [
            keyword,
            _concatenate_with_spaces(name, abbreviation) + colon,
            "",
            "",
            comment,
        ],
    )
    return [_Block([], header_row, eol + body)]


@_formats(
    'conditional-struct-field-block -> "if" expression ":" Comment? eol'
    "                                  Indent unconditional-struct-field+"
    "                                  Dedent"
)
@_formats(
    'conditional-bits-field-block -> "if" expression ":" Comment? eol'
    "                                Indent unconditional-bits-field+"
    "                                Dedent"
)
@_formats(
    "conditional-anonymous-bits-field-block ->"
    '    "if" expression ":" Comment? eol'
    "    Indent unconditional-anonymous-bits-field+ Dedent"
)
def _conditional_field(if_, condition, colon, comment, eol, indent, body, dedent):
    """Formats an `if` construct."""
    del indent, dedent  # Unused
    # The body of an 'if' should be columnized with the surrounding blocks, so
    # much like an inline 'bits', its body is treated as an inline list of blocks.
    header_row = _Row("if", ["{} {}{}  {}".format(if_, condition, colon, comment)])
    indented_body = _indent_blocks(body)
    assert indented_body, "Expected body of if condition."
    return [
        _Block(
            [header_row] + eol + indented_body[0].prefix,
            indented_body[0].header,
            indented_body[0].body,
        )
    ] + indented_body[1:]


_InlineBitsBodyType = collections.namedtuple(
    "InlineBitsBodyType", ["header_lines", "field_blocks"]
)


@_formats(
    "anonymous-bits-body ->"
    "    Indent attribute-line* anonymous-bits-field-block Dedent"
)
def _inline_bits_body(indent, attributes, fields, dedent):
    del indent, dedent  # Unused
    return _InlineBitsBodyType(
        header_lines=_indent_rows(attributes), field_blocks=_indent_blocks(fields)
    )


@_formats_with_config(
    "enum-body -> Indent doc-line* attribute-line* enum-value+" "             Dedent"
)
def _enum_body(indent, docs, attributes, values, dedent, config):
    del indent, dedent  # Unused
    spacing = [_Row("value-separator")] if _should_add_blank_lines(values) else []
    columnized_values = _columnize(values, config.indent_width)
    return _indent_rows(_intersperse(spacing, [docs, attributes] + columnized_values))


@_formats("enum-value* -> enum-value enum-value*")
@_formats("enum-value+ -> enum-value enum-value*")
def _enum_values(value, block):
    return value + block


@_formats(
    'enum-value -> constant-name "=" expression attribute* doc? Comment? eol'
    "              enum-value-body?"
)
def _enum_value(name, equals, value, attributes, docs, comment, eol, body):
    return [
        _Block(
            [],
            _Row("enum-value", [name, equals, value, attributes, docs, comment]),
            eol + body,
        )
    ]


@_formats("enum-value-body -> Indent doc-line* attribute-line* Dedent")
def _enum_value_body(indent, docs, attributes, dedent):
    del indent, dedent  # Unused
    return _indent_rows(docs + attributes)


@_formats("external-body -> Indent doc-line* attribute-line* Dedent")
def _external_body(indent, docs, attributes, dedent):
    del indent, dedent  # Unused
    return _indent_rows(_intersperse([_Row("section-break")], [docs, attributes]))


@_formats('comment-line -> Comment? "\\n"')
def _comment_line(comment, eol):
    del eol  # Unused
    if comment:
        return [_Row("comment", [comment])]
    else:
        return [_Row("comment")]


@_formats('eol -> "\\n" comment-line*')
def _eol(eol, comments):
    del eol  # Unused
    return _strip_empty_leading_trailing_comment_lines(comments)


def _strip_empty_leading_trailing_comment_lines(comments):
    first_non_empty_line = None
    last_non_empty_line = None
    for i in range(len(comments)):
        if comments[i].columns:
            if first_non_empty_line is None:
                first_non_empty_line = i
            last_non_empty_line = i
    if first_non_empty_line is None:
        return []
    else:
        return comments[first_non_empty_line : last_non_empty_line + 1]


@_formats("attribute-line* -> ")
@_formats("anonymous-bits-field-block -> ")
@_formats("bits-field-block -> ")
@_formats("comment-line* -> ")
@_formats("doc-line* -> ")
@_formats("enum-value* -> ")
@_formats("enum-value-body? -> ")
@_formats("field-body? -> ")
@_formats("import-line* -> ")
@_formats("struct-field-block -> ")
@_formats("type-definition* -> ")
@_formats("unconditional-anonymous-bits-field* -> ")
@_formats("unconditional-bits-field* -> ")
@_formats("unconditional-struct-field* -> ")
def _empty_list():
    return []


@_formats("abbreviation? -> ")
@_formats("additive-expression-right* -> ")
@_formats("and-expression-right* -> ")
@_formats("argument-list -> ")
@_formats("array-length-specifier* -> ")
@_formats("attribute* -> ")
@_formats("attribute-context? -> ")
@_formats("comma-then-expression* -> ")
@_formats("Comment? -> ")
@_formats('"$default"? -> ')
@_formats("delimited-argument-list? -> ")
@_formats("delimited-parameter-definition-list? -> ")
@_formats("doc? -> ")
@_formats("equality-expression-right* -> ")
@_formats("equality-or-greater-expression-right* -> ")
@_formats("equality-or-less-expression-right* -> ")
@_formats("field-reference-tail* -> ")
@_formats("or-expression-right* -> ")
@_formats("parameter-definition-list -> ")
@_formats("parameter-definition-list-tail* -> ")
@_formats("times-expression-right* -> ")
@_formats("type-size-specifier? -> ")
def _empty_string():
    return ""


@_formats("abbreviation? -> abbreviation")
@_formats('additive-operator -> "-"')
@_formats('additive-operator -> "+"')
@_formats('and-operator -> "&&"')
@_formats("attribute-context? -> attribute-context")
@_formats("attribute-value -> expression")
@_formats("attribute-value -> string-constant")
@_formats("boolean-constant -> BooleanConstant")
@_formats("bottom-expression -> boolean-constant")
@_formats("bottom-expression -> builtin-reference")
@_formats("bottom-expression -> constant-reference")
@_formats("bottom-expression -> field-reference")
@_formats("bottom-expression -> numeric-constant")
@_formats('builtin-field-word -> "$max_size_in_bits"')
@_formats('builtin-field-word -> "$max_size_in_bytes"')
@_formats('builtin-field-word -> "$min_size_in_bits"')
@_formats('builtin-field-word -> "$min_size_in_bytes"')
@_formats('builtin-field-word -> "$size_in_bits"')
@_formats('builtin-field-word -> "$size_in_bytes"')
@_formats("builtin-reference -> builtin-word")
@_formats('builtin-word -> "$is_statically_sized"')
@_formats('builtin-word -> "$next"')
@_formats('builtin-word -> "$static_size_in_bits"')
@_formats("choice-expression -> logical-expression")
@_formats("Comment? -> Comment")
@_formats("comparison-expression -> additive-expression")
@_formats("constant-name -> constant-word")
@_formats("constant-reference -> constant-reference-tail")
@_formats("constant-reference-tail -> constant-word")
@_formats("constant-word -> ShoutyWord")
@_formats('"$default"? -> "$default"')
@_formats("delimited-argument-list? -> delimited-argument-list")
@_formats("doc? -> doc")
@_formats("doc -> Documentation")
@_formats("enum-value-body? -> enum-value-body")
@_formats('equality-operator -> "=="')
@_formats("equality-or-greater-expression-right -> equality-expression-right")
@_formats("equality-or-greater-expression-right -> greater-expression-right")
@_formats("equality-or-less-expression-right -> equality-expression-right")
@_formats("equality-or-less-expression-right -> less-expression-right")
@_formats("expression -> choice-expression")
@_formats("field-body? -> field-body")
@_formats('function-name -> "$lower_bound"')
@_formats('function-name -> "$present"')
@_formats('function-name -> "$max"')
@_formats('function-name -> "$upper_bound"')
@_formats('greater-operator -> ">="')
@_formats('greater-operator -> ">"')
@_formats('inequality-operator -> "!="')
@_formats('less-operator -> "<="')
@_formats('less-operator -> "<"')
@_formats("logical-expression -> and-expression")
@_formats("logical-expression -> comparison-expression")
@_formats("logical-expression -> or-expression")
@_formats('multiplicative-operator -> "*"')
@_formats("negation-expression -> bottom-expression")
@_formats("numeric-constant -> Number")
@_formats('or-operator -> "||"')
@_formats("snake-name -> snake-word")
@_formats("snake-reference -> builtin-field-word")
@_formats("snake-reference -> snake-word")
@_formats("snake-word -> SnakeWord")
@_formats("string-constant -> String")
@_formats("type-definition -> bits")
@_formats("type-definition -> enum")
@_formats("type-definition -> external")
@_formats("type-definition -> struct")
@_formats("type-name -> type-word")
@_formats("type-reference-tail -> type-word")
@_formats("type-reference -> type-reference-tail")
@_formats("type-size-specifier? -> type-size-specifier")
@_formats("type-word -> CamelWord")
@_formats("unconditional-anonymous-bits-field -> field")
@_formats("unconditional-anonymous-bits-field -> inline-bits-field-definition")
@_formats("unconditional-anonymous-bits-field -> inline-enum-field-definition")
@_formats("unconditional-bits-field -> unconditional-anonymous-bits-field")
@_formats("unconditional-bits-field -> virtual-field")
@_formats("unconditional-struct-field -> anonymous-bits-field-definition")
@_formats("unconditional-struct-field -> field")
@_formats("unconditional-struct-field -> inline-bits-field-definition")
@_formats("unconditional-struct-field -> inline-enum-field-definition")
@_formats("unconditional-struct-field -> inline-struct-field-definition")
@_formats("unconditional-struct-field -> virtual-field")
def _identity(x):
    return x


@_formats("argument-list -> expression comma-then-expression*")
@_formats("times-expression -> negation-expression times-expression-right*")
@_formats(
    "type -> type-reference delimited-argument-list? type-size-specifier?"
    "        array-length-specifier*"
)
@_formats('array-length-specifier -> "[" expression "]"')
@_formats(
    "array-length-specifier* -> array-length-specifier"
    "                           array-length-specifier*"
)
@_formats('type-size-specifier -> ":" numeric-constant')
@_formats('attribute-context -> "(" snake-word ")"')
@_formats('constant-reference -> snake-reference "." constant-reference-tail')
@_formats('constant-reference-tail -> type-word "." constant-reference-tail')
@_formats('constant-reference-tail -> type-word "." snake-reference')
@_formats('type-reference-tail -> type-word "." type-reference-tail')
@_formats("field-reference -> snake-reference field-reference-tail*")
@_formats('abbreviation -> "(" snake-word ")"')
@_formats("additive-expression-right -> additive-operator times-expression")
@_formats(
    "additive-expression-right* -> additive-expression-right"
    "                              additive-expression-right*"
)
@_formats("additive-expression -> times-expression additive-expression-right*")
@_formats('array-length-specifier -> "[" "]"')
@_formats('delimited-argument-list -> "(" argument-list ")"')
@_formats(
    "delimited-parameter-definition-list? ->" "    delimited-parameter-definition-list"
)
@_formats(
    "delimited-parameter-definition-list ->" '    "(" parameter-definition-list ")"'
)
@_formats(
    "parameter-definition-list -> parameter-definition"
    "                             parameter-definition-list-tail*"
)
@_formats(
    "parameter-definition-list-tail* -> parameter-definition-list-tail"
    "                                   parameter-definition-list-tail*"
)
@_formats(
    "times-expression-right -> multiplicative-operator"
    "                          negation-expression"
)
@_formats(
    "times-expression-right* -> times-expression-right"
    "                           times-expression-right*"
)
@_formats('field-reference-tail -> "." snake-reference')
@_formats("field-reference-tail* -> field-reference-tail field-reference-tail*")
@_formats("negation-expression -> additive-operator bottom-expression")
@_formats('type-reference -> snake-word "." type-reference-tail')
@_formats('bottom-expression -> "(" expression ")"')
@_formats('bottom-expression -> function-name "(" argument-list ")"')
@_formats(
    "comma-then-expression* -> comma-then-expression"
    "                          comma-then-expression*"
)
@_formats("or-expression-right* -> or-expression-right or-expression-right*")
@_formats(
    "less-expression-right-list -> equality-expression-right*"
    "                              less-expression-right"
    "                              equality-or-less-expression-right*"
)
@_formats("or-expression-right+ -> or-expression-right or-expression-right*")
@_formats("and-expression -> comparison-expression and-expression-right+")
@_formats(
    "comparison-expression -> additive-expression"
    "                         greater-expression-right-list"
)
@_formats(
    "comparison-expression -> additive-expression"
    "                         equality-expression-right+"
)
@_formats("or-expression -> comparison-expression or-expression-right+")
@_formats(
    "equality-expression-right+ -> equality-expression-right"
    "                              equality-expression-right*"
)
@_formats("and-expression-right* -> and-expression-right and-expression-right*")
@_formats(
    "equality-or-greater-expression-right* ->"
    "    equality-or-greater-expression-right"
    "    equality-or-greater-expression-right*"
)
@_formats("and-expression-right+ -> and-expression-right and-expression-right*")
@_formats(
    "equality-or-less-expression-right* ->"
    "    equality-or-less-expression-right"
    "    equality-or-less-expression-right*"
)
@_formats(
    "equality-expression-right* -> equality-expression-right"
    "                              equality-expression-right*"
)
@_formats(
    "greater-expression-right-list ->"
    "    equality-expression-right* greater-expression-right"
    "    equality-or-greater-expression-right*"
)
@_formats(
    "comparison-expression -> additive-expression"
    "                         less-expression-right-list"
)
def _concatenate(*elements):
    """Concatenates all arguments with no delimiters."""
    return "".join(elements)


@_formats("equality-expression-right -> equality-operator additive-expression")
@_formats("less-expression-right -> less-operator additive-expression")
@_formats("greater-expression-right -> greater-operator additive-expression")
@_formats("or-expression-right -> or-operator comparison-expression")
@_formats("and-expression-right -> and-operator comparison-expression")
def _concatenate_with_prefix_spaces(*elements):
    """Concatenates non-empty `elements` with leading spaces."""
    return "".join(" " + element for element in elements if element)


@_formats("attribute* -> attribute attribute*")
@_formats('comma-then-expression -> "," expression')
@_formats(
    "comparison-expression -> additive-expression inequality-operator"
    "                         additive-expression"
)
@_formats(
    'choice-expression -> logical-expression "?" logical-expression'
    '                                        ":" logical-expression'
)
@_formats('parameter-definition-list-tail -> "," parameter-definition')
def _concatenate_with_spaces(*elements):
    """Concatenates non-empty `elements` with spaces between."""
    return _concatenate_with(" ", *elements)


def _concatenate_with(joiner, *elements):
    """Concatenates non-empty `elements` with `joiner` between."""
    return joiner.join(element for element in elements if element)


@_formats("attribute-line* -> attribute-line attribute-line*")
@_formats("comment-line* -> comment-line comment-line*")
@_formats("doc-line* -> doc-line doc-line*")
@_formats("import-line* -> import-line import-line*")
def _concatenate_lists(head, tail):
    return head + tail


_check_productions()
