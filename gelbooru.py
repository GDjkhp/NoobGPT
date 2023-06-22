from pygelbooru import Gelbooru
from discord.ext import commands
import re
import discord
import random

async def R34(ctx: commands.Context, arg: str):
    if not ctx.channel.nsfw: return await ctx.reply("**No.**")
    tags = re.split(r'\s*,\s*', arg)
    message = await ctx.reply(f"Searching posts with tags `{tags}`\nPlease wait…")
    results = []
    page = 0
    while len(results) < 10000: # hard limit
        cached = await Gelbooru(api='https://api.rule34.xxx/').search_posts(tags=tags, page=page)
        if not cached: break
        results.extend(cached)
        await message.edit(content=f"Searching posts with tags `{tags}`\nPlease wait…\n{len(results)} found")
        page+=1
    if len(results) == 0: return await message.edit(content="**No results found**")
    await message.edit(content=None, embed = await BuildEmbed(tags, results, 0, False), view = ImageView(tags, results, 0, False))

async def GEL(ctx: commands.Context, arg: str):
    if not ctx.channel.nsfw: return await ctx.reply("**No.**")
    tags = re.split(r'\s*,\s*', arg)
    message = await ctx.reply(f"Searching posts with tags `{tags}`\nPlease wait…")
    results = []
    page = 0
    while len(results) < 10000: # hard limit
        cached = await Gelbooru().search_posts(tags=tags, page=page)
        if not cached: break
        results.extend(cached)
        await message.edit(content=f"Searching posts with tags `{tags}`\nPlease wait…\n{len(results)} found")
        page+=1
    if len(results) == 0: return await message.edit(content="**No results found**")
    await message.edit(content=None, embed = await BuildEmbed(tags, results, 0, False), view = ImageView(tags, results, 0, False))

async def SAFE(ctx: commands.Context, arg: str):
    tags = re.split(r'\s*,\s*', arg)
    message = await ctx.reply(f"Searching posts with tags `{tags}`\nPlease wait…")
    results = []
    page = 0
    while len(results) < 10000: # hard limit
        cached = await Gelbooru(api='https://safebooru.org/').search_posts(tags=tags, page=page)
        if not cached: break
        results.extend(cached)
        await message.edit(content=f"Searching posts with tags `{tags}`\nPlease wait…\n{len(results)} found")
        page+=1
    if len(results) == 0: return await message.edit(content="**No results found**")
    await message.edit(content=None, embed = await BuildEmbed(tags, results, 0, True), view = ImageView(tags, results, 0, True))

async def BuildEmbed(tags: list, results, index: int, safe: bool) -> discord.Embed():
    embed = discord.Embed(title=f"Search results: `{tags}`", description=f"{index+1}/{len(results)} found", color=0x00ff00)
    # if safe and not await Gelbooru(api='https://safebooru.org/').is_deleted(results[index].hash): 
    #     embed.add_field(name="This post was deleted.", value=results[index].hash)
    #     return embed
    embed.add_field(name="Tags", value=f"`{results[index].tags}`"[:1024], inline=False)
    embed.add_field(name="Source", value=results[index].source, inline=False)
    if results[index].file_url.endswith(".mp4"): embed.add_field(name="Video link:", value=results[index].file_url)
    else: embed.set_image(url = results[index].file_url)
    return embed

class ImageView(discord.ui.View):
    def __init__(self, tags, results, index, safe):
        super().__init__(timeout=None)
        if not index == 0: 
            self.add_item(ButtonAction(tags, safe, results, 0, "⏪", 0))
            self.add_item(ButtonAction(tags, safe, results, index - 1, "◀️", 0))
        if index + 1 < len(results): 
            self.add_item(ButtonAction(tags, safe, results, index + 1, "▶️", 0))
            self.add_item(ButtonAction(tags, safe, results, len(results)-1, "⏩", 0))
        self.add_item(ButtonAction(tags, safe, results, random.randrange(0, len(results)), "🔀", 1))

class ButtonAction(discord.ui.Button):
    def __init__(self, tags, safe, results, index, l, row):
        super().__init__(emoji=l, style=discord.ButtonStyle.success, row=row)
        self.results, self.index, self.tags, self.safe = results, index, tags, safe
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed = await BuildEmbed(self.tags, self.results, self.index, self.safe),
                                                view = ImageView(self.tags, self.results, self.index, self.safe))
