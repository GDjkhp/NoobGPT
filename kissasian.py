from bs4 import BeautifulSoup
import re
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from util_discord import command_check, description_helper, get_guild_prefix

BASE_URL = "https://kissasian.lu"
provider="https://gdjkhp.github.io/img/kissasian.png"
pagelimit=12

async def help_tv(ctx: commands.Context):
    if await command_check(ctx, "tv", "media"): return await ctx.reply("command disabled", ephemeral=True)
    p = await get_guild_prefix(ctx)
    sources = [f"`{p}flix` sflix", f"`{p}kiss` kissasian"]
    await ctx.reply("\n".join(sources))

async def kiss_search(ctx: commands.Context, arg: str):
    if await command_check(ctx, "tv", "media"): return await ctx.reply("command disabled", ephemeral=True)
    return await ctx.reply("KISSASIAN down?????????\nOMG NOOOOOOOOOO!!!!!!!!!")
    if not arg: return await ctx.reply(f"usage: `{await get_guild_prefix(ctx)}kiss <query>`")
    results = await search(arg)
    if not results['data']: return await ctx.reply("none found")
    await ctx.reply(embed=buildSearch(arg, results["data"], 0), view=SearchView(ctx, arg, results["data"], 0))

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
                                                      description=result[i]['id'][:100])
            if (i == index+pagelimit): break
            i += 1

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.edit_message(view=None)
        id = self.result[int(self.values[0])]['id']
        selected = await series_info(id)
        selected['id'] = id
        await interaction.edit_original_response(embed=buildKiss(selected), view=EpisodeView(self.ctx, selected, 0))

# episode
class nextPageEP(discord.ui.Button):
    def __init__(self, ctx: commands.Context, details: list, index: int, row: int, l: str):
        super().__init__(emoji=l, style=discord.ButtonStyle.success, row=row)
        self.details, self.index, self.ctx = details, index, ctx
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.edit_message(view=EpisodeView(self.ctx, self.details, self.index))

class EpisodeView(discord.ui.View):
    def __init__(self, ctx: commands.Context, details: dict, index: int):
        super().__init__(timeout=None)
        i = index
        column, row, last_index = 0, -1, len(details['episode_links'])
        while i < len(details['episode_links']):
            if column % 4 == 0: row += 1
            if (i < index+pagelimit): self.add_item(ButtonEpisode(ctx, i, details, row))
            if (i == index+pagelimit): last_index = i
            i += 1
            column += 1
        if index - pagelimit > -1:
            self.add_item(nextPageEP(ctx, details, 0, 3, "⏪"))
            self.add_item(nextPageEP(ctx, details, index - pagelimit, 3, "◀️"))
        else:
            self.add_item(DisabledButton("⏪", 3))
            self.add_item(DisabledButton("◀️", 3))
        if not last_index == len(details['episode_links']):
            self.add_item(nextPageEP(ctx, details, last_index, 3, "▶️"))
            max_page = get_max_page(len(details['episode_links']))
            self.add_item(nextPageEP(ctx, details, max_page, 3, "⏩"))
        else:
            self.add_item(DisabledButton("▶️", 3))
            self.add_item(DisabledButton("⏩", 3))
        self.add_item(CancelButton(ctx, 3))

class ButtonEpisode(discord.ui.Button):
    def __init__(self, ctx: commands.Context, index: int, details: dict, row: int):
        super().__init__(label=ep_no(details['episode_links'][index]), style=discord.ButtonStyle.primary, row=row)
        self.index, self.ctx, self.details = index, ctx, details
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.defer()
        link = await get_stream(self.details['id'], ep_no(self.details['episode_links'][self.index]))
        msg_content = f"{self.details['title']}: Episode {ep_no(self.details['episode_links'][self.index])}"
        await interaction.followup.send(msg_content, view=WatchView([link]), ephemeral=True)

class WatchView(discord.ui.View):
    def __init__(self, links: list):
        super().__init__(timeout=None)
        for x in links[:25]:
            self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, url=x, emoji="🎞️",
                                            label=f"Watch Full HD Movies & TV Shows"))

def buildSearch(arg: str, result: list, index: int) -> discord.Embed:
    embed = discord.Embed(title=f"Search results: `{arg}`", description=f"{len(result)} found", color=0x00ff00)
    embed.set_thumbnail(url=provider)
    i = index
    while i < len(result):
        if (i < index+pagelimit): embed.add_field(name=f"[{i + 1}] `{result[i]['title']}`", value=result[i]['id'])
        i += 1
    return embed

def buildKiss(details: dict) -> discord.Embed:
    cook_deets = f'**Other names:**\n{", ".join(details["other_names"])}'
    cook_deets+= f'\n**Casts:** {", ".join(details["casts"])}'
    cook_deets+= f'\n**Genres:** {", ".join(details["genres"])}'
    embed = discord.Embed(title=details['title'], description=cook_deets, color=0x00ff00)
    embed.set_thumbnail(url=provider)
    embed.set_image(url = details['img_url'])
    embed.set_footer(text="Note: Use Adblockers :)")
    return embed

def get_max_page(length):
    if length % pagelimit != 0: return length - (length % pagelimit)
    return length - pagelimit

def ep_no(url):
    pattern = r"Episode-(\d+)"
    match = re.search(pattern, url)
    if match: return match.group(1)

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
            "img_url": f'{BASE_URL}{soup.find("div", class_="col cover").find("img").get("src")}',
            "other_names": other_names,
            "genres": genres,
            "casts": casts,
            "no_eps": no_eps,
            "episode_links": eps_list[::-1]
        }
        return content

async def get_stream(series_id: str, ep_no: int):
    url = BASE_URL + f"/Drama/{series_id}/Episode-{str(ep_no)}"
    soup, response = await get_soup(url)
    if response:
        return soup.find("iframe", {"id": "mVideo"}).attrs['src']

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
        
class CogKiss(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # @commands.hybrid_command(description=f"{description_helper['emojis']['tv']} kissasian")
    # @app_commands.describe(query="Search query")
    # @app_commands.allowed_installs(guilds=True, users=True)
    # @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @commands.command()
    async def kiss(self, ctx: commands.Context, *, query:str=None):
        await kiss_search(ctx, query)

    @commands.hybrid_command(description=f'{description_helper["emojis"]["media"]} {description_helper["media"]["tv"]}')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def tv(self, ctx: commands.Context):
        await help_tv(ctx)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogKiss(bot))