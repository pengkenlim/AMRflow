#!/usr/bin/env python3
"""Download a small set of FASTQ files for the AMRflow project dataset."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ENA_PORTAL_API = "https://www.ebi.ac.uk/ena/portal/api/search"
PROJECT_ACCESSION = "PRJNA1335824"


def fetch_fastq_links(project_accession: str = PROJECT_ACCESSION, limit: int = 2) -> list[str]:
    """Query ENA for FASTQ download links and return the first N files."""
    if limit <= 0:
        raise ValueError("limit must be greater than zero")

    params = {
        "result": "read_run",
        "query": f'study_accession="{project_accession}"',
        "fields": "run_accession,fastq_ftp",
        "format": "tsv",
        "limit": "0",
    }
    url = f"{ENA_PORTAL_API}?{urllib.parse.urlencode(params)}"
    print(f"Querying ENA API for project {project_accession}...")
    print(f"URL: {url}")

    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            payload = response.read().decode("utf-8", errors="replace")
    except Exception as exc:  # pragma: no cover - network failure path
        raise RuntimeError(f"Failed to query ENA API: {exc}") from exc

    lines = [line for line in payload.splitlines() if line.strip()]
    if len(lines) < 2:
        raise RuntimeError(f"ENA returned no data for project {project_accession}.")

    links: list[str] = []
    for line in lines[1:]:
        fields = line.split("\t")
        if len(fields) < 2:
            continue

        for value in fields[1].split(";"):
            cleaned = value.strip()
            if cleaned:
                links.append(cleaned)

    if not links:
        raise RuntimeError("No FASTQ FTP links were found in the ENA response.")

    print(f"Found {len(links)} FASTQ link(s); downloading the first {min(limit, len(links))}.")
    return links[:limit]


def download_file(url: str, destination: Path) -> None:
    """Download a single file using wget if available, otherwise curl."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} -> {destination.name}")

    if shutil.which("wget"):
        cmd = ["wget", "--show-progress", "-O", str(destination), url]
    elif shutil.which("curl"):
        cmd = ["curl", "-L", "--fail", "--progress-bar", "-o", str(destination), url]
    else:
        raise RuntimeError("Neither wget nor curl is installed. Please install one of them before downloading data.")

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Download failed for {url}: exit code {exc.returncode}") from exc

    print(f"Completed: {destination}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download the first N FASTQ files for BioProject PRJNA1335824 from ENA."
    )
    parser.add_argument("--outdir", required=True, help="Directory where downloaded FASTQ files will be saved.")
    parser.add_argument(
        "--n-samples",
        type=int,
        default=2,
        help="Number of FASTQ files to download (default: 2).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.n_samples <= 0:
        print("Error: --n-samples must be greater than 0.", file=sys.stderr)
        return 2

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    try:
        links = fetch_fastq_links(PROJECT_ACCESSION, limit=args.n_samples)
        for index, link in enumerate(links, start=1):
            filename = Path(urllib.parse.urlparse(link).path).name or f"sample_{index}.fastq.gz"
            download_file(link, outdir / filename)
    except Exception as exc:  # pragma: no cover - CLI error path
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Finished downloading {len(links)} FASTQ file(s) to {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
