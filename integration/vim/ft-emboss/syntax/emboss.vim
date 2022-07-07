" Copyright 2019 Google LLC
"
" Licensed under the Apache License, Version 2.0 (the "License");
" you may not use this file except in compliance with the License.
" You may obtain a copy of the License at
"
"     https://www.apache.org/licenses/LICENSE-2.0
"
" Unless required by applicable law or agreed to in writing, software
" distributed under the License is distributed on an "AS IS" BASIS,
" WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
" See the License for the specific language governing permissions and
" limitations under the License.

" Vim syntax file for Emboss.

" Quit when a (custom) syntax file was already loaded.
if exists('b:current_syntax')
  finish
endif

" TODO(bolms): Generate the syntax patterns from the patterns in tokenizer.py.
" Note that Python regex syntax and Vim regexp syntax differ significantly, and
" the matching logic Vim uses for syntactic elements is significantly different
" from what a tokenizer uses.

syn clear

" Emboss keywords.
syn keyword embStructure struct union enum bits external
syn keyword embKeyword $reserved $default
syn keyword embKeyword $static_size_in_bits $is_statically_sized this
syn keyword embKeyword $next $max $present $upper_bound $lower_bound
syn keyword embKeyword import as
syn keyword embKeyword if let
syn keyword embBoolean true false
syn keyword embIdentifier $size_in_bits $size_in_bytes
syn keyword embIdentifier $max_size_in_bits $max_size_in_bytes
syn keyword embIdentifier $min_size_in_bits $min_size_in_bytes

" Per standard convention, highlight to-do patterns in comments.
syn keyword embTodo contained TODO FIXME XXX

" When more than one syntax pattern matches a particular chunk of text, Vim
" picks the last one.  These 'catch-all' patterns will match any word or number,
" valid or invalid; valid tokens will be matched again by later patterns,
" overriding the embBadNumber or embBadWord match.
syn match embBadNumber display '\v\C<[0-9][0-9a-zA-Z_$]*>'
syn match embBadWord display '\v\C<[A-Za-z_$][A-Za-z0-9_$]*>'

" Type names are always CamelCase, enum constants are always SHOUTY_CASE, and
" most other identifiers (field names, attribute names) are snake_case.
syn match embType display '\v\C<[A-Z][A-Z0-9]*[a-z][A-Za-z0-9]*>'
syn match embConstant display '\v\C<[A-Z][A-Z0-9_]+>'
syn match embIdentifier display '\v\C<[a-z][a-z0-9_]*>'

" Decimal integers both with and without thousands separators.
syn match embNumber display '\v\C<\d+>'
syn match embNumber display '\v\C<\d{1,3}(_\d{3})*>'

" Hex integers with and without word/doubleword separators.
syn match embNumber display '\v\C<0[xX]\x+>'
syn match embNumber display '\v\C<0[xX]\x{1,4}(_\x{4})*>'
syn match embNumber display '\v\C<0[xX]\x{1,8}(_\x{8})*>'

" Binary integers with and without byte/nibble separators.
syn match embNumber display '\v\C<0[bB][01]+>'
syn match embNumber display '\v\C<0[bB][01]{1,4}(_[01]{4})*>'
syn match embNumber display '\v\C<0[bB][01]{1,8}(_[01]{8})*>'

" Strings
syn match embString display '\v\C"([^"\n\\]|\\[n\\"])*"'

" Comments and documentation.
syn match embComment display contains=embTodo '\v\C\#.*$'
syn match embDocumentation display contains=embTodo '\v\C\-\- .*$'
syn match embDocumentation display '\v\C\-\-$'
syn match embBadDocumentation display '\v\C\-\-[^ ].*$'


" Most Emboss constructs map neatly onto the standard Vim syntax types.
hi def link embComment Comment
hi def link embConstant Constant
hi def link embIdentifier Identifier
hi def link embNumber Number
hi def link embOperator Operator
hi def link embString String
hi def link embStructure Structure
hi def link embTodo Todo
hi def link embType Type

" SpecialComment seems to be the best match for embDocumentation, as it is used
" for things like javadoc.
hi def link embDocumentation SpecialComment
hi def link embBadDocumentation Error
hi def link embBadWord Error
hi def link embBadNumber Error

let b:current_syntax = 'emboss'
