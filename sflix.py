import re
import discord
from discord import app_commands
from discord.ext import commands
from httpclient import HttpClient
from bs4 import BeautifulSoup as BS
from urllib import parse as p
import base64
from Crypto.Cipher import AES
import hashlib
import json
from Crypto.Util.Padding import unpad
from util_discord import command_check, description_helper, check_if_not_owner, get_guild_prefix
from util_database import myclient
mycol = myclient["utils"]["cant_do_json_shit_dynamically_on_docker"]

client, client_cdn = HttpClient(), HttpClient()
title, url, aid, mv_tv, poster = 0, 1, 2, 3, 4
pagelimit = 12
domain_sflix = "https://sflix.to"
provider="https://gdjkhp.github.io/img/66356c25ce98cb12993249e21742b129.png"

async def help_tv(ctx: commands.Context):
    if await command_check(ctx, "tv", "media"): return await ctx.reply("command disabled", ephemeral=True)
    p = await get_guild_prefix(ctx)
    sources = [
        # f"`{p}flix` sflix",
        f"`{p}kiss` kisskh",
        # f"`{p}kiss` kissasian",
    ]
    await ctx.reply("\n".join(sources))

async def get_domain():
    global domain_sfix
    cursor = mycol.find()
    data = await cursor.to_list(None)
    domain_sfix = data[0]["sflix"]

async def set_domain(ctx: commands.Context, arg: str):
    await mycol.update_one({}, {"$set": {"sflix": arg}})
    await get_domain()
    await ctx.reply(domain_sfix)

async def Sflix(ctx: commands.Context, arg: str):
    if await command_check(ctx, "tv", "media"): return await ctx.reply("command disabled", ephemeral=True)
    return await ctx.reply("sflix is retiring!\nreplacement in the works -> `https://vidlink.pro`")
    await get_domain()
    msg = await ctx.reply(f"Searching `{arg}`\nPlease wait…")
    try:
        result = results(await searchQuery(arg)) 
        embed = buildSearch(arg, result, 0)
        await msg.edit(content=None, embed=embed, view=MyView(ctx, result, arg, 0))
    except Exception as e: return await msg.edit(content=f"**No results found**")

# embed builders
async def detail(result) -> list:
    req = await client.get(f"{domain_sfix}{result[1]}")
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
async def buildMovie(result) -> discord.Embed:
    details = await detail(result)
    embed = discord.Embed(title=result[title], description=details[0], color=0x00ff00)
    embed.set_thumbnail(url=provider)
    valid_url = p.quote(result[poster], safe=":/")
    embed.set_image(url = valid_url)
    detailed(embed, details)
    embed.set_footer(text="Note: Use Adblockers :)")
    return embed
async def buildSeasons(season_ids, result) -> discord.Embed:
    details = await detail(result)
    embed = discord.Embed(title=result[title], description=details[0], color=0x00ff00)
    embed.set_thumbnail(url=provider)
    valid_url = p.quote(result[poster], safe=":/")
    embed.set_image(url = valid_url)
    detailed(embed, details)
    embed.add_field(name="Seasons", value=len(season_ids))
    return embed
async def buildEpisodes(episodes, season, result) -> discord.Embed:
    embed = discord.Embed(title=f"{result[title]}", description=f"Season {season}", color=0x00ff00)
    embed.set_thumbnail(url=provider)
    valid_url = p.quote(result[poster], safe=":/")
    embed.set_image(url = valid_url)
    details = await detail(result)
    detailed(embed, details)
    embed.add_field(name="Episodes", value=len(episodes))
    embed.set_footer(text="Note: Use Adblockers :)")
    return embed
def buildSearch(arg: str, result: list, index: int) -> discord.Embed:
    embed = discord.Embed(title=f"Search results: `{arg}`", description=f"{len(result)} found", color=0x00ff00)
    embed.set_thumbnail(url=provider)
    i = index
    while i < len(result):
        if (i < index+pagelimit): embed.add_field(name=f"[{i + 1}] `{result[i][title]}`", value=f"{result[i][url]}")
        i += 1
    return embed

# actvid
def get_max_page(length):
    if length % pagelimit != 0: return length - (length % pagelimit)
    return length - pagelimit
def parse(txt: str) -> str:
    return re.sub(r"\W+", "-", txt.lower())
async def searchQuery(q) -> str:
    res = await client.get(f"{domain_sfix}/search/{parse(q)}")
    return res.text
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
            pattern="full|/tv/|/movie/|hd|watch|free|[0-9]{2,}",
            repl="",
            string=" ".join(i.split("-")),
        )
        for i in urls
    ]
    ids = [i.split("-")[-1] for i in urls]
    return [list(sublist) for sublist in zip(title, urls, ids, mov_or_tv, img)]

# search
class MyView(discord.ui.View):
    def __init__(self, ctx: commands.Context, result: list, arg: str, index: int):
        super().__init__(timeout=None)
        last_index = min(index + pagelimit, len(result))
        self.add_item(SelectChoice(ctx, index, result))
        if index - pagelimit > -1:
            self.add_item(ButtonNextSearch(ctx, arg, result, 0, "⏪"))
            self.add_item(ButtonNextSearch(ctx, arg, result, index - pagelimit, "◀️"))
        else:
            self.add_item(DisabledButton("⏪", 1))
            self.add_item(DisabledButton("◀️", 1))
        if not last_index == len(result):
            self.add_item(ButtonNextSearch(ctx, arg, result, last_index, "▶️"))
            max_page = get_max_page(len(result))
            self.add_item(ButtonNextSearch(ctx, arg, result, max_page, "⏩"))
        else:
            self.add_item(DisabledButton("▶️", 1))
            self.add_item(DisabledButton("⏩", 1))
        self.add_item(CancelButton(ctx, 1))

class SelectChoice(discord.ui.Select):
    def __init__(self, ctx: commands.Context, index: int, result: list):
        super().__init__(placeholder=f"{min(index + pagelimit, len(result))}/{len(result)} found")
        i, self.result, self.ctx = index, result, ctx
        while i < len(result): 
            if (i < index+pagelimit): self.add_option(label=f"[{i + 1}] {result[i][title]}", description=f"{result[i][url]}", value=i)
            if (i == index+pagelimit): break
            i += 1

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.edit_message(view=None)
        if self.result[int(self.values[0])][mv_tv] == "TV":
            r = await client.get(f"{domain_sfix}/ajax/v2/tv/seasons/{self.result[int(self.values[0])][aid]}")
            season_ids = [i["data-id"] for i in BS(r, "lxml").select(".dropdown-item")]
            embed = await buildSeasons(season_ids, self.result[int(self.values[0])])
            await interaction.edit_original_response(embed = embed, view = MyView2(self.ctx, self.result[int(self.values[0])], season_ids, 0))
        else:
            sid = await server_id(self.result[int(self.values[0])][aid])
            iframe_url, tv_id = await get_link(sid)
            iframe_link, iframe_id = rabbit_id(iframe_url)
            try:
                # url = await cdn_url(iframe_link, iframe_id)
                embed = await buildMovie(self.result[int(self.values[0])])
                await interaction.edit_original_response(embed=embed, view=None)
                await interaction.followup.send(f"{self.result[int(self.values[0])][title]}",
                                                view=WatchView([f"{iframe_url}&_debug=true"]), ephemeral=True)
            except Exception as e: await interaction.edit_original_response(content=e, view=None)

# legacy code
class ButtonSelect(discord.ui.Button):
    def __init__(self, ctx: commands.Context, index: int, result: list, row: int):
        super().__init__(label=index, style=discord.ButtonStyle.primary, row=row)
        self.result, self.ctx = result, ctx
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.edit_message(view=None)
        if self.result[mv_tv] == "TV":
            r = await client.get(f"{domain_sfix}/ajax/v2/tv/seasons/{self.result[aid]}")
            season_ids = [i["data-id"] for i in BS(r, "lxml").select(".dropdown-item")]
            embed = await buildSeasons(season_ids, self.result)
            await interaction.edit_original_response(embed = embed, view = MyView2(self.ctx, self.result, season_ids, 0))
        else:
            sid = await server_id(self.result[aid])
            iframe_url, tv_id = await get_link(sid)
            iframe_link, iframe_id = rabbit_id(iframe_url)
            try:
                # url = await cdn_url(iframe_link, iframe_id)
                embed = await buildMovie(self.result)
                await interaction.edit_original_response(embed=embed, view=None, content=f"[{self.result[title]}]({iframe_url}&_debug=true)")
            except Exception as e: await interaction.edit_original_response(content=e, view=None)
            
class ButtonNextSearch(discord.ui.Button):
    def __init__(self, ctx: commands.Context, arg: str, result: list, index: int, l: str):
        super().__init__(emoji=l, style=discord.ButtonStyle.success)
        self.result, self.index, self.arg, self.ctx = result, index, arg, ctx

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.edit_message(view = MyView(self.ctx, self.result, self.arg, self.index))

# season
class MyView2(discord.ui.View):
    def __init__(self, ctx: commands.Context, result: list, season_ids: list, index: int):
        super().__init__(timeout=None)
        i = index
        column, row, last_index = 0, -1, len(season_ids)
        while i < len(season_ids):
            if column % 4 == 0: row += 1
            if (i < index+pagelimit): self.add_item(ButtonSelect2(ctx, i + 1, season_ids[i], result, row))
            if (i == index+pagelimit): last_index = i
            i += 1
            column += 1
        if index - pagelimit > -1:
            self.add_item(ButtonNextSeason(ctx, result, season_ids, 0, 4, "⏪"))
            self.add_item(ButtonNextSeason(ctx, result, season_ids, index - pagelimit, 4, "◀️"))
        else:
            self.add_item(DisabledButton("⏪", 4))
            self.add_item(DisabledButton("◀️", 4))
        if not last_index == len(season_ids):
            self.add_item(ButtonNextSeason(ctx, result, season_ids, last_index, 4, "▶️"))
            max_page = get_max_page(len(season_ids))
            self.add_item(ButtonNextSeason(ctx, result, season_ids, max_page, 4, "⏩"))
        else:
            self.add_item(DisabledButton("▶️", 4))
            self.add_item(DisabledButton("⏩", 4))
        self.add_item(CancelButton(ctx, 4))

class ButtonSelect2(discord.ui.Button):
    def __init__(self, ctx: commands.Context, index: int, season_id: str, result: list, row: int):
        super().__init__(label=index, style=discord.ButtonStyle.primary, row=row)
        self.result, self.season_id, self.index, self.ctx = result, season_id, index, ctx
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.edit_message(view=None)
        z = f"{domain_sfix}/ajax/v2/season/episodes/{self.season_id}"
        rf = await client.get(z)
        episodes = [i["data-id"] for i in BS(rf, "lxml").select(".episode-item")]
        embed = await buildEpisodes(episodes, self.index, self.result)
        await interaction.edit_original_response(embed = embed, view = MyView3(self.ctx, self.season_id, episodes, self.result, 0, self.index))

class ButtonNextSeason(discord.ui.Button):
    def __init__(self, ctx: commands.Context, result: list, season_ids: list, index: int, row: int, l: str):
        super().__init__(emoji=l, style=discord.ButtonStyle.success, row=row)
        self.result, self.season_ids, self.index, self.ctx = result, season_ids, index, ctx
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.edit_message(view = MyView2(self.ctx, self.result, self.season_ids, self.index))

# episode
class MyView3(discord.ui.View):
    def __init__(self, ctx: commands.Context, season_id: str, episodes: list, result: list, index: int, season: int):
        super().__init__(timeout=None)
        i = index
        column, row, last_index = 0, -1, len(episodes)
        while i < len(episodes):
            if column % 4 == 0: row += 1
            if (i < index+pagelimit): self.add_item(ButtonSelect3(ctx, i + 1, season_id, episodes[i], season, result[title], row))
            if (i == index+pagelimit): last_index = i
            i += 1
            column += 1
        if index - pagelimit > -1:
            self.add_item(ButtonNextEp(ctx, season_id, episodes, result, 0, season, 4, "⏪"))
            self.add_item(ButtonNextEp(ctx, season_id, episodes, result, index - pagelimit, season, 4, "◀️"))
        else:
            self.add_item(DisabledButton("⏪", 4))
            self.add_item(DisabledButton("◀️", 4))
        if not last_index == len(episodes):
            self.add_item(ButtonNextEp(ctx, season_id, episodes, result, last_index, season, 4, "▶️"))
            max_page = get_max_page(len(episodes))
            self.add_item(ButtonNextEp(ctx, season_id, episodes, result, max_page, season, 4, "⏩"))
        else:
            self.add_item(DisabledButton("▶️", 4))
            self.add_item(DisabledButton("⏩", 4))
        self.add_item(CancelButton(ctx, 4))

class ButtonNextEp(discord.ui.Button):
    def __init__(self, ctx: commands.Context, season_id: str, episodes: list, result: list, index: int, season: int, row: int, l: str):
        super().__init__(emoji=l, style=discord.ButtonStyle.success, row=row)
        self.season_id, self.episodes, self.result, self.index, self.season, self.ctx = season_id, episodes, result, index, season, ctx
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.edit_message(view = MyView3(self.ctx, self.season_id, self.episodes, self.result, self.index, self.season))

class ButtonSelect3(discord.ui.Button):
    def __init__(self, ctx: commands.Context, index: int, season_id: str, episode: str, season: int, title: str, row: int):
        super().__init__(label=index, style=discord.ButtonStyle.primary, row=row)
        self.episode, self.season_id, self.season, self.title, self.index, self.ctx = episode, season_id, season, title, index, ctx
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.defer()
        sid = await ep_server_id(self.episode)
        iframe_url, tv_id = await get_link(sid)
        iframe_link, iframe_id = rabbit_id(iframe_url)
        try:
            # url = await cdn_url(iframe_link, iframe_id)
            await interaction.followup.send(f"{self.title} S{self.season}E{self.index}", 
                                            view=WatchView([f"{iframe_url}&_debug=true"]), ephemeral=True)
        except Exception as e: await interaction.edit_original_response(content=e, view=None)

class WatchView(discord.ui.View):
    def __init__(self, links: list):
        super().__init__(timeout=None)
        for x in links[:25]:
            self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, url=x, emoji="🎞️",
                                            label=f"Watch Full HD Movies & TV Shows"))

class DisabledButton(discord.ui.Button):
    def __init__(self, e: str, r: int):
        super().__init__(emoji=e, style=discord.ButtonStyle.success, disabled=True, row=r)

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

# sflix functions
async def server_id(mov_id: str) -> str:
    req = await client.get(f"{domain_sfix}/ajax/movie/episodes/{mov_id}")
    soup = BS(req, "lxml")
    return [i["data-id"] for i in soup.select(".link-item")][1]    
async def ep_server_id(ep_id: str) -> str:
    req = await client.get(f"{domain_sfix}/ajax/v2/episode/servers/{ep_id}/#servers-list")
    soup = BS(req, "lxml")
    return [i["data-id"] for i in soup.select(".link-item")][1]
async def get_link(thing_id: str) -> tuple:
    res = await client.get(f"{domain_sfix}/ajax/sources/{thing_id}")
    req = res.json()["link"]
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
async def cdn_url(final_link: str, rabb_id: str) -> str:
    client_cdn.set_headers({"X-Requested-With": "XMLHttpRequest"})
    res = await client_cdn.get(f"{final_link}getSources?id={rabb_id}")
    data = res.json()
    n = await decryption(data["sources"])
    return n[0]["file"]
async def decryption(string):
    key, new_string = key_extraction(string, await gh_key())
    decryption_key = gen_key(
        base64_decode_array(new_string)[8:16], key.encode("utf-8")
    )
    main_decryption = aes_decrypt(decryption_key, new_string)
    return json.loads(main_decryption)
def key_extraction(string, table):
    sources_array = list(string)
    extracted_key = ""
    current_index = 0
    for index in table:
        start = index[0] + current_index
        end = start + index[1]
        for i in range(start, end):
            extracted_key += sources_array[i]
            sources_array[i] = ' '
        current_index += index[1]
    return extracted_key, ''.join(sources_array)
async def gh_key():
    res = await client.get('https://github.com/theonlymo/keys/blob/e4/key')
    response_key = res.json()
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

class CogSflix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def rflix(self, ctx: commands.Context, arg=None):
        if check_if_not_owner(ctx): return
        await set_domain(ctx, arg)

    @commands.hybrid_command(description=f"{description_helper['emojis']['tv']} sflix")
    @app_commands.describe(query="Search query")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def flix(self, ctx: commands.Context, *, query:str=None):
        await Sflix(ctx, query)

    @commands.hybrid_command(description=f'{description_helper["emojis"]["media"]} {description_helper["media"]["tv"]}')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def tv(self, ctx: commands.Context):
        await help_tv(ctx)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogSflix(bot))