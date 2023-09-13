import re
import discord
from httpclient import HttpClient
from bs4 import BeautifulSoup as BS
from urllib import parse as p
import base64
from Crypto.Cipher import AES
import hashlib
import json
from Crypto.Util.Padding import unpad

client, client0 = HttpClient(), HttpClient()
title, url, aid, mv_tv, poster = 0, 1, 2, 3, 4
pagelimit = 12
domain = "https://sflix.se"

async def Sflix(msg: discord.Message, arg: str):
    result = results(searchQuery(arg))
    embed = buildSearch(arg, result, 0)
    await msg.edit(content=None, embed = embed, view = MyView(result, arg, 0))

# embed builders
def detail(result) -> list:
    req = client.get(f"{domain}{result[1]}")
    soup = BS(req, "lxml")
    desc = soup.find("div", {"class": "description"}).get_text()
    items = soup.find("div", {"class": "elements"}).find_all("div", {"class": "row-line"})
    details = []
    for item in items:
        detail = re.sub(r"^\s+|\s+$|\s+(?=\s)", "", item.get_text().split(": ")[1])
        details.append(detail)
    return [desc] + details # [desc, rel, genre, casts, dur, country, prod]
def detailed(embed: discord.Embed, details: list):
    embed.add_field(name="Released", value=details[1])
    embed.add_field(name="Duration", value=details[4])
    embed.add_field(name="Country", value=details[5])
    embed.add_field(name="Genre", value=details[2])
    embed.add_field(name="Casts", value=details[3])
    embed.add_field(name="Production", value=details[6])
def buildMovie(result) -> discord.Embed():
    details = detail(result)
    embed = discord.Embed(title=result[title], description=details[0], color=0x00ff00)
    valid_url = p.quote(result[poster], safe=":/")
    embed.set_image(url = valid_url)
    detailed(embed, details)
    embed.set_footer(text="Note: Play the file using VLC/MPV media player :)")
    return embed
def buildSeasons(season_ids, result) -> discord.Embed():
    details = detail(result)
    embed = discord.Embed(title=result[title], description=details[0], color=0x00ff00)
    valid_url = p.quote(result[poster], safe=":/")
    embed.set_image(url = valid_url)
    detailed(embed, details)
    embed.add_field(name="Seasons", value=len(season_ids))
    return embed
def buildEpisodes(episodes, season, result) -> discord.Embed():
    embed = discord.Embed(title=f"{result[title]}", description=f"Season {season}", color=0x00ff00)
    valid_url = p.quote(result[poster], safe=":/")
    embed.set_image(url = valid_url)
    details = detail(result)
    detailed(embed, details)
    embed.add_field(name="Episodes", value=len(episodes))
    embed.set_footer(text="Note: Play the file using VLC/MPV media player :)")
    return embed
def buildSearch(arg: str, result: list, index: int) -> discord.Embed():
    embed = discord.Embed(title=f"Search results: `{arg}`", description=f"{len(result)} found", color=0x00ff00)
    # embed.set_thumbnail(url = bot.user.avatar)
    i = index
    while i < len(result):
        if (i < index+pagelimit): embed.add_field(name=f"[{i + 1}] {result[i][title]}", value=f"{result[i][url]}")
        i += 1
    return embed

# actvid
def get_max_page(length):
    if length % pagelimit != 0: return length - (length % pagelimit)
    return length - pagelimit
def parse(txt: str) -> str:
    return re.sub(r"\W+", "-", txt.lower())
def searchQuery(q) -> str:
    return client.get(f"{domain}/search/{parse(q)}").text
def results(html: str) -> list:
    soup = BS(html, "lxml")
    img = [i["data-src"] for i in soup.select(".film-poster-img")]
    urls = [i["href"] for i in soup.select(".film-poster-ahref")]
    mov_or_tv = [
        "MOVIE" if i["href"].__contains__("/movie/") else "TV"
        for i in soup.select(".film-poster-ahref")
    ]
    title = [
        re.sub(
            pattern="full|/tv/|/movie/|hd|watch|[0-9]{2,}",
            repl="",
            string=" ".join(i.split("-")),
        )
        for i in urls
    ]
    ids = [i.split("-")[-1] for i in urls]
    return [list(sublist) for sublist in zip(title, urls, ids, mov_or_tv, img)]

# search
class MyView(discord.ui.View):
    def __init__(self, result: list, arg: str, index: int):
        super().__init__(timeout=None)
        last_index = min(index + pagelimit, len(result))
        self.add_item(SelectChoice(index, result))
        if index - pagelimit > -1:
            self.add_item(ButtonNextSearch(arg, result, 0, "⏪"))
            self.add_item(ButtonNextSearch(arg, result, index - pagelimit, "◀️"))
        if not last_index == len(result):
            self.add_item(ButtonNextSearch(arg, result, last_index, "▶️"))
            max_page = get_max_page(len(result))
            self.add_item(ButtonNextSearch(arg, result, max_page, "⏩"))

class SelectChoice(discord.ui.Select):
    def __init__(self, index: int, result: list):
        super().__init__(placeholder=f"{min(index + pagelimit, len(result))}/{len(result)} found")
        i, self.result = index, result
        while i < len(result): 
            if (i < index+pagelimit): self.add_option(label=f"[{i + 1}] {result[i][title]}", description=f"{result[i][url]}", value=i)
            if (i == index+pagelimit): break
            i += 1

    async def callback(self, interaction: discord.Interaction):
        if self.result[int(self.values[0])][mv_tv] == "TV":
            r = client.get(f"{domain}/ajax/v2/tv/seasons/{self.result[int(self.values[0])][aid]}")
            season_ids = [i["data-id"] for i in BS(r, "lxml").select(".dropdown-item")]
            embed = buildSeasons(season_ids, self.result[int(self.values[0])])
            await interaction.response.defer()
            await interaction.message.edit(embed = embed, view = MyView2(self.result[int(self.values[0])], season_ids, 0))
        else:
            sid = server_id(self.result[int(self.values[0])][aid])
            iframe_url, tv_id = get_link(sid)
            iframe_link, iframe_id = rabbit_id(iframe_url)
            await interaction.response.defer()
            try:
                url = cdn_url(iframe_link, iframe_id)
                embed = buildMovie(self.result[int(self.values[0])])
                await interaction.message.edit(embed=embed, view=None, content=f"[{self.result[int(self.values[0])][title]}]({url})")
            except Exception as e: await interaction.message.edit(e, view=None)
        

# legacy code
class ButtonSelect(discord.ui.Button):
    def __init__(self, index: int, result: list, row: int):
        super().__init__(label=index, style=discord.ButtonStyle.primary, row=row)
        self.result = result
    
    async def callback(self, interaction: discord.Interaction):
        if self.result[mv_tv] == "TV":
            r = client.get(f"{domain}/ajax/v2/tv/seasons/{self.result[aid]}")
            season_ids = [i["data-id"] for i in BS(r, "lxml").select(".dropdown-item")]
            embed = buildSeasons(season_ids, self.result)
            await interaction.response.defer()
            await interaction.message.edit(embed = embed, view = MyView2(self.result, season_ids, 0))
        else:
            sid = server_id(self.result[aid])
            iframe_url, tv_id = get_link(sid)
            iframe_link, iframe_id = rabbit_id(iframe_url)
            await interaction.response.defer()
            try:
                url = cdn_url(iframe_link, iframe_id)
                embed = buildMovie(self.result)
                await interaction.message.edit(embed=embed, view=None, content=f"[{self.result[title]}]({url})")
            except Exception as e: await interaction.message.edit(e, view=None)
            
class ButtonNextSearch(discord.ui.Button):
    def __init__(self, arg: str, result: list, index: int, l: str):
        super().__init__(emoji=l, style=discord.ButtonStyle.success)
        self.result, self.index, self.arg = result, index, arg

    async def callback(self, interaction: discord.Interaction):
        embed = buildSearch(self.arg, self.result, self.index)
        await interaction.response.defer()
        await interaction.message.edit(embed = embed, view = MyView(self.result, self.arg, self.index))

# season
class MyView2(discord.ui.View):
    def __init__(self, result: list, season_ids: list, index: int):
        super().__init__(timeout=None)
        i = index
        column, row, last_index = 0, -1, len(season_ids)
        while i < len(season_ids):
            if column % 4 == 0: row += 1
            if (i < index+pagelimit): self.add_item(ButtonSelect2(i + 1, season_ids[i], result, row))
            if (i == index+pagelimit): last_index = i
            i += 1
            column += 1
        if index - pagelimit > -1:
            self.add_item(ButtonNextSeason(result, season_ids, 0, 4, "⏪"))
            self.add_item(ButtonNextSeason(result, season_ids, index - pagelimit, 4, "◀️"))
        if not last_index == len(season_ids):
            self.add_item(ButtonNextSeason(result, season_ids, last_index, 4, "▶️"))
            max_page = get_max_page(len(season_ids))
            self.add_item(ButtonNextSeason(result, season_ids, max_page, 4, "⏩"))

class ButtonSelect2(discord.ui.Button):
    def __init__(self, index: int, season_id: str, result: list, row: int):
        super().__init__(label=index, style=discord.ButtonStyle.primary, row=row)
        self.result, self.season_id, self.index = result, season_id, index
    
    async def callback(self, interaction: discord.Interaction):
        z = f"{domain}/ajax/v2/season/episodes/{self.season_id}"
        rf = client.get(z)
        episodes = [i["data-id"] for i in BS(rf, "lxml").select(".episode-item")]
        embed = buildEpisodes(episodes, self.index, self.result)
        await interaction.response.defer()
        await interaction.message.edit(embed = embed, view = MyView3(self.season_id, episodes, self.result, 0, self.index))

class ButtonNextSeason(discord.ui.Button):
    def __init__(self, result: list, season_ids: list, index: int, row: int, l: str):
        super().__init__(emoji=l, style=discord.ButtonStyle.success, row=row)
        self.result, self.season_ids, self.index = result, season_ids, index
    
    async def callback(self, interaction: discord.Interaction):
        embed = buildSeasons(self.season_ids, self.result)
        await interaction.response.defer()
        await interaction.message.edit(embed = embed, view = MyView2(self.result, self.season_ids, self.index))

# episode
class MyView3(discord.ui.View):
    def __init__(self, season_id: str, episodes: list, result: list, index: int, season: int):
        super().__init__(timeout=None)
        i = index
        column, row, last_index = 0, -1, len(episodes)
        while i < len(episodes):
            if column % 4 == 0: row += 1
            if (i < index+pagelimit): self.add_item(ButtonSelect3(i + 1, season_id, episodes[i], season, result[title], row))
            if (i == index+pagelimit): last_index = i
            i += 1
            column += 1
        if index - pagelimit > -1:
            self.add_item(ButtonNextEp(season_id, episodes, result, 0, season, 4, "⏪"))
            self.add_item(ButtonNextEp(season_id, episodes, result, index - pagelimit, season, 4, "◀️"))
        if not last_index == len(episodes):
            self.add_item(ButtonNextEp(season_id, episodes, result, last_index, season, 4, "▶️"))
            max_page = get_max_page(len(episodes))
            self.add_item(ButtonNextEp(season_id, episodes, result, max_page, season, 4, "⏩"))

class ButtonNextEp(discord.ui.Button):
    def __init__(self, season_id: str, episodes: list, result: list, index: int, season: int, row: int, l: str):
        super().__init__(emoji=l, style=discord.ButtonStyle.success, row=row)
        self.season_id, self.episodes, self.result, self.index, self.season = season_id, episodes, result, index, season
    
    async def callback(self, interaction: discord.Interaction):
        embed = buildEpisodes(self.episodes, self.season, self.result)
        await interaction.response.defer()
        await interaction.message.edit(embed = embed, view = MyView3(self.season_id, self.episodes, self.result, self.index, self.season))

class ButtonSelect3(discord.ui.Button):
    def __init__(self, index: int, season_id: str, episode: str, season: int, title: str, row: int):
        super().__init__(label=index, style=discord.ButtonStyle.primary, row=row)
        self.episode, self.season_id, self.season, self.title, self.index = episode, season_id, season, title, index
    
    async def callback(self, interaction: discord.Interaction):
        sid = ep_server_id(self.episode)
        iframe_url, tv_id = get_link(sid)
        iframe_link, iframe_id = rabbit_id(iframe_url)
        await interaction.response.defer()
        try:
            url = cdn_url(iframe_link, iframe_id)
            await interaction.followup.send(f"{self.title} [S{self.season}E{self.index}]({url})")
        except Exception as e: await interaction.message.edit(e, view=None)

# sflix functions
def server_id(mov_id: str) -> str:
    req = client.get(f"{domain}/ajax/movie/episodes/{mov_id}")
    soup = BS(req, "lxml")
    return [i["data-id"] for i in soup.select(".link-item")][0]    
def ep_server_id(ep_id: str) -> str:
    req = client.get(f"{domain}/ajax/v2/episode/servers/{ep_id}/#servers-list")
    soup = BS(req, "lxml")
    return [i["data-id"] for i in soup.select(".link-item")][0]
def get_link(thing_id: str) -> tuple:
    req = client.get(f"{domain}/ajax/sources/{thing_id}").json()["link"]
    print(req)
    return req, rabbit_id(req)
def rabbit_id(url: str) -> tuple:
    parts = p.urlparse(url, allow_fragments=True, scheme="/").path.split("/")
    return (
        re.findall(r"(https:\/\/.*\/embed-4)", url)[0].replace(
            "embed-4", "ajax/embed-4/"), 
        parts[-1],
    )

# actvid function
def cdn_url(final_link: str, rabb_id: str) -> str:
    client0.set_headers({"X-Requested-With": "XMLHttpRequest"})
    data = client0.get(f"{final_link}getSources?id={rabb_id}").json()
    n = decryption(data["sources"])
    return n[0]["file"]
def decryption(string):
    key, new_string = key_extraction(string, gh_key())
    decryption_key = gen_key(
        base64_decode_array(new_string)[8:16], key.encode("utf-8")
    )
    main_decryption = aes_decrypt(decryption_key, new_string)
    return json.loads(main_decryption)
def key_extraction(string, table):
    decrypted_key = []
    offset = 0
    encrypted_string = string

    for start, end in table:
        decrypted_key.append(encrypted_string[start - offset:end - offset])
        encrypted_string = (
            encrypted_string[:start - offset] + encrypted_string[end - offset:]
        )
        offset += end - start

    return "".join(decrypted_key), encrypted_string
def gh_key():
    response_key = client.get('https://github.com/enimax-anime/key/blob/e4/key.txt').json()
    key = response_key["payload"]["blob"]["rawLines"][0]
    key = json.loads(key)
    return key
def gen_key(salt, secret):
    key = md5(secret + salt)
    current_key = key
    while len(current_key) < 48:
        key = md5(key + secret + salt)
        current_key += key
    return current_key
def md5(input_bytes):
    return hashlib.md5(input_bytes).digest()
def base64_decode_array(encoded_str):
    return bytearray(base64.b64decode(encoded_str))
def aes_decrypt(decryption_key, source_url):
    cipher_data = base64_decode_array(source_url)
    encrypted = cipher_data[16:]
    AES_CBC = AES.new(
        decryption_key[:32], AES.MODE_CBC, iv=decryption_key[32:]
    )
    decrypted_data = unpad(
        AES_CBC.decrypt(encrypted), AES.block_size
    )
    return decrypted_data.decode("utf-8")