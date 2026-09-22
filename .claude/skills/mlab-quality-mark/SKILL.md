---
name: mlab-quality-mark
description: Score MLAB module listing quality (photos/description/consistency) against the rubric in src/mlabtools/module_quality_rubric.md, implementing MLABweb issue #47. Use when the user asks to score module quality, assess/judge MLAB modules, fill in the quality mark, work on issue 47, or continue the module quality triage.
user-invocable: true
allowed-tools:
  - Read
  - Bash(python3 *)
  - Bash(cd *)
---

# /mlab-quality-mark — score MLAB module listing quality

Fills in the judged part of the module-quality rubric (photos appearance,
description stylistics, text/image consistency) for modules in the
`mlab-modules` org, using **your own** multimodal reading — not an API
call. This exists specifically because the user's Claude access is through
Claude Code, with no separate `ANTHROPIC_API_KEY` to call the Anthropic API
directly (see `src/mlabtools/assess_module_quality.py score`, which does
the same job the API way for anyone who does have a key — both paths
produce the identical `<name>.score.json` schema, so `report` works either
way).

**Read the rubric and calibration before scoring anything, every time you
run this skill** — don't rely on remembering it from a previous run:

```bash
cat src/mlabtools/module_quality_rubric.md
cat src/mlabtools/quality_mark_calibration.json
```

The rubric explains *why* the weights are what they are (photos 40% /
description 35% / consistency 25%, hard cap when consistency < 30) and what
"good" looks like for renders vs. photos. The calibration file has 8 real
worked examples spanning the range (0 to 91) — use them as your anchors so
scores stay comparable across modules instead of drifting. Pay particular
attention to the calibration file's `caveat`: this rubric only judges
*presentation* quality, never penalize or reward based on guesses about
component sourcing/reliability you can't actually verify from the README
and image in front of you.

## Workflow

**0. Make sure the cache is populated.** If `.quality_cache/` doesn't exist
or `.quality_cache/modules.json` is missing, the discover+fetch steps
haven't run yet — tell the user and stop; those need a `GITHUB_TOKEN` and
are a different step (`assess_module_quality.py discover` then `fetch`),
not part of this skill.

**1. Check progress and pick a batch:**

```bash
python3 src/mlabtools/assess_module_quality.py progress --limit 20
```

This prints how many of the ~298 modules are already scored and lists the
next unscored ones. Work through **one batch of ~20 per invocation** — this
keeps a single run to a reasonable size. Tell the user up front roughly how
many you're about to do, and that they can re-invoke this skill (or `/loop`
it) to keep working through the backlog; you are not expected to finish
all ~298 in one run.

**2. For each module in the batch:**

a. Pull its text bundle (metadata, README, deterministic signals — this
   deliberately never includes the raw image bytes, so it stays small):

   ```bash
   python3 src/mlabtools/assess_module_quality.py show --name <MODULE>
   ```

b. Decide whether you need to look at the image at all:
   - If `deterministic.is_qr_code_image` is `true`, or `has_image` is
     `false`: **photos = 0** automatically, per the rubric. Don't bother
     extracting/viewing the image.
   - Otherwise, extract it to a real file and view it:

     ```bash
     python3 src/mlabtools/assess_module_quality.py extract-image --name <MODULE>
     ```
     This prints a file path (or `UNVIEWABLE_FORMAT:svg` if the title
     image is a vector format Read can't rasterize — in that case score
     photos from the deterministic signals + description alone, note it in
     `reasoning`, don't guess at appearance). If it printed a path, `Read`
     that path to actually view the image before scoring photos/consistency.

c. Score the three sub-metrics per the rubric (0–100 each), using the
   README text from step (a) for description, and the image (if viewed)
   plus the README for photos/consistency. Write one or two sentences of
   `reasoning` — cite the specific thing that drove the score, the same
   way the calibration file does. Add short `flags` tags where they apply
   (e.g. `qr-code-only-image`, `ai-draft-artifact`, `thin-readme`,
   `render-hides-product`, `stock-photo-background` — free-form, keep them
   short and reuse ones you've already used this batch where they fit).

d. Persist it (this validates the 0–100 range and the module actually
   has a cached bundle, so a typo can't silently write garbage):

   ```bash
   python3 src/mlabtools/assess_module_quality.py record-score \
     --name <MODULE> --photos <N> --description <N> --consistency <N> \
     --reasoning "<one or two sentences>" --flags "<tag1,tag2>"
   ```

**3. After the batch, report back to the user:** how many you scored, the
new total (`progress` again), and anything that stood out (a module that
looks like a clear "list now", or a pattern across several modules worth
flagging separately, e.g. a batch of modules sharing the same stale README
template). Don't run `report` or `write-back` yourself — those are the
user's explicit next steps once they're ready to see numbers or write
back to GitHub, not something this skill does automatically.

## What NOT to do

- Don't rate a module on sourcing/reliability/EOL risk you can't see in the
  README or image — that's explicitly out of scope (see the calibration
  file's caveat). If something in the README *does* mention a real problem
  (e.g. "chip discontinued", an inline warning), that's fair game for the
  consistency/description score since it's visible in the text itself.
- Don't skip straight to a number without reading the actual image for
  non-QR/non-missing cases — the whole point of this skill over a purely
  deterministic script is judgment on appearance and consistency.
- Don't re-score a module that already has a `<name>.score.json` unless
  the user explicitly asks you to re-check it (e.g. after a README/photo
  update) — `progress` already filters these out for you.
- Don't spawn subagents for this — read and score modules yourself, in the
  main loop, one at a time. That's what keeps this resumable/simple.
