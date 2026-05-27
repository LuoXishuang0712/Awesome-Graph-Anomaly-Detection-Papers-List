import argparse

import bs4
import requests


def parse_file(file_path: str):
    if file_path.startswith("http"):
        resp = requests.get(file_path)
        resp.raise_for_status()
        content = resp.text
    else:
        with open(file_path, "r") as fp:
            content = fp.read()

    soup = bs4.BeautifulSoup(content, "lxml")
    item_lists = soup.select(".publ-list")
    results = []
    for item_list in item_lists:
        for paper_item in item_list.children:
            if not paper_item:
                continue
            authors = []
            title = None
            for span_item in paper_item.select_one(".data").select("span"):
                item_type = span_item.get("itemprop")
                if item_type == "author":
                    authors.append(span_item.text)
                elif item_type == "name":
                    title = span_item.text
                else:
                    continue
            if len(authors) > 0 and title is not None:
                results.append({"title": title, "authors": authors})

    return results


def filter(item: dict):
    title = item.get("title", None)
    if title is None:
        return False
    title = str(title).lower()
    return "graph" in title and ("anomaly" in title or "fraud" in title)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("""DBLP parser""")
    # parser.add_argument("--type", choices=["aaai"], default="aaai")  # TBD
    parser.add_argument("--path", required=True)
    args = parser.parse_args()

    res = parse_file(args.path)
    for res_item in res:
        if not filter(res_item):
            continue
        print(f"filtered: {res_item.get('title')}")
