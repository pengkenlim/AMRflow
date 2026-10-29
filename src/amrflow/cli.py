"""Command-line entry point for AMRflow."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser with subcommands."""
    parser = argparse.ArgumentParser(description="AMRflow command line interface")
    subparsers = parser.add_subparsers(dest="command")

    download_parser = subparsers.add_parser(
        "download-dbs",
        help="Download reference databases for nt-core and CARD",
    )
    download_parser.add_argument(
        "--db",
        choices=["nt-core", "card", "all"],
        default="all",
        help="Database to download (default: all)",
    )
    download_parser.add_argument(
        "--outdir",
        default="./databases",
        help="Directory where databases will be stored (default: ./databases)",
    )
    download_parser.add_argument(
        "-j",
        "--threads",
        type=int,
        default=4,
        help="Number of parallel threads to use for nt-core downloads (default: 4)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the AMRflow CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "download-dbs":
        from amrflow.downloader import main as download_main

        return download_main(["--db", args.db, "--outdir", args.outdir, "--threads", str(args.threads)])

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
