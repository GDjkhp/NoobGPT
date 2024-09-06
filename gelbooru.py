from pygelbooru import Gelbooru
from discord.ext import commands
import re
import discord
import random
from util_database import myclient
from util_discord import command_check

async def help_booru(ctx: commands.Context):
    if await command_check(ctx, "booru", "media"): return
    text = ["`-gel` gelbooru", "`-safe` safebooru", "`-r34` rule34"]
    await ctx.reply("\n".join(text))

async def R34(ctx: commands.Context, arg: str):
    if await command_check(ctx, "booru", "media"): return
    if not ctx.guild or not ctx.channel.nsfw: return await ctx.reply("**No.**")
    if arg: await search_posts(ctx, arg, "r34")
    else: await view_collection(ctx, "r34")

async def GEL(ctx: commands.Context, arg: str):
    if await command_check(ctx, "booru", "media"): return
    if not ctx.guild or not ctx.channel.nsfw: return await ctx.reply("**No.**")
    if arg: await search_posts(ctx, arg, "gel")
    else: await view_collection(ctx, "gel")

async def SAFE(ctx: commands.Context, arg: str):
    if await command_check(ctx, "booru", "media"): return
    if arg: await search_posts(ctx, arg, "safe")
    else: await view_collection(ctx, "safe")

async def view_collection(ctx: commands.Context, api: str):
    message = await ctx.reply(f"Retrieving collection…")
    results, errors = [], []
    mycol = myclient["gel"][api]
    user = await mycol.find_one({"user": ctx.message.author.id})
    if not user: 
        return await message.edit(content="**No results found**")
    for x in user["favorites"]:
        try:
            if api == "safe": cached = await Gelbooru(api='https://safebooru.org/').get_post(x)
            if api == "gel": cached = await Gelbooru().get_post(x)
            if api == "r34": cached = await Gelbooru(api='https://api.rule34.xxx/').get_post(x)
            results.append(cached)
            await message.edit(content=f"Retrieving collection…\nErrors: {errors}\n{len(results)} found")
        except: errors.append(x)
    if errors: await ctx.reply(f"Error retrieving `{errors}`")
    await message.edit(content=None, embed = await BuildEmbed(ctx.message.author, results, 0, True if api == "safe" else False, [False, False], ctx), 
                       view = ImageView(ctx.message.author, results, 0, True if api == "safe" else False, [False, False], ctx, api))

async def search_posts(ctx: commands.Context, arg: str, api: str):
    tags = re.split(r'\s*,\s*', arg)
    message = await ctx.reply(f"Searching posts with tags `{tags}`\nPlease wait…")
    results = []
    page = 0
    while len(results) < 25000: # hard limit
        if api == "safe": cached = await Gelbooru(api='https://safebooru.org/').search_posts(tags=tags, page=page)
        if api == "gel": cached = await Gelbooru().search_posts(tags=tags, page=page)
        if api == "r34": cached = await Gelbooru(api='https://api.rule34.xxx/').search_posts(tags=tags, page=page)
        if not cached: break
        results.extend(cached)
        await message.edit(content=f"Searching posts with tags `{tags}`\nPlease wait…\n{len(results)} found")
        page+=1
    if not results: return await message.edit(content="**No results found**")
    await message.edit(content=None, embed = await BuildEmbed(tags, results, 0, True if api == "safe" else False, [False, False], ctx), 
                       view = ImageView(tags, results, 0, True if api == "safe" else False, [False, False], ctx, api))

async def BuildEmbed(tags: list, results, index: int, safe: bool, lock: list, ctx: commands.Context) -> discord.Embed:
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
    def __init__(self, tags: list, results: list, index: int, safe: bool, lock: list, ctx: commands.Context, db: str):
        super().__init__(timeout=None)
        column, row, pagelimit = 0, -1, 8
        i = (index // pagelimit) * pagelimit
        while i < len(results):
            if column % 4 == 0: row += 1
            if (i < ((index // pagelimit) * pagelimit)+pagelimit): 
                self.add_item(ButtonAction(tags, safe, results, i, None, row, lock, ctx, db, str(i+1)))
            i += 1
            column += 1
        if not index == 0: 
            self.add_item(ButtonAction(tags, safe, results, 0, "⏪", 2, lock, ctx, db, ""))
            self.add_item(ButtonAction(tags, safe, results, index - 1, "◀️", 2, lock, ctx, db, ""))
        else:
            self.add_item(DisabledButton("⏪", 2))
            self.add_item(DisabledButton("◀️", 2))
        if index + 1 < len(results): 
            self.add_item(ButtonAction(tags, safe, results, index + 1, "▶️", 2, lock, ctx, db, ""))
            self.add_item(ButtonAction(tags, safe, results, len(results)-1, "⏩", 2, lock, ctx, db, ""))
        else:
            self.add_item(DisabledButton("▶️", 2))
            self.add_item(DisabledButton("⏩", 2))
        self.add_item(ButtonAction(tags, safe, results, random.randrange(0, len(results)), "🔀", 3, lock, ctx, db, ""))
        self.add_item(ButtonHeart(ctx, db, results[index].id, 3))
        self.add_item(ButtonAction(tags, safe, results, index, "🔒" if lock[1] else "🔓", 3, [lock[1], not lock[1]], ctx, db, ""))
        self.add_item(ButtonEnd(ctx, lock[1], 3))

class DisabledButton(discord.ui.Button):
    def __init__(self, e: str, r: int):
        super().__init__(emoji=e, style=discord.ButtonStyle.success, disabled=True, row=r)

class ButtonEnd(discord.ui.Button):
    def __init__(self, ctx: commands.Context, lock: bool, row: int):
        super().__init__(style=discord.ButtonStyle.success, emoji="🛑", row=row)
        self.ctx, self.lock = ctx, lock
    
    async def callback(self, interaction: discord.Interaction):
        if self.lock and interaction.user != self.ctx.author:
            return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can delete this message.", 
                                                    ephemeral=True)
        await interaction.response.edit_message(content="🤨", view=None, embed=None)
        await interaction.message.delete(delay=5)

class ButtonHeart(discord.ui.Button):
    def __init__(self, ctx: commands.Context, db: str, id: int, row: int):
        self.mycol = myclient["gel"][db]
        # emoji = "❤️" if list(self.mycol.find({"user": ctx.message.author.id, "favorites": id})) else "💔"
        super().__init__(style=discord.ButtonStyle.success, emoji="❤️", row=row)
        self.db, self.ctx, self.id = db, ctx, id
    
    async def callback(self, interaction: discord.Interaction):
        if not await self.mycol.find_one({"user": interaction.user.id}):
            await self.mycol.insert_one({"user": interaction.user.id})

        if not await self.mycol.find_one({"user": interaction.user.id, "favorites": self.id}):
            await self.mycol.update_one({"user": interaction.user.id}, {"$push": {"favorites" : self.id}})
            await interaction.response.send_message(f"❤️ Added to favorites ❤️\nUse `-{self.db}` to view your collection.", ephemeral=True)
        else: 
            await self.mycol.update_one({"user": interaction.user.id}, {"$pull": {"favorites" : self.id}})
            await interaction.response.send_message(f"💔 Removed to favorites 💔\nUse `-{self.db}` to view your collection.", ephemeral=True)

class ButtonAction(discord.ui.Button):
    def __init__(self, tags: list, safe: bool, results: list, index: list, l: str, row: int, lock: list, ctx: commands.Context, db: str, la: str):
        super().__init__(emoji=l, style=discord.ButtonStyle.success, row=row, label=la)
        self.results, self.index, self.tags, self.safe, self.lock, self.ctx, self.db = results, index, tags, safe, lock, ctx, db
    
    async def callback(self, interaction: discord.Interaction):
        if self.lock[0] != self.lock[1]:
            if interaction.user != self.ctx.author:
                return await interaction.response.send_message(f"Only <@{self.ctx.message.author.id}> can lock/unlock this message.", 
                                                               ephemeral=True)
            else: self.lock = [self.lock[1], self.lock[1]]
        if self.lock[1] and interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"<@{self.ctx.message.author.id}> locked this message.", ephemeral=True)
        await interaction.response.edit_message(embed = await BuildEmbed(self.tags, self.results, self.index, self.safe, self.lock, self.ctx), 
                                                view = ImageView(self.tags, self.results, self.index, self.safe, self.lock, self.ctx, self.db))
        
class CogSus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def booru(ctx: commands.Context):
        await help_booru(ctx)
    @commands.command()
    async def r34(ctx: commands.Context, *, arg=None):
        await R34(ctx, arg)
    @commands.command()
    async def gel(ctx: commands.Context, *, arg=None):
        await GEL(ctx, arg)
    @commands.command()
    async def safe(ctx: commands.Context, *, arg=None):
        await SAFE(ctx, arg)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogSus(bot))