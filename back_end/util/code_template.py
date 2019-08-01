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

"""A formatter for code templates.

Use the format_template function to render a code template.
"""

import collections
import re
import string


class _CppFormatter(string.Formatter):
  """Customized Formatter using $_name_$ instead of {name}.

  This class exists for the format_template() function; see its documentation
  for details.
  """

  def parse(self, format_string):
    """Overrides string.Formatter.parse.

    Arguments:
      format_string: a format string to be parsed.

    Yields:
      A sequence of 4-element tuples (literal, name, format_spec, conversion),
      where:

        literal: A literal string to include in the output.  This will be
          output before the substitution, if any.
        name: The name of a substitution, or None if no substitution.
        format_spec: A format specification.
        conversion: A conversion specification.

      Consult the documentation for string.Formatter for the format of the
      format_spec and conversion elements.
    """
    # A replacement spec is $_field_name!conversion:format_spec_$, where
    # conversion and format_spec are optional.  string.Formatter will take care
    # of parsing and interpreting the conversion and format_spec, so this method
    # just extracts them.
    delimiter_matches = re.finditer(
        r"""(?x)
            \$_
                  (?P<field_name>  ( [^!:_] | _[^$] )* )
              ( ! (?P<conversion>  ( [^:_]  | _[^$] )* ) )?
              ( : (?P<format_spec> ( [^_]   | _[^$] )* ) )?
            _\$""", format_string)
    after_last_delimiter = 0
    for match in delimiter_matches:
      yield (format_string[after_last_delimiter:match.start()],
             match.group("field_name"),
             # A missing format_spec is indicated by ""...
             match.group("format_spec") or "",
             # ... but a missing conversion is indicated by None.  Consistency!
             match.group("conversion") or None)
      after_last_delimiter = match.end()
    yield format_string[after_last_delimiter:], None, None, None


_FORMATTER = _CppFormatter()


def format_template(template, *args, **kwargs):
  """format_template acts like str.format, but uses $_name_$ instead of {name}.

  format_template acts like a str.format, except that instead of using { and }
  to delimit substitutions, format_template uses $_ and _$.  This simplifies
  templates of source code in most languages, which frequently use "{" and "}",
  but very rarely use "$".  The choice of "$_" and "_$" is conducive to the use
  of clang-format on templates.

  format_template does not currently have a way to put literal "$_..._$" into a
  format string.

  See the documentation for str.format and string.Formatter for details about
  template strings and the format of substitutions.

  Arguments:
    template: A template to format.
    *args: Positional arguments for string.Formatter.format.
    **kwargs: Keyword arguments for string.Formatter.format.

  Returns:
    A formatted string.
  """
  return _FORMATTER.format(template, *args, **kwargs)


def parse_templates(text):
  """Parses text into a namedtuple of templates.

  parse_templates will split its argument into templates by searching for lines
  of the form:

      [punctuation] " ** " [name] " ** " [punctuation]

  e.g.:

      // ** struct_field_accessor ** ////////

  Leading and trailing punctuation is ignored, and [name] is used as the name
  of the template.  [name] should match [A-Za-z][A-Za-z0-9_]* -- that is, it
  should be a valid ASCII Python identifier.

  Arguments:
    text: The text to parse into templates.

  Returns:
    A namedtuple object whose attributes are the templates from text.
  """
  delimiter_re = re.compile(r"^\W*\*\* ([A-Za-z][A-Za-z0-9_]*) \*\*\W*$")
  templates = {}
  name = None
  template = []
  for line in text.splitlines():
    if delimiter_re.match(line):
      if name:
        templates[name] = "\n".join(template)
      name = delimiter_re.match(line).group(1)
      template = []
    else:
      template.append(line)
  if name:
    templates[name] = "\n".join(template)
  return collections.namedtuple("Templates",
                                list(templates.keys()))(**templates)
