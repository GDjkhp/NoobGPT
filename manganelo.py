from bs4 import BeautifulSoup
import urllib.parse
import ast
import contextlib as cl
import html
import locale
import string
import re
from typing import Union
import datetime as dt
from pydantic import BaseModel
import aiohttp

class RequestError(BaseException):
	...

ROOT_URL = "http://manganato.com"
HOME_TOOLTIPS_URL = f"{ROOT_URL}/home_tooltips_json"
STORY_SEARCH_URL = f"{ROOT_URL}/search/story/" + "{title}"

async def download_chapter(url):
	r = await request(url)
	soup = BeautifulSoup(r, "html.parser")
	return _get_image_urls_from_soup(soup)

def _get_image_urls_from_soup(soup):
	def valid(url: str):
		return url.endswith((".png", ".jpg")) and not url.startswith("https://chapmanganato.to")
	return [url for url in map(lambda ele: ele["src"], soup.find_all("img")) if valid(url)]
    
async def request(url: str, **kwargs):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, **kwargs) as response:
            if response.status == 200: return await response.read()

async def fetch_image(url):
	headers = {
		'Host': urllib.parse.urlparse(url).netloc, 'Accept-Language': 'en-ca', 'Referer': ROOT_URL,
	}
	return await request(url, headers=headers)

async def get_story_page(url) -> "StoryPage":
	r = await request(url)
	soup = BeautifulSoup(r, "html.parser")
	if "404" in soup.find("title").text: raise RequestError(f"Page '{url}' was not found")
	return StoryPage.from_soup(url, soup)

async def get_search_results(title: str) -> list["SearchResult"]:
	r = await request(STORY_SEARCH_URL.format(title=encode_querystring(title)))
	if not r: raise RequestError(f"Search request failed")
	soup = BeautifulSoup(r, "html.parser")
	return [SearchResult.from_soup(ele) for ele in soup.find_all(class_="search-story-item")]

def parse_views(number_string: str) -> int:
	with cl.suppress(Exception): return ast.literal_eval(number_string)
	number_string, unit = number_string[:-1], number_string[-1].upper()
	multiplier = {
		"B": 1_000_000_000,
		"M": 1_000_000,
		"K": 1_000
	}.get(unit, 1)
	with cl.suppress(Exception): return int(float(number_string) * multiplier)
	return -1

def unescape_html(s: str) -> str:
	return html.unescape(s).strip()

def split_at(s: str, sep: str) -> list[str]:
	return [x.strip() for x in s.split(sep)]

def encode_querystring(s: str) -> str:
	allowed_characters: str = string.ascii_letters + string.digits + "_"
	return "".join([char.lower() for char in s.strip().replace(" ", "_") if char in allowed_characters])

def parse_date(s: str, _format: str):
	try:
		locale.setlocale(locale.LC_ALL, "en_US.UTF8")
		return dt.datetime.strptime(s, _format)
	finally:
		locale.setlocale(locale.LC_ALL, '')

class Chapter(BaseModel):
    title: str
    url: str
    chapter: Union[int, float]
    views: int
    # uploaded: dt.datetime

    async def download(self):
        return await download_chapter(self.url)

    @staticmethod
    def from_soup(soup):
        obj = Chapter(
            title=_parse_title_chapter(soup),
            url=_parse_url_chapter(soup),
            chapter=-1,
            views=_parse_views_chapter(soup),
            # uploaded=_parse_uploaded(soup)
        )
        obj.chapter = _parse_chapter(obj.url)
        return obj

def _parse_title_chapter(soup):
    return soup.find("a").text

def _parse_url_chapter(soup):
    return soup.find("a").get("href")

def _parse_chapter(url: str) -> Union[int, float]:
    return ast.literal_eval(re.split("[-_]", url.split("chapter")[-1])[-1])

def _parse_views_chapter(soup):
    s = soup.find_all("span", class_="chapter-view text-nowrap")[-1].text.replace(",", "")
    return parse_views(s)

# def _parse_uploaded(soup):
#     s = soup.find("span", class_="chapter-time text-nowrap").get("title")
#     return parse_date(s, "%b %d,%Y %H:%M")

class HomeStoryTooltip:
    __slots__ = ("id", "name", "other_names", "authors", "genres", "description", "update_time")

    def __init__(self, data: dict):
        self.id: int = data["id"]
        self.name: str = data["name"]
        self.other_names: list[str] = split_at(data["nameother"], ";")
        self.authors: list[str] = split_at(data["author"], ",")
        self.genres: list[str] = split_at(data["genres"], ",")
        self.description: str = unescape_html(data["description"])
        self.update_time: dt.datetime = parse_date(data["updatetime"], "%b %d,%Y - %H:%M")

class SearchResult(BaseModel):
    title: str
    url: str
    icon_url: str
    authors: list[str]
    rating: float
    views: int
    # updated: dt.datetime

    @property
    async def story_page(self) -> "StoryPage":
        return await get_story_page(self.url)

    @property
    async def chapter_list(self) -> list[Chapter]:
        story = await self.story_page
        return story.chapter_list

    @staticmethod
    def from_soup(soup):
        return SearchResult(
            title=_parse_title_search(soup),
            url=_parse_url(soup),
            icon_url=_parse_icon_url_search(soup),
            authors=_parse_authors_search(soup),
            rating=_parse_rating(soup),
            views=_parse_views_search(soup),
            # updated=_parse_updated_search(soup)
        )

def _parse_title_search(soup):
    return soup.find(class_="item-img").get("title")

def _parse_url(soup):
    return soup.find(class_="item-img").get("href")

def _parse_icon_url_search(soup):
    return soup.find("img", class_="img-loading").get("src")

def _parse_authors_search(soup):
    authors = soup.find("span", class_="text-nowrap item-author")
    return split_at(authors.text, ",") if authors else []

def _parse_rating(soup):
    return float(soup.find("em", class_="item-rate").text)

def _parse_views_search(soup):
    s = soup.find_all("span", class_="text-nowrap item-time")[-1].text
    number_string = s.replace("View : ", "").replace(",", "")
    return parse_views(number_string)

# def _parse_updated_search(soup):
#     s = soup.find("span", class_="text-nowrap item-time").text
#     return parse_date(s, "Updated : %b %d,%Y - %H:%M")

class StoryPage(BaseModel):
    url: str
    title: str
    icon_url: str
    description: str
    genres: list[str]
    views: int
    authors: list[str]
    # updated: dt.datetime
    chapter_list: list[Chapter]

    @staticmethod
    def from_soup(url: str, soup) -> "StoryPage":
        return StoryPage(
            url=url,
            title=_parse_title(soup),
            icon_url=_parse_icon_url(soup),
            description=_parse_description(soup),
            genres=_parse_genres(soup),
            views=_parse_views(soup),
            authors=_parse_authors(soup),
            # updated=_parse_updated(soup),
            chapter_list=_parse_chapters(soup)
        )

def _parse_title(soup):
    return soup.find(class_="story-info-right").find("h1").text.strip()

def _parse_icon_url(soup):
    return soup.find("div", class_="story-info-left").find("img", class_="img-loading").get("src")

def _parse_description(soup):
    return unescape_html(soup.find("div", class_="panel-story-info-description").text)

def _parse_authors(soup):
    authors_row = soup.find("i", class_="info-author").findNext("td", class_="table-value")
    return [e.strip() for e in authors_row.text.split(" - ")]

def _parse_genres(soup):
    genres_row = soup.find("i", class_="info-genres").findNext("td", class_="table-value")
    genres = genres_row.find_all("a", class_="a-h")
    return [e.text.strip() for e in genres]

# def _parse_updated(soup) -> dt.datetime:
#     values = soup.find("div", class_="story-info-right-extent").find_all("span", class_="stre-value")
#     return parse_date(values[0].text.strip(), "%b %d,%Y - %H:%M %p")

def _parse_views(soup) -> int:
    values = soup.find("div", class_="story-info-right-extent").find_all("span", class_="stre-value")
    s = values[1].text.strip().replace(",", "")
    return parse_views(s)

def _parse_chapters(soup) -> list[Chapter]:
    panels = soup.find(class_="panel-story-chapter-list")
    return [Chapter.from_soup(ele) for ele in panels.find_all(class_="a-h")[::-1] if ele is not None]