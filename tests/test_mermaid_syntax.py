"""Mermaid blocks in the repository's Markdown must stay renderable on GitHub.

Contract test mirroring the system-wide ``lint_mermaid.py`` guardrail
(AUFTRAG-MERMAID-SYNTAX-GUARDRAILS-2026-09-07): unquoted brackets, parentheses,
angle brackets or semicolons in flowchart edge labels and square nodes, and
semicolons in sequence-diagram messages, abort GitHub's Mermaid renderer with
``Unable to render rich display``. Automated documentation runs must not be able
to push such a diagram with a green test suite.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MERMAID_BLOCK = re.compile(r"```mermaid\s*\n(.*?)\n```", re.DOTALL)
EDGE_LABEL = re.compile(r"(?:--+>|<-+>|-\.-+>|==+>)\|([^|\r\n]+)\|")
SQUARE_NODE = re.compile(r'\b\w+\s*\[([^"\[\]\r\n]+)\]')
SEQUENCE_MESSAGE = re.compile(r"^\s*[^:\r\n]*(?:->>|-->>|->|-->)\s*[^:\r\n]+:\s*(.*)$")
HTML_ENTITY = re.compile(r"&[a-zA-Z0-9#]+;")
ILLEGAL_EDGE_CHARS = set("()[]{}<>;")
SKIP_PARTS = {".git", ".venv", "node_modules", "build", "dist", ".providers", ".local-demo"}


def _markdown_files() -> list[Path]:
    return sorted(
        path
        for path in REPOSITORY_ROOT.rglob("*.md")
        if not (SKIP_PARTS & set(path.relative_to(REPOSITORY_ROOT).parts))
    )


def _block_issues(block: str) -> list[str]:
    issues: list[str] = []
    lines = block.splitlines()
    is_sequence = any("sequenceDiagram" in line for line in lines)
    for number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            continue
        if is_sequence:
            match = SEQUENCE_MESSAGE.match(line)
            if match and ";" in HTML_ENTITY.sub("", match.group(1)):
                issues.append(f"line {number}: semicolon in sequence message: {stripped}")
            continue
        for label in EDGE_LABEL.findall(line):
            text = label.strip()
            quoted = text.startswith('"') and text.endswith('"')
            if not quoted and ILLEGAL_EDGE_CHARS & set(text):
                issues.append(f"line {number}: unquoted edge label: |{text}|")
        for inner in SQUARE_NODE.findall(line):
            text = inner.strip()
            if text.startswith("(") and text.endswith(")"):
                continue  # stadium shape ([ ... ])
            quoted = text.startswith('"') and text.endswith('"')
            if not quoted and any(char in text for char in "();"):
                issues.append(f"line {number}: unquoted square node: [{text}]")
    return issues


@pytest.mark.parametrize(
    "path", [pytest.param(p, id=str(p.relative_to(REPOSITORY_ROOT))) for p in _markdown_files()]
)
def test_mermaid_blocks_stay_renderable(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    problems = [
        f"block {index}: {issue}"
        for index, block in enumerate(MERMAID_BLOCK.findall(text), start=1)
        for issue in _block_issues(block)
    ]
    assert problems == [], "\n".join(problems)


def test_mermaid_guard_detects_the_github_parse_errors() -> None:
    broken_flowchart = 'flowchart LR\n  A -->|dry_run: true (default)| B[Preview (draft); done]\n'
    broken_sequence = "sequenceDiagram\n  App-->>User: Letter artifacts; run ready\n"
    fixed = 'flowchart LR\n  A -->|"dry_run: true (default)"| B["Preview (draft); done"]\n'
    assert len(_block_issues(broken_flowchart)) == 2
    assert len(_block_issues(broken_sequence)) == 1
    assert _block_issues(fixed) == []
    assert _block_issues("flowchart LR\n  A --> B([stadium (ok)])\n") == []
