"""Download and extract the NCBI nt and CARD reference databases."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

NCBI_INDEX_URL = "https://ftp.ncbi.nlm.nih.gov/blast/db/"
CARD_URL = "https://card.mcmaster.ca/latest/data"


def check_wget() -> None:
    """Ensure wget is available on the PATH."""
    if shutil.which("wget") is None:
        raise SystemExit("Error: wget is required but was not found in PATH. Install wget and try again.")


def fetch_nt_archive_names() -> list[str]:
    """Fetch the current set of NCBI core_nt archive names by parsing the FTP directory index."""
    print(f"Fetching nt-core archive list from {NCBI_INDEX_URL}...")
    try:
        with urllib.request.urlopen(NCBI_INDEX_URL, timeout=60) as response:
            html_content = response.read().decode("utf-8", errors="replace")
    except Exception as exc:
        raise RuntimeError(f"Unable to fetch NCBI directory index: {exc}") from exc

    # Find all links ending in core_nt.XX.tar.gz
    archive_names = sorted(list(set(re.findall(r'href="(core_nt\.\d{2}\.tar\.gz)"', html_content))))

    if not archive_names:
        raise RuntimeError("No core_nt archive names were found in the NCBI directory index.")

    print(f"Found {len(archive_names)} core_nt archive(s).")
    return archive_names


def download_file(url: str, destination: Path) -> None:
    """Download a single file with wget, resuming if possible."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} -> {destination}")

    cmd = [
        "wget",
        "-c",
        "-q",
        "-O",
        str(destination),
        url,
    ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Download failed for {url} (exit code {exc.returncode}).") from exc


def download_and_extract_single_file(filename: str, base_url: str, nt_dir: Path) -> bool:
    """Download and extract a single nt archive file using wget and tarfile."""
    archive_path = nt_dir / filename
    stem = filename[:-7] if filename.endswith(".tar.gz") else filename

    extracted_present = any(
        os.path.exists(os.path.join(nt_dir, p.name)) and p.name.startswith(stem)
        for p in nt_dir.iterdir()
        if p.is_file()
    )

    if os.path.exists(archive_path) and archive_path.stat().st_size > 0 and extracted_present:
        print(f" [SKIP] {filename} already downloaded and extracted")
        return True

    if extracted_present:
        print(f" [SKIP] {filename} already downloaded and extracted")
        return True

    url = f"{base_url.rstrip('/')}/{filename}"
    print(f" [START] Downloading {filename}")

    try:
        subprocess.run(["wget", "-c", "-q", "-O", str(archive_path), url], check=True)
        with tarfile.open(archive_path, mode="r:gz") as tar:
            tar.extractall(path=nt_dir)
    except (subprocess.CalledProcessError, tarfile.TarError, OSError) as exc:
        raise RuntimeError(f"Failed to download/extract {filename}: {exc}") from exc

    print(f" [OK] Downloaded and extracted {filename}")
    return True


def extract_tarfile(archive_path: Path, extract_dir: Path) -> None:
    """Extract a tar.gz or tar.bz2 archive to a destination directory."""
    extract_dir.mkdir(parents=True, exist_ok=True)
    print(f"Extracting {archive_path.name} to {extract_dir}...")

    try:
        with tarfile.open(archive_path, mode="r:*") as tar:
            tar.extractall(path=extract_dir)
    except (tarfile.TarError, OSError) as exc:
        raise RuntimeError(f"Failed to extract archive {archive_path}: {exc}") from exc

    print(f"Extraction complete for {archive_path.name}.")


def download_nt_core(outdir: str | Path, threads: int = 4) -> None:
    """Download and extract the NCBI nt-core database archives in parallel."""
    check_wget()
    base_dir = Path(outdir)
    nt_dir = base_dir / "nt-core"
    nt_dir.mkdir(parents=True, exist_ok=True)

    archives = fetch_nt_archive_names()
    if not archives:
        print("No nt-core archives were found to download.")
        return

    print(f"Preparing parallel nt-core database download in {nt_dir} using {threads} worker(s)...")

    base_url = "https://ftp.ncbi.nlm.nih.gov/blast/db"
    with ThreadPoolExecutor(max_workers=max(1, threads)) as executor:
        futures = [
            executor.submit(download_and_extract_single_file, filename, base_url, nt_dir)
            for filename in archives
        ]
        for future in futures:
            try:
                future.result()
            except Exception as exc:
                print(f"Warning: worker error: {exc}", file=sys.stderr)

    print(f"Finished nt-core database downloads in {nt_dir}.")


def download_card(outdir: str | Path) -> None:
    """Download the CARD database archive, extract it, and remove the tarball to save space."""
    check_wget()
    base_dir = Path(outdir)
    base_dir.mkdir(parents=True, exist_ok=True)

    archive_path = base_dir / "card-data.tar.bz2"
    print(f"Downloading CARD archive to {archive_path}...")

    if not archive_path.exists() or archive_path.stat().st_size == 0:
        try:
            download_file(CARD_URL, archive_path)
        except Exception as exc:
            raise RuntimeError(f"CARD download failed: {exc}") from exc
    else:
        print(f"Using existing CARD archive: {archive_path}")

    try:
        extract_tarfile(archive_path, base_dir)
    except Exception as exc:
        raise RuntimeError(f"CARD archive extraction failed: {exc}") from exc
    finally:
        if archive_path.exists():
            archive_path.unlink()
            print(f"Removed archive after extraction: {archive_path}")

    print(f"CARD database extraction complete in {base_dir}.")


def build_parser() -> argparse.ArgumentParser:
    """Create the main downloader CLI parser."""
    parser = argparse.ArgumentParser(description="Download AMRflow reference databases.")
    parser.add_argument("--db", choices=["nt-core", "card", "all"], default="all", help="Database to download.")
    parser.add_argument("--outdir", default="./databases", help="Directory where downloaded databases will be stored.")
    parser.add_argument("-j", "--threads", type=int, default=4, help="Number of parallel threads to use for nt-core downloads.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point for database downloads."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.db in {"nt-core", "all"}:
            download_nt_core(args.outdir, threads=args.threads)
        if args.db in {"card", "all"}:
            download_card(args.outdir)
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover - CLI failure path
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
