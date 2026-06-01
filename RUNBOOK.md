# ds-linux-cheatsheet — Runbook

Practical operations guide for installing, running, editing, testing, and
troubleshooting `ds-linux-cheatsheet`. Covers both **conda** and **venv**
workflows.

> Companion to [`README.md`](./README.md). The README is the marketing/overview
> page; this file is what you keep open while operating the app.

---

## 1. System prerequisites

| Requirement | Why                                                              |
| ----------- | ---------------------------------------------------------------- |
| Python ≥ 3.11 | Textual, pydantic v2, modern type hints                        |
| A real TTY  | Textual needs a terminal; SSH is fine, plain pipes are not       |
| `git`       | To clone / pull updates                                          |
| `xclip` *or* `xsel` (Linux X11) | Required by `pyperclip` for the `c` (copy) action  |
| `wl-clipboard` (Linux Wayland)  | Same purpose under Wayland                         |
| `$EDITOR` env var | The `e` (edit YAML) action shells out to whatever you set    |

On Debian/Ubuntu:

```bash
sudo apt install -y xclip          # X11
# or
sudo apt install -y wl-clipboard   # Wayland
```

If no clipboard tool is available the `c` action still works — it just
returns a "Clipboard unavailable" status; nothing crashes.

---

## 2. Installation

Pick **one** of the two paths below. Both end with a working
`ds-cheatsheet` command.

### 2a. Conda (recommended if you already live in conda)

```bash
git clone https://github.com/pitcany/ds-linux-cheatsheet.git
cd ds-linux-cheatsheet

conda create -n ds-cheatsheet python=3.12 -y
conda activate ds-cheatsheet

pip install -e ".[dev]"
ds-cheatsheet --version
```

**Notes:**
- `conda activate` must run in an interactive shell that has sourced
  `conda.sh`. Inside scripts, do `source "$(conda info --base)/etc/profile.d/conda.sh"`
  first.
- All runtime deps (textual, rich, pydantic, pyyaml, pyperclip) live on
  PyPI, not conda-forge proper, so `pip install` inside the conda env is
  the correct call. Mixing `conda install` and `pip install` for these
  packages would just slow you down.
- If you want a fully reproducible env, freeze:
  ```bash
  conda env export --no-builds > environment.yml
  ```

### 2b. venv (lighter, no conda dependency)

```bash
git clone https://github.com/pitcany/ds-linux-cheatsheet.git
cd ds-linux-cheatsheet

python -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"
ds-cheatsheet --version
```

### 2c. Verifying the install

```bash
ds-cheatsheet validate     # OK — loaded 101 commands.
pytest                     # 48 passed
```

If `validate` succeeds, content + schema are healthy. If `pytest` succeeds,
the package is wired correctly end-to-end.

---

## 3. Running the app

### 3a. Interactive TUI

```bash
ds-cheatsheet              # default subcommand is `tui`
ds-cheatsheet tui          # same thing, explicit
```

The TUI is a three-pane browser: categories (left), matching commands
(middle), detail (right), with a search box on top.

### 3b. Non-interactive CLI

| Command                                  | What it does                                  |
| ---------------------------------------- | --------------------------------------------- |
| `ds-cheatsheet validate`                 | Parse + validate every YAML file              |
| `ds-cheatsheet list`                     | Print every command (flag `(!)` = dangerous)  |
| `ds-cheatsheet list --category gpu`      | Filter to one category                        |
| `ds-cheatsheet explain "rg -uu TODO ."`  | Local rule-based command explainer            |
| `ds-cheatsheet --version`                | Print version                                 |
| `python -m ds_cheatsheet …`              | Equivalent to `ds-cheatsheet …`               |

### 3c. Pointing at a different content directory

```bash
export DS_CHEATSHEET_DATA_DIR=/path/to/my/commands
ds-cheatsheet validate
ds-cheatsheet
```

Useful for forking the YAML content into a private repo and keeping the
binary install shared.

---

## 4. Keyboard shortcuts (TUI)

| Key  | Action                                       |
| ---- | -------------------------------------------- |
| `/`  | Focus the search box                         |
| `j` / `k` / arrows | Move within the focused list       |
| `tab`| Cycle search → categories → commands         |
| `enter` | Select highlighted item                   |
| `D`  | Focus the detail panel                       |
| `/` with detail focused | Search within the selected entry |
| `n` / `N` | Next / previous detail search match     |
| `PgUp` / `PgDn` | Scroll the focused detail panel   |
| `Home` / `End` | Jump to top / bottom of detail     |
| `c`  | Copy the selected template/example to clipboard |
| `1`-`9` | Copy example N directly                  |
| `C`  | Cycle copy target: template → examples       |
| `s`  | Fill placeholders before copying             |
| `e`  | Edit the underlying YAML file in `$EDITOR`   |
| `x`  | Run the selected command (gated, see §6)     |
| `E`  | Explain a command you type                   |
| `t`  | Toggle dark / light theme                    |
| `?`  | Help modal                                   |
| `q`  | Quit                                         |

Search supports both plain keyword matching *and* intent phrases like
`find large files`, `monitor gpu`, `kill process`, `copy files to server`,
`split csv`, `tmux new session`, `grep recursively`. The expansions live in
`src/ds_cheatsheet/search.py::INTENT_SYNONYMS` — add your own freely.

---

## 5. Editing content

Each category has its own YAML file under `data/commands/`. The schema is
enforced by pydantic v2 (`src/ds_cheatsheet/models.py`).

### 5a. Schema (one entry)

```yaml
- id: tmux-new-session            # required, stable, globally unique
  title: Create a new named tmux session
  category: tmux                  # optional; defaults to file-level category
  command: tmux new -s <name>
  explanation: |
    Multi-line markdown. Renders in the detail panel.
  flags:                           # optional list[str]
    - -s <name>  session name
  examples:                        # at least one required for tests to pass
    - description: Start a session for training
      command: tmux new -s train
  gotchas:                         # optional list[str]
    - Prefix is Ctrl-b by default.
  tags: [tmux, session]            # optional list[str]
  dangerous: false                 # optional; auto-set if pattern matches
```

### 5b. Quoting rules that bite

PyYAML is strict in two places:

1. A list item that **starts with a backtick** must be quoted:
   ```yaml
   gotchas:
     - "`-c` counts matching lines, not occurrences."
   ```
2. A scalar containing `": "` (colon + space) or ending a token with `:`
   followed by space must be quoted:
   ```yaml
   command: "pip install --no-cache-dir --no-binary :all: numpy"
   ```

Symptoms of breaking these: `ScannerError: found character '\`' that cannot
start any token` or `mapping values are not allowed here`. Wrap the offending
value in double quotes or switch to a `|` literal block.

### 5c. Edit-and-reload loop

The fastest workflow is inside the TUI:

1. Highlight the entry, press `e`. The TUI suspends, your `$EDITOR` opens
   the source YAML file.
2. Save and quit. The TUI resumes and reloads the full set — the status bar
   shows `Reloaded N commands.` or a parse error.
3. If the parse failed, fix the file from another terminal and press `e`
   again to retry.

Outside the TUI, run `ds-cheatsheet validate` after manual edits.

### 5d. Adding a new category

1. Create `data/commands/<name>.yaml` with the top-level `category` key and
   a `commands:` list.
2. Restart the TUI (or press `e` on any entry — reload picks it up).
3. Update `tests/test_loader.py::test_categories_sorted` if you want the
   new category in the asserted-required set.

---

## 6. Safety model (the runner)

The optional command runner is intentionally conservative:

- **Default mode is copy-only.** `c` always works.
- **`x` runs non-dangerous commands** with output captured into a modal.
- **Dangerous commands are refused.** Patterns matched in
  `src/ds_cheatsheet/safety.py::DANGEROUS_PATTERNS`:
  `rm -rf*`, `chmod -R`, `chown -R`, `dd if=`, `mkfs*`, `sudo`, fork bomb,
  `> /dev/sda`, `shred`, `curl|sh`/`wget|sh`, `git push --force`,
  `git reset --hard`, `docker system prune -a`, `kill -9 -1`,
  `truncate -s 0`.
- Authors do not need to remember to set `dangerous: true` — the loader
  auto-flags any entry whose command matches.
- Forcing execution of a dangerous entry from the TUI is **not** wired up
  on purpose. To override, call `ds_cheatsheet.runner.run(cmd,
  confirm=True, force=True)` from a script.

To add a new pattern, edit `DANGEROUS_PATTERNS` (a list of `(regex, reason)`
tuples) and add a positive test case to `tests/test_safety.py`.

---

## 7. Themes

- `t` toggles between `textual-dark` (default) and `textual-light`.
- The constants `CheatSheetApp.DARK_THEME` and `LIGHT_THEME` are the source
  of truth. To use a different default, override them in a subclass or set
  `self.theme` in `on_mount`.
- Other themes ship with Textual (nord, gruvbox, dracula, catppuccin,
  tokyo-night, monokai, …); call `app.theme = "nord"` interactively in a
  Python REPL with `app.run_test()` to preview, or wire a third binding.

---

## 8. Development workflow

```bash
# work in a feature branch
git checkout -b feature/<thing>

# edit, then format + lint
ruff format src tests
ruff check src tests --fix

# run the test suite
pytest -q                   # quiet
pytest -v                   # per-test names
pytest --cov=src --cov-report=term-missing

# manual smoke
ds-cheatsheet validate
ds-cheatsheet               # try the change in the TUI

# commit + push + PR
git add -A
git commit -m "feat: ..."
git push -u origin feature/<thing>
gh pr create --fill
```

### Headless TUI smoke test

Useful for CI or remote boxes:

```python
import asyncio
from ds_cheatsheet.tui.app import CheatSheetApp

async def smoke():
    app = CheatSheetApp()
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        app.query_one("#search-input").focus()
        await pilot.pause()
        for ch in "monitor gpu":
            await pilot.press(ch if ch != " " else "space")
        await pilot.pause()
        assert app.selected_id == "nvtop"
        app.save_screenshot(path="/tmp", filename="dscheat.svg")

asyncio.run(smoke())
```

Render to PNG: `rsvg-convert -w 1400 /tmp/dscheat.svg -o /tmp/dscheat.png`.

---

## 9. Troubleshooting

| Symptom                                                   | Cause / fix                                                                                                  |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `command not found: ds-cheatsheet`                        | The env isn't activated. `conda activate ds-cheatsheet` or `source .venv/bin/activate`.                       |
| `CheatSheetLoadError: Invalid YAML in …`                  | A list item starts with a backtick or a value contains `": "`. See §5b.                                       |
| `pyperclip` exception when pressing `c`                   | Install `xclip` (X11) or `wl-clipboard` (Wayland), or accept "Clipboard unavailable" status.                  |
| TUI launches but layout is squished                       | Terminal too narrow. Aim for ≥ 100 columns.                                                                   |
| `e` opens nothing                                         | `$EDITOR` is unset → defaults to `vi`. Export `EDITOR=nvim` (or similar) in your shell rc.                    |
| Theme toggle does nothing                                 | Make sure the `categories` or `commands` list is focused, not the search input (the input swallows `t`).      |
| `ModuleNotFoundError: No module named 'ds_cheatsheet'`    | Did `pip install -e ".[dev]"` from inside the activated env? Re-run.                                          |
| Pre-existing `.venv` refuses to recreate (`Permission denied: activate.csh`) | `chmod -R u+w .venv && rm -rf .venv` then recreate.                                            |
| Test failure: `Input should be a valid string`            | A flag string accidentally became a dict because of an unquoted colon. Quote it (§5b).                        |
| `ds-cheatsheet validate` works but TUI crashes on launch  | Probably no TTY (e.g. piped through `tee`). Run directly in a terminal.                                       |
| `conda activate` in a non-interactive shell does nothing  | Source the shell hook first: `source "$(conda info --base)/etc/profile.d/conda.sh"`.                          |

---

## 10. Release / packaging

The project uses Hatchling. To build wheels for distribution:

```bash
pip install build
python -m build              # writes dist/*.whl + dist/*.tar.gz
```

To install from a built wheel (no source checkout needed):

```bash
pip install dist/ds_linux_cheatsheet-0.1.0-py3-none-any.whl
ds-cheatsheet validate       # uses the bundled YAML shipped in the wheel
```

Bumping the version: edit `version` in `pyproject.toml` and
`__version__` in `src/ds_cheatsheet/__init__.py`, then commit and tag:

```bash
git tag v0.2.0
git push origin v0.2.0
```

---

## 11. Repo / GitHub workflow

- `main` is the long-lived branch; force-push is not allowed.
- New work goes on `feature/<thing>` or `fix/<thing>` branches.
- Commits use the Conventional Commits style (`feat:`, `fix:`, `refactor:`,
  `docs:`, `test:`, `chore:`).
- PR titles should be ≤ 70 chars; details belong in the body.
- The repo currently has no GitHub Actions wired up; `pytest` is the only
  required gate. Add a workflow under `.github/workflows/test.yml` when you
  want CI.

---

## 12. Quick reference cards

### Daily user

```bash
conda activate ds-cheatsheet            # or: source .venv/bin/activate
ds-cheatsheet                            # /  to search, c to copy, t to toggle theme, q to quit
```

### Adding a command

1. Open the right `data/commands/<category>.yaml`.
2. Append an entry with `id`, `title`, `command`, `explanation`, ≥ 1
   `examples` entry.
3. Run `ds-cheatsheet validate`.
4. Run `pytest -q`.
5. Commit.

### Debugging a load failure

```bash
ds-cheatsheet validate                   # tells you which file/line failed
python -c "import yaml; yaml.safe_load(open('data/commands/foo.yaml'))"
```

### Resetting the env from scratch

```bash
# conda
conda env remove -n ds-cheatsheet -y
conda create -n ds-cheatsheet python=3.12 -y
conda activate ds-cheatsheet
pip install -e ".[dev]"

# venv
chmod -R u+w .venv && rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```
