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


def format_template(template, **kwargs):
    """format_template acts like str.format, but uses ${name} instead of {name}.

    format_template acts like a str.format, except that instead of using { and }
    to delimit substitutions, format_template uses ${name}.  This simplifies
    templates of source code in most languages, which frequently use "{" and "}",
    but very rarely use "$".

    See the documentation for string.Template for details about
    template strings and the format of substitutions.

    Arguments:
      template: A template to format.
      **kwargs: Keyword arguments for string.Template.substitute.

    Returns:
      A formatted string.
    """
    return template.substitute(**kwargs)


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

    Additionally any `//` style comment without leading space of the form:
    ```C++
    // This is an emboss developer related comment, it's useful internally
    // but not relevant to end-users of generated code.
    ```
    will be stripped out of the generated code.

    If a template wants to define a comment that will be included in the
    generated code a C-style comment is recommended:
    ```C++
    /** This will be included in the generated source. */

    /**
     * So will this!
     */
    ```

    Arguments:
      text: The text to parse into templates.

    Returns:
      A namedtuple object whose attributes are the templates from text.
    """
    delimiter_re = re.compile(r"^\W*\*\* ([A-Za-z][A-Za-z0-9_]*) \*\*\W*$")
    comment_re = re.compile(r"^\s*//.*$")
    templates = {}
    name = None
    template = []

    def finish_template(template):
        return string.Template("\n".join(template))

    for line in text.splitlines():
        if delimiter_re.match(line):
            if name:
                templates[name] = finish_template(template)
            name = delimiter_re.match(line).group(1)
            template = []
        else:
            if not comment_re.match(line):
                template.append(line)
    if name:
        templates[name] = finish_template(template)
    return collections.namedtuple("Templates", list(templates.keys()))(**templates)
