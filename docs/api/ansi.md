# pycli.term.ansi

ANSI escape sequences and cursor movement helpers. All sequences are plain
strings; import the constants rather than hard-coding escapes.

Cursor helpers clamp their argument to at least 1, mirroring the behaviour of
the escape sequences themselves.

## Constants

| Constant | Purpose |
|---|---|
| `ESC`, `CSI` | Raw escape byte and the CSI prefix |
| `RESET`, `BOLD`, `DIM`, `REVERSE` | Text styling |
| `CYAN`, `RED` | Foreground colours |
| `CLEAR_SCREEN`, `CLEAR_LINE`, `ERASE_BELOW` | Erasing |
| `HIDE_CURSOR`, `SHOW_CURSOR` | Cursor visibility |
| `ALT_SCREEN_ENTER`, `ALT_SCREEN_LEAVE` | Alternate screen buffer |
| `BRACKETED_PASTE_ON`, `BRACKETED_PASTE_OFF` | Bracketed paste mode |
| `SYNC_UPDATE_ON`, `SYNC_UPDATE_OFF` | Synchronized output mode |
| `WRAP_OFF`, `WRAP_ON` | Automatic line wrapping |

::: pycli.term.ansi
    options:
      show_root_heading: false
      members:
        - ESC
        - CSI
        - RESET
        - BOLD
        - DIM
        - REVERSE
        - CYAN
        - RED
        - CLEAR_SCREEN
        - CLEAR_LINE
        - ERASE_BELOW
        - HIDE_CURSOR
        - SHOW_CURSOR
        - ALT_SCREEN_ENTER
        - ALT_SCREEN_LEAVE
        - BRACKETED_PASTE_ON
        - BRACKETED_PASTE_OFF
        - SYNC_UPDATE_ON
        - SYNC_UPDATE_OFF
        - WRAP_OFF
        - WRAP_ON
        - cursor_up
        - cursor_down
        - cursor_prev_line
        - cursor_next_line
        - move_to
        - erase_line
