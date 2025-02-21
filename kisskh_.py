import aiohttp
from typing import Any, Dict, List
from pydantic import BaseModel, Field, RootModel
from quickjs import Context as quickjsContext
from bs4 import BeautifulSoup as BS
import re

class Episode(BaseModel):
    id: int
    number: float
    sub: int

class Drama(BaseModel):
    description: str
    release_date: str = Field(..., alias="releaseDate")
    trailer: str
    country: str
    status: str
    type: str
    next_ep_date_id: int = Field(..., alias="nextEpDateID")
    episodes: List[Episode]
    episodes_count: int = Field(..., alias="episodesCount")
    label: Any
    favorite_id: int = Field(..., alias="favoriteID")
    thumbnail: str
    id: int
    title: str

    def __init__(self, **data: Any) -> None:
        data["episodes"] = sorted(data["episodes"], key=lambda episode: episode["number"])
        super().__init__(**data)

    def get_episodes_ids(self) -> Dict[int, int]:
        episode_ids = {}
        for episode in self.episodes:
            episode_ids[episode.number] = episode.id
        return episode_ids

class DramaInfo(BaseModel):
    episodes_count: int = Field(..., alias="episodesCount")
    label: str
    favorite_id: int = Field(..., alias="favoriteID")
    thumbnail: str
    id: int
    title: str

class Search(RootModel):
    root: List[DramaInfo]

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

    def __len__(self) -> int:
        return len(self.root)

class SubItem(BaseModel):
    src: str
    label: str
    land: str
    default: bool

class Sub(RootModel):
    root: List[SubItem]

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

    def __len__(self) -> int:
        return len(self.root)

class KissKHApi:
    def __init__(self, url: str):
        self.base_url = url

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

    async def _request(self, url: str, json: bool=True):
        """Helper for all the request call

        :param url: url to do the get request on
        :return: reponse for a specific get request
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    if not json: return await response.text()
                    content_type = None
                    if response.content_type == "image/png":
                        content_type = "image/png"
                    return await response.json(content_type=content_type)

    async def get_episode_ids(self, drama_id: int) -> Dict[int, int]:
        """Get episode ids for a specific drama

        :param drama_id: drama id
        :param start: starting episode, defaults to 1
        :param stop: ending episode, defaults to sys.maxsize
        :return: returns episode id for starting episode till ending episode range
        """
        drama_api_url = self._drama_api_url(drama_id=drama_id)
        response = await self._request(drama_api_url)
        drama = Drama.parse_obj(response)
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
        subtitles: Sub = Sub.parse_obj(response)
        filtered_subtitles: List[SubItem] = []
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
        return Search.parse_obj(response)

    async def get_stream_url(self, episode_id: int) -> str:
        """Stream video url for specific episode

        :param episode_id: episode id
        :return: m3u8 stream url for that episode
        """
        kkey = await self._get_token(episode_id)
        stream_api_url = self._stream_api_url(episode_id, kkey)
        response = await self._request(stream_api_url)
        # m3u8_list = await self._parse_m3u8_links(response.get("Video"))
        # return m3u8_list
        return response.get("Video")

    async def get_drama(self, drama_id: int):
        drama_api_url = self._drama_api_url(drama_id=drama_id)
        response = await self._request(drama_api_url)
        return Drama.parse_obj(response)

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
    
    async def _parse_m3u8_links(self, master_m3u8_link):
        '''
        parse master m3u8 data and return dict of resolutions and m3u8 links
        '''
        m3u8_links = []
        base_url = '/'.join(master_m3u8_link.split('/')[:-1])
        master_m3u8_data = await self._request(master_m3u8_link, False) # NOTE: removed referer
        print(f'Master m3u8 data: {master_m3u8_data}')

        _regex_list = lambda data, rgx, grp: [ url.group(grp) for url in re.finditer(rgx, data) ]
        _full_link = lambda link: link if link.startswith('http') else base_url + '/' + link
        resolutions = _regex_list(master_m3u8_data, r'RESOLUTION=(\d+x\d+)', 1)
        resolution_names = _regex_list(master_m3u8_data, 'NAME="(.*)"', 1)
        if len(resolution_names) == 0:
            resolution_names = [ res.lower().split('x')[-1] for res in resolutions ]
        resolution_links = _regex_list(master_m3u8_data, '(.*)m3u8', 0)
        print(f'Resolutions data: {resolutions}, {resolution_names}, {resolution_links}')

        if len(resolution_links) == 0:
            # check for original keyword in the link, or if '#EXT-X-ENDLIST' in m3u8 data
            master_is_child = re.search('#EXT-X-ENDLIST', master_m3u8_data)
            if 'original' in master_m3u8_link or master_is_child:
                m3u8_links.append({
                    'downloadLink': master_m3u8_link,
                    'downloadType': 'hls'
                })

            return m3u8_links

        # calculate duration from any resolution, as it is same for all resolutions
        for _res, _pixels, _link in zip(resolution_names, resolutions, resolution_links):
            # prepend base url if it is relative url
            m3u8_link = _full_link(_link)
            m3u8_links.append({
                'resolution': _res.replace('p',''),
                'resolution_size': _pixels,
                'downloadLink': m3u8_link,
                'downloadType': 'hls',
            })

        return m3u8_links