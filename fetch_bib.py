import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote_plus

import bs4
import requests

HEADER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
}
SEARCH_RESULT_LIMIT = 5


class GoogleScholar:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADER)
        self.base_url = "https://scholar.google.com"
        resp = self.session.get(self.base_url)
        resp.raise_for_status()

    def __parse_list(self, resp_text: str):
        soup = bs4.BeautifulSoup(resp_text, "html.parser")
        papers = []
        for item in soup.select(".gs_r"):
            title_obj = item.select_one(".gs_rt")
            authors_obj = item.select_one(".gs_a")
            if title_obj is None or authors_obj is None:
                continue
            title = title_obj.get_text(" ", strip=True)
            link_obj = title_obj.select_one("[data-clk-atid]")
            if link_obj is None:
                continue
            paper_id = link_obj.get("data-clk-atid")
            if not paper_id:
                continue
            authors = authors_obj.text
            papers.append({"title": title, "authors": authors, "paper_id": paper_id})
        return papers

    def get_cite_info(self, paper_id):
        url = f"{self.base_url}/scholar?q=info:{paper_id}:scholar.google.com/&output=cite&scirp=0&hl=en"
        resp = self.session.get(url)
        resp.raise_for_status()
        soup = bs4.BeautifulSoup(resp.text, "html.parser")
        cites = soup.select(".gs_citi")
        cites_res = {}
        for cite in cites:
            cite_type = cite.text
            cite_url = cite.get("href")
            cites_res[cite_type] = cite_url
        return cites_res

    def search(self, query):
        url = f"{self.base_url}/scholar?q={quote_plus(query)}&hl=en"
        resp = self.session.get(url)
        resp.raise_for_status()
        return self.__parse_list(resp.text)

    def simple_request(self, url):
        """Make a simple GET request to the given URL and return the response text. For cite requests."""
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.text


def read_clipboard() -> str:
    commands = [
        ["powershell.exe", "-NoProfile", "-Command", "Get-Clipboard"],
        ["pbpaste"],
        ["wl-paste", "--no-newline"],
        ["xclip", "-selection", "clipboard", "-out"],
        ["xsel", "--clipboard", "--output"],
    ]
    for command in commands:
        if shutil.which(command[0]) is None:
            continue
        try:
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (subprocess.SubprocessError, OSError):
            continue
        text = result.stdout.strip()
        if text:
            return text
    raise RuntimeError(
        "Could not read clipboard. Install xclip/xsel/wl-clipboard, or use Windows/WSL powershell.exe."
    )


def fetch_bibtex_by_id(gs: GoogleScholar, paper_id: str) -> str:
    cite_info = gs.get_cite_info(paper_id)
    bibtex_url = cite_info.get("BibTeX")
    if not bibtex_url:
        raise LookupError(f"No BibTeX link found for paper id: {paper_id}")

    return gs.simple_request(bibtex_url).strip()


def select_paper(papers: list[dict[str, str]]) -> dict[str, str]:
    if not papers:
        raise LookupError("No Google Scholar result found")
    if len(papers) == 1:
        return papers[0]

    candidates = papers[:SEARCH_RESULT_LIMIT]
    print("Multiple Google Scholar results found. Choose a match:")
    for index, paper in enumerate(candidates, start=1):
        print(f"  {index}. {paper['title']}")
        print(f"     {paper['authors']}")
        print(f"     id:{paper['paper_id']}")

    while True:
        try:
            choice = input(f"Select [1-{len(candidates)}], Enter for 1, or s to skip: ").strip()
        except EOFError:
            print()
            return candidates[0]
        if not choice:
            return candidates[0]
        if choice.lower() in {"s", "skip"}:
            raise LookupError("Skipped by user")
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(candidates):
                return candidates[index - 1]
        print(f"Please enter a number from 1 to {len(candidates)}, Enter, or s.")


def fetch_bibtex(gs: GoogleScholar, query: str) -> tuple[dict[str, str], str]:
    if query.startswith("id:"):
        paper_id = query.removeprefix("id:").strip()
        if not paper_id:
            raise ValueError("Empty Google Scholar paper id")
        paper = {"title": f"id:{paper_id}", "authors": "", "paper_id": paper_id}
        return paper, fetch_bibtex_by_id(gs, paper_id)

    paper = select_paper(gs.search(query))
    return paper, fetch_bibtex_by_id(gs, paper["paper_id"])


def append_bibtex(output_file: Path, bibtex: str) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    bibtex = bibtex.strip()
    if not bibtex:
        return

    if output_file.exists() and output_file.stat().st_size > 0:
        existing = output_file.read_text(encoding="utf-8")
        separator = "\n\n" if existing.endswith("\n") else "\n\n"
        output_file.write_text(existing.rstrip() + separator + bibtex + "\n", encoding="utf-8")
    else:
        output_file.write_text(bibtex + "\n", encoding="utf-8")


def iter_queries(use_clipboard: bool):
    if use_clipboard:
        print("Clipboard mode. Press Enter to query clipboard text. Type q to quit.")
    else:
        print("Interactive mode. Paste or type one paper title per query. Type q to quit.")

    while True:
        try:
            if use_clipboard:
                user_input = input("fetch-bib[clipboard]> ")
                if user_input.strip().lower() in {"q", "quit", "exit"}:
                    return
                query = read_clipboard()
                print(f"[QUERY] {query}")
            else:
                query = input("fetch-bib> ")
                if query.strip().lower() in {"q", "quit", "exit"}:
                    return

            query = query.strip()
            if query:
                yield query
        except (EOFError, KeyboardInterrupt):
            print()
            return


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Search Google Scholar by paper title and print the first result's BibTeX."
    )
    parser.add_argument(
        "--clipboard",
        action="store_true",
        help="Press Enter to read the query title from clipboard instead of stdin.",
    )
    parser.add_argument(
        "--output_file",
        type=Path,
        help="Append each fetched BibTeX entry to this .bib file.",
    )
    args = parser.parse_args()

    exit_code = 0
    gs = None
    for query in iter_queries(args.clipboard):
        try:
            if gs is None:
                gs = GoogleScholar()
            paper, bibtex = fetch_bibtex(gs, query)
        except Exception as exc:
            print(f"[ERROR] {query}: {exc}", file=sys.stderr)
            exit_code = 1
            continue

        print(f"% Query: {query}")
        print(f"% Matched: {paper['title']}")
        print(bibtex)
        if args.output_file is not None:
            append_bibtex(args.output_file, bibtex)
            print(f"% Appended to: {args.output_file}")
        print()

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
