import discord
from discord.ext import commands
from discord import app_commands
from aki_new import Akinator, CantGoBackAnyFurther
from util_discord import command_check, description_helper

categories = ['people', 'objects', 'animals']
languages = ['en', 'ar', 'cn', 'de', 'es', 'fr', 'it', 'jp', 'kr', 'nl', 'pl', 'pt', 'ru', 'tr', 'id']

def w(ctx: commands.Context, aki: Akinator) -> discord.Embed:
    embed_win = discord.Embed(title=aki.name_proposition, description=aki.description_proposition,
                              colour=0x00FF00)
    if ctx.message.author.avatar: embed_win.set_author(name=ctx.author, icon_url=ctx.message.author.avatar.url)
    else: embed_win.set_author(name=ctx.author)
    embed_win.set_image(url=aki.photo)
    # embed_win.add_field(name="Ranking", value="#"+aki.first_guess['ranking'], inline=True)
    embed_win.add_field(name="Questions", value=aki.step+1, inline=True)
    embed_win.add_field(name="Progress", value=f"{aki.progression}%", inline=True)
    return embed_win
def qEmbed(aki: Akinator, ctx: commands.Context) -> discord.Embed:
    e = discord.Embed(title=f"{aki.step+1}. {aki.question}", description=f"{aki.progression}%", color=0x00FF00)
    if ctx.message.author.avatar: e.set_author(name=ctx.author, icon_url=ctx.message.author.avatar.url)
    else: e.set_author(name=ctx.author)
    return e

class QView(discord.ui.View):
    def __init__(self, aki: Akinator, ctx: commands.Context):
        super().__init__(timeout=None)
        self.add_item(ButtonAction(aki, ctx, 0, 'Yes', '✅', 'y'))
        self.add_item(ButtonAction(aki, ctx, 0, 'No', '❌', 'n'))
        self.add_item(ButtonAction(aki, ctx, 0, 'Don\'t Know', '❓', 'idk'))
        self.add_item(ButtonAction(aki, ctx, 1, 'Probably', '👍', 'p'))
        self.add_item(ButtonAction(aki, ctx, 1, 'Probably Not', '👎', 'pn'))
        self.add_item(ButtonAction(aki, ctx, 2, 'Back', '⏮', 'b'))
        self.add_item(ButtonAction(aki, ctx, 2, 'Stop', '🛑', 's'))

class ButtonAction(discord.ui.Button):
    def __init__(self, aki: Akinator, ctx: commands.Context, row: int, l: str, emoji: str, action: str):
        super().__init__(label=l, style=discord.ButtonStyle.success, emoji=emoji, row=row)
        self.aki, self.action, self.ctx = aki, action, ctx
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(content=f"<@{self.ctx.message.author.id}> is playing this game! Use `-aki` to create your own game.", 
                                                   ephemeral=True)
        if self.action == 's':
            return await interaction.response.edit_message(content=f"Skill issue <@{interaction.user.id}>", view=None, embed=None)
        if self.action == 'b':
            try: await self.aki.back()
            except CantGoBackAnyFurther:
                return await interaction.response.send_message(content=f"CantGoBackAnyFurther", ephemeral=True)
        else: await self.aki.answer(self.action)
        if not self.aki.win and self.aki.step < 79:
            await interaction.response.edit_message(embed=qEmbed(self.aki, self.ctx), view=QView(self.aki, self.ctx))
        else:
            embed = w(self.ctx, self.aki)
            await interaction.response.edit_message(embed=embed, view=RView(self.aki, self.ctx))

class RView(discord.ui.View):
    def __init__(self, aki: Akinator, ctx):
        super().__init__(timeout=None)
        self.add_item(ButtonAction0(aki, ctx, 'Yes', '✅', 'y'))
        self.add_item(ButtonAction0(aki, ctx, 'No', '❌', 'n'))

class ButtonAction0(discord.ui.Button):
    def __init__(self, aki: Akinator, ctx: commands.Context, l: str, emoji: str, action: str):
        super().__init__(label=l, style=discord.ButtonStyle.success, emoji=emoji)
        self.aki, self.action, self.ctx = aki, action, ctx

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(content=f"<@{self.ctx.message.author.id}> is playing this game! Use `-aki` to create your own game.", 
                                                   ephemeral=True)
        if self.action == 'y':
            embed_win = discord.Embed(title='GG!', color=0x00FF00)
            embed_win.add_field(name=self.aki.name_proposition, value=self.aki.description_proposition, inline=False)
            embed_win.set_image(url=self.aki.photo)
            # embed_win.add_field(name="Ranking", value="#"+self.aki.first_guess['ranking'], inline=True)
            embed_win.add_field(name="Questions", value=self.aki.step+1, inline=True)
            embed_win.add_field(name="Progress", value=f"{self.aki.progression}%", inline=True)
            if self.ctx.message.author.avatar: embed_win.set_author(name=self.ctx.author, icon_url=self.ctx.message.author.avatar.url)
            else: embed_win.set_author(name=self.ctx.author)
            await interaction.response.edit_message(embed=embed_win, view=None)
        else:
            # FIXME: problematic, might remove
            # if self.aki.step < 79:
            #     try: await self.aki.exclude()
            #     except: pass
            #     return await interaction.response.edit_message(embed=qEmbed(self.aki, self.ctx), view=QView(self.aki, self.ctx))

            embed_loss = discord.Embed(title="Game over!", description="Please try again.", color=0xFF0000) # Here's some of my guesses:
            # for times in self.aki.guesses:
            #     embed_loss.add_field(name=times['name'], value=times['description'])
            
            if self.ctx.message.author.avatar: embed_loss.set_author(name=self.ctx.author, icon_url=self.ctx.message.author.avatar.url)
            else: embed_loss.set_author(name=self.ctx.author)
            await interaction.response.edit_message(embed=embed_loss, view=None)

# @commands.max_concurrency(1, per=BucketType.default, wait=False)
async def Aki(ctx: commands.Context, cat: str, lang: str):
    if await command_check(ctx, "aki", "games"): return
    msg = await ctx.reply('Starting game…')
    if not cat: cat = 'people'
    if not lang: lang = 'en'
    sfw = not ctx.channel.nsfw if ctx.guild else True
    if not lang in languages:
        return await msg.edit(content=f"Invalid language parameter.\nSupported languages:```{languages}```")
    if not cat in categories:
        return await msg.edit(content=f'Category `{cat}` not found.\nAvailable categories:```{categories}```')
    try: 
        aki = Akinator()
        await aki.start_game(language=f'{lang}' if cat == 'people' else f'{lang}_{cat}', child_mode=sfw)
        await msg.edit(content=None, embed=qEmbed(aki, ctx), view=QView(aki, ctx))
    except Exception as e: await msg.edit(content=f"Error! :(\n{e}")

async def cat_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=cat, value=cat) for cat in categories if current.lower() in cat.lower()
    ]

async def lang_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=lang, value=lang) for lang in languages if current.lower() in lang.lower()
    ]

class CogAki(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description=f'{description_helper["emojis"]["games"]} {description_helper["games"]["aki"]}')
    @app_commands.autocomplete(category=cat_auto, language=lang_auto)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    # @commands.max_concurrency(1, per=BucketType.default, wait=False)
    async def aki(self, ctx: commands.Context, category:str=None, language:str=None):
        await Aki(ctx, category, language)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogAki(bot))