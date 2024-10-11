import discord
from discord import app_commands
from discord.ext import commands
from util_discord import command_check, description_helper

async def game_rps(ctx: commands.Context):
    if await command_check(ctx, "rps", "games"): return await ctx.reply("command disabled", ephemeral=True)
    await ctx.reply(":index_pointing_at_the_viewer:", view=RPSView(None, None))

def id2e(id: str) -> str:
    if id == "ROCK": return "🪨"
    if id == "PAPER": return "🧻"
    if id == "SCISSORS": return "✂️"

def logic_sense(id0: str, id1: str) -> str:
    winning_combinations = {
        ("ROCK", "PAPER"): "PAPER",
        ("PAPER", "SCISSORS"): "SCISSORS",
        ("SCISSORS", "ROCK"): "ROCK"
    }

    if (id0, id1) in winning_combinations:
        return winning_combinations[(id0, id1)]
    elif (id1, id0) in winning_combinations:
        return winning_combinations[(id1, id0)]
    else:
        return "DRAW"

class RPSView(discord.ui.View):
    def __init__(self, player: discord.User, w: str):
        super().__init__(timeout=None)
        self.add_item(ButtonChoice("ROCK", player, w))
        self.add_item(ButtonChoice("PAPER", player, w))
        self.add_item(ButtonChoice("SCISSORS", player, w))

class ButtonChoice(discord.ui.Button):
    def __init__(self, id: str, player: discord.User, w: str):
        super().__init__(label=id, emoji=id2e(id))
        self.id, self.player, self.w = id, player, w

    async def callback(self, interaction: discord.Interaction):
        if not self.player:
            await interaction.response.edit_message(content=f"{interaction.user.mention} :vs: :interrobang:", 
                                                    view=RPSView(interaction.user, self.id))
        else:
            if self.player == interaction.user: 
                return await interaction.response.send_message("You played yourself. Oh wait, you can't.", ephemeral=True)
            result = logic_sense(self.w, self.id)
            winner: discord.User = None if result == "DRAW" else self.player if result == self.w else interaction.user
            await interaction.response.edit_message(
                content=f"{id2e(self.w)}:vs:{id2e(self.id)}\n{'DRAW' if not winner else f'{winner.mention} won'}", view=None)

class CogRPS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description=f'{description_helper["emojis"]["games"]} {description_helper["games"]["rps"]}')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def rps(self, ctx: commands.Context):
        await game_rps(ctx)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogRPS(bot))