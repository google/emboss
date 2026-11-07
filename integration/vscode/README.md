# Emboss for Visual Studio Code

This directory is a small VS Code extension that adds syntax highlighting for
Emboss `.emb` files. It has no code: it only contributes a TextMate grammar
(`syntaxes/emboss.tmLanguage.json`) and basic editor settings
(`language-configuration.json`, for `#` line comments and bracket matching).

## Installing

The extension is not published to the Visual Studio Marketplace. Install it
from this directory in one of these ways. Both commands run from the root of
the Emboss repository.

Build a `.vsix` package and install it:

```
cd integration/vscode
npx @vscode/vsce package --skip-license
code --install-extension emboss-0.0.1.vsix
```

Or link this directory into your VS Code extensions directory, then restart
VS Code:

```
ln -s "$PWD/integration/vscode" ~/.vscode/extensions/emboss
```

On Windows, the extensions directory is `%USERPROFILE%\.vscode\extensions`.

## Keeping the grammar up to date

The grammar follows the token rules in
[`compiler/front_end/tokenizer.py`](../../compiler/front_end/tokenizer.py).
If you add or change a token there, update the grammar too.
`grammar_test.py` checks that the grammar and the tokenizer agree; run it with:

```
bazel test //integration/vscode:grammar_test
```
