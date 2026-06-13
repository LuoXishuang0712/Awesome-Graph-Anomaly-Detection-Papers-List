import argparse
import json
import requests
from pathlib import Path


CONFIG_PATH = Path(__file__).resolve().parent / "config.json"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class ICML:
    def __init__(self, year):
        self.url = f"https://icml.cc/static/virtual/data/icml-{year}-orals-posters.json"

    def do_requests(self):
        resp = requests.get(self.url)
        resp.raise_for_status()
        content = resp.json()
        assert "results" in content

        result = []
        for record_item in content["results"]:
            authors = record_item.get("authors", [])
            title = record_item.get("name", None)

            if len(authors) == 0 or title is None:
                continue
            authors_str = ", ".join(person.get("fullname", "") for person in authors)
            result.append({"title": title, "author": authors_str})

        return result


def filter(item: dict, config: dict) -> bool:
    title = item.get("title", None)
    if title is None:
        return False
    title = str(title).lower()
    rules = config["filter"]
    required_ok = all(kw in title for kw in rules["required"])
    any_of_ok = any(kw in title for kw in rules["any_of"])
    return required_ok and any_of_ok


def deduplicate(items: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for item in items:
        key = item["title"].strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


if __name__ == "__main__":
    import io
    import sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    config = load_config()

    parser = argparse.ArgumentParser(description="Fetch ICML GAD papers from official API")
    parser.add_argument("--year", default=config["default_year"],
                        help=f"Conference year (default: {config['default_year']})")
    args = parser.parse_args()

    icml = ICML(year=args.year)
    res = icml.do_requests()
    res = [res_item for res_item in res if filter(res_item, config)]
    res = deduplicate(res)
    for res_item in res:
        print(f"""
1. **{res_item["title"]}**

    *{res_item["author"]}*
""")
