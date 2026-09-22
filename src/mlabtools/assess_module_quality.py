#!/usr/bin/env python3
"""
Fill in the "mark" quality field for every module in the mlab-modules org.

Implements MLABweb issue #47: https://github.com/MLAB-project/MLABweb/issues/47
Rubric: see module_quality_rubric.md (same directory) — read that first, it
explains *why* the score is built this way, not just what fields it reads.
Calibration anchors used to steer the LLM prompt: quality_mark_calibration.json.

This intentionally follows the same conventions as the sibling
update_github_*.py scripts in this directory: plain `requests` against the
GitHub Contents API, a GitHub token on the command line / in GITHUB_TOKEN,
metadata.yaml round-tripped through yaml.safe_load/safe_dump.

USAGE
-----
All commands default --cache-dir to <repo root>/.quality_cache (gitignored
- see .gitignore) regardless of your current directory, so plain `--out`/
`--cache-dir`-less invocations below just work from anywhere in the repo.

  # 1. Discover every repo in the org that actually has doc/metadata.yaml.
  #    (GitHub code search under-reports badly for this org — confirmed by
  #    hand: it found 89 of the real 299 modules. Don't use search; this
  #    scans the whole org and HEAD-checks each repo, ~325 API calls.)
  python3 assess_module_quality.py discover --token $GITHUB_TOKEN \
      --out modules.json

  # 2. Fetch metadata.yaml + README.md + title image + deterministic
  #    metrics for every discovered module, cached to disk so re-runs are
  #    cheap and the LLM step can be retried without re-hitting GitHub.
  python3 assess_module_quality.py fetch --token $GITHUB_TOKEN \
      --modules modules.json

  # 3. Score every cached module with an LLM judging the rubric's
  #    "appearance", "stylistics" and "consistency" sub-metrics.
  #    Requires ANTHROPIC_API_KEY. Deterministic sub-metrics (image count/
  #    resolution/blur, description length/structure) don't need this step
  #    at all — `report` will emit them even with no key configured, just
  #    with the judged sub-scores left null.
  #    NOTE: if you don't have an ANTHROPIC_API_KEY (e.g. Claude Code
  #    subscription with no separate API access), use the
  #    `mlab-quality-mark` Claude Code skill instead — it does this step
  #    via Claude Code's own multimodal reading, writing the exact same
  #    <name>.score.json files this command would, so `report` below
  #    works identically either way.
  ANTHROPIC_API_KEY=... python3 assess_module_quality.py score

  # 4. Emit the triage report (this is the actual deliverable — read this,
  #    not the metadata write, to decide what to fix vs. list).
  python3 assess_module_quality.py report \
      --out-csv report.csv --out-md report.md

  # 5. Only after reviewing the report: write the computed `mark` back.
  #    Dry-run by default; --write actually PUTs. Never overwrites a
  #    module a human already hand-scored (mark not in {0, 50, absent}) —
  #    those are reported as a diff instead, use --force-overwrite-human
  #    to override deliberately for a specific run.
  python3 assess_module_quality.py write-back --token $GITHUB_TOKEN --write
"""

import argparse
import base64
import io
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests
import yaml

try:
    import numpy as np
    from PIL import Image
    HAVE_IMAGING = True
except ImportError:
    HAVE_IMAGING = False

ORG = "mlab-modules"
API = "https://api.github.com"
RUBRIC_PATH = os.path.join(os.path.dirname(__file__), "module_quality_rubric.md")
CALIBRATION_PATH = os.path.join(os.path.dirname(__file__), "quality_mark_calibration.json")
# src/mlabtools/assess_module_quality.py -> repo root is two levels up.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
QUALITY_CACHE_DEFAULT = os.path.join(REPO_ROOT, ".quality_cache")

# Repos that are org infrastructure, not modules — never treated as one
# even if they happen to grow a doc/metadata.yaml some day.
SKIP_REPOS = {".github", "MODUL01"}


def gh_headers(token):
    h = {"Accept": "application/vnd.github.v3+json"}
    if token:
        h["Authorization"] = f"token {token}"
    return h


# --------------------------------------------------------------------------
# 1. discover
# --------------------------------------------------------------------------

def list_org_repos(token):
    repos = []
    page = 1
    while True:
        r = requests.get(
            f"{API}/orgs/{ORG}/repos",
            headers=gh_headers(token),
            params={"per_page": 100, "page": page, "type": "public"},
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos


def has_metadata_yaml(token, repo_name):
    r = requests.get(
        f"{API}/repos/{ORG}/{repo_name}/contents/doc/metadata.yaml",
        headers=gh_headers(token),
    )
    return r.status_code == 200


def cmd_discover(args):
    token = args.token
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    print(f"Listing all repos in org {ORG}...", file=sys.stderr)
    repos = list_org_repos(token)
    print(f"  {len(repos)} repos total", file=sys.stderr)

    modules = []
    no_metadata = []
    for i, repo in enumerate(repos):
        name = repo["name"]
        if name in SKIP_REPOS:
            continue
        if repo.get("archived"):
            continue
        ok = has_metadata_yaml(token, name)
        print(f"  [{i+1}/{len(repos)}] {name}: {'module' if ok else 'no metadata.yaml'}", file=sys.stderr)
        if ok:
            modules.append({
                "name": name,
                "default_branch": repo["default_branch"],
                "pushed_at": repo.get("pushed_at"),
            })
        else:
            no_metadata.append(name)

    json.dump(modules, open(args.out, "w"), indent=2)
    json.dump(no_metadata, open(args.out.replace(".json", ".no_metadata.json"), "w"), indent=2)
    print(f"Discovered {len(modules)} modules with doc/metadata.yaml.", file=sys.stderr)
    print(f"{len(no_metadata)} repos have NO doc/metadata.yaml at all — these can't be "
          f"scored until that file exists; see {args.out.replace('.json', '.no_metadata.json')}.",
          file=sys.stderr)


# --------------------------------------------------------------------------
# 2. fetch
# --------------------------------------------------------------------------

def get_file(token, repo, path):
    r = requests.get(f"{API}/repos/{ORG}/{repo}/contents/{path}", headers=gh_headers(token))
    if r.status_code != 200:
        return None, None
    d = r.json()
    content = base64.b64decode(d["content"])
    return content, d["sha"]


def get_open_issue_count(token, repo):
    r = requests.get(
        f"{API}/repos/{ORG}/{repo}",
        headers=gh_headers(token),
    )
    if r.status_code != 200:
        return None
    return r.json().get("open_issues_count")


def blur_variance(image_bytes):
    """Laplacian-variance sharpness estimate. Lower = blurrier.
    Only meaningful for raster photos; SVG/vector renders should be
    exempted by the caller (rasterizing an SVG tells you nothing about
    the original photo/render's actual sharpness)."""
    if not HAVE_IMAGING:
        return None
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("L")
        arr = np.asarray(img, dtype=np.float64)
        # simple discrete Laplacian kernel via finite differences
        lap = (
            -4 * arr
            + np.roll(arr, 1, axis=0) + np.roll(arr, -1, axis=0)
            + np.roll(arr, 1, axis=1) + np.roll(arr, -1, axis=1)
        )
        return float(lap.var())
    except Exception:
        return None


def image_resolution(image_bytes):
    if not HAVE_IMAGING:
        return None
    try:
        img = Image.open(io.BytesIO(image_bytes))
        return img.size  # (w, h)
    except Exception:
        return None


def cmd_fetch(args):
    token = args.token
    modules = json.load(open(args.modules))
    os.makedirs(args.cache_dir, exist_ok=True)

    for i, mod in enumerate(modules):
        name = mod["name"]
        out_path = os.path.join(args.cache_dir, f"{name}.json")
        if os.path.exists(out_path) and not args.refetch:
            print(f"  [{i+1}/{len(modules)}] {name}: cached, skip", file=sys.stderr)
            continue

        print(f"  [{i+1}/{len(modules)}] {name}: fetching...", file=sys.stderr)
        meta_bytes, meta_sha = get_file(token, name, "doc/metadata.yaml")
        if meta_bytes is None:
            print(f"    WARNING: lost doc/metadata.yaml since discover, skipping", file=sys.stderr)
            continue
        meta = yaml.safe_load(meta_bytes)

        readme_bytes, _ = get_file(token, name, "README.md")
        readme_text = readme_bytes.decode("utf-8", errors="replace") if readme_bytes else ""

        img_path = (meta.get("image_title") or (meta.get("images") or [None])[0] or "").lstrip("/")
        img_bytes = None
        img_b64 = None
        if img_path:
            branch = meta.get("github_branch") or mod["default_branch"]
            img_url = f"https://raw.githubusercontent.com/{ORG}/{name}/{branch}/{img_path}"
            r = requests.get(img_url)
            if r.status_code == 200:
                img_bytes = r.content
                img_b64 = base64.b64encode(img_bytes).decode("ascii")

        is_raster = img_path.lower().endswith((".png", ".jpg", ".jpeg"))
        record = {
            "name": name,
            "metadata": meta,
            "metadata_sha": meta_sha,
            "default_branch": mod["default_branch"],
            "readme": readme_text,
            "image_path": img_path,
            "image_b64": img_b64,
            "image_is_raster": is_raster,
            "open_issues_count": get_open_issue_count(token, name),
            "deterministic": {
                "image_count": len(meta.get("images") or []),
                "description_len": len(meta.get("description") or ""),
                "readme_len": len(readme_text),
                "resolution": image_resolution(img_bytes) if img_bytes else None,
                "blur_variance": blur_variance(img_bytes) if (img_bytes and is_raster) else None,
                "is_qr_code_image": "qrcode" in img_path.lower(),
            },
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        json.dump(record, open(out_path, "w"), indent=2)
        time.sleep(0.1)  # be polite to raw.githubusercontent.com

    print(f"Done. Cache at {args.cache_dir}", file=sys.stderr)



# Non-module files that can live in the same cache dir (discover's output) -
# never mistaken for a per-module <name>.json bundle.
NON_MODULE_CACHE_FILES = {"modules.json", "modules.no_metadata.json"}


def list_module_bundle_files(cache_dir):
    return sorted(
        f for f in os.listdir(cache_dir)
        if f.endswith(".json")
        and not f.endswith(".score.json")
        and f not in NON_MODULE_CACHE_FILES
    )


# --------------------------------------------------------------------------
# 3. score (LLM judgment — needs ANTHROPIC_API_KEY)
# --------------------------------------------------------------------------

SCORE_PROMPT_TEMPLATE = """\
You are scoring one hardware module's listing quality for MLAB, an open
hardware module catalog. Follow this rubric exactly:

{rubric}

Calibration anchors (already-scored real examples, use these to calibrate
your scale — do not just default to the middle):

{anchors}

Now score this module. Its title image is attached (if present).

Module: {name}
Description (short blurb): {description}
README.md:
---
{readme}
---
Deterministic signals already computed (you don't need to re-derive these,
factor them in): {deterministic}

Respond with ONLY a JSON object, no prose, no markdown fences:
{{
  "photos": <0-100 int>,
  "description": <0-100 int>,
  "consistency": <0-100 int>,
  "reasoning": "<one or two sentences citing the specific thing that drove the score>",
  "flags": ["<short tags like 'qr-code-only-image', 'ai-draft-artifact', 'thin-readme', 'render-hides-product'>"]
}}
"""


def call_anthropic(api_key, prompt, image_b64, image_media_type):
    content = [{"type": "text", "text": prompt}]
    if image_b64:
        content.insert(0, {
            "type": "image",
            "source": {"type": "base64", "media_type": image_media_type, "data": image_b64},
        })
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": content}],
        },
        timeout=60,
    )
    r.raise_for_status()
    text = r.json()["content"][0]["text"]
    return json.loads(text)


def media_type_for(path):
    ext = path.lower().rsplit(".", 1)[-1]
    return {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "gif": "image/gif", "webp": "image/webp"}.get(ext)


def cmd_score(args):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set — cannot run the judged sub-scores.\n"
              "`report` still works without this step: it will just leave "
              "photos/description/consistency null and show only the "
              "deterministic signals for triage.", file=sys.stderr)
        return 1

    rubric = open(RUBRIC_PATH).read()
    calibration = json.load(open(CALIBRATION_PATH))
    anchors_text = json.dumps(calibration["anchors"], indent=2) + "\n\nCaveat: " + calibration["caveat"]

    files = list_module_bundle_files(args.cache_dir)
    for i, fn in enumerate(files):
        name = fn[:-5]
        score_path = os.path.join(args.cache_dir, f"{name}.score.json")
        if os.path.exists(score_path) and not args.rescore:
            print(f"  [{i+1}/{len(files)}] {name}: already scored, skip", file=sys.stderr)
            continue

        record = json.load(open(os.path.join(args.cache_dir, fn)))
        meta = record["metadata"]
        prompt = SCORE_PROMPT_TEMPLATE.format(
            rubric=rubric,
            anchors=anchors_text,
            name=name,
            description=meta.get("description", ""),
            readme=record["readme"][:6000],
            deterministic=json.dumps(record["deterministic"]),
        )
        media_type = media_type_for(record["image_path"]) if record.get("image_b64") else None
        try:
            print(f"  [{i+1}/{len(files)}] {name}: scoring...", file=sys.stderr)
            result = call_anthropic(api_key, prompt, record.get("image_b64") if media_type else None, media_type)
            json.dump(result, open(score_path, "w"), indent=2)
        except Exception as e:
            print(f"    FAILED: {e}", file=sys.stderr)
        time.sleep(1)  # crude rate limiting


# --------------------------------------------------------------------------
# 3b. skill-facing helpers: show / extract-image / record-score / progress
#
# These exist so the mlab-quality-mark Claude Code skill (used when no
# ANTHROPIC_API_KEY is available -- see cmd_score above) has clean, safe
# primitives instead of ad-hoc inline Python in the skill's instructions.
# `show` never dumps image_b64 to stdout -- that field is only ever a few
# hundred KB to 1MB+ of base64, and printing it would blow the judging
# model's context for no benefit (it can't "see" base64 text; it needs an
# actual image file via extract-image + Read).
# --------------------------------------------------------------------------

def cmd_show(args):
    record = json.load(open(os.path.join(args.cache_dir, f"{args.name}.json")))
    meta = dict(record["metadata"])
    print(json.dumps({
        "name": record["name"],
        "metadata": meta,
        "readme": record["readme"][:6000],
        "image_path": record["image_path"],
        "has_image": bool(record.get("image_b64")),
        "open_issues_count": record.get("open_issues_count"),
        "deterministic": record["deterministic"],
    }, indent=2, ensure_ascii=False))


def cmd_extract_image(args):
    record = json.load(open(os.path.join(args.cache_dir, f"{args.name}.json")))
    if record["deterministic"].get("is_qr_code_image"):
        print("QR_CODE_ONLY")
        return
    if not record.get("image_b64"):
        print("NO_IMAGE")
        return
    ext = (record["image_path"].rsplit(".", 1)[-1] if "." in record["image_path"] else "png").lower()
    if ext not in ("png", "jpg", "jpeg", "gif", "webp"):
        # SVG or something Read can't render as an image -- nothing to view.
        print("UNVIEWABLE_FORMAT:" + ext)
        return
    out_path = args.out or os.path.join(args.cache_dir, f"{args.name}.title.{ext}")
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(record["image_b64"]))
    print(out_path)


def cmd_record_score(args):
    for field_name, value in (("photos", args.photos), ("description", args.description), ("consistency", args.consistency)):
        if not (0 <= value <= 100):
            print(f"REJECTED: {field_name}={value} out of range 0-100", file=sys.stderr)
            sys.exit(1)
    bundle_path = os.path.join(args.cache_dir, f"{args.name}.json")
    if not os.path.exists(bundle_path):
        print(f"REJECTED: no cached bundle for {args.name} -- run `fetch` first", file=sys.stderr)
        sys.exit(1)
    score = {
        "photos": args.photos,
        "description": args.description,
        "consistency": args.consistency,
        "reasoning": args.reasoning,
        "flags": [f.strip() for f in (args.flags or "").split(",") if f.strip()],
    }
    score_path = os.path.join(args.cache_dir, f"{args.name}.score.json")
    json.dump(score, open(score_path, "w"), indent=2, ensure_ascii=False)
    # compute_mark() is defined later in this file (section 4) -- fine to
    # call here since Python resolves the name at call time, not def time.
    print(f"WROTE {score_path}: mark={compute_mark(score)}")


def cmd_progress(args):
    files = list_module_bundle_files(args.cache_dir)
    all_names = [f[:-5] for f in files]
    unscored = [n for n in all_names if not os.path.exists(
        os.path.join(args.cache_dir, n + ".score.json"))]

    skipped_human = 0
    if not args.include_human_scored:
        kept = []
        for name in unscored:
            record = json.load(open(os.path.join(args.cache_dir, name + ".json")))
            existing_mark = record["metadata"].get("mark")
            if existing_mark not in (None, 50):
                skipped_human += 1
            else:
                kept.append(name)
        unscored = kept

    print(f"{len(all_names) - len(unscored) - skipped_human}/{len(all_names)} modules scored.")
    if skipped_human:
        print(f"({skipped_human} more already have a human-set mark and are left alone by default "
              f"-- pass --include-human-scored to judge them anyway, e.g. to cross-check.)")
    if unscored:
        n = args.limit or 20
        print(f"Next {min(n, len(unscored))} unscored modules:")
        for name in unscored[:n]:
            print(f"  {name}")
    else:
        print("Nothing left to score" + ("" if args.include_human_scored else " (excluding human-scored)") + ".")


# --------------------------------------------------------------------------
# 4. report + mark computation
# --------------------------------------------------------------------------

def compute_mark(judged):
    photos = judged["photos"]
    description = judged["description"]
    consistency = judged["consistency"]
    mark = round(0.40 * photos + 0.35 * description + 0.25 * consistency)
    if consistency < 30:
        mark = min(mark, 40)
    return max(0, min(100, mark))


STATUS_NAMES = {0: "Návrh", 1: "V přípravě", 2: "Produkce", 3: "Nahrazen", 4: "Starý"}


def cmd_report(args):
    files = list_module_bundle_files(args.cache_dir)
    rows = []
    for fn in files:
        name = fn[:-5]
        record = json.load(open(os.path.join(args.cache_dir, fn)))
        meta = record["metadata"]
        score_path = os.path.join(args.cache_dir, f"{name}.score.json")
        judged = json.load(open(score_path)) if os.path.exists(score_path) else None

        computed_mark = compute_mark(judged) if judged else None
        existing_mark = meta.get("mark")
        # metadata.yaml has no way to distinguish "never assessed" from
        # "a human set it to exactly 50" -- treat 50 as the sentinel per
        # git_to_mongo.py's own default. mark=0 IS treated as human-scored
        # (a human can deliberately zero it via the admin edit form).
        is_human_scored = existing_mark not in (None, 50)
        status = meta.get("status")

        if status in (3, 4):
            recommendation = "not a listing candidate (replaced/old)"
        elif status in (0, 1):
            recommendation = "not yet released (draft/in prep)"
        elif computed_mark is None:
            recommendation = "needs LLM scoring pass"
        elif computed_mark >= 70:
            recommendation = "list now"
        elif computed_mark >= 45:
            recommendation = "fix, then list"
        else:
            recommendation = "needs significant rework"

        rows.append({
            "name": name,
            "status": STATUS_NAMES.get(status, status),
            "existing_mark": existing_mark,
            "human_scored": is_human_scored,
            "computed_mark": computed_mark,
            "photos": judged["photos"] if judged else None,
            "description": judged["description"] if judged else None,
            "consistency": judged["consistency"] if judged else None,
            "flags": ",".join(judged.get("flags", [])) if judged else "",
            "reasoning": judged.get("reasoning", "") if judged else "",
            "open_issues": record.get("open_issues_count"),
            "image_count": record["deterministic"]["image_count"],
            "readme_len": record["deterministic"]["readme_len"],
            "recommendation": recommendation,
        })

    if args.out_csv:
        import csv
        with open(args.out_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
            w.writeheader()
            w.writerows(rows)
        print(f"Wrote {args.out_csv}", file=sys.stderr)

    if args.out_md:
        with open(args.out_md, "w") as f:
            f.write("# Module quality triage report\n\n")
            f.write(f"Generated {datetime.now(timezone.utc).isoformat()}. "
                    f"{len(rows)} modules assessed.\n\n")
            for rec in ("list now", "fix, then list", "needs significant rework",
                        "needs LLM scoring pass", "not yet released (draft/in prep)",
                        "not a listing candidate (replaced/old)"):
                group = [r for r in rows if r["recommendation"] == rec]
                if not group:
                    continue
                f.write(f"## {rec} ({len(group)})\n\n")
                f.write("| Module | Mark | Photos | Desc | Consistency | Issues | Flags |\n")
                f.write("|---|---|---|---|---|---|---|\n")
                for r in sorted(group, key=lambda x: (x["computed_mark"] or -1)):
                    f.write(f"| {r['name']} | {r['computed_mark']} | {r['photos']} | "
                            f"{r['description']} | {r['consistency']} | {r['open_issues']} | "
                            f"{r['flags']} |\n")
                f.write("\n")
        print(f"Wrote {args.out_md}", file=sys.stderr)

    return rows


# --------------------------------------------------------------------------
# 5. write-back
# --------------------------------------------------------------------------

def cmd_write_back(args):
    token = args.token
    rows = cmd_report(argparse.Namespace(cache_dir=args.cache_dir, out_csv=None, out_md=None))
    for row in rows:
        name = row["name"]
        if row["computed_mark"] is None:
            continue
        if row["human_scored"] and not args.force_overwrite_human:
            print(f"SKIP {name}: human-set mark={row['existing_mark']} vs computed={row['computed_mark']} "
                  f"— not overwriting (use --force-overwrite-human to override)")
            continue
        if not args.write:
            print(f"DRY-RUN {name}: would set mark={row['computed_mark']} "
                  f"(was {row['existing_mark']})")
            continue

        record = json.load(open(os.path.join(args.cache_dir, f"{name}.json")))
        meta_bytes, sha = get_file(token, name, "doc/metadata.yaml")
        meta = yaml.safe_load(meta_bytes)
        meta["mark"] = row["computed_mark"]
        meta["mark_source"] = "llm-assisted"
        meta["mark_assessed_at"] = datetime.now(timezone.utc).isoformat()
        updated = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False)
        r = requests.put(
            f"{API}/repos/{ORG}/{name}/contents/doc/metadata.yaml",
            headers=gh_headers(token),
            json={
                "message": "Set automated quality mark (issue MLAB-project/MLABweb#47)",
                "content": base64.b64encode(updated.encode("utf-8")).decode("ascii"),
                "sha": sha,
                "branch": record["default_branch"],
            },
        )
        if r.status_code == 200:
            print(f"WROTE {name}: mark={row['computed_mark']}")
        else:
            print(f"FAILED {name}: {r.status_code} {r.text[:200]}")
        time.sleep(0.5)


# --------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("discover")
    d.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))
    d.add_argument("--out", default=os.path.join(QUALITY_CACHE_DEFAULT, "modules.json"))
    d.set_defaults(func=cmd_discover)

    f = sub.add_parser("fetch")
    f.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))
    f.add_argument("--modules", default=os.path.join(QUALITY_CACHE_DEFAULT, "modules.json"))
    f.add_argument("--cache-dir", default=QUALITY_CACHE_DEFAULT)
    f.add_argument("--refetch", action="store_true")
    f.set_defaults(func=cmd_fetch)

    s = sub.add_parser("score")
    s.add_argument("--cache-dir", default=QUALITY_CACHE_DEFAULT)
    s.add_argument("--rescore", action="store_true")
    s.set_defaults(func=cmd_score)

    r = sub.add_parser("report")
    r.add_argument("--cache-dir", default=QUALITY_CACHE_DEFAULT)
    r.add_argument("--out-csv", default=os.path.join(QUALITY_CACHE_DEFAULT, "report.csv"))
    r.add_argument("--out-md", default=os.path.join(QUALITY_CACHE_DEFAULT, "report.md"))
    r.set_defaults(func=cmd_report)

    w = sub.add_parser("write-back")
    w.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))
    w.add_argument("--cache-dir", default=QUALITY_CACHE_DEFAULT)
    w.add_argument("--write", action="store_true", help="actually PUT; default is dry-run")
    w.add_argument("--force-overwrite-human", action="store_true")
    w.set_defaults(func=cmd_write_back)

    sh = sub.add_parser("show", help="print one module's text bundle (no image bytes) for the skill to read")
    sh.add_argument("--cache-dir", default=QUALITY_CACHE_DEFAULT)
    sh.add_argument("--name", required=True)
    sh.set_defaults(func=cmd_show)

    ei = sub.add_parser("extract-image", help="write one module's title image to a file so Read can view it")
    ei.add_argument("--cache-dir", default=QUALITY_CACHE_DEFAULT)
    ei.add_argument("--name", required=True)
    ei.add_argument("--out", default=None)
    ei.set_defaults(func=cmd_extract_image)

    rs = sub.add_parser("record-score", help="validate and persist one module's judged sub-scores")
    rs.add_argument("--cache-dir", default=QUALITY_CACHE_DEFAULT)
    rs.add_argument("--name", required=True)
    rs.add_argument("--photos", type=int, required=True)
    rs.add_argument("--description", type=int, required=True)
    rs.add_argument("--consistency", type=int, required=True)
    rs.add_argument("--reasoning", default="")
    rs.add_argument("--flags", default="", help="comma-separated short tags")
    rs.set_defaults(func=cmd_record_score)

    pg = sub.add_parser("progress", help="how many modules are scored, and what's next")
    pg.add_argument("--cache-dir", default=QUALITY_CACHE_DEFAULT)
    pg.add_argument("--limit", type=int, default=20)
    pg.add_argument("--include-human-scored", action="store_true",
                     help="also list modules that already have a human-set mark (skipped by default)")
    pg.set_defaults(func=cmd_progress)

    args = p.parse_args()
    if args.cmd in ("discover", "fetch", "write-back") and not args.token:
        print("Need a GitHub token: --token or $GITHUB_TOKEN", file=sys.stderr)
        sys.exit(1)
    result = args.func(args)
    # Only an explicit int return (e.g. cmd_score's "1" for "no API key") is
    # a real exit code. cmd_report returns its row list for reuse by
    # cmd_write_back -- sys.exit(a_list) would dump the whole thing to
    # stderr and exit 1, which is not an error, just Python's sys.exit()
    # behavior for a non-int/non-None argument.
    sys.exit(result if isinstance(result, int) else 0)


if __name__ == "__main__":
    main()
