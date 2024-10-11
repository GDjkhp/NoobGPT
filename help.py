import discord
from discord.ext import commands
from discord import app_commands
from util_discord import command_check, description_helper, get_guild_prefix
import os
from datetime import datetime

# this is a deed that i should've done a long time ago
async def HALP(ctx: commands.Context):
    if await command_check(ctx, "halp", "utils"): return await ctx.reply("command disabled", ephemeral=True)
    desc = "A **very simple yet complicated** multi-purpose Discord bot that does pretty much nothing but insult you."
    url = "https://gdjkhp.github.io/NoobGPT"
    thumb = "https://gdjkhp.github.io/img/tama-anim-walk----Copy.gif"
    await ctx.reply(embed=await create_embed(0x00ff00, ctx, "NoobGPT", desc, url, thumb), view=HelpView(ctx, thumb))

async def HALP_MOOSIC(ctx: commands.Context):
    if await command_check(ctx, "halp", "utils"): return await ctx.reply("command disabled", ephemeral=True)
    desc = "grass is greenr on the othr side"
    url = "https://gdjkhp.github.io/NoobGPT/#moosic"
    thumb = "https://gdjkhp.github.io/img/sillynubcat.jpg"
    await ctx.reply(embed=await create_embed(0x00ffff, ctx, "Moosic", desc, url, thumb), view=HelpViewMoosic(ctx, thumb))

class HelpView(discord.ui.View):
    def __init__(self, ctx: commands.Context, thumb: str=None):
        super().__init__(timeout=None)
        self.add_item(ButtonSelect("AI", "🤖", 0, ctx, thumb, discord.ButtonStyle.success))
        self.add_item(ButtonSelect("GAMES", "🎲", 0, ctx, thumb, discord.ButtonStyle.primary))
        self.add_item(ButtonSelect("MEDIA", "💽", 0, ctx, thumb, discord.ButtonStyle.danger))
        self.add_item(ButtonSelect("UTILS", "🔧", 0, ctx, thumb, discord.ButtonStyle.secondary))

class HelpViewMoosic(discord.ui.View):
    def __init__(self, ctx: commands.Context, thumb: str=None):
        super().__init__(timeout=None)
        self.add_item(ButtonSelect("PLAYER", "⏯️", 0, ctx, thumb, discord.ButtonStyle.success))
        self.add_item(ButtonSelect("QUEUE", "🔀", 0, ctx, thumb, discord.ButtonStyle.primary))

class ButtonSelect(discord.ui.Button):
    def __init__(self, l: str, e: str, row: int, ctx: commands.Context, thumb: str, s: discord.ButtonStyle):
        super().__init__(label=l, emoji=e, style=s, row=row)
        self.l, self.ctx, self.thumb = l, ctx, thumb
    
    async def callback(self, interaction: discord.Interaction):
        if self.l == "AI":
            await interaction.response.send_message(embed=await ai_embed(self.ctx, self.thumb), ephemeral=True)
        if self.l == "GAMES":
            await interaction.response.send_message(embed=await games_embed(self.ctx, self.thumb), ephemeral=True)
        if self.l == "MEDIA":
            await interaction.response.send_message(embed=await media_embed(self.ctx, self.thumb), ephemeral=True)
        if self.l == "UTILS":
            await interaction.response.send_message(embed=await utils_embed(self.ctx, self.thumb), ephemeral=True)
        if self.l == "PLAYER":
            await interaction.response.send_message(embed=await player_embed(self.ctx, self.thumb), ephemeral=True)
        if self.l == "QUEUE":
            await interaction.response.send_message(embed=await queue_embed(self.ctx, self.thumb), ephemeral=True)

async def create_embed(color: int, ctx: commands.Context, title: str, desc: str=None, url: str=None, thumb: str=None) -> discord.Embed:
    bot: commands.Bot = ctx.bot
    user = await bot.fetch_user(int(os.getenv("OWNER")))
    emby = discord.Embed(title=title, description=desc, url=url, color=color)
    emby.set_thumbnail(url=thumb)
    emby.set_footer(text=f'Bot by GDjkhp\n© The Karakters Kompany, {datetime.now().year}',
                    icon_url=user.avatar.url if user.avatar else None)
    return emby

async def ai_embed(ctx: commands.Context, thumb: str) -> discord.Embed:
    emby = await create_embed(0x00ff00, ctx, "AI 🤖", thumb=thumb)
    prefix = await get_guild_prefix(ctx)
    for key in list(description_helper["ai"]):
        emby.add_field(name=f'`{prefix}{key}`', value=description_helper["ai"][key], inline=False)
    return emby

async def games_embed(ctx: commands.Context, thumb: str) -> discord.Embed:
    emby = await create_embed(0x00ffff, ctx, "Games 🎲", thumb=thumb)
    prefix = await get_guild_prefix(ctx)
    for key in list(description_helper["games"]):
        emby.add_field(name=f'`{prefix}{key}`', value=description_helper["games"][key], inline=False)
    return emby
    
async def media_embed(ctx: commands.Context, thumb: str) -> discord.Embed:
    emby = await create_embed(0xff0000, ctx, "Media 💽", thumb=thumb)
    prefix = await get_guild_prefix(ctx)
    for key in list(description_helper["media"]):
        emby.add_field(name=f'`{prefix}{key}`', value=description_helper["media"][key], inline=False)
    return emby

async def utils_embed(ctx: commands.Context, thumb: str) -> discord.Embed:
    emby = await create_embed(0x0000ff, ctx, "Utils 🔧", thumb=thumb)
    prefix = await get_guild_prefix(ctx)
    for key in list(description_helper["utils"]):
        emby.add_field(name=f'`{prefix}{key}`', value=description_helper["utils"][key], inline=False)
    # emby.add_field(name='`-lex [prompt]`', 
    #                value='Search AI Generated art (Stable Diffusion) made by the prompts of the community using Lexica', 
    #                inline=False)
    return emby

async def player_embed(ctx: commands.Context, thumb: str) -> discord.Embed:
    emby = await create_embed(0x00ff00, ctx, "Player ⏯️", thumb=thumb)
    prefix = await get_guild_prefix(ctx)
    for key in list(description_helper["player"]):
        emby.add_field(name=f'`{prefix}{key}`', value=description_helper["player"][key], inline=False)
    return emby

async def queue_embed(ctx: commands.Context, thumb: str) -> discord.Embed:
    emby = await create_embed(0x0000ff, ctx, "Queue 🔀", thumb=thumb)
    prefix = await get_guild_prefix(ctx)
    for key in list(description_helper["queue"]):
        emby.add_field(name=f'`{prefix}{key}`', value=description_helper["queue"][key], inline=False)
    return emby

class CogHelp(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.command()
    async def halp(self, ctx: commands.Context):
        await HALP(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['utils']} How to use this bot")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def help(self, ctx: commands.Context):
        await HALP(ctx)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogHelp(bot))