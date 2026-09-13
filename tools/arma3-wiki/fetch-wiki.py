#!/usr/bin/env python3
"""Fetch Arma 3 wiki pages for offline reference.

Usage:
    python3 fetch-wiki.py <command_name> [--output-dir <dir>]
    python3 fetch-wiki.py setTerrainHeight
    python3 fetch-wiki.py setTerrainHeight --output-dir ./cache

Fetches from:
1. BIKI (community.bistudio.com/wiki/) - full documentation
2. acemod/arma3-wiki (YAML format) - structured data
"""

import argparse
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path


BIKI_BASE = "https://community.bistudio.com/wiki/"
ARMA3_WIKI_BASE = "https://raw.githubusercontent.com/acemod/arma3-wiki/dist/commands/"


def fetch_biki_page(command_name: str) -> str | None:
    """Fetch wiki page from BIKI."""
    url = f"{BIKI_BASE}{command_name}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AEE-Reference/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"BIKI fetch failed for {command_name}: {e.code}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"BIKI fetch failed for {command_name}: {e}", file=sys.stderr)
        return None


def fetch_yaml_definition(command_name: str) -> str | None:
    """Fetch YAML definition from acemod/arma3-wiki."""
    url = f"{ARMA3_WIKI_BASE}{command_name.lower()}.yaml"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AEE-Reference/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError:
        # Try alternate casing
        url = f"{ARMA3_WIKI_BASE}{command_name}.yaml"
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "AEE-Reference/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.read().decode("utf-8")
        except Exception:
            return None
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Fetch Arma 3 wiki pages")
    parser.add_argument("command", help="Command or function name")
    parser.add_argument("--output-dir", "-o", default=".", help="Output directory")
    parser.add_argument("--yaml-only", action="store_true", help="Only fetch YAML")
    parser.add_argument("--biki-only", action="store_true", help="Only fetch BIKI page")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    command = args.command

    if not args.yaml_only:
        print(f"Fetching BIKI page for {command}...")
        biki_content = fetch_biki_page(command)
        if biki_content:
            biki_path = output_dir / f"{command}.html"
            biki_path.write_text(biki_content, encoding="utf-8")
            print(f"  Saved to {biki_path}")
        else:
            print(f"  BIKI page not found for {command}")

    if not args.biki_only:
        print(f"Fetching YAML definition for {command}...")
        yaml_content = fetch_yaml_definition(command)
        if yaml_content:
            yaml_path = output_dir / f"{command}.yaml"
            yaml_path.write_text(yaml_content, encoding="utf-8")
            print(f"  Saved to {yaml_path}")
        else:
            print(f"  YAML definition not found for {command}")

    print("Done.")


if __name__ == "__main__":
    main()
