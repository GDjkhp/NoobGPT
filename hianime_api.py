import os
import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from util_discord import command_check, get_guild_prefix, description_helper
aniwatch = os.getenv("ANIWATCH")
provider="https://gdjkhp.github.io/img/hi.png"
ubel="https://gdjkhp.github.io/ubel/?url="
pagelimit=12

async def hi_search(ctx: commands.Context, arg: str):
    if await command_check(ctx, "tv", "media"): return await ctx.reply("command disabled", ephemeral=True)
    if not arg: return await ctx.reply(f"usage: `{await get_guild_prefix(ctx)}aniwatch <query>`")
    results = await req(f"{aniwatch}/api/v2/hianime/search?q={arg}")
    if not results["data"]["animes"]: return await ctx.reply("none found")
    await ctx.reply(embed=buildSearch(arg, results["data"]["animes"], 0), view=SearchView(ctx, arg, results["data"]["animes"], 0))

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
            if (i < index+pagelimit): self.add_option(label=f"[{i + 1}] {result[i]['jname']}"[:100], value=i, 
                                                      description=result[i]['name'][:100])
            if (i == index+pagelimit): break
            i += 1

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.edit_message(view=None)
        anime = self.result[int(self.values[0])]
        selected = await req(f"{aniwatch}/api/v2/hianime/anime/{anime['id']}/episodes")
        anime["episodes"] = selected["data"]["episodes"]
        await interaction.edit_original_response(embed=buildAniwatch(anime), view=EpisodeView(self.ctx, anime, 0))

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
        column, row, last_index = 0, -1, len(details["episodes"])
        while i < len(details["episodes"]):
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
        if not last_index == len(details["episodes"]):
            self.add_item(nextPageEP(ctx, details, last_index, 3, "▶️"))
            max_page = get_max_page(len(details["episodes"]))
            self.add_item(nextPageEP(ctx, details, max_page, 3, "⏩"))
        else:
            self.add_item(DisabledButton("▶️", 3))
            self.add_item(DisabledButton("⏩", 3))
        self.add_item(CancelButton(ctx, 3))

class ButtonEpisode(discord.ui.Button):
    def __init__(self, ctx: commands.Context, index: int, details: dict, row: int):
        super().__init__(label=str(details["episodes"][index]["number"]), style=discord.ButtonStyle.primary, row=row)
        self.index, self.ctx, self.details = index, ctx, details
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.defer()
        msg_content = f"{self.details['jname']}: Episode {self.details['episodes'][self.index]['number']}"
        stream_source = f"{aniwatch}/api/v2/hianime/episode/sources?animeEpisodeId="
        link = await req(f'{stream_source}{self.details["episodes"][self.index]["episodeId"]}')
        link_dub = await req(f'{stream_source}{self.details["episodes"][self.index]["episodeId"]}&category=dub')
        link_raw = await req(f'{stream_source}{self.details["episodes"][self.index]["episodeId"]}&category=raw')
        links = []
        # sub_param = "&subtitles="
        for s in link["data"]["tracks"]:
            if s["kind"] == "captions":
                # if s.get("default"):
                #     sub_param += f"{s['label']};{s['file']}"
                if link: links.append({f"{s['label'].upper()} SUB": f'{ubel}{link["data"]["sources"][0]["url"]}&subtitles={s["file"]}'})
        if link_dub: links.append({"ENGLISH DUB": f'{ubel}{link_dub["data"]["sources"][0]["url"]}'})
        if link_raw: links.append({"RAW": f'{ubel}{link_raw["data"]["sources"][0]["url"]}'})
        await interaction.followup.send(msg_content, view=WatchView(links), ephemeral=True)

class WatchView(discord.ui.View):
    def __init__(self, links: list[dict]):
        super().__init__(timeout=None)
        for x in links[:25]:
            for k, v in x.items():
                self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, url=v, label=k, emoji=get_subtitle_flags(k)))

# utils
def get_max_page(length):
    if length % pagelimit != 0: return length - (length % pagelimit)
    return length - pagelimit

async def req(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            
def get_language_flag(language_code: str):
    language_to_flag = {
        'ar': '🇸🇦',  # Arabic - Saudi Arabia flag
        'en': '🇬🇧',  # English - UK flag
        'fr': '🇫🇷',  # French flag
        'de': '🇩🇪',  # German flag
        'it': '🇮🇹',  # Italian flag
        'pt': '🇧🇷',  # Portuguese - Brazil flag
        'ru': '🇷🇺',  # Russian flag
        'es': '🇪🇸',  # Spanish flag
        'es-419': '🇲🇽'  # Spanish (Latin America) - Mexico flag
    }
    
    return language_to_flag.get(language_code.lower(), '🎞️')

def get_subtitle_flags(subtitle_text: str):
    text = subtitle_text.lower().strip()
    
    if 'arabic' in text:
        return get_language_flag('ar')
    elif 'english' in text:
        return get_language_flag('en')
    elif 'french' in text:
        return get_language_flag('fr')
    elif 'german' in text:
        return get_language_flag('de')
    elif 'italian' in text:
        return get_language_flag('it')
    elif 'portuguese' in text and 'brazil' in text:
        return get_language_flag('pt')
    elif 'russian' in text:
        return get_language_flag('ru')
    elif 'spanish' in text and 'latin_america' in text:
        return get_language_flag('es-419')
    elif 'spanish' in text:
        return get_language_flag('es')
    else:
        return '🎞️'

def buildSearch(arg: str, result, index: int) -> discord.Embed:
    embed = discord.Embed(title=f"Search results: `{arg}`", description=f"{len(result)} found", color=0x00ff00)
    embed.set_thumbnail(url=provider)
    i = index
    while i < len(result):
        if (i < index+pagelimit): embed.add_field(name=f"[{i + 1}] `{result[i]['name']}`", value=f"{result[i]['episodes']['sub']} episode/s")
        i += 1
    return embed

def buildAniwatch(details: dict) -> discord.Embed:
    desc = [
        f"**English:** {details['name']}",
        f"**Type:** {details['type']}",
        f"**Episodes:** {len(details['episodes'])}",
    ]
    embed = discord.Embed(title=details["jname"], description="\n".join(desc), color=0x00ff00)
    embed.set_thumbnail(url=provider)
    embed.set_image(url=details["poster"])
    embed.set_footer(text="Powered by Übel Web Player :)")
    return embed

class CogAniwatch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description=f"{description_helper['emojis']['tv']} hianime")
    @app_commands.describe(query="Search query")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def aniwatch(self, ctx: commands.Context, *, query:str=None):
        await hi_search(ctx, query)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogAniwatch(bot))