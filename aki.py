import discord
from discord.ext import commands
from discord import app_commands
from akinator import AsyncAkinator, CantGoBackAnyFurther
from util_discord import command_check, description_helper, get_guild_prefix

CATEGORIES = {
    'people': 'c', 
    'objects': 'o', 
    'animals': 'a'
}

LANGUAGES = ['en', 'ar', 'cn', 'de', 'es', 'fr', 'it', 'jp', 'kr', 'nl', 'pl', 'pt', 'ru', 'tr', 'id']

def create_win_embed(ctx: commands.Context, aki: AsyncAkinator) -> discord.Embed:
    embed_win = discord.Embed(
        title=aki.name_proposition,
        description=aki.description_proposition,
        colour=0x00FFFF
    )
    if ctx.author.avatar:
        embed_win.set_author(name=ctx.author, icon_url=ctx.author.avatar.url)
    else:
        embed_win.set_author(name=ctx.author)
    embed_win.set_image(url=aki.photo)
    embed_win.add_field(name="Questions", value=aki.step+1, inline=True)
    embed_win.add_field(name="Progress", value=f"{aki.progression}%", inline=True)
    return embed_win

def create_final_embed(ctx: commands.Context, aki: AsyncAkinator) -> discord.Embed:
    embed_win = discord.Embed(title='GG!', color=0x00FF00)
    embed_win.add_field(name=aki.name_proposition, value=aki.description_proposition, inline=False)
    embed_win.set_image(url=aki.photo)
    embed_win.add_field(name="Questions", value=aki.step+1, inline=True)
    embed_win.add_field(name="Progress", value=f"{aki.progression}%", inline=True)
    if ctx.author.avatar:
        embed_win.set_author(name=ctx.author, icon_url=ctx.author.avatar.url)
    else:
        embed_win.set_author(name=ctx.author)
    return embed_win

def create_loss_embed(ctx: commands.Context) -> discord.Embed:
    embed_loss = discord.Embed(
        title="Game over!",
        description="Please try again.",
        color=0xFF0000
    )
    if ctx.author.avatar:
        embed_loss.set_author(name=ctx.author, icon_url=ctx.author.avatar.url)
    else:
        embed_loss.set_author(name=ctx.author)
    return embed_loss

def create_question_embed(aki: AsyncAkinator, ctx: commands.Context) -> discord.Embed:
    embed = discord.Embed(
        title=f"{aki.step+1}. {aki.question}",
        description=f"{aki.progression}%",
        color=0x00FFFF
    )
    if ctx.author.avatar:
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar.url)
    else:
        embed.set_author(name=ctx.author)
    return embed

class QuestionView(discord.ui.View):
    def __init__(self, aki: AsyncAkinator, ctx: commands.Context):
        super().__init__(timeout=None)
        self.add_item(ButtonAction(aki, ctx, 0, 'Yes', '✅', 'y'))
        self.add_item(ButtonAction(aki, ctx, 0, 'No', '❌', 'n'))
        self.add_item(ButtonAction(aki, ctx, 0, 'Don\'t Know', '❓', 'idk'))
        self.add_item(ButtonAction(aki, ctx, 1, 'Probably', '👍', 'p'))
        self.add_item(ButtonAction(aki, ctx, 1, 'Probably Not', '👎', 'pn'))
        self.add_item(ButtonAction(aki, ctx, 2, 'Back', '⏮️', 'b'))
        self.add_item(ButtonAction(aki, ctx, 2, 'Stop', '🛑', 's'))

class ButtonAction(discord.ui.Button):
    def __init__(self, aki: AsyncAkinator, ctx: commands.Context, row: int, label: str, emoji: str, action: str):
        super().__init__(label=label, style=discord.ButtonStyle.success, emoji=emoji, row=row)
        self.aki = aki
        self.action = action
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(
                content=f"<@{self.ctx.author.id}> is playing this game! Use `{await get_guild_prefix(self.ctx)}aki` to create your own game.",
                ephemeral=True
            )
        if self.action == 's':
            return await interaction.response.edit_message(content=f"Skill issue <@{interaction.user.id}>", view=None, embed=None)
        try:
            if self.action == 'b':
                await interaction.response.defer()
                await self.aki.back()
            else:
                # Handle answer actions
                await interaction.response.edit_message(view=None)
                if self.aki.step == 79:
                    embed_loss = create_loss_embed(self.ctx)
                    return await interaction.edit_original_response(embed=embed_loss, view=None)
                await self.aki.answer(self.action)
                if self.aki.progression > 95 and self.aki.win:
                    embed = create_win_embed(self.ctx, self.aki)
                    return await interaction.edit_original_response(
                        embed=embed,
                        view=ResultView(self.aki, self.ctx)
                    )
            # Continue with next question
            await interaction.edit_original_response(
                embed=create_question_embed(self.aki, self.ctx), 
                view=QuestionView(self.aki, self.ctx)
            )
        except CantGoBackAnyFurther:
            await interaction.followup.send(content="Cannot go back any further!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(content=f"Error: {str(e)}", ephemeral=True)

class ResultView(discord.ui.View):
    def __init__(self, aki: AsyncAkinator, ctx):
        super().__init__(timeout=None)
        self.add_item(ResultButton(aki, ctx, 'Yes', '✅', 'y'))
        self.add_item(ResultButton(aki, ctx, 'No', '❌', 'n'))

class ResultButton(discord.ui.Button):
    def __init__(self, aki: AsyncAkinator, ctx: commands.Context, label: str, emoji: str, action: str):
        super().__init__(label=label, style=discord.ButtonStyle.success, emoji=emoji)
        self.aki = aki
        self.action = action
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message(
                content=f"<@{self.ctx.author.id}> is playing this game! Use `{await get_guild_prefix(self.ctx)}aki` to create your own game.",
                ephemeral=True
            )
        try:
            if self.action == 'y':
                embed_win = create_final_embed(self.ctx, self.aki)
                await interaction.response.edit_message(embed=embed_win, view=None)
            else:
                if self.aki.step < 79:
                    try:
                        await self.aki.exclude()
                        return await interaction.response.edit_message(
                            embed=create_question_embed(self.aki, self.ctx), 
                            view=QuestionView(self.aki, self.ctx)
                        )
                    except Exception: pass
                embed_loss = create_loss_embed(self.ctx)
                await interaction.response.edit_message(embed=embed_loss, view=None)
        except Exception as e:
            await interaction.response.send_message(content=f"Error: {str(e)}", ephemeral=True)

async def start_akinator_game(ctx: commands.Context, category: str = None, language: str = None):
    if await command_check(ctx, "aki", "games"): return await ctx.reply("Command disabled", ephemeral=True)
    msg = await ctx.reply('Starting game…')
    category = category or 'people'
    language = language or 'en'
    sfw = not ctx.channel.nsfw if ctx.guild else True

    if language not in LANGUAGES:
        return await msg.edit(
            content=f"Invalid language parameter.\nSupported languages:```{', '.join(LANGUAGES)}```"
        )
    if category not in CATEGORIES:
        return await msg.edit(
            content=f'Category `{category}` not found.\nAvailable categories:```{", ".join(CATEGORIES.keys())}```'
        )

    try:
        aki = AsyncAkinator()
        theme = CATEGORIES[category]
        await aki.start_game(language=language, theme=theme, child_mode=sfw)
        await msg.edit(
            content=None, 
            embed=create_question_embed(aki, ctx), 
            view=QuestionView(aki, ctx)
        )
    except Exception as e:
        await msg.edit(content=f"Error starting Akinator! :(\n{e}")

async def cat_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=cat, value=cat) 
        for cat in CATEGORIES.keys() 
        if current.lower() in cat.lower()
    ]

async def lang_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=lang, value=lang) 
        for lang in LANGUAGES 
        if current.lower() in lang.lower()
    ]

class CogAki(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description=f'{description_helper["emojis"]["games"]} {description_helper["games"]["aki"]}')
    @app_commands.autocomplete(category=cat_auto, language=lang_auto)
    @app_commands.describe(category="Set category", language="Set language")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    # @commands.max_concurrency(1, per=BucketType.default, wait=False)
    async def aki(self, ctx: commands.Context, category: str = None, language: str = None):
        await start_akinator_game(ctx, category, language)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogAki(bot))