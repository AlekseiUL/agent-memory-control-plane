#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

TEXT_SUFFIXES = {".py", ".md", ".toml", ".yaml", ".yml", ".json", ".txt"}
TEXT_NAMES = {".gitignore"}
EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "agent_memory_control_plane.egg-info",
}
GENERIC_IDENTITIES = {
    ("AMCP Contributors", "noreply@example.invalid"),
}
FORBIDDEN_TERMS = {
    "MIKE" + "_" + "CENTER",
    "AI" + "_" + "CENTER",
    "/" + "Users" + "/",
    "/private/" + "tmp/",
    "277" + "478969",
    "Алексей" + " Ульянов",
    "Aleksei" + " Ulianov",
    "Alexey" + " Ulyanov",
}
EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
PHONE = re.compile(r"(?<!\w)(?:\+?\d[\s().-]*){9,15}(?!\w)")
SECRET_ASSIGNMENT = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|password|client[_-]?secret)"
    r"\s*[:=]\s*[^\s]{8,}"
)
PRIVATE_KEY = re.compile(r"BEGIN [A-Z ]*PRIVATE KEY")


def release_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in TEXT_NAMES:
            files.append(path)
    return sorted(files)


def scan_text(label: str, text: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for term in FORBIDDEN_TERMS:
        if term in text:
            findings.append({"item": label, "kind": "private_identifier"})
    if SECRET_ASSIGNMENT.search(text):
        findings.append({"item": label, "kind": "secret_assignment"})
    if PRIVATE_KEY.search(text):
        findings.append({"item": label, "kind": "private_key"})
    for value in EMAIL.findall(text):
        if value.lower() != "noreply@example.invalid":
            findings.append({"item": label, "kind": "email_address"})
            break
    if PHONE.search(text):
        findings.append({"item": label, "kind": "phone_like_identifier"})
    return findings


def commit_identity_findings(root: Path, revs: list[str]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for rev in revs:
        raw = subprocess.check_output(
            ["git", "show", "-s", "--format=%an%x00%ae%x00%cn%x00%ce", rev],
            cwd=root,
            text=True,
        ).rstrip("\n")
        author_name, author_email, committer_name, committer_email = raw.split("\x00")
        if (author_name, author_email) not in GENERIC_IDENTITIES:
            findings.append({"item": f"history:{rev[:12]}", "kind": "non_generic_author"})
        if (committer_name, committer_email) not in GENERIC_IDENTITIES:
            findings.append({"item": f"history:{rev[:12]}", "kind": "non_generic_committer"})
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", action="store_true")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    findings: list[dict[str, str]] = []
    files = release_files(root)
    for path in files:
        findings.extend(
            scan_text(
                path.relative_to(root).as_posix(),
                path.read_text(encoding="utf-8", errors="replace"),
            )
        )

    revs: list[str] = []
    if args.history:
        revs = subprocess.check_output(
            ["git", "rev-list", "--all"], cwd=root, text=True
        ).splitlines()
        findings.extend(commit_identity_findings(root, revs))
        for rev in revs:
            try:
                tree = subprocess.check_output(
                    ["git", "grep", "-I", "-n", "-E", ".", rev],
                    cwd=root,
                    text=True,
                    stderr=subprocess.DEVNULL,
                )
            except subprocess.CalledProcessError as exc:
                if exc.returncode == 1:
                    tree = ""
                else:
                    raise
            findings.extend(scan_text(f"history:{rev[:12]}", tree))

    result = {
        "status": "pass" if not findings else "fail",
        "working_text_files": len(files),
        "commits_scanned": len(revs),
        "findings": findings,
    }
    print(json.dumps(result, indent=2))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())