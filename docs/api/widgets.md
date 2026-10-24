# pycli.widgets

The prompt implementations behind [`select`][pycli.select],
[`checkbox`][pycli.checkbox], [`textbox`][pycli.textbox], and
[`confirm`][pycli.confirm].

The convenience functions are documented on the [`pycli`][pycli.select] page.
This page covers the classes and helpers you need to build or test widgets
directly. The prompt classes are stateful and pure: they render lines and
consume [`Key`][pycli.input.Key] events, but never touch a terminal. Run them
with [`App`][pycli.app.App].

::: pycli.widgets
    options:
      show_root_heading: false
      members:
        - Option
        - FreeText
        - normalize_options
        - SelectPrompt
        - CheckboxPrompt
        - TextboxPrompt
        - ConfirmPrompt

## Prompt protocol

Custom prompts only need to satisfy this protocol. See
[Custom widgets](../guides/custom-widgets.md) for a worked example.

::: pycli.widgets.base.Prompt
    options:
      show_root_heading: false
