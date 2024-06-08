from bs4 import BeautifulSoup
import re
import aiohttp

BASE_URL = "https://kissasian.lu"

async def req_real(url: str, params: dict=None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                return await response.read()
            
async def req_real_post(url: str, data: dict=None):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data) as response:
            if response.status == 200:
                return await response.read()

async def get_soup(url):
    response = await req_real(url)
    soup = BeautifulSoup(response, 'html.parser')
    return soup, response

async def search(query: str):
    url = BASE_URL + "/Search/SearchSuggest"
    params = {'type': 'drama',
              'keyword': query}
    response = await req_real_post(url, params)
    search_results = []
    soup = BeautifulSoup(response, 'html.parser')
    for lis in soup.findAll("a"):
        temp = {
            "id": lis.get("href").replace("/Drama/", ""),
            "title": lis.text,
            "url": f'{BASE_URL}{lis.get("href")}'
        }
        search_results.append(temp)

    return {
        "query": query,
        "response_length": len(soup.findAll("a")),
        "data": search_results
    }

async def series_info(query: str):
    url = BASE_URL + "/Drama/" + query
    soup, response = await get_soup(url)
    other_names = []
    genres = []
    casts = []
    eps_list = []
    if response:
        for othername in (soup.find("div", class_="section group").find("p").findAll("a")):
            other_names.append(othername.text)

        for genre in soup.find("div", class_="section group").findAll("a", class_="dotUnder"):
            genres.append(genre.text)

        for ele in (soup.findAll("div", class_="actor-info")):
            casts.append(ele.text.strip())

        content_list = soup.find("ul", class_="list")
        no_eps = len(content_list.findAll('a'))
        for ele in content_list.findAll('a'):
            eps_list.append(f"{BASE_URL}{ele.get('href')}")

        content = {
            "title": soup.find("div", class_="heading").text,
            "img_url": f'{BASE_URL}/{soup.find("div", class_="col cover").find("img").get("src")}',
            "other_names": other_names,
            "genre": genres,
            "casts": casts,
            "no_eps": no_eps,
            "episode_links": eps_list
        }
        return content

async def get_stream(series_id: str, ep_no: int):
    url = BASE_URL + f"/Drama/{series_id}/Episode-{str(ep_no)}"
    soup, response = await get_soup(url)
    if response:
        try:
            vidmoly_url = soup.find("iframe", {"id": "mVideo"}).attrs['src']
            vid_soup, vid_res = await get_soup(vidmoly_url)
        except:
            return # "Invalid Input"
        if vid_res:
            pattern = r'file:"(https://[^"]+)"'

            # Use re.search() to find the first match in the text
            match = re.search(pattern, vid_res.decode('utf-8'))

            # Check if a match was found and extract the URL
            if match:
                url_main = match.group(1)
                temp =  {"series_id":series_id,"ep_no":ep_no,"stream_url":url_main}
                return temp
            else:
                return # "Cannot find any url"

async def latest():
    soup, response = await get_soup(BASE_URL)
    latest_res = []
    if response:
        for ele in (soup.find("div", class_="item-list").findAll("div", class_="info")):
            ep_url = f'{BASE_URL}/{ele.find("a").get("href")}'
            latest_series = ele.find("a").text.strip().split("\n")
            temp = {
                "title": latest_series[0],
                "latest_ep": latest_series[1],
                "ep_url": ep_url
            }
            latest_res.append(temp)

        return {
            "list_len":len(latest_res),
            "data":latest_res
        }

async def sortby(query:str, page:int):
    url = BASE_URL+f"/DramaList/{query}/?page={str(page)}"
    soup, response = await get_soup(url)
    if response:
        if ("Not found" not in str(response)):
            sort_by_list = []
            for ele in (soup.find("div", class_="item-list").findAll("div", class_="item")):
                temp={
                    "title":ele.findNext("img").get("title"),
                    "url":f'{BASE_URL}{ele.findNext("a").get("href")}',
                    "img_url":f'{BASE_URL}{ele.findNext("img").get("src")}',
                }
                sort_by_list.append(temp)

            return {
                "query":query,
                "page":page,
                "list_count":len(sort_by_list),
                "data":sort_by_list
            }
    else:
        return # "Invaild Input"

async def sortbycountry(query:str, page:int):
    url = BASE_URL+f"/Country/{query}/?page={str(page)}"
    soup, response = await get_soup(url)
    print(soup)
    if response:
        if ("Not found" not in str(response)):
            sort_by_list = []
            for ele in (soup.find("div", class_="item-list").findAll("div", class_="col cover")):
                temp={
                    "title":ele.findNext("img").get("title"),
                    "url":f'{BASE_URL}{ele.findNext("a").get("href")}',
                    "img_url":f'{BASE_URL}{ele.findNext("img").get("src")}',
                }
                sort_by_list.append(temp)

            return {
                "query":query,
                "page":page,
                "list_count": len(sort_by_list),
                "data":sort_by_list
            }
    else:
        return # "Invaild Input"

async def sortbygenre(query:str, page:int):
    url = BASE_URL+f"/Genre/{query}/?page={str(page)}"
    soup, response = await get_soup(url)
    if response:
        if ("Not found" not in str(response)):
            sort_by_list = []
            for ele in (soup.find("div", class_="item-list").findAll("div", class_="item")):
                temp={
                    "title":ele.findNext("img").get("title"),
                    "url":f'{BASE_URL}{ele.findNext("a").get("href")}',
                    "img_url":f'{BASE_URL}{ele.findNext("img").get("src")}',
                }
                sort_by_list.append(temp)

            return {
                "query":query,
                "page":page,
                "list_count": len(sort_by_list),
                "data":sort_by_list
            }
        else:
            return # "Invaild Input"