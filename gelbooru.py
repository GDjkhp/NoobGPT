from typing import Optional, Union
from discord.emoji import Emoji
from discord.enums import ButtonStyle
from discord.interactions import Interaction
from discord.partial_emoji import PartialEmoji
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
    await message.edit(content=None, embed = await BuildEmbed(tags, results, 0, False, [False, False], ctx), 
                       view = ImageView(tags, results, 0, False, [False, False], ctx))

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
    await message.edit(content=None, embed = await BuildEmbed(tags, results, 0, False, [False, False], ctx), 
                       view = ImageView(tags, results, 0, False, [False, False], ctx))

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
    await message.edit(content=None, embed = await BuildEmbed(tags, results, 0, True, [False, False], ctx), 
                       view = ImageView(tags, results, 0, True, [False, False], ctx))

async def BuildEmbed(tags: list, results, index: int, safe: bool, lock: list, ctx: commands.Context) -> discord.Embed():
    embed = discord.Embed(title=f"Search results: `{tags}`", description=f"{index+1}/{len(results)} found", color=0x00ff00)
    # if safe and not await Gelbooru(api='https://safebooru.org/').is_deleted(results[index].hash): 
    #     embed.add_field(name="This post was deleted.", value=results[index].hash)
    #     return embed
    embed.add_field(name="Tags", value=f"`{results[index].tags}`"[:1024], inline=False)
    embed.add_field(name="Source", value=results[index].source, inline=False)
    if results[index].file_url.endswith(".mp4"): embed.add_field(name="Video link:", value=results[index].file_url)
    else: embed.set_image(url = results[index].file_url)
    embed.set_footer(text=f"{index+1}/{len(results)}")
    return embed

class ImageView(discord.ui.View):
    def __init__(self, tags: list, results: list, index: int, safe: bool, lock: list, ctx: commands.Context):
        super().__init__(timeout=None)
        if not index == 0: 
            self.add_item(ButtonAction(tags, safe, results, 0, "⏪", 0, lock, ctx))
            self.add_item(ButtonAction(tags, safe, results, index - 1, "◀️", 0, lock, ctx))
        if index + 1 < len(results): 
            self.add_item(ButtonAction(tags, safe, results, index + 1, "▶️", 0, lock, ctx))
            self.add_item(ButtonAction(tags, safe, results, len(results)-1, "⏩", 0, lock, ctx))
        self.add_item(ButtonAction(tags, safe, results, random.randrange(0, len(results)), "🔀", 1, lock, ctx))
        self.add_item(ButtonHeart())
        self.add_item(ButtonAction(tags, safe, results, index, "🔒" if lock[1] else "🔓", 1, [lock[1], not lock[1]], ctx))
        self.add_item(ButtonEnd())

class ButtonEnd(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, emoji="🛑", row=1)
    
    async def callback(self, interaction: Interaction):
        await interaction.response.edit_message(content="🤨", view=None, embed=None)

class ButtonHeart(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, emoji="❤️", row=1)
    
    async def callback(self, interaction: Interaction):
        await interaction.response.send_message("Coming soon. ❤️", ephemeral=True)

class ButtonAction(discord.ui.Button):
    def __init__(self, tags: list, safe: bool, results: list, index: list, l: str, row: int, lock: list, ctx: commands.Context):
        super().__init__(emoji=l, style=discord.ButtonStyle.success, row=row)
        self.results, self.index, self.tags, self.safe, self.lock, self.ctx = results, index, tags, safe, lock, ctx
    
    async def callback(self, interaction: discord.Interaction):
        if self.lock[0] != self.lock[1]:
            if interaction.user != self.ctx.author:
                return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can lock/unlock this message.", 
                                                               ephemeral=True)
            else: self.lock = [self.lock[1], self.lock[1]]
        if self.lock[1] and interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"<@{self.ctx.message.author.id}> locked this message.", ephemeral=True)
        await interaction.response.edit_message(embed = await BuildEmbed(self.tags, self.results, self.index, self.safe, self.lock, self.ctx), 
                                                view = ImageView(self.tags, self.results, self.index, self.safe, self.lock, self.ctx))