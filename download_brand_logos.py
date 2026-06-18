#!/usr/bin/env python3
"""Download brand logo assets from the Brandfetch API.

For each brand it resolves a domain (or looks one up via the Brandfetch Search
API), pulls the brand's logo set from the Brand API, and saves every logo
variant -- logo / symbol / icon, light / dark theme, SVG / PNG / etc. -- into
./logos/<brand>/.

Setup
-----
    pip install requests python-dotenv

Provide credentials either as a .env file next to this script (see .env.example)::

    BRANDFETCH_API_KEY=...      # required; create one at brandfetch.com/developers
    BRANDFETCH_CLIENT_ID=...    # optional; only used for name->domain search fallback

or as plain environment variables (export BRANDFETCH_API_KEY=...). The .env file
is loaded automatically when python-dotenv is installed.

Choosing which brands to download
---------------------------------
Brands come from a text file (default: brands.txt next to this script), or from
command-line arguments which override the file. Copy brands.example.txt to
brands.txt to get started. Each non-empty, non-# line is one brand:

    apple.com                       # bare domain -> folder named "apple"
    Procter & Gamble = pg.com       # custom display name, exact domain
    Starbucks                       # bare name -> resolved via Search API

Usage
-----
    python download_brand_logos.py                       # read brands.txt
    python download_brand_logos.py --file mylist.txt     # read a specific file
    python download_brand_logos.py apple.com nike.com    # brands straight from the CLI
    python download_brand_logos.py "Coca-Cola = coca-cola.com"
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is optional; fall back to real env vars.
    load_dotenv = None

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "logos"
DEFAULT_BRANDS_FILE = SCRIPT_DIR / "brands.txt"
API_BASE = "https://api.brandfetch.io/v2"
TIMEOUT = 30

USAGE = (
    "Usage: python download_brand_logos.py [--file PATH] [BRAND ...]\n"
    "  With no arguments, reads brands from brands.txt next to the script.\n"
    "  A BRAND is a domain (apple.com), a 'Name = domain' pair, or a bare name.\n"
    "  Copy brands.example.txt to brands.txt to get started."
)


def slugify(value: str) -> str:
    """Filesystem-safe slug, e.g. 'Procter & Gamble' -> 'procter-gamble'."""
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "brand"


def parse_brand_entry(line: str) -> tuple[str, str]:
    """Turn one brands-file/CLI entry into a (display_name, hint) pair.

    hint is either a domain (contains a dot) or a name to search for.
    """
    if "=" in line:
        name, _, hint = line.partition("=")
        return name.strip(), hint.strip()
    line = line.strip()
    if "." in line:  # bare domain -> derive a tidy name from the first label
        return line.split("/")[0].split(".")[0], line
    return line, line  # bare name -> resolved via Search API


def load_brands(path: Path) -> dict[str, str]:
    """Read a brands file into an ordered {display_name: hint} mapping."""
    brands: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, hint = parse_brand_entry(line)
        if name:
            brands[name] = hint
    return brands


def search_domain(name: str, client_id: str) -> str | None:
    """Resolve a brand name to a domain via the Brandfetch Search API."""
    try:
        resp = requests.get(
            f"{API_BASE}/search/{name}",
            params={"c": client_id},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        results = resp.json()
    except requests.RequestException as exc:
        print(f"    ! search failed for {name!r}: {exc}")
        return None
    if results:
        domain = results[0].get("domain")
        print(f"    -> resolved {name!r} to {domain}")
        return domain
    print(f"    ! no search match for {name!r}")
    return None


def fetch_brand(domain: str, api_key: str) -> dict | None:
    """Fetch a brand record (including its logos) from the Brand API."""
    try:
        resp = requests.get(
            f"{API_BASE}/brands/{domain}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        print(f"    ! brand lookup failed for {domain} (HTTP {status})")
    except requests.RequestException as exc:
        print(f"    ! brand lookup failed for {domain}: {exc}")
    return None


def download_file(url: str, dest: Path) -> bool:
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"    ! could not download {url}: {exc}")
        return False
    dest.write_bytes(resp.content)
    return True


def save_logos(name: str, brand: dict) -> int:
    """Save every logo format for a brand. Returns the count of files written."""
    brand_dir = OUTPUT_DIR / slugify(name)
    brand_dir.mkdir(parents=True, exist_ok=True)

    saved = 0
    seen: dict[str, int] = {}
    for logo in brand.get("logos", []):
        kind = logo.get("type") or "logo"        # logo | symbol | icon | other
        theme = logo.get("theme") or "default"   # light | dark | default
        for fmt in logo.get("formats", []):
            url = fmt.get("src")
            if not url:
                continue
            ext = fmt.get("format") or url.rsplit(".", 1)[-1]
            stem = f"{slugify(name)}_{kind}_{theme}"
            # Disambiguate when several files share type+theme+format.
            key = f"{stem}.{ext}"
            seen[key] = seen.get(key, 0) + 1
            suffix = "" if seen[key] == 1 else f"-{seen[key]}"
            dest = brand_dir / f"{stem}{suffix}.{ext}"
            if download_file(url, dest):
                print(f"    + {dest.relative_to(OUTPUT_DIR.parent)}")
                saved += 1
    if not saved:
        print("    ! no logo assets returned")
    return saved


def resolve_targets(argv: list[str]) -> dict[str, str] | None:
    """Work out which brands to fetch from CLI args, or return None to abort."""
    brands_file = DEFAULT_BRANDS_FILE
    positional: list[str] = []

    it = iter(argv)
    for arg in it:
        if arg in ("-h", "--help"):
            print(USAGE)
            return None
        if arg in ("-f", "--file"):
            value = next(it, None)
            if value is None:
                print("Error: --file needs a path.", file=sys.stderr)
                return None
            brands_file = Path(value).expanduser()
        else:
            positional.append(arg)

    if positional:
        targets: dict[str, str] = {}
        for entry in positional:
            name, hint = parse_brand_entry(entry)
            if name:
                targets[name] = hint
        return targets

    if not brands_file.exists():
        print(
            f"Error: no brands file at {brands_file}.\n"
            "Copy brands.example.txt to brands.txt, or pass brands as arguments.\n\n"
            + USAGE,
            file=sys.stderr,
        )
        return None
    return load_brands(brands_file)


def main(argv: list[str]) -> int:
    if load_dotenv is not None:
        # Load a .env beside the script first, then any .env in the working dir.
        load_dotenv(SCRIPT_DIR / ".env")
        load_dotenv()

    api_key = os.environ.get("BRANDFETCH_API_KEY")
    if not api_key:
        hint = ""
        if load_dotenv is None:
            hint = " (or `pip install python-dotenv` to load it from a .env file)"
        print(
            "Error: set BRANDFETCH_API_KEY -- in a .env file or the environment"
            f"{hint}. Create a key at brandfetch.com/developers.",
            file=sys.stderr,
        )
        return 1
    client_id = os.environ.get("BRANDFETCH_CLIENT_ID")

    targets = resolve_targets(argv)
    if targets is None:
        return 1
    if not targets:
        print("No brands to download.", file=sys.stderr)
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    total_files = 0
    failed: list[str] = []

    for name, hint in targets.items():
        print(f"\n{name}")
        # A hint with a dot is treated as a domain; otherwise search for it.
        domain = hint if "." in hint else None
        if domain is None:
            if not client_id:
                print(f"    ! {hint!r} is not a domain and BRANDFETCH_CLIENT_ID is unset")
                failed.append(name)
                continue
            domain = search_domain(hint, client_id)
            if not domain:
                failed.append(name)
                continue

        brand = fetch_brand(domain, api_key)
        if brand is None:
            failed.append(name)
            continue
        count = save_logos(name, brand)
        total_files += count
        if count == 0:
            failed.append(name)

    print(f"\nDone: {total_files} file(s) into {OUTPUT_DIR}")
    if failed:
        print(f"No assets for: {', '.join(failed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
