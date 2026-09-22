# Module quality mark toolset

How to actually run the module-quality-mark tooling built for
[issue #47](https://github.com/MLAB-project/MLABweb/issues/47). This file
only covers that toolset (`assess_module_quality.py` +
`module_quality_rubric.md` + `quality_mark_calibration.json` + the
`mlab-quality-mark` skill) — it doesn't document the other, older scripts
in this directory (`update_github_*.py`, `generate.py`, `readme.py`, ...).

**Start here if you just want to know "what do I actually type":** jump to
[Day-to-day: scoring more modules](#day-to-day-scoring-more-modules) below.

## What this does

Fills in the `mark` field (0–100) in every `mlab-modules` repo's
`doc/metadata.yaml`, so modules can be triaged: list for sale now / fix
then list / not a listing candidate. The *why* and the actual scoring
rubric live in [`module_quality_rubric.md`](module_quality_rubric.md) —
read that once, you don't need to re-read it to use the tool day to day.

Two ways to get the judged part of the score (photo appearance/description
stylistics/consistency) filled in:

1. **The `mlab-quality-mark` Claude Code skill** (`.claude/skills/mlab-quality-mark/SKILL.md`)
   — Claude Code reads each module's README + photo itself and scores it.
   **Use this one if you don't have a separate `ANTHROPIC_API_KEY`** (e.g.
   a Claude Code subscription with no standalone API access — this is the
   normal case).
2. **`assess_module_quality.py score`** — calls the Anthropic API directly.
   Only works if `ANTHROPIC_API_KEY` is set in your environment.

Everything else (finding modules, downloading their data, building the
report, writing marks back to GitHub) is the same either way — one script,
`assess_module_quality.py`, run from anywhere inside this repo.

## One-time setup: populate the cache

Before any scoring can happen, the tool needs to know which repos are
modules and pull their data down. This needs a GitHub token (`gh auth
token` works fine if you're logged in with `gh`):

```bash
cd MLABweb   # anywhere inside the repo works; paths are resolved automatically
export GITHUB_TOKEN=$(gh auth token)

python3 src/mlabtools/assess_module_quality.py discover
python3 src/mlabtools/assess_module_quality.py fetch
```

- `discover` scans **every** repo in the `mlab-modules` org (not GitHub
  code search — it badly under-reports this org, ~89 vs. the real ~298) and
  finds the ones with `doc/metadata.yaml`. Takes a few minutes (~325 API
  calls). Writes `.quality_cache/modules.json` (the module list) and
  `.quality_cache/modules.no_metadata.json` (repos with no metadata file at
  all — these can't be scored until someone adds one; that's a separate,
  smaller follow-up, not this tool's job).
- `fetch` downloads each module's `metadata.yaml` + `README.md` + title
  image, and computes the deterministic metrics (image count/resolution/
  blur, README length) — no LLM needed for any of this. Also takes a few
  minutes.

Both are safe to re-run later (e.g. `fetch --refetch` to pick up README/
photo updates for modules already cached) — they don't touch GitHub beyond
reading.

Everything lands in `.quality_cache/` at the repo root. **This directory is
gitignored on purpose** — it's ~100MB+ of downloaded images and run output,
not source. It persists on disk across sessions (it's not a temp
directory), so you only need to do this setup step once per machine, and
re-run `fetch` occasionally to refresh stale data.

## Day-to-day: scoring more modules

Once the cache exists, this is the loop:

```
/mlab-quality-mark
```

Run this as a Claude Code slash command (it's a project skill, so it only
shows up when Claude Code is running inside this repo). Each invocation:

1. Re-reads the rubric and calibration examples (so it doesn't drift).
2. Picks up to ~20 modules that don't have a score yet (skips modules a
   human already hand-scored — those are left alone unless you ask
   otherwise).
3. For each one: looks at the title image (unless it's a QR-code
   placeholder or missing, in which case photos = 0 automatically — no
   need to spend a look on it) and the README, scores it against the
   rubric, and saves the result.
4. Tells you how many it did and what's left.

**Just keep re-invoking it** (or ask Claude to keep going, or `/loop` it)
until nothing's left. There are 298 modules total; as of this writing 27
are scored and ~256 remain (the other 15 already have a human-set mark and
are skipped by default). No need to do it all in one sitting — it's fully
resumable, nothing is lost between runs.

To check where things stand without scoring anything:

```bash
python3 src/mlabtools/assess_module_quality.py progress
```

## Getting the report

```bash
python3 src/mlabtools/assess_module_quality.py report
```

Writes `.quality_cache/report.csv` and `.quality_cache/report.md`. The
Markdown one is the readable version — modules grouped into:

- **list now** — mark ≥ 70
- **fix, then list** — mark 45–69
- **needs significant rework** — mark < 45
- **needs LLM scoring pass** — not scored yet
- **not yet released (draft/in prep)** — status is Návrh/V přípravě, not
  a listing question yet
- **not a listing candidate (replaced/old)** — status is Nahrazen/Starý

Re-run this any time — it's just reading the cache, takes a couple of
seconds, safe to run as often as you like to check progress.

**One thing the report can't tell you:** a high mark only means the
*listing* (photos + text) is good. It says nothing about whether the part
is still sourceable, in stock, or has a known hardware issue — check a
module's own GitHub issues for that (the report shows the open-issue count
as a hint). See the rubric's "what this score is not" section for the
concrete example that motivated this caveat.

## Writing marks back to GitHub

This is the only step that changes anything outside your machine — it
commits to up to ~298 public repos. **Review the report with a human
first.** Once you're ready:

```bash
export GITHUB_TOKEN=$(gh auth token)

# Always look at this before adding --write:
python3 src/mlabtools/assess_module_quality.py write-back

# Only once the dry-run output looks right:
python3 src/mlabtools/assess_module_quality.py write-back --write
```

Without `--write` it only prints what it *would* do — nothing is sent.
With `--write`, for each scored module it:

- Skips it entirely if a human already set a non-default `mark` (prints
  `SKIP <name>: human-set mark=... vs computed=...` so you can see the
  diff) — pass `--force-overwrite-human` to override this for a specific
  run, e.g. if you've decided the automated score should win.
- Otherwise commits `mark`, plus `mark_source: llm-assisted` and
  `mark_assessed_at: <timestamp>` alongside it, so it's always possible to
  tell "computed" apart from "a human looked at this" later.

You can run `write-back` again later for modules scored in a subsequent
batch — it only ever touches modules that have a `<name>.score.json` in
the cache and picks up where it left off.

## Where things live

| Path | What |
|---|---|
| `module_quality_rubric.md` | The rubric itself and why it's built this way — read once |
| `quality_mark_calibration.json` | 8 hand-scored reference examples, used to keep scores comparable |
| `assess_module_quality.py` | The CLI: `discover` / `fetch` / `score` / `report` / `write-back`, plus `show` / `extract-image` / `record-score` / `progress` (used internally by the skill) |
| `.claude/skills/mlab-quality-mark/SKILL.md` | The `/mlab-quality-mark` skill |
| `<repo root>/.quality_cache/` | Downloaded data + scores + reports (gitignored, regenerate anytime) |

Run `python3 src/mlabtools/assess_module_quality.py <command> --help` for
the full flag list on any command — defaults are sane (cache dir resolves
to `.quality_cache` at the repo root automatically, no matter where in the
repo you run it from).
