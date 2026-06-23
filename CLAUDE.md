# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`download_brand_logos.py` is a single-file CLI that pulls every logo variant Brandfetch offers for a list of brands and writes them into `logos/<brand>/`. There is no package, build step, or test suite — it's one script plus the `requests` and (optional) `python-dotenv` libraries. Python 3.9+.

## Commands

```bash
# One-time setup
pip install requests python-dotenv     # python-dotenv is optional (see ".env loading" below)
cp .env.example .env                   # then add BRANDFETCH_API_KEY

# Run
python download_brand_logos.py                     # read brands.txt next to the script
python download_brand_logos.py --file mylist.txt   # read a specific file
python download_brand_logos.py apple.com nike.com  # brands from argv (these OVERRIDE the file)
python download_brand_logos.py "Coca-Cola = coca-cola.com"
python download_brand_logos.py --help
```

No linter, formatter, or test runner is configured — run the script directly to exercise changes.

## Architecture

A single linear pipeline in `download_brand_logos.py`, orchestrated by `main()`:

1. **Resolve targets** (`resolve_targets`) — builds an ordered `{display_name: hint}` map. CLI positional args, when present, *replace* the brands file entirely; otherwise it reads `--file` or the default `brands.txt`.
2. **Parse each entry** (`parse_brand_entry`) — `Name = domain` → exact domain with a custom folder name; a token containing `.` → bare domain (folder named from the first label); anything else → a name to search. Rule of thumb: a `hint` is treated as a domain iff it contains a dot.
3. **Resolve to a domain** — a dotted hint is used as-is; a bare name is sent through `search_domain` (Search API).
4. **Fetch the brand record** (`fetch_brand`) — Brand API; returns JSON containing a `logos` array.
5. **Save every variant** (`save_logos`) — iterates `logos[].formats[]`, writing `<slug>_<type>_<theme>.<ext>` into `logos/<slug>/`.

### Two credentials → two APIs

- `BRANDFETCH_API_KEY` (**required**) — Bearer auth for the Brand API (`/v2/brands/{domain}`).
- `BRANDFETCH_CLIENT_ID` (**optional**) — `c=` query param for the Search API (`/v2/search/{name}`), used *only* to resolve bare brand names. A bare name with no client ID is skipped with a warning; entries that already include a domain never need it.

### Conventions and behaviors that matter

- **Slugs** (`slugify`) lower-case and hyphenate names; the same slug names both the folder and the file stem, so `Procter & Gamble` → `logos/procter-gamble/procter-gamble_logo_dark.svg`.
- **Collision suffixes** — within one brand, files that share type+theme+format are disambiguated with `-2`, `-3`, … via the `seen` counter in `save_logos`.
- **Failure handling** — per-brand errors (network failure, unresolved name, no assets) print a `!` line and are collected into `failed`; the run never aborts for a single brand. The process exits `0` even when some brands fail — a non-zero exit is reserved for setup errors (missing API key, no targets, bad `--file`).
- **`.env` loading order** — loads `.env` beside the script first, then any `.env` in the working directory; if `python-dotenv` isn't installed it silently falls back to real environment variables.

### Local vs. committed files

`brands.txt` (your personal brand list) and `logos/` (downloaded assets) are git-ignored; `brands.example.txt` is the committed template. `.env*` is ignored except `.env.example`.

## Agent skills

### Issue tracker

Issues and PRDs live in this repo's GitHub Issues, managed via the `gh` CLI; external PRs are not treated as a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles map to identically-named GitHub labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
