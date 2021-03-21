import webbrowser
from io import BytesIO

import bs4 as bs
import requests
import wikipedia
from PIL import Image


class WikipediaError(Exception):
    pass


class WikipediaExtractor:
    def __init__(self, lang="fr"):

        # Set language for future search
        wikipedia.set_lang(lang)
        # print(f"[INFO] Wikipedia bot initialized in {lang.upper()}")

    def search_pages(
        self, query, return_pages=True, results=5, category=None, best_match=False
    ):

        page_names = wikipedia.search(query, results=results)

        if return_pages:

            if category is not None:

                if best_match:
                    for page in page_names:
                        page = WikipediaPage(page)
                        if page.has_category_like(category):
                            return page
                    return None

                else:
                    pages = []
                    for page in page_names:
                        page = WikipediaPage(page)
                        if page.has_category_like(category):
                            pages.append(page)

            else:

                if best_match:
                    return WikipediaPage(page_names[0])
                else:
                    return [WikipediaPage(page) for page in page_names]
        else:
            if best_match:
                return page_names[0]
            else:
                return page_names

    def search_biology_page(self, query, results=5):

        # Warning harcoded french parameter
        category = "biologie"

        # Search using wikipedia API
        page = self.search_pages(
            query,
            results=results,
            category=category,
            best_match=True,
            return_pages=True,
        )
        return page


class WikipediaPage(wikipedia.WikipediaPage):
    ATTRS = [
        "categories",
        "content",
        "summary",
        "images",
        "links",
        "original_title",
        "pageid",
        "parentid",
        "references",
        "summary",
        "url",
    ]

    def get_categories(self, as_string=False):
        cats = self.categories
        cats = [cat.rsplit(":", 1)[-1] for cat in cats]

        if as_string:
            return "|".join(cats)
        else:
            return cats

    def has_category_like(self, query):
        return query.lower() in self.get_categories(as_string=True).lower()

    def get_description(self):
        return self.content

    def get_beautifulsoup_page(self, html):
        return bs.BeautifulSoup(html, "lxml")

    def get_species_image(self, as_img=False, thumbnail=True):
        page = self.get_beautifulsoup_page(self.html())

        image_url = (
            "https:" + page.find("div", class_="images").find("img").attrs["src"]
        )
        if thumbnail == False:
            image_url = image_url.replace("/thumb/", "/").rsplit("/", 1)[0]

        if as_img:
            r = requests.get(image_url)
            img = Image.open(BytesIO(r.content), "r")
            return img
        else:
            return image_url

    def is_species(self):

        # Warning check if it works for other species than animals
        # Hardcoded category info
        taxobox = "taxobox-animal"

        return taxobox in self.get_categories(as_string=True).lower()

    def open(self):
        webbrowser.open(self.url)

    def explore(self):

        for attribute in self.ATTRS:
            if not attribute.startswith("_"):
                try:
                    print("-" * 3, attribute, "-" * 50)
                    content = getattr(self, attribute)
                    print(attribute)
                    if isinstance(content, str):
                        print(content[:500])
                    else:
                        print(content)
                    print("")
                except Exception as e:
                    print(f"-- Skipped attribute {attribute} because of {e}")

    def to_dict(self):

        return {a: getattr(self, a) for a in self.ATTRS}
