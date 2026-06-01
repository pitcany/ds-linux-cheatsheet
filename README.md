# ds-linux-cheatsheet

An interactive terminal cheat sheet of Linux commands for data scientists and
ML engineers. Built with [Textual](https://textual.textualize.io/).

- Three-pane browser (categories / commands / detail)
- Fuzzy keyword search **and** intent search ("find large files", "monitor gpu")
- 100+ curated commands across tmux, bash, grep/rg, find/fd, awk, sed, xargs,
  ssh/scp/rsync, git, docker, conda/venv/pip/uv, jq, CSV tools, process
  monitoring, disk usage, GPU monitoring, networking
- Local rule-based **explain-this-command** — no API calls
- Optional, gated command runner — copy-only by default, dangerous commands
  blocked unless you explicitly force them
- Editable YAML content — `e` opens the entry in `$EDITOR`, then reloads
- Validation tests for every command file (`pytest`)

> For step-by-step ops and troubleshooting (conda *and* venv paths, YAML
> editing, runner safety, theming, releases), see [`RUNBOOK.md`](./RUNBOOK.md).

## Quick start

### conda

```bash
git clone https://github.com/pitcany/ds-linux-cheatsheet.git
cd ds-linux-cheatsheet
conda create -n ds-cheatsheet python=3.12 -y
conda activate ds-cheatsheet
pip install -e ".[dev]"
ds-cheatsheet              # launches the TUI
```

### venv

```bash
git clone https://github.com/pitcany/ds-linux-cheatsheet.git
cd ds-linux-cheatsheet
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ds-cheatsheet
```

The CLI also supports:

```bash
ds-cheatsheet tui          # explicit TUI launch (default)
ds-cheatsheet validate     # validate bundled YAML files
ds-cheatsheet list         # list every command
ds-cheatsheet list --category gpu
ds-cheatsheet explain "rg -uu --hidden TODO ./src"
```

## Keyboard shortcuts

| Key  | Action                                  |
| ---- | --------------------------------------- |
| `/`  | Focus the search box                    |
| `j`/`k` or arrows | Move within the focused list |
| `tab`| Cycle search → categories → commands    |
| `enter` | Select the highlighted item          |
| `c`  | Copy the selected template/example to clipboard |
| `1`-`9` | Copy example N directly             |
| `C`  | Cycle copy target: template → examples |
| `s`  | Fill placeholders before copying        |
| `e`  | Edit the underlying YAML in `$EDITOR`   |
| `x`  | Run the selected command (gated)        |
| `E`  | Explain a command you type              |
| `t`  | Toggle dark / light theme               |
| `?`  | Help                                    |
| `q`  | Quit                                    |

## Safety model

The runner is intentionally cautious:

1. Default mode is **copy only** — `c` puts the command on your clipboard.
2. Pressing `x` only runs *non-dangerous* commands.
3. Anything containing patterns like `rm -rf`, `chmod -R`, `chown -R`, `dd`,
   `mkfs`, `sudo`, `git push --force`, `git reset --hard`, fork bombs,
   `curl | sh`, raw block-device writes, or `docker system prune -a` is
   flagged dangerous and refused.
4. Dangerous entries can still be opened, copied, and explained — they just
   can't be executed from inside the TUI.

The dangerous-pattern list lives in `src/ds_cheatsheet/safety.py`.

## Content layout

Commands live in editable YAML files under `data/commands/`. One file per
category. Each entry conforms to the pydantic schema in
`src/ds_cheatsheet/models.py`:

```yaml
category: tmux
commands:
  - id: tmux-new-session            # stable unique id
    title: Create a new named tmux session
    category: tmux
    command: tmux new -s <name>
    explanation: |
      Starts a new tmux session ...
    flags:
      - -s <name>  session name
      - -d         start detached
    examples:
      - description: Start a session for training
        command: tmux new -s train
    gotchas:
      - Inside tmux, the prefix is Ctrl-b by default.
    tags: [tmux, session, persistence]
    dangerous: false                 # optional; auto-detected if omitted
```

Validation is enforced both at load time and by the test suite — `pytest`
will fail if any entry is missing examples or has a duplicate id.

## Development

```bash
pip install -e ".[dev]"
pytest                    # 45 tests
ruff format src tests
ruff check src tests
```

### Project structure

```
ds-linux-cheatsheet/
├── pyproject.toml
├── README.md
├── data/commands/*.yaml         # editable content
├── src/ds_cheatsheet/
│   ├── cli.py                   # `ds-cheatsheet` entrypoint
│   ├── models.py                # pydantic schema
│   ├── loader.py                # YAML loader + validator
│   ├── safety.py                # dangerous-pattern detector
│   ├── search.py                # keyword + intent search
│   ├── explain.py               # local command-explainer
│   ├── runner.py                # gated command runner
│   ├── clipboard.py             # pyperclip wrapper
│   └── tui/
│       ├── app.py               # Textual application
│       ├── help_screen.py
│       └── styles.tcss
└── tests/                       # pytest suite
```

### Overriding the data directory

Point at a fork of the YAML content:

```bash
export DS_CHEATSHEET_DATA_DIR=/path/to/my/commands
ds-cheatsheet
```

## License

MIT — see `LICENSE`.
