# ds-linux-cheatsheet — Improvement Plan

Self-contained spec for the next iteration. Each item lists the problem, files
to touch, implementation approach, required tests, and acceptance criteria so
an agentic coding tool (codex, Claude Code, Aider, etc.) can pick items off
without further clarification.

**Repo:** https://github.com/pitcany/ds-linux-cheatsheet  •  **Branch baseline:** `main`
(commit `282ee90` or later)

---

## Ground rules

1. **Don't break existing tests.** Current baseline: 48 passing.
2. **Maintain backwards-compatible YAML.** All 101 entries must still validate.
3. **Type-annotated, ruff-clean.** `ruff format src tests && ruff check src tests`
   must pass after every change.
4. **One commit per phase**, conventional-commits style
   (`feat(tui): …`, `fix(search): …`, `refactor(loader): …`).
5. **Tests live in `tests/test_<area>.py`.** New TUI tests use `pilot.press`
   inside `app.run_test(size=(140, 40))` and `@pytest.mark.asyncio`
   (asyncio_mode = "auto" is already set in `pyproject.toml`).
6. **Settle dependencies in `pyproject.toml`** if you introduce new ones
   (likely none required for this plan — keep it stdlib + existing deps).

---

## Priority overview

| # | Item                                              | Phase | Risk | Lines (rough) |
| - | ------------------------------------------------- | ----- | ---- | ------------- |
| 1 | Copy specific example (number keys + cycle)       | 1     | low  | ~60           |
| 2 | Parameter substitution modal                       | 1     | med  | ~180          |
| 3 | `t` works when search has focus                    | 1     | low  | ~10           |
| 4 | `↓` from search drops into commands list           | 1     | low  | ~25           |
| 5 | Clipboard fallback on headless systems             | 5     | low  | ~40           |
| 6 | Detail panel scroll affordances + PgUp/PgDn        | 2     | low  | ~30           |
| 7 | Runner output in modal instead of detail pane      | 4     | med  | ~80           |
| 8 | `e` opens YAML at the entry's line                  | 4     | low  | ~30           |
| 9 | Typo-tolerant / prefix-aware search                | 3     | med  | ~80           |
| 10| Favorites + recently-copied tabs                   | 5     | med  | ~140          |
| 11| Footer shows nav keys by default                   | 2     | low  | ~5            |
| 12| Category list shows entry counts                   | 2     | low  | ~20           |
| 13| `/` inside detail panel for in-entry search        | 3     | med  | ~70           |
| 14| Explain → cross-link to cheat sheet entries        | 3     | low  | ~50           |
| 15| "New in last N days" badge from git history        | 2     | low  | ~50           |

Total scope: ~900 LOC excluding tests. Estimated 4–6 focused sessions.

---

## Phase 1 — Core UX wins (do these first)

### ✅ 1. Copy a specific example, not just the template

**Problem.** `c` always copies `entry.command` (the template with
`<placeholders>`). 95% of the time the user wants a concrete example.

**Files to modify.**
- `src/ds_cheatsheet/tui/app.py`
- `src/ds_cheatsheet/tui/help_screen.py` (update help text)
- `README.md` and `RUNBOOK.md` (binding tables)

**Approach.**
- Add a reactive `copy_target_index: int = -1` to `CheatSheetApp`.
  `-1` = template, `0..n-1` = example index. Reset to `-1` on
  `selected_id` change.
- Add bindings:
  - `c` — copies whatever the current `copy_target_index` resolves to.
    Default behavior unchanged on first press (template).
  - `1`–`9` — copy example N (1-indexed). If example missing, status
    bar shows "No example N for this entry."
  - `C` (shift-c) — cycle through template → ex1 → ex2 → … → template.
- In `_render_detail`, prefix each example row with `[1]`, `[2]`… and
  highlight the currently-selected copy target.
- Status bar after copy: `Copied template` or `Copied example 2`.

**Tests.** Add to `tests/test_tui.py`:
- Pressing `1` on an entry with examples copies the first example's command.
- Pressing `9` on an entry with 3 examples shows "No example 9".
- Pressing `C` repeatedly cycles indices.

**Acceptance.**
- All 48 existing tests pass.
- 3 new tests pass.
- Number keys 1–9 work even when a list has focus (no priority issue, ListView
  doesn't claim digits).
- README + RUNBOOK keybinding tables updated.

---

### ✅ 2. Parameter substitution modal

**Problem.** Templates contain `<name>`, `<host>`, `<port>`, `<dir>`,
`<pattern>`, etc. Users always have to hand-edit after copying.

**New module.** `src/ds_cheatsheet/substitute.py`
```python
import re
PLACEHOLDER_RE = re.compile(r"<([A-Za-z_][A-Za-z0-9_-]*)>")

def find_placeholders(command: str) -> list[str]:
    """Return placeholder names in order of first appearance, deduped."""

def substitute(command: str, mapping: dict[str, str]) -> str:
    """Replace <name> tokens. Missing keys leave the token intact."""
```

**TUI.**
- New file `src/ds_cheatsheet/tui/substitute_screen.py` defining
  `SubstituteScreen(ModalScreen[str | None])`.
- Contents: one labeled `Input` per placeholder, an `enter` submit, an
  `escape` cancel. On submit, dismiss with the substituted command string.
- Wire from `CheatSheetApp`:
  - New binding `s` ("substitute"). When pressed:
    1. Resolve the current copy target (template or example).
    2. `find_placeholders(cmd)` → if empty, copy directly and toast
       "No placeholders to fill."
    3. Otherwise `push_screen(SubstituteScreen(cmd, placeholders), callback)`.
    4. Callback copies the substituted string and updates status.

**Tests.**
- `tests/test_substitute.py`:
  - `find_placeholders("rsync -avzP <src>/ <user>@<host>:<dst>/")` →
    `["src", "user", "host", "dst"]`.
  - `substitute("scp <src> <host>:<dst>", {"src": "a", "dst": "/b"})` →
    `"scp a <host>:/b"`.
- `tests/test_tui.py`:
  - `s` on an entry with placeholders pushes the modal.
  - Modal `dismiss("filled-cmd")` triggers a clipboard copy.

**Acceptance.**
- New module is pure, no Textual deps.
- Modal renders one input per placeholder.
- All tests pass.
- Help + README + RUNBOOK updated.

---

### ✅ 3. Theme toggle works when search has focus

**Problem.** Pressing `t` while the search Input is focused types the
letter `t` instead of toggling.

**Files.** `src/ds_cheatsheet/tui/app.py`

**Approach.**
- Change `Binding("t", "toggle_theme", "Theme")` to
  `Binding("t", "toggle_theme", "Theme", priority=True)`.
- Verify the existing `Input` widget no longer swallows it — Textual
  honours `priority=True` at the app level.
- If `t` collides with future input-typing needs, fall back to `ctrl+t`.

**Tests.** Extend `tests/test_tui.py`:
- Focus the search input → press `t` → assert theme flipped.

**Acceptance.** New + existing tests pass.

---

### ✅ 4. `↓` from the search box drops into the commands list

**Problem.** After typing a query the natural next motion is `↓` to walk
results, but `↓` does nothing useful inside the Input.

**Files.** `src/ds_cheatsheet/tui/app.py`

**Approach.**
- Add `on_key` handler scoped to the search input (or use the
  `Input.Submitted` + arrow handler pattern):
  ```python
  def on_key(self, event: events.Key) -> None:
      if self.focused and self.focused.id == "search-input" and event.key == "down":
          event.prevent_default()
          self.query_one("#commands", ListView).focus()
  ```
- Also allow `enter` in the search input to do the same (jump to first
  result) without losing the query.

**Tests.**
- Type query, press `down`, assert focus is now on `#commands`.
- Type query, press `enter`, assert focus is on `#commands` and
  `selected_id` matches the first match.

**Acceptance.** Tests pass; arrow-key cursor navigation inside the input
still works for `←`/`→`.

---

## Phase 2 — Information & affordances

### ✅ 11. Show nav keys in the Footer

**Files.** `src/ds_cheatsheet/tui/app.py`

**Approach.** Remove `show=False` from `j`, `k`, `tab` bindings, OR
introduce a `KeyBindingsHelp` widget at the bottom that lists the most
useful keys with concise labels. Pick the simpler path: drop `show=False`
and accept the slightly busier footer.

**Tests.** None needed; visual change.

**Acceptance.** Footer shows `Quit Help Search Copy Edit YAML Run Explain
Theme … Down Up Cycle`.

---

### ✅ 12. Category list shows entry counts

**Files.** `src/ds_cheatsheet/tui/app.py`, `src/ds_cheatsheet/loader.py`

**Approach.**
- Add helper `count_by_category(entries) -> dict[str, int]` in `loader.py`.
- In `_refresh_categories`, render labels like `tmux (6)` and `All (101)`.
- Keep `category_name` attribute as the bare name for routing logic.

**Tests.** Add to `tests/test_loader.py`:
- `count_by_category(load_all())["gpu"] == 5` (currently 5; update if data grows).

**Acceptance.** Category list visually shows counts; selecting still
filters correctly.

---

### ✅ 15. "New in last N days" badge

**Files.** `src/ds_cheatsheet/loader.py`, `src/ds_cheatsheet/tui/app.py`

**Approach.**
- New helper `recent_entry_ids(repo_root, days=7)` in a new module
  `src/ds_cheatsheet/git_meta.py`. Implementation: run
  `git log --since="<N> days ago" --name-only --pretty=format: -- data/commands/*.yaml`,
  parse modified files, then re-parse those YAML files and collect every
  entry id whose source line was added in those commits via
  `git log -L /<id>/,+1:<path>`. **Fallback**: if `git` isn't available
  or the repo lacks history, return `set()` (silently).
- In `CommandItem`, prefix labels with `★` for `entry.id in recent_ids`.
- Compute once at startup; store on `CheatSheetApp.recent_ids`.

**Tests.**
- `tests/test_git_meta.py`: with a fake temp git repo, assert
  `recent_entry_ids` returns the seeded id; with no git, returns empty.

**Acceptance.** No crash on non-git installs; badge renders when run from
a git checkout.

---

### ✅ 6. Detail panel scroll affordances

**Files.** `src/ds_cheatsheet/tui/styles.tcss`, `src/ds_cheatsheet/tui/app.py`

**Approach.**
- Make `#detail` (the `VerticalScroll`) focusable and show a scrollbar
  always: `scrollbar-size: 1 1; overflow-y: auto;`.
- Add bindings `pageup` / `pagedown` / `home` / `end` that, when the
  detail panel has focus, scroll it by a viewport.
- Add `D` binding that focuses the detail pane directly.

**Tests.** Skip rendering; just assert that pressing `D` then `pagedown`
runs without error on a long entry.

**Acceptance.** Long entries scroll; scrollbar is visible.

---

## Phase 3 — Search quality

### ✅ 9. Typo-tolerant / prefix-aware search

**Files.** `src/ds_cheatsheet/search.py`, `tests/test_search.py`

**Approach.**
- Add a token-prefix step: when a search token of length ≥ 4 doesn't
  match the haystack as a substring, retry with `re.search(rf"\b{token[:3]}\w*", haystack)`.
- Add a tiny Levenshtein helper (stdlib-only, e.g. `difflib.get_close_matches`)
  to suggest "Did you mean: …" lines for entirely unmatched queries.
- Rank: substring > prefix > fuzzy.

**Tests.**
- `search(entries, "monitr gpu")` returns the same GPU entries.
- `search(entries, "tunneling")` finds `ssh-tunnel-local`.
- `search(entries, "xyzzy")` returns `[]` but a new helper
  `suggest(entries, "xyzzy")` returns at most 5 candidate ids.

**Acceptance.** New tests pass; existing intent-search tests still pass.

---

### ✅ 13. `/` inside detail panel for in-entry search

**Files.** `src/ds_cheatsheet/tui/app.py`, `src/ds_cheatsheet/tui/styles.tcss`

**Approach.**
- When detail panel is focused, `/` opens a small inline `Input` at the
  bottom of the detail panel. Typed text highlights matches in the
  rendered explanation/examples via Rich `Text` markup. `n`/`N` step
  through matches; `escape` closes.
- Implementation: store last-rendered Rich `Text` per entry; on search,
  rebuild with `[reverse]match[/reverse]` spans.

**Tests.** Light test: focus detail, press `/`, type "GPU", assert input
appears and at least one highlight marker exists in the rendered output.

**Acceptance.** Doesn't interfere with the main `/` (which only fires
when search panel is the natural target — namespace by the focused
widget).

---

### ✅ 14. Explain → cross-link to cheat sheet entries

**Files.** `src/ds_cheatsheet/tui/app.py` (the `_ExplainScreen` class),
`src/ds_cheatsheet/search.py`

**Approach.**
- After explaining, run `search(self.app.entries, first_token)` and
  display the top 3 entry titles at the bottom of the modal.
- Each is a `ListItem`; pressing enter dismisses the modal *and* jumps
  to that entry in the main view.

**Tests.** Pilot test: open explain, type `rg foo`, press enter, assert
the suggestions panel lists at least one entry whose id starts with
`ripgrep` or `grep`.

**Acceptance.** Suggestions don't appear if the explained command's
first token has no cheat sheet entries; modal still works fine.

---

## Phase 4 — Runner & editor polish

### ✅ 7. Runner output in a modal instead of replacing the detail pane

**Files.** `src/ds_cheatsheet/tui/app.py`, new
`src/ds_cheatsheet/tui/run_result_screen.py`

**Approach.**
- New `RunResultScreen(ModalScreen[None])` showing `Panel` of stdout +
  `Panel` of stderr + the returncode + a "copy output" button (`c`).
- `action_run_command` pushes this screen instead of mutating
  `#detail-body`.
- Closing the modal returns the user to the same highlight unchanged.

**Tests.** Run a safe command (`echo hi`), assert the modal contains
"hi" and the underlying detail pane still shows the entry.

**Acceptance.** No regression for dangerous-command refusal path.

---

### ✅ 8. `e` opens YAML at the entry's line

**Files.** `src/ds_cheatsheet/tui/app.py`

**Approach.**
- After locating the YAML file containing the entry id, find the
  line number with `enumerate(open(path))` matching `id: <entry.id>`.
- For vim-like editors (`vi`, `vim`, `nvim`), invoke
  `[editor, f"+{line_number}", str(path)]`.
- For VS Code: detect `code`/`codium` and use
  `[editor, "--goto", f"{path}:{line_number}"]`.
- Anything else: fall back to current behavior (`[editor, path]`).

**Tests.**
- Unit test a new helper
  `editor_command(editor: str, path: Path, line: int) -> list[str]`:
  vim → `["vi", "+12", "..."]`; code → `["code", "--goto", ".../foo.yaml:12"]`;
  nano → `["nano", "+12", "..."]`; unknown → `["foo", "..."]`.

**Acceptance.** Helper has 100% branch coverage; opening still works
with `EDITOR=cat` (smoke).

---

## Phase 5 — Workflow extras

### ✅ 10. Favorites + recently-copied

**Files.** New `src/ds_cheatsheet/state.py`, `src/ds_cheatsheet/tui/app.py`

**Approach.**
- State persisted at `$XDG_STATE_HOME/ds-cheatsheet/state.json` (fall back
  to `~/.local/state/ds-cheatsheet/state.json`).
- Schema: `{"favorites": ["id1", "id2"], "recent": [{"id": ..., "at": ts}]}`.
- New bindings:
  - `f` toggles favorite on the highlighted entry.
  - `F` opens a "Favorites" view (categories list becomes
    `Favorites | Recent | All | <real categories>`).
  - Every `c` press appends to `recent` (cap at 50, dedupe).
- Render a `★` prefix for favorited entries in the commands list.

**Tests.**
- `tests/test_state.py`: round-trip save/load to a temp dir via
  monkeypatched `XDG_STATE_HOME`.
- Pilot test: load entries, press `f`, restart app (new pilot session),
  assert the entry is favorited.

**Acceptance.** State file is created lazily; missing or corrupt file
falls back to empty defaults without crashing.

---

### ✅ 5. Clipboard fallback for headless systems

**Files.** `src/ds_cheatsheet/clipboard.py`, `src/ds_cheatsheet/tui/app.py`

**Approach.**
- When `pyperclip` fails, write the payload to
  `$XDG_RUNTIME_DIR/ds-cheatsheet-last.txt` (or `/tmp/ds-cheatsheet-last.txt`).
- Status bar message becomes:
  `No clipboard — wrote /tmp/ds-cheatsheet-last.txt (press y to print to stdout)`.
- New binding `y`: temporarily prints the last-copied command to stdout
  via `self.suspend()` so the user can manually select+copy in their
  terminal emulator.

**Tests.**
- Monkeypatch `pyperclip.copy` to raise; assert `copy_to_clipboard`
  writes the fallback file and returns `(False, "<message>")`.

**Acceptance.** Behavior on a clipboard-equipped system is unchanged.

---

## Test plan summary

| File                              | New tests |
| --------------------------------- | --------- |
| `tests/test_substitute.py`        | 4         |
| `tests/test_state.py`             | 3         |
| `tests/test_git_meta.py`          | 2         |
| `tests/test_tui.py` (additions)   | ~12       |
| `tests/test_search.py` (add)      | 3         |
| `tests/test_loader.py` (add)      | 1         |
| `tests/test_clipboard.py` (new)   | 2         |

Expected total: ~75 passing tests after the plan ships (currently 48).

---

## Documentation updates

After all phases:
- `README.md`: refresh keybinding table, add screenshots of substitute
  modal + favorites view.
- `RUNBOOK.md`:
  - §4 (shortcuts): add `1`–`9`, `C`, `s`, `f`, `F`, `D`, `y`,
    pageup/pagedown.
  - §6 (safety): mention the new run-result modal.
  - §9 (troubleshooting): add rows for "favorites file corrupt",
    "headless system, no clipboard".
- `PLAN.md` (this file): mark items as ✅ as they're completed; the file
  itself is the change history of the plan.

---

## Execution order recommendation

1. **Session 1:** items 3 + 4 + 11 (small, immediate UX). Tag `v0.2.0`.
2. **Session 2:** items 1 + 2 (copy + substitute — the biggest leverage).
   Tag `v0.3.0`.
3. **Session 3:** items 6 + 7 + 8 (panel polish).
4. **Session 4:** items 9 + 13 + 14 (search/explain quality).
5. **Session 5:** items 5 + 10 + 12 + 15 (workflow extras + counts/badges).
   Tag `v0.4.0`.

Each session leaves `pytest` green and ships a tagged release on `main`.
