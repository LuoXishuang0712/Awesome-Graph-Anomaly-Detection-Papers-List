# Toolbox

This repository uses two small scripts to maintain the paper list:

- `fetch_bib.py`: fetch BibTeX entries from Google Scholar.
- `compile.py`: compile `README.md` from `TEMPLATE.md` and files under `bibs/`.

## Fetch BibTeX

Run the interactive fetcher:

```bash
python fetch_bib.py
```

Then paste or type one paper title at the prompt:

```text
fetch-bib> HLSAD: Hodge Laplacian-based Simplicial Anomaly Detection
```

The script searches Google Scholar, fetches the BibTeX for the selected result, and prints it to stdout. Type `q`, `quit`, or `exit` to stop.

### Clipboard Mode

Use `--clipboard` to query from the clipboard:

```bash
python fetch_bib.py --clipboard
```

In this mode, press Enter to read the current clipboard text and search it:

```text
fetch-bib[clipboard]>
```

This is useful when copying paper titles from conference proceedings pages.

### Append To A Bib File

Use `--output_file` to append each fetched BibTeX entry directly to a `.bib` file:

```bash
python fetch_bib.py --output_file bibs/kdd-25.bib
```

It also works with clipboard mode:

```bash
python fetch_bib.py --clipboard --output_file bibs/kdd-25.bib
```

The script keeps a blank line between BibTeX entries when appending.

### Choosing Search Results

If Google Scholar returns exactly one result, the script uses it automatically.

If multiple results are found, the script shows up to five candidates:

```text
Multiple Google Scholar results found. Choose a match:
  1. Paper title
     Authors and venue info
     id:paper_id
Select [1-5], Enter for 1, or s to skip:
```

Press Enter to choose the first result, enter a number to choose another result, or enter `s` / `skip` to skip the query.

### Fetch By Google Scholar ID

For difficult searches, use the printed `id:{id}` form directly:

```text
fetch-bib> id:paper_id
```

This bypasses title search and fetches the BibTeX citation page for that Google Scholar paper id.

## Compile README

Generate `README.md` from `TEMPLATE.md`:

```bash
python compile.py
```

The template uses two kinds of placeholders:

```markdown
  - {contents}

{kdd-25:KDD-2025}
```

- `{contents}` is replaced by a Markdown table of contents.
- `{kdd-25:KDD-2025}` reads `bibs/kdd-25.bib` and renders a section titled `KDD-2025`.

To add another section, create a matching bib file and add a placeholder:

```markdown
{www-25:WWW-2025}
```

Then create:

```text
bibs/www-25.bib
```

### Check Mode

Use `--check` to verify that `README.md` is up to date without writing it:

```bash
python compile.py --check
```

This exits with a non-zero status if `README.md` differs from the compiled output.

### Custom Paths

`compile.py` also accepts custom paths:

```bash
python compile.py \
  --template TEMPLATE.md \
  --bib-dir bibs \
  --output README.md
```

## Typical Workflow

1. Fetch and append BibTeX entries:

```bash
python fetch_bib.py --clipboard --output_file bibs/kdd-25.bib
```

2. Compile the paper list:

```bash
python compile.py
```

3. Check the result:

```bash
python compile.py --check
```
