import discord
from bs4 import BeautifulSoup as BS
import aiohttp
from discord.ext import commands
import re
from util_discord import command_check, description_helper, get_guild_prefix, is_valid_uuid
from curl_cffi.requests import AsyncSession
from discord import app_commands

base="https://animepahe.si"
provider="https://gdjkhp.github.io/img/apdoesnthavelogotheysaidapistooplaintheysaid.png"
pagelimit=12
headers = {"cookie": "__ddg2_=", "referer": base}
session = AsyncSession(impersonate='chrome')

# feat: mp4 dl (it just works): https://github.com/justfoolingaround/animdl/blob/master/animdl/core/codebase/providers/animepahe/inner/__init__.py
CHARACTER_MAP = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+/"
KWIK_PARAMS_RE = re.compile(r'\("(\w+)",\d+,"(\w+)",(\d+),(\d+),\d+\)')
KWIK_D_URL = re.compile(r'action="(.+?)"')
KWIK_D_TOKEN = re.compile(r'value="(.+?)"')
regex_extract = lambda rgx, txt, grp: re.search(rgx, txt).group(grp) if re.search(rgx, txt) else False

async def help_anime(ctx: commands.Context):
    if await command_check(ctx, "anime", "media"): return await ctx.reply("command disabled", ephemeral=True)
    p = await get_guild_prefix(ctx)
    sources = [
        f"`{p}pahe` animepahe",
        # f"`{p}aniwatch` hianime",
    ]
    await ctx.reply("\n".join(sources))

async def new_req_old(url: str, headers: dict, json_mode: bool):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json() if json_mode else await response.read()
async def new_req(url: str, headers: dict, json_mode: bool):
    req = await session.get(url, headers=headers)
    return req.json() if json_mode else req.content
def get_string(content, s1, s2):
    slice_2 = CHARACTER_MAP[0:s2]
    acc = 0
    for n, i in enumerate(content[::-1]):
        acc += int(i if i.isdigit() else 0) * s1**n
    k = ""
    while acc > 0:
        k = slice_2[int(acc % s2)] + k
        acc = (acc - (acc % s2)) / s2
    return k or "0"
def decrypt(full_string, key, v1, v2):
    v1, v2 = int(v1), int(v2)
    r = ""
    i = 0
    while i < len(full_string):
        s = ""
        while full_string[i] != key[v2]:
            s += full_string[i]
            i += 1
        j = 0
        while j < len(key):
            s = s.replace(key[j], str(j))
            j += 1
        r += chr(int(get_string(s, v2, 10)) - v1)
        i += 1
    return r
def parse_m3u8_link(text):
    '''
    parse m3u8 link using javascript's packed function implementation
    '''
    x = r"\}\('(.*)'\)*,*(\d+)*,*(\d+)*,*'((?:[^'\\]|\\.)*)'\.split\('\|'\)*,*(\d+)*,*(\{\})"
    try:
        p, a, c, k, e, d = re.findall(x, text)[0]
        p, a, c, k, e, d = p, int(a), int(c), k.split('|'), int(e), {}
    except Exception as e:
        raise Exception('m3u8 link extraction failed. Unable to extract packed args')

    def e(c):
        x = '' if c < a else e(int(c/a))
        c = c % a
        return x + (chr(c + 29) if c > 35 else '0123456789abcdefghijklmnopqrstuvwxyz'[c])

    for i in range(c): d[e(i)] = k[i] or e(i)
    parsed_js_code = re.sub(r'\b(\w+)\b', lambda e: d.get(e.group(0)) or e.group(0), p)

    parsed_link = regex_extract('http.*.m3u8', parsed_js_code, 0)
    if not parsed_link:
        raise Exception('m3u8 link extraction failed. link not found')

    return parsed_link
def soupify(data): return BS(data, "lxml")
def get_max_page(length):
    if length % pagelimit != 0: return length - (length % pagelimit)
    return length - pagelimit
def buildSearch(arg: str, result: list, index: int) -> discord.Embed:
    embed = discord.Embed(title=f"Search results: `{arg}`", description=f"{len(result)} found", color=0x00ff00)
    embed.set_thumbnail(url=provider)
    i = index
    while i < len(result):
        value = f"**{result[i]['type']}** - {result[i]['episodes']} {'episodes' if result[i]['episodes'] > 1 else 'episode'}\n({result[i]['status']})"
        value+= f"\n{result[i]['season']} {result[i]['year']}"
        if (i < index+pagelimit): embed.add_field(name=f"[{i + 1}] `{result[i]['title']}`", value=value)
        i += 1
    return embed
def format_links(string: str, links: list):
    items = string.split('\n', 1)[-1].split(', ')
    result = "**External Links:**\n"
    for i in range(len(links)):
        result += f"[{items[i]}]({links[i]}), "
    return result.rstrip(", ")
def enclose_words(texts: list[str]):
    new_list = []
    for word in texts:
        split = word.split(":")
        split[0] = f"**{split[0]}:**"
        new_list.append(" ".join(split))
    return new_list
def buildAnime(details: dict) -> discord.Embed:
    cook_deets = "\n".join(details["details"])
    cook_deets+= f'\n**Genres:** {", ".join(details["genres"])}'
    embed = discord.Embed(title=details['title'], description=cook_deets, color=0x00ff00)
    embed.set_thumbnail(url=provider)
    embed.set_image(url = details['poster'])
    embed.set_footer(text='Use "Allow CORS: Access-Control-Allow-Origin" extension to stream the content.')
    return embed

async def pahe_search(ctx: commands.Context, arg: str):
    if await command_check(ctx, "anime", "media"): return await ctx.reply("command disabled", ephemeral=True)
    if not arg: return await ctx.reply(f"usage: `{await get_guild_prefix(ctx)}pahe <query>`")
    results = await new_req(f"{base}/api?m=search&q={arg.replace(' ', '+')}", headers, True)
    if not results: return await ctx.reply("none found")
    await ctx.reply(embed=buildSearch(arg, results["data"], 0), view=SearchView(ctx, arg, results["data"], 0))

async def pahe_anime(bot: commands.Bot, ctx: discord.Interaction, selected_session: str):
    ctx: commands.Context = await bot.get_context(ctx)
    if await command_check(ctx, "anime", "media"): return await ctx.reply("command disabled", ephemeral=True)
    if not is_valid_uuid(selected_session):
        return await pahe_search(ctx, selected_session)
    selected, urls, ep_texts = await fetch_anime(selected_session)
    if not selected: return await ctx.reply("no episodes found")
    await ctx.reply(embed=buildAnime(selected), view=EpisodeView(ctx, selected, urls, ep_texts, 0))

class CancelButton(discord.ui.Button):
    def __init__(self, ctx: commands.Context, r: int):
        super().__init__(emoji="❌", style=discord.ButtonStyle.success, row=r)
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.",
                                                           ephemeral=True)
        await interaction.response.defer()
        await interaction.delete_original_response()

class DisabledButton(discord.ui.Button):
    def __init__(self, e: str, r: int):
        super().__init__(emoji=e, style=discord.ButtonStyle.success, disabled=True, row=r)

# search
class nextPage(discord.ui.Button):
    def __init__(self, ctx: commands.Context, arg: str, result: list, index: int, l: str):
        super().__init__(emoji=l, style=discord.ButtonStyle.success)
        self.result, self.index, self.arg, self.ctx = result, index, arg, ctx

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.",
                                                           ephemeral=True)
        await interaction.response.edit_message(embed=buildSearch(self.arg, self.result, self.index),
                                                view=SearchView(self.ctx, self.arg, self.result, self.index))

class SearchView(discord.ui.View):
    def __init__(self, ctx: commands.Context, arg: str, result: list, index: int):
        super().__init__(timeout=None)
        last_index = min(index + pagelimit, len(result))
        self.add_item(SelectChoice(ctx, index, result))
        if index - pagelimit > -1:
            self.add_item(nextPage(ctx, arg, result, 0, "⏪"))
            self.add_item(nextPage(ctx, arg, result, index - pagelimit, "◀️"))
        else:
            self.add_item(DisabledButton("⏪", 1))
            self.add_item(DisabledButton("◀️", 1))
        if not last_index == len(result):
            self.add_item(nextPage(ctx, arg, result, last_index, "▶️"))
            max_page = get_max_page(len(result))
            self.add_item(nextPage(ctx, arg, result, max_page, "⏩"))
        else:
            self.add_item(DisabledButton("▶️", 1))
            self.add_item(DisabledButton("⏩", 1))
        self.add_item(CancelButton(ctx, 1))

class SelectChoice(discord.ui.Select):
    def __init__(self, ctx: commands.Context, index: int, result: list):
        super().__init__(placeholder=f"{min(index + pagelimit, len(result))}/{len(result)} found")
        i, self.result, self.ctx = index, result, ctx
        while i < len(result):
            if (i < index+pagelimit): self.add_option(label=f"[{i + 1}] {result[i]['title']}"[:100], value=i,
                                                      description=f"{result[i]['season']} {result[i]['year']}")
            if (i == index+pagelimit): break
            i += 1

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.",
                                                           ephemeral=True)
        await interaction.response.edit_message(view=None)
        selected, urls, ep_texts = await fetch_anime(self.result[int(self.values[0])]["session"])
        if not selected: return await interaction.edit_original_response(content="no episodes found", embed=None)
        await interaction.edit_original_response(embed=buildAnime(selected), view=EpisodeView(self.ctx, selected, urls, ep_texts, 0))

async def fetch_anime(selected_session):
    r_search = await new_req(f"{base}/api?m=release&id={selected_session}&sort=episode_asc&page=1", headers, True)
    if not r_search.get('data'): return None, None, None

    req = await new_req(f"{base}/play/{selected_session}/{r_search['data'][0]['session']}", headers, False)
    soup = soupify(req)
    items = soup.find("div", {"class": "clusterize-scroll"}).findAll("a")
    urls = [items[i].get("href") for i in range(len(items))]
    ep_texts = [items[i].text for i in range(len(items))]

    req = await new_req(f"{base}/anime/{selected_session}", headers, False)
    soup = soupify(req)
    selected = {}

    details = soup.find("div", {"class": "anime-info"}).findAll("p")
    external = soup.find("p", {"class": "external-links"}).findAll("a")
    genres = soup.find("div", {"class": "anime-genre"}).findAll("li")
    thumbnail = soup.find("div", {"class": "anime-poster"}).findAll("img")
    title = soup.find("div", {"class": "title-wrapper"}).findAll("span")

    selected["genres"] = [re.sub(r"^\s+|\s+$|\s+(?=\s)", "", genres[i].text) for i in range(len(genres))]
    not_final = [re.sub(r"^\s+|\s+$|\s+(?=\s)", "", details[i].text) for i in range(len(details))]
    externals = [external[i].get("href").replace("//", "https://") for i in range(len(external))]
    selected["details"] = enclose_words(not_final)
    selected["details"][len(selected["details"])-1] = format_links(selected["details"][len(selected["details"])-1], externals)
    selected["poster"] = thumbnail[0].get("data-src")
    selected["title"] = title[0].text

    return selected, urls, ep_texts

async def pahe_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    if not current: return []
    results = await new_req(f"{base}/api?m=search&q={current.replace(' ', '+')}", headers, True)
    if not results: return []
    return [
        app_commands.Choice(name=f"{anime['title']} [{anime['type']} - {anime['episodes']} {'episodes' if anime['episodes'] > 1 else 'episode'} / {anime['season']} {anime['year']}]"[:100],
                            value=anime["session"]) for anime in results["data"]
    ][:25]

# episode
class nextPageEP(discord.ui.Button):
    def __init__(self, ctx: commands.Context, details: list, index: int, row: int, l: str, urls: list, ep_texts: list):
        super().__init__(emoji=l, style=discord.ButtonStyle.success, row=row)
        self.details, self.index, self.ctx, self.urls, self.ep_texts = details, index, ctx, urls, ep_texts

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.",
                                                           ephemeral=True)
        await interaction.response.edit_message(view=EpisodeView(self.ctx, self.details, self.urls, self.ep_texts, self.index))

class EpisodeView(discord.ui.View):
    def __init__(self, ctx: commands.Context, details: dict, urls: list, ep_texts: list, index: int):
        super().__init__(timeout=None)
        i = index
        column, row, last_index = 0, -1, len(urls)
        while i < len(urls):
            if column % 4 == 0: row += 1
            if (i < index+pagelimit): self.add_item(ButtonEpisode(ctx, i, urls[i], ep_texts[i], details, row))
            if (i == index+pagelimit): last_index = i
            i += 1
            column += 1
        if index - pagelimit > -1:
            self.add_item(nextPageEP(ctx, details, 0, 3, "⏪", urls, ep_texts))
            self.add_item(nextPageEP(ctx, details, index - pagelimit, 3, "◀️", urls, ep_texts))
        else:
            self.add_item(DisabledButton("⏪", 3))
            self.add_item(DisabledButton("◀️", 3))
        if not last_index == len(urls):
            self.add_item(nextPageEP(ctx, details, last_index, 3, "▶️", urls, ep_texts))
            max_page = get_max_page(len(urls))
            self.add_item(nextPageEP(ctx, details, max_page, 3, "⏩", urls, ep_texts))
        else:
            self.add_item(DisabledButton("▶️", 3))
            self.add_item(DisabledButton("⏩", 3))
        self.add_item(CancelButton(ctx, 3))

class ButtonEpisode(discord.ui.Button):
    def __init__(self, ctx: commands.Context, index: int, url_session: str, ep_text: str, details: dict, row: int):
        super().__init__(label=ep_text.replace("Episode ", ""), style=discord.ButtonStyle.primary, row=row)
        self.index, self.url_session, self.ctx, self.details, self.ep_text = index, url_session, ctx, details, ep_text

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.",
                                                           ephemeral=True)
        await interaction.response.defer()
        req = await new_req(f"{base}{self.url_session}", headers, False)
        soup = soupify(req)
        items = soup.find("div", {"id": "pickDownload"}).findAll("a")
        embeds = soup.find("div", {"id": "resolutionMenu"}).findAll("button")
        embeds = [e["data-src"] for e in embeds]
        urls = [items[i].get("href") for i in range(len(items))]
        texts = [items[i].text for i in range(len(items))]
        msg_content = f"{self.details['title']}: {self.ep_text}"
        for x in range(len(urls)):
            msg_content += f"\n{x+1}. {texts[x]}"
        await interaction.followup.send(msg_content, view=DownloadView(self.ctx, urls, self.details, self.index, texts, self.ep_text, embeds),
                                        ephemeral=True)

class ButtonDownload(discord.ui.Button):
    def __init__(self, ctx: commands.Context, url_fake: str, l: str, details: dict, index: int, text: str, ep_text: str, embed: str):
        super().__init__(label=l+1)
        self.url_fake, self.ctx, self.details, self.index, self.text, self.ep_text, self.embed = url_fake, ctx, details, index, text, ep_text, embed

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.",
                                                           ephemeral=True)
        await interaction.response.defer()
        req = await new_req(self.url_fake, None, False)
        soup = soupify(req)
        script_tag = soup.find("script")
        match = re.search(r"https://kwik\.cx/f/\w+", script_tag.string)
        dl_page = await new_req(match.group(), None, False)
        full_key, key, v1, v2 = KWIK_PARAMS_RE.search(dl_page.decode()).group(1, 2, 3, 4)
        decrypted = decrypt(full_key, key, v1, v2)
        head = {"Referer": "https://kwik.cx/"}
        data = {"_token": KWIK_D_TOKEN.search(decrypted).group(1)}
        semi_final = await session.post(KWIK_D_URL.search(decrypted).group(1), data=data, headers=head, allow_redirects=False)
        final_mp4 = semi_final.headers["Location"]
        req_embed = await new_req(self.embed, headers, False)
        m3u8 = parse_m3u8_link(req_embed.decode())
        soup_code = soupify(dl_page)
        code_tags = soup_code.find_all('code')
        txt_content = [
            f"{self.details['title']}: {self.ep_text} [{self.text}]",
            f"CRC32: `{code_tags[0].text}`",
            f"MD5: `{code_tags[1].text}`"
        ]
        real_links = [
            {
                "emoji": "▶️",
                "label": "Stream",
                "url": f"https://gdjkhp.github.io/ubel/?url={m3u8}",
            },
            {
                "emoji": "⬇️",
                "label": "Download",
                "url": final_mp4,
            },
            {
                "emoji": "🌏",
                "label": "Link",
                "url": match.group(),
            },
        ]
        await interaction.followup.send("\n".join(txt_content), view=WatchView(real_links), ephemeral=True)

class DownloadView(discord.ui.View):
    def __init__(self, ctx: commands.Context, urls: list, details: dict, index: int, texts: list, ep_text: str, embeds: list):
        super().__init__(timeout=None)
        for x in range(len(urls)):
            self.add_item(ButtonDownload(ctx, urls[x], x, details, index, texts[x], ep_text, embeds[x]))

class WatchView(discord.ui.View):
    def __init__(self, links: list):
        super().__init__(timeout=None)
        for x in links[:25]:
            self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, url=x["url"], emoji=x["emoji"], label=x["label"]))

class CogPahe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def pahe(self, ctx: commands.Context, *, query:str=None):
        await pahe_search(ctx, query)

    @app_commands.command(name="pahe", description=f"{description_helper['emojis']['anime']} animepahe")
    @app_commands.describe(query="Search query")
    @app_commands.autocomplete(query=pahe_auto)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def pahe_slash(self, ctx: discord.Interaction, *, query:str=None):
        await pahe_anime(self.bot, ctx, query)

    @commands.hybrid_command(description=f'{description_helper["emojis"]["media"]} {description_helper["media"]["anime"]}')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def anime(self, ctx: commands.Context):
        await help_anime(ctx)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogPahe(bot))