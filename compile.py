#!/usr/bin/env python3
"""Compile README.md from TEMPLATE.md and BibTeX files."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = ROOT / "TEMPLATE.md"
DEFAULT_OUTPUT = ROOT / "README.md"
DEFAULT_BIB_DIR = ROOT / "bibs"
PLACEHOLDER_RE = re.compile(r"\{([A-Za-z0-9_.-]*):([^{}]+)\}")
SECTION_TITLE_RE = re.compile(r"^([A-Za-z0-9]+)-(\d{4})$")


@dataclass(frozen=True)
class BibEntry:
    key: str
    fields: dict[str, str]


def strip_outer_braces(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == "{" and value[-1] == "}":
        return value[1:-1].strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1].strip()
    return value


def normalize_whitespace(value: str) -> str:
    return " ".join(value.replace("\n", " ").split())


def split_top_level(text: str, delimiter: str = ",") -> list[str]:
    parts: list[str] = []
    start = 0
    brace_depth = 0
    in_quote = False
    escaped = False

    for index, char in enumerate(text):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"' and brace_depth == 0:
            in_quote = not in_quote
            continue
        if in_quote:
            continue
        if char == "{":
            brace_depth += 1
            continue
        if char == "}":
            brace_depth = max(0, brace_depth - 1)
            continue
        if char == delimiter and brace_depth == 0:
            parts.append(text[start:index].strip())
            start = index + 1

    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def find_matching_brace(text: str, opening_index: int) -> int:
    depth = 0
    in_quote = False
    escaped = False

    for index in range(opening_index, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"' and depth == 0:
            in_quote = not in_quote
            continue
        if in_quote:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index

    raise ValueError("Unmatched brace in BibTeX file")


def parse_bibtex(text: str) -> list[BibEntry]:
    entries: list[BibEntry] = []
    index = 0

    while True:
        at_index = text.find("@", index)
        if at_index == -1:
            break

        opening_index = text.find("{", at_index)
        if opening_index == -1:
            break

        closing_index = find_matching_brace(text, opening_index)
        body = text[opening_index + 1 : closing_index].strip()
        chunks = split_top_level(body, ",")
        if not chunks:
            index = closing_index + 1
            continue

        key = chunks[0].strip()
        fields: dict[str, str] = {}
        for chunk in chunks[1:]:
            if "=" not in chunk:
                continue
            name, raw_value = chunk.split("=", 1)
            fields[name.strip().lower()] = normalize_whitespace(
                strip_outer_braces(raw_value)
            )

        entries.append(BibEntry(key=key, fields=fields))
        index = closing_index + 1

    return entries


def format_author(author: str) -> str:
    author = normalize_whitespace(strip_outer_braces(author))
    if "," not in author:
        return author

    last, first = [part.strip() for part in author.split(",", 1)]
    return normalize_whitespace(f"{first} {last}")


def format_authors(raw_authors: str) -> str:
    authors = re.split(r"\s+and\s+", raw_authors.strip())
    return ", ".join(format_author(author) for author in authors if author.strip())


def format_entry(entry: BibEntry) -> str:
    title = entry.fields.get("title")
    authors = entry.fields.get("author")
    if not title or not authors:
        raise ValueError(f"BibTeX entry {entry.key!r} must contain title and author")

    return f"1. **{title}** \n\n    *{format_authors(authors)}*"


def format_section(section_id: str, section_title: str, bib_dir: Path) -> str:
    bib_path = bib_dir / f"{section_id}.bib"
    md_path = bib_dir / f"{section_id}.md"

    if bib_path.exists():
        entries = parse_bibtex(bib_path.read_text(encoding="utf-8"))
        rendered_entries = "\n\n".join(format_entry(entry) for entry in entries)
    elif md_path.exists():
        rendered_entries = md_path.read_text(encoding="utf-8").strip()
    else:
        raise FileNotFoundError(
            f"Missing source file for {{{section_id}:{section_title}}}: "
            f"expected {bib_path} or {md_path}"
        )

    if rendered_entries:
        rendered_entries += "\n"

    return f"### [{section_title}](#contents)\n\n{rendered_entries}"


def compile_readme(template_path: Path, bib_dir: Path) -> str:
    template = template_path.read_text(encoding="utf-8")
    placeholders = PLACEHOLDER_RE.findall(template)

    contents = format_contents(placeholders)

    output = template.replace("{contents}", contents)
    for section_id, section_title in placeholders:
        placeholder = f"{{{section_id}:{section_title}}}"
        if section_id:
            output = output.replace(
                placeholder,
                format_section(section_id, section_title.strip(), bib_dir),
            )
        else:
            output = remove_placeholder_line(output, placeholder)

    return output.rstrip() + "\n"


def parse_section_title(title: str) -> tuple[str, str]:
    title = title.strip()
    match = SECTION_TITLE_RE.fullmatch(title)
    if match is None:
        raise ValueError(
            f"Invalid section title {title!r}. Expected format '<conference>-<year>', "
            "for example 'KDD-2025'."
        )
    conference, year = match.groups()
    return conference, year


def format_contents(placeholders: list[tuple[str, str]]) -> str:
    links_by_year: dict[str, list[str]] = {}
    years: list[str] = []

    for section_id, title in placeholders:
        title = title.strip()
        _, year = parse_section_title(title)
        if year not in links_by_year:
            links_by_year[year] = []
            years.append(year)
        if section_id:
            links_by_year[year].append(f"[{title}](#{slugify(title)})")
        else:
            links_by_year[year].append(title)

    return "\n  - ".join(" ".join(links_by_year[year]) for year in years)


def remove_placeholder_line(text: str, placeholder: str) -> str:
    line_pattern = re.compile(
        rf"(?m)^[ \t]*{re.escape(placeholder)}[ \t]*\r?\n(?:[ \t]*\r?\n)?"
    )
    updated = line_pattern.sub("", text)
    if updated != text:
        return updated
    return text.replace(placeholder, "")


def slugify(title: str) -> str:
    slug = title.strip().lower()
    slug = re.sub(r"[^a-z0-9 -]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return slug


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate README.md from TEMPLATE.md and bibs/*.bib."
    )
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--bib-dir", type=Path, default=DEFAULT_BIB_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write files; fail if the output is not up to date.",
    )
    args = parser.parse_args()

    compiled = compile_readme(args.template, args.bib_dir)

    if args.check:
        current = args.output.read_text(encoding="utf-8") if args.output.exists() else ""
        if current != compiled:
            print(f"{args.output} is not up to date. Run python compile.py.", file=sys.stderr)
            return 1
        return 0

    args.output.write_text(compiled, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
