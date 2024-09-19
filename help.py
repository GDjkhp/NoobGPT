import discord
from discord.ext import commands
from discord import app_commands
from util_discord import command_check, description_helper, get_guild_prefix

# this is a deed that i should've done a long time ago
user_id = 729554186777133088
async def HALP(ctx: commands.Context):
    if await command_check(ctx, "halp", "utils"): return
    desc = "A **very simple yet complicated** multi-purpose Discord bot that does pretty much nothing but insult you."
    url = "https://gdjkhp.github.io/NoobGPT"
    await ctx.reply(embed=await create_embed(0x00ff00, ctx, "NoobGPT", desc, url), view=HelpView(ctx))

class HelpView(discord.ui.View):
    def __init__(self, ctx: commands.Context):
        super().__init__(timeout=None)
        self.add_item(ButtonSelect("AI", "🤖", 0, ctx, discord.ButtonStyle.success))
        self.add_item(ButtonSelect("GAMES", "🎲", 0, ctx, discord.ButtonStyle.primary))
        self.add_item(ButtonSelect("MEDIA", "💽", 0, ctx, discord.ButtonStyle.danger))
        self.add_item(ButtonSelect("UTILS", "🔧", 0, ctx, discord.ButtonStyle.secondary))

class ButtonSelect(discord.ui.Button):
    def __init__(self, l: str, e: str, row: int, ctx: commands.Context, s: discord.ButtonStyle):
        super().__init__(label=l, emoji=e, style=s, row=row)
        self.l, self.ctx = l, ctx
    
    async def callback(self, interaction: discord.Interaction):
        if self.l == "AI":
            await interaction.response.send_message(embed=await ai_embed(self.ctx), ephemeral=True)
        if self.l == "GAMES":
            await interaction.response.send_message(embed=await games_embed(self.ctx), ephemeral=True)
        if self.l == "MEDIA":
            await interaction.response.send_message(embed=await media_embed(self.ctx), ephemeral=True)
        if self.l == "UTILS":
            await interaction.response.send_message(embed=await utils_embed(self.ctx), ephemeral=True)

async def create_embed(color: int, ctx: commands.Context, title: str, desc: str=None, url: str=None) -> discord.Embed:
    bot: commands.Bot = ctx.bot
    user = await bot.fetch_user(user_id)
    emby = discord.Embed(title=title, description=desc, url=url, color=color)
    emby.set_thumbnail(url='https://gdjkhp.github.io/img/tama-anim-walk----Copy.gif')
    emby.set_footer(text='Bot by GDjkhp\n© The Karakters Kompany, 2024',
                    icon_url=user.avatar.url if user.avatar else None)
    return emby

async def ai_embed(ctx: commands.Context) -> discord.Embed:
    emby = await create_embed(0x00ff00, ctx, "AI 🤖")
    prefix = await get_guild_prefix(ctx)
    for key in list(description_helper["ai"]):
        emby.add_field(name=f'`{prefix}{key}`', value=description_helper["ai"][key], inline=False)
    return emby

async def games_embed(ctx: commands.Context) -> discord.Embed:
    emby = await create_embed(0x00ffff, ctx, "Games 🎲")
    prefix = await get_guild_prefix(ctx)
    for key in list(description_helper["games"]):
        emby.add_field(name=f'`{prefix}{key}`', value=description_helper["games"][key], inline=False)
    return emby
    
async def media_embed(ctx: commands.Context) -> discord.Embed:
    emby = await create_embed(0xff0000, ctx, "Media 💽")
    prefix = await get_guild_prefix(ctx)
    for key in list(description_helper["media"]):
        emby.add_field(name=f'`{prefix}{key}`', value=description_helper["media"][key], inline=False)
    return emby

async def utils_embed(ctx: commands.Context) -> discord.Embed:
    emby = await create_embed(0x0000ff, ctx, "Utils 🔧")
    prefix = await get_guild_prefix(ctx)
    for key in list(description_helper["utils"]):
        emby.add_field(name=f'`{prefix}{key}`', value=description_helper["utils"][key], inline=False)
    # emby.add_field(name='`-lex [prompt]`', 
    #                value='Search AI Generated art (Stable Diffusion) made by the prompts of the community using Lexica', 
    #                inline=False)
    return emby

class CogHelp(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.command()
    async def halp(self, ctx: commands.Context):
        await HALP(ctx)

    @commands.hybrid_command(description=f"{description_helper['emojis']['utils']} how to use")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def help(self, ctx: commands.Context):
        await HALP(ctx)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogHelp(bot))