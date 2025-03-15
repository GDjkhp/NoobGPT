from typing import Any, Dict, List
from quickjs import Context as quickjsContext
from bs4 import BeautifulSoup as BS
from curl_cffi.requests import AsyncSession

class Episode:
    def __init__(self, id: int, number: float, sub: int):
        self.id = id
        self.number = number
        self.sub = sub

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Episode':
        return cls(
            id=data["id"],
            number=data["number"],
            sub=data["sub"]
        )

class Drama:
    def __init__(
        self,
        description: str,
        release_date: str,
        trailer: str,
        country: str,
        status: str,
        type: str,
        next_ep_date_id: int,
        episodes: List[Episode],
        episodes_count: int,
        label: Any,
        favorite_id: int,
        thumbnail: str,
        id: int,
        title: str
    ):
        self.description = description
        self.release_date = release_date
        self.trailer = trailer
        self.country = country
        self.status = status
        self.type = type
        self.next_ep_date_id = next_ep_date_id
        self.episodes = episodes
        self.episodes_count = episodes_count
        self.label = label
        self.favorite_id = favorite_id
        self.thumbnail = thumbnail
        self.id = id
        self.title = title

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Drama':
        # Sort episodes by episode number
        episode_data = sorted(data["episodes"], key=lambda episode: episode["number"])
        episodes = [Episode.from_dict(ep) for ep in episode_data]
        
        return cls(
            description=data["description"],
            release_date=data["releaseDate"],
            trailer=data["trailer"],
            country=data["country"],
            status=data["status"],
            type=data["type"],
            next_ep_date_id=data["nextEpDateID"],
            episodes=episodes,
            episodes_count=data["episodesCount"],
            label=data["label"],
            favorite_id=data["favoriteID"],
            thumbnail=data["thumbnail"],
            id=data["id"],
            title=data["title"]
        )

    def get_episodes_ids(self) -> Dict[int, int]:
        episode_ids = {}
        for episode in self.episodes:
            episode_ids[episode.number] = episode.id
        return episode_ids

class DramaInfo:
    def __init__(
        self,
        episodes_count: int,
        label: str,
        favorite_id: int,
        thumbnail: str,
        id: int,
        title: str
    ):
        self.episodes_count = episodes_count
        self.label = label
        self.favorite_id = favorite_id
        self.thumbnail = thumbnail
        self.id = id
        self.title = title

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DramaInfo':
        return cls(
            episodes_count=data["episodesCount"],
            label=data["label"],
            favorite_id=data["favoriteID"],
            thumbnail=data["thumbnail"],
            id=data["id"],
            title=data["title"]
        )

class Search:
    def __init__(self, dramas: List[DramaInfo]):
        self.dramas = dramas

    def __iter__(self):
        return iter(self.dramas)

    def __getitem__(self, item):
        return self.dramas[item]

    def __len__(self) -> int:
        return len(self.dramas)

    @classmethod
    def from_list(cls, data: List[Dict[str, Any]]) -> 'Search':
        dramas = [DramaInfo.from_dict(item) for item in data]
        return cls(dramas)

class SubItem:
    def __init__(
        self,
        src: str,
        label: str,
        land: str,
        default: bool
    ):
        self.src = src
        self.label = label
        self.land = land
        self.default = default

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubItem':
        return cls(
            src=data["src"],
            label=data["label"],
            land=data["land"],
            default=data["default"]
        )

class Sub:
    def __init__(self, subtitles: List[SubItem]):
        self.subtitles = subtitles

    def __iter__(self):
        return iter(self.subtitles)

    def __getitem__(self, item):
        return self.subtitles[item]

    def __len__(self) -> int:
        return len(self.subtitles)

    @classmethod
    def from_list(cls, data: List[Dict[str, Any]]) -> 'Sub':
        subtitles = [SubItem.from_dict(item) for item in data]
        return cls(subtitles)

class KissKHApi:
    def __init__(self, url: str):
        self.base_url = url
        self.session = AsyncSession(impersonate='chrome')

    def set_base_url(self, url: str):
        self.base_url = url

    def _drama_api_url(self, drama_id: int) -> str:
        """API endpoint for drama details

        :param drama_id: drama id
        :return: api url for a specific drama
        """
        return f"{self.base_url}/api/DramaList/Drama/{drama_id}"

    def _search_api_url(self, query: str) -> str:
        """API endpoint for drama search details

        :param query: search string
        :return: api url to get search result
        """
        return f"{self.base_url}/api/DramaList/Search?q={query}"

    def _subtitle_api_url(self, episode_id: int) -> str:
        """API endpoint for subtitles

        :param episode_id: episode id
        :return: api url for subtitles for a specific episode
        """
        return f"{self.base_url}/api/Sub/{episode_id}"

    def _stream_api_url(self, episode_id: int, kkey: str) -> str:
        """API endpoint for stream url

        :param episode_id: episode id
        :return: api url for getting stream video details
        """
        return f"{self.base_url}/api/DramaList/Episode/{episode_id}.png?kkey={kkey}"

    async def _request(self, url: str, json: bool=True, content_type: str=None) -> Any:
        """Helper for all the request call

        :param url: url to do the get request on
        :return: reponse for a specific get request
        """
        response = await self.session.get(url)
        print(response.content.decode())
        if not json: return response.content.decode()
        if content_type: return response.json(content_type=content_type)
        return response.json()

    async def get_episode_ids(self, drama_id: int) -> Dict[int, int]:
        """Get episode ids for a specific drama

        :param drama_id: drama id
        :param start: starting episode, defaults to 1
        :param stop: ending episode, defaults to sys.maxsize
        :return: returns episode id for starting episode till ending episode range
        """
        drama_api_url = self._drama_api_url(drama_id=drama_id)
        response = await self._request(drama_api_url)
        drama = Drama.from_dict(response)
        return drama.get_episodes_ids()

    async def get_subtitles(self, episode_id: int, *language_filter: str) -> List[SubItem]:
        """Get subtitle details for a specific episode

        :param episode_id: episode id
        :param language_filter: multiple language filters like 'en', 'id', 'ar' etc.
        :return: subtitles based on language_filter.
        If 'all' is present in language filter, then all subtitles are returned
        """
        subtitle_api_url = self._subtitle_api_url(episode_id=episode_id)
        response = await self._request(subtitle_api_url)
        subtitles = Sub.from_list(response)
        filtered_subtitles = []
        if "all" in language_filter:
            filtered_subtitles.extend(subtitle for subtitle in subtitles)
        elif language_filter:
            filtered_subtitles.extend(subtitle for subtitle in subtitles if subtitle.land in language_filter)
        return filtered_subtitles

    async def search_dramas_by_query(self, query: str) -> Search:
        """Get all drama for a specific search query

        :param query: search string
        :return: dramas for that search query
        """
        search_api_url = self._search_api_url(query)
        response = await self._request(search_api_url)
        return Search.from_list(response)

    async def get_stream_url(self, episode_id: int) -> str:
        """Stream video url for specific episode

        :param episode_id: episode id
        :return: m3u8 stream url for that episode
        """
        kkey = await self._get_token(episode_id)
        stream_api_url = self._stream_api_url(episode_id, kkey)
        response = await self._request(stream_api_url, content_type="image/png")
        return response.get("Video")

    async def get_drama(self, drama_id: int):
        drama_api_url = self._drama_api_url(drama_id=drama_id)
        response = await self._request(drama_api_url)
        return Drama.from_dict(response)

    async def _get_token(self, episode_id: int) -> str:
        '''
        create token required to fetch stream & subtitle links
        '''
        # js code to generate token from kisskh site
        html_content = await self._request(self.base_url, False)
        soup = BS(html_content, 'html.parser')
        common_js_url = f"{self.base_url}/{[ i['src'] for i in soup.select('script') if i.get('src') and 'common' in i['src'] ][0]}"
        token_generation_js_code = await self._request(common_js_url, False)

        # quickjs context for evaluating js code
        quickjs_context = quickjsContext()

        # evaluate js code to generate token
        token = quickjs_context.eval(token_generation_js_code + f'_0x54b991({episode_id}, null, "2.8.10", "62f176f3bb1b5b8e70e39932ad34a0c7", 4830201,  "kisskh", "kisskh", "kisskh", "kisskh", "kisskh", "kisskh")')
        return token