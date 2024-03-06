import discord
from discord.ext import commands
import aiohttp
from urllib import parse as p

async def req_real(api):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api) as response:
                if response.status == 200: return await response.json()
    except Exception as e: 
        print(e)
    return None

async def LEX(ctx: commands.Context, arg):
    message = await ctx.reply(f"Searching images with query `{arg}`\nPlease wait…")
    req = await req_real('https://lexica.art/api/v1/search?q='+p.quote_plus(arg))
    results = req['images']
    if not ctx.channel.nsfw: results = [image for image in results if not image["nsfw"]]
    if len(results) == 0: return await message.edit(content="**No results found**") # rare
    await message.edit(content=None, embed = await BuildEmbed(arg, results, 0), view = ImageView(arg, results, 0))

async def BuildEmbed(tags: list, results, index: int) -> discord.Embed:
    embed = discord.Embed(title=f"Search results: `{tags}`", description=f"{index+1}/{len(results)} found", color=0x00ff00)
    embed.add_field(name="Prompt", value=f"`{results[index]['prompt']}`"[:1024], inline=False)
    embed.add_field(name="Model", value=f"`{results[index]['model']}`", inline=False)
    embed.set_image(url = results[index]['src'])
    return embed

class ImageView(discord.ui.View):
    def __init__(self, tags, results, index):
        super().__init__(timeout=None)
        if not index == 0: 
            self.add_item(ButtonAction(tags, results, 0, "⏪", 0))
            self.add_item(ButtonAction(tags, results, index - 1, "◀️", 0))
        if index + 1 < len(results): 
            self.add_item(ButtonAction(tags, results, index + 1, "▶️", 0))
            self.add_item(ButtonAction(tags, results, len(results)-1, "⏩", 0))

class ButtonAction(discord.ui.Button):
    def __init__(self, tags, results, index, l, row):
        super().__init__(emoji=l, style=discord.ButtonStyle.success, row=row)
        self.results, self.index, self.tags = results, index, tags
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed = await BuildEmbed(self.tags, self.results, self.index),
                                                view = ImageView(self.tags, self.results, self.index))
