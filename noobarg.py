import discord
from discord.ext import commands
import os

class ArgView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ButtonChoice(0))
        self.add_item(ButtonChoice(1))

class ButtonChoice(discord.ui.Button):
    def __init__(self, choice: int):
        super().__init__(label=str(choice), style=discord.ButtonStyle.primary)
        self.choice = choice
    
    async def callback(self, interaction: discord.Interaction):
        if (self.choice == 0): await interaction.response.edit_message(content="you won nitor basic dm the guy you deserved it", view=None)
        if (self.choice == 1): await interaction.response.edit_message(content="you won a game on steam worth <₱100 dm the guy you deserved it", view=None)

async def start(ctx: commands.Context, arg: str):
    if (arg == "0"): await ctx.reply(content="mwahahahaha you can't stop me\nhttps://i.imgur.com/1JNb9PB.png")
    elif (arg == "1"): await ctx.reply(content="(i want to actually) [block](https://github.com/mrpond/BlockTheSpot) the SPOT, but DEEZ [boat](https://fredboat.com/) ZUCK.\nhttps://i.imgur.com/naaZQ9V.png")
    elif (arg == "2"): await ctx.reply(content="now my [stack](https://myanimelist.net/forum/?topicid=2006510) of anime is in [trouble](https://myanimelist.net/anime/3455/To_LOVE-Ru)\nhttps://i.imgur.com/wHkMEqr.png")
    elif (arg == "3"): await ctx.reply(content="while I look at it, there's a GROUND in my CLOUD\nhttps://i.imgur.com/LYk4tjn.png")
    elif (arg == "44"): await ctx.reply(content="check 'disagreement between people ~~(HUMAN VS BOT)~~' steam\nhttps://i.imgur.com/P6ya221.png")
    elif (arg): await ctx.reply(content="https://i.imgur.com/6PnuZ1Q.jpg")

async def end(ctx: commands.Context, arg: str):
    if (ctx.guild == None and arg == os.getenv("ANSWER")): 
        # await ctx.reply(content="congregation, you killed the bot\nhttps://i.imgur.com/Krl2law.png", view=ArgView())
        await ctx.reply(content="event already ended :(")