import bs4
import requests


class IJCAI:
    def __init__(self, year="2026") -> None:
        self.url = f"https://{year}.ijcai.org/accepted-papers/"

    def do_requests(self):
        resp = requests.get(self.url)
        resp.raise_for_status()
        content = resp.text
        soup = bs4.BeautifulSoup(content, features="lxml")

        list_obj = soup.select_one(".ijcai-papers .ij-list")
        assert list_obj, "no paper list object was found"

        result = []
        for paper_item in list_obj.select(".ij-paper"):
            title_tag = paper_item.select_one(".ij-ptitle")
            authors_tag = paper_item.select_one(".ij-authors")

            if title_tag is None or authors_tag is None:
                continue

            title = title_tag.text
            authors = authors_tag.text

            result.append({"title": title, "author": authors})

        return result


def filter(item: dict):
    title = item.get("title", None)
    if title is None:
        return False
    title = str(title).lower()
    return "graph" in title and ("anomaly" in title or "fraud" in title)


if __name__ == "__main__":
    ijcai = IJCAI()
    res = ijcai.do_requests()
    res = [res_item for res_item in res if filter(res_item)]
    for res_item in res:
        print(f"""
1. **{res_item["title"]}**

    *{res_item["author"]}*
""")
