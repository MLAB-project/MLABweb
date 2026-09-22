# Module quality mark — rubric

Implements MLABweb issue [#47](https://github.com/MLAB-project/MLABweb/issues/47):
give every module in [mlab-modules](https://github.com/mlab-modules) an
automatically-judged `mark` (0–100) in `doc/metadata.yaml`, so modules can be
triaged into: **list for sale now** / **fix, then list** / **not a listing
candidate** (draft, replaced, old).

## Why this matters downstream (not just a number)

`mark` already drives real behaviour in MLABweb, so the score has to mean
something, not just look plausible:

- `sitemap.xml` uses `mark/100.0` as the page's search-engine priority
  (`handlers/admin.py:83,98`).
- The homepage only features a module when `status == 2` (Produkce) **and**
  `mark >= 55`, and only if it has a real `image_title` that isn't a QR code
  placeholder (`handlers/admin.py:140-146`).
- `status` (`Návrh`/`V přípravě`/`Produkce`/`Nahrazen`/`Starý` = draft / in
  prep / production / replaced / old) already encodes lifecycle. Quality
  scoring is orthogonal to it: a `Produkce` module can still have terrible
  photos, and a `Starý` module isn't a listing candidate no matter how good
  its score is.
- Every unassessed module currently sits at the default sentinel `mark: 50`
  (`git_to_mongo.py:169,195`), which is indistinguishable from "someone
  looked and scored it 50". The tooling must not perpetuate that ambiguity
  (see "Sentinel/provenance" below).

## Score components

Final `mark` = weighted average of three 0–100 sub-scores, each with its own
weight because they answer different questions for the triage decision:

| Component | Weight | What it answers |
|---|---|---|
| **Photos** | 40% | Can a buyer tell what they're getting? |
| **Description** | 35% | Does the README explain what it does, how to use it, and why? |
| **Consistency** | 25% | Does the text match what's actually in the images/BOM/repo? |

Consistency is weighted lowest on its own but acts as a **cap**, not just an
input: a module whose description contradicts its photos (wrong part shown,
claims a feature the photographed revision doesn't have) is a mislisting
risk, worse than a module that's merely thin. So:

```
mark = round(0.40*photos + 0.35*description + 0.25*consistency)
if consistency < 30:
    mark = min(mark, 40)   # hard cap: don't let good photos/text hide a mismatch
```

### 1. Photos (0–100)

Split into deterministic sub-metrics (computed locally, no model needed) and
one judged sub-metric:

- **Presence/count** (deterministic): 0 images → 0. 1 image → cap at 40. 2–3
  → cap at 70. 4+ with both a top and bottom/angle view → no cap.
- **Resolution** (deterministic): flag anything below ~400px on the short
  side; such images cap at 50 regardless of content.
- **Sharpness** (deterministic): Laplacian-variance blur estimate on each
  raster image (PNG/JPG only — SVG/rendered CAD exports are exempt, see
  below). Below-threshold images cap their own contribution at 40.
- **Appearance / usefulness** (judged): does the photo actually show the
  module (not just a QR code or a schematic snippet used as `image_title`)?
  Is it a clean, well-lit product photo *or* a clean 3D/CAD render — both are
  acceptable "photos" for this rubric; a blurry phone snapshot on a cluttered
  desk is not. `image_title` pointing at a QR code image is an automatic
  fail on this sub-metric (it also breaks the homepage feature condition
  directly).

Renders vs. photos: the issue text explicitly lists "render" as an accepted
form of product image. Don't penalize a clean KiCad 3D render or generated
top/bottom PNG for "not being a real photo" — score it on the same
sharp/legible/shows-the-actual-board criteria.

### 2. Description (0–100)

Primary source is `README.md`, not the one-line `description` field in
metadata.yaml (that field is a blurb, typically 17–300 chars across the
corpus and too short to judge on its own).

- **Length/depth** (deterministic, soft signal only): a 300-word README with
  features, pinout/connector info, and typical applications scores higher
  than a two-sentence stub — but length alone is not quality; a padded
  README should not outscore a crisp short one that actually answers "what
  is this, how do I use it."
- **Structure** (deterministic): presence of headings, a features/typical
  applications list, connector/pinout info, links to schematic/BOM.
- **Stylistics / clarity** (judged): readable English or Czech, no leftover
  templating (`{{...}}`), no unresolved TODOs, no raw LLM-artifact debris —
  watch for stray citation markers like `【9†tlv3604.pdf】` seen in some
  READMEs, which indicate an unedited AI draft.
- **Genuinely explains the module** (judged): a reader unfamiliar with the
  part should understand what it does and why they'd use it — not just a
  restated part number.

### 3. Consistency (0–100)

Judged, cross-referencing text against images/BOM:

- Do the photographed/rendered board and the described features match (chip
  names, connector types, channel counts)?
- Does `image_title` actually depict this module (not a placeholder, not a
  QR code, not a schematic-only crop)?
- Do component references in the text correspond to visible parts, where
  checkable?

Start at 100, subtract for each material mismatch found; a single
contradicted claim (e.g. text claims a feature not present on the board) is
significant (-30 to -50) because it's a buyer-trust issue, not cosmetic.

## Calibration anchors

These anchors were manually scored in-session (2026-09-21) by reading the
module's actual README + images, to give the LLM judging step fixed
reference points instead of drifting per-module. See
`quality_mark_calibration.json` for the full worked scores and reasoning.

## What this score is *not*

Calibrating against the 9 modules a human already hand-scored turned up one
important gap: this rubric only judges **presentation** quality (photos,
writing, text/image consistency). It cannot know that a module's core chip
is going end-of-life, that a revision has a known hardware bug, or that
stock is gone — things only visible from issue trackers, BOM sourcing, or
the maintainer's head.

Concrete example: `ISM03` scores ~84 on presentation alone (clean renders,
one of the best-written READMEs in the corpus, links to a real third-party
integration) — yet its human-set `mark` is 30, because the module's repo has
two open issues about its Si4463 chip going EOL and needing a firmware
patch. The automated score and the human score are both "right" — they're
answering different questions. See `quality_mark_calibration.json` for the
full worked comparison.

Practical consequence: **"sellable" needs presentation quality *and*
absence of a known sourcing/reliability blocker.** This tool only automates
the first. A module the tool scores high should still be checked against
its own open issues before being listed; the report should surface open
issue counts per module as a hint, not attempt to grade them.

## Sentinel / provenance

Never silently overwrite an unassessed module's `mark: 50` with another
opaque number. Every write from this tooling also sets:

```yaml
mark: 62
mark_assessed_at: '2026-09-21T00:00:00Z'
mark_source: llm-assisted   # vs '(unset)' for the pre-existing sentinel
```

so a future pass (or a human) can tell "computed" from "never looked at",
and so a module a human previously hand-scored (9 modules currently have
non-50 `mark` values) can be treated as reviewed rather than clobbered
without comment — the tool should report a diff against the human value
rather than silently overwrite it.

## Out of scope / explicit non-goals for the first pass

- `status` and `replaced` are lifecycle fields, not quality — this tool
  reads them for triage grouping but never writes them.
- No write-back happens without an explicit `--write` flag and human
  sign-off on the dry-run report first; the report (not the metadata write)
  is the primary deliverable of a run.
