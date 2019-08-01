This directory contains an `.emb` and a set of golden files which correspond to
various parsing stages of the `.emb`.  The primary purpose is to highlight
changes to the parse tree, tokenization, or (uncooked) intermediate
representation in a code review, where the before/after can be seen in
side-by-side diffs.  The golden files *are* checked by unit tests, but test
failures generally just mean that the files need to be regenerated, not that
there is an actual bug.


## `span_se_log_file_status.emb`

The .emb file from which the other files are derived.


## `span_se_log_file_status.tokens.txt`

The tokenization.  This file should change very rarely.  From the workspace root
directory, it can be generated with:

    bazel run //front_end:emboss_front_end \
        -- --no-debug-show-header-lines --debug-show-tokenization \
        $(pwd)/testdata/golden/span_se_log_file_status.emb \
        > $(pwd)/testdata/golden/span_se_log_file_status.tokens.txt


## `span_se_log_file_status.parse_tree.txt`

The syntactic parse tree.  From the workspace root directory, it can be
generated with:

    bazel run //front_end:emboss_front_end \
        -- --no-debug-show-header-lines --debug-show-parse-tree \
        $(pwd)/testdata/golden/span_se_log_file_status.emb \
        > $(pwd)/testdata/golden/span_se_log_file_status.parse_tree.txt


## `span_se_log_file_status.ir.txt`

The "uncooked" module-level IR: that is, the IR of *only*
`span_se_log_file_status.emb` (without the prelude or any imports), straight out
of `module_ir.py` with no "middle end" transformations.  From the workspace root
directory, it can be generated with:

    blaze run //front_end:emboss_front_end \
        -- --no-debug-show-header-lines --debug-show-module-ir \
        $(pwd)/testdata/golden/span_se_log_file_status.emb \
        > $(pwd)/testdata/golden/span_se_log_file_status.ir.txt
