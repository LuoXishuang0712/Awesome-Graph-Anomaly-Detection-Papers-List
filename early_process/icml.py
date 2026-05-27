import requests


class ICML:
    def __init__(self, year="2026"):
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


def filter(item: dict):
    title = item.get("title", None)
    if title is None:
        return False
    title = str(title).lower()
    return "graph" in title and ("anomaly" in title or "fraud" in title)


if __name__ == "__main__":
    icml = ICML()
    res = icml.do_requests()
    res = [res_item for res_item in res if filter(res_item)]
    for res_item in res:
        print(f"""
1. **{res_item["title"]}**

    *{res_item["author"]}*
""")
