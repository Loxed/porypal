#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"

FULL_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:([-+][0-9A-Za-z.-]+))?$")


@dataclass(frozen=True)
class VersionInfo:
    major: int
    minor: int
    patch: int
    suffix: str = ""

    @property
    def full(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}{self.suffix}"

    @property
    def short(self) -> str:
        return f"{self.major}.{self.minor}"

    @property
    def tag(self) -> str:
        return f"v{self.full}"

    @classmethod
    def parse(cls, raw: str) -> "VersionInfo":
        value = raw.strip()
        match = FULL_VERSION_RE.fullmatch(value)
        if not match:
            raise ValueError(
                "Version must look like X.Y.Z, vX.Y.Z, or include a suffix like 3.2.0-rc1"
            )
        major, minor, patch, suffix = match.groups()
        return cls(int(major), int(minor), int(patch), suffix or "")


def read_current_version() -> str:
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text(encoding="utf-8").strip()

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version = "([^"]+)"$', pyproject)
    if not match:
        raise RuntimeError("Could not determine current version")
    return match.group(1)


def bump_release(current: VersionInfo, mode: str) -> VersionInfo:
    major, minor, patch = current.major, current.minor, current.patch
    if mode == "major":
        return VersionInfo(major + 1, 0, 0)
    if mode == "minor":
        return VersionInfo(major, minor + 1, 0)
    if mode == "patch":
        return VersionInfo(major, minor, patch + 1)
    raise ValueError(f"Unknown bump mode: {mode}")


def replace_once(path: Path, pattern: str, replacement: str) -> None:
    original = path.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, replacement, original, count=1)
    if count != 1:
        raise RuntimeError(f"Expected exactly one match in {path}")
    if updated != original:
        path.write_text(updated, encoding="utf-8")


def sync_version_files(version: VersionInfo) -> list[Path]:
    full = version.full
    short = version.short

    touched = []

    VERSION_FILE.write_text(full + "\n", encoding="utf-8")
    touched.append(VERSION_FILE)

    replace_once(ROOT / "pyproject.toml", r'(?m)^version = "[^"]+"$', f'version = "{full}"')
    touched.append(ROOT / "pyproject.toml")

    replace_once(
        ROOT / "frontend" / "package.json",
        r'(?m)^  "version": "[^"]+",$',
        f'  "version": "{full}",',
    )
    touched.append(ROOT / "frontend" / "package.json")

    replace_once(
        ROOT / "frontend" / "package-lock.json",
        r'(?m)^  "version": "[^"]+",$',
        f'  "version": "{full}",',
    )
    replace_once(
        ROOT / "frontend" / "package-lock.json",
        r'(?m)^      "version": "[^"]+",$',
        f'      "version": "{full}",',
    )
    touched.append(ROOT / "frontend" / "package-lock.json")

    replace_once(ROOT / "model" / "__init__.py", r"__version__ = '[^']+'", f"__version__ = '{full}'")
    touched.append(ROOT / "model" / "__init__.py")

    replace_once(
        ROOT / "server" / "app.py",
        r'version="[^"]+"',
        f'version="{full}"',
    )
    touched.append(ROOT / "server" / "app.py")

    replace_once(
        ROOT / "server" / "api" / "pipeline.py",
        r'PORYPAL_VERSION = "[^"]+"',
        f'PORYPAL_VERSION = "{full}"',
    )
    touched.append(ROOT / "server" / "api" / "pipeline.py")

    replace_once(
        ROOT / "main.py",
        r'print\("  Porypal v[^"]+"\)',
        f'print("  Porypal v{short}")',
    )
    touched.append(ROOT / "main.py")

    replace_once(
        ROOT / "frontend" / "index.html",
        r"<title>Porypal \(v[^)]+\)</title>",
        f"<title>Porypal (v{short})</title>",
    )
    touched.append(ROOT / "frontend" / "index.html")

    replace_once(
        ROOT / "frontend" / "src" / "tabs" / "HomeTab.jsx",
        r'home-hero-eyebrow">v[^<]+ · Gen 3 ROM hacking</p>',
        f'home-hero-eyebrow">v{short} · Gen 3 ROM hacking</p>',
    )
    replace_once(
        ROOT / "frontend" / "src" / "tabs" / "HomeTab.jsx",
        r'home-footer-left">porypal v[^<]+ · by prison_lox</span>',
        f'home-footer-left">porypal v{short} · by prison_lox</span>',
    )
    touched.append(ROOT / "frontend" / "src" / "tabs" / "HomeTab.jsx")

    return touched


def run_git(*args: str) -> None:
    subprocess.run(["git", *args], cwd=ROOT, check=True)


def git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def ensure_clean_tree() -> None:
    status = git_output("status", "--short")
    if status:
        raise RuntimeError(
            "Git working tree is not clean. Commit/stash other changes first, or run without "
            "--commit/--tag/--push."
        )


def create_commit_and_tag(version: VersionInfo, touched: list[Path], do_commit: bool, do_tag: bool) -> None:
    rel_paths = [str(path.relative_to(ROOT)) for path in touched]
    if do_commit or do_tag:
        run_git("add", *rel_paths)
    if do_commit:
        run_git("commit", "-m", f"release: {version.tag}")
    if do_tag:
        run_git("tag", "-a", version.tag, "-m", version.tag)


def push_release(version: VersionInfo, remote: str) -> None:
    run_git("push", remote, "HEAD")
    run_git("push", remote, version.tag)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync Porypal version files and optionally commit, tag, and push a release."
    )
    parser.add_argument(
        "version",
        nargs="?",
        help="Set an explicit version, for example 3.2.0",
    )
    parser.add_argument(
        "--major",
        action="store_true",
        help="Bump the major version from VERSION",
    )
    parser.add_argument(
        "--minor",
        action="store_true",
        help="Bump the minor version from VERSION",
    )
    parser.add_argument(
        "--patch",
        action="store_true",
        help="Bump the patch version from VERSION",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Print the current version and exit",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Create a release commit after syncing files",
    )
    parser.add_argument(
        "--tag",
        action="store_true",
        help="Create an annotated git tag vX.Y.Z after syncing files",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push the current branch and the new tag to the remote after tagging",
    )
    parser.add_argument(
        "--remote",
        default="origin",
        help="Git remote to push to when using --push (default: origin)",
    )
    return parser


def resolve_target_version(args: argparse.Namespace, current: VersionInfo) -> VersionInfo | None:
    bump_flags = [args.major, args.minor, args.patch]
    if sum(bool(flag) for flag in bump_flags) > 1:
        raise ValueError("Use only one of --major, --minor, or --patch")

    if args.show:
        return None

    if args.version and any(bump_flags):
        raise ValueError("Use either an explicit version or a bump flag, not both")

    if args.major:
        return bump_release(current, "major")
    if args.minor:
        return bump_release(current, "minor")
    if args.patch:
        return bump_release(current, "patch")
    if args.version:
        return VersionInfo.parse(args.version)

    raise ValueError("Provide a version or one of --major/--minor/--patch")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    current = VersionInfo.parse(read_current_version())
    if args.show:
        print(current.full)
        return 0

    try:
        if args.tag and not args.commit:
            raise ValueError("--tag requires --commit so the tag points at the bumped version")
        if args.push and not (args.commit and args.tag):
            raise ValueError("--push requires both --commit and --tag")

        if args.commit or args.tag or args.push:
            ensure_clean_tree()

        target = resolve_target_version(args, current)
        assert target is not None
        touched = sync_version_files(target)

        if args.commit or args.tag:
            create_commit_and_tag(target, touched, do_commit=args.commit, do_tag=args.tag)

        if args.push:
            push_release(target, args.remote)

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Updated version: {current.full} -> {target.full}")
    print(f"Short display version: {target.short}")
    if args.tag or args.push:
        print(f"Git tag: {target.tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
