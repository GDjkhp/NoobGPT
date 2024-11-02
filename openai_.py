from openai import AsyncOpenAI
import discord
import time
import aiohttp
import io
from discord.ext import commands
import os
from util_discord import command_check, get_guild_prefix

client = AsyncOpenAI(api_key=os.getenv('OPENAI'))
client_sus = AsyncOpenAI(api_key=os.getenv('PAWAN'), base_url="https://api.pawan.krd/cosmosrp/v1")

# ugly
def strip_dash(text: str, prefix: str):
    words = text.split()
    for i, word in enumerate(words):
        if word.startswith(prefix) and i != len(words)-1:
            words = words[:i] + words[i+1:]
            break
    return " ".join(words)

# i really love this function, improved
async def loopMsg(message: discord.Message, prefix: str):
    role = "assistant" if message.author.bot else "user"
    content = message.content if message.author.bot else strip_dash(message.content, prefix)
    content = "Hello!" if content and content.startswith(prefix) else content
    base_data = [{"role": role, "content": content}]
    if not message.reference: return base_data
    repliedMessage = await message.channel.fetch_message(message.reference.message_id)
    previousMessages = await loopMsg(repliedMessage, prefix)
    return previousMessages + base_data

async def discord_image(link: str, prompt: str) -> discord.File:
    async with aiohttp.ClientSession() as session:
        async with session.get(link) as response:
            if response.status == 200:
                image_bytes = await response.read()
                image_data = io.BytesIO(image_bytes)
                return discord.File(fp=image_data, filename=f'{prompt}.png')
            
async def help_openai(ctx: commands.Context):
    if await command_check(ctx, "openai", "ai"): return await ctx.reply("command disabled", ephemeral=True)
    p = await get_guild_prefix(ctx)
    text = [
        f"`{p}ask` gpt-3.5-turbo",
        f"`{p}gpt` gpt-3.5-turbo-instruct",
        f"`{p}imagine` dall-e-2"
    ]
    await ctx.reply("\n".join(text))

async def chat(ctx: commands.Context, client: AsyncOpenAI, model: str):
    if await command_check(ctx, "openai", "ai"): return await ctx.reply("command disabled", ephemeral=True)
    # async with ctx.typing():
    message = ctx.message
    info = await message.reply("Generating response…")
    old = round(time.time() * 1000)
    prefix = await get_guild_prefix(ctx)
    messagesArray = await loopMsg(message, prefix)
    try:
        completion = await client.chat.completions.create(
            model=model,
            messages=messagesArray
        )
    except Exception as e:
        return await info.edit(content=f"**Error! :(**\n{e}")
    text = completion.choices[0].message.content
    chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
    replyFirst = True
    for chunk in chunks:
        if replyFirst: 
            replyFirst = False
            await message.reply(chunk)
        else: await message.channel.send(chunk)
    await info.edit(content=f"Took {round(time.time() * 1000)-old}ms")

async def image(ctx: commands.Context):
    if await command_check(ctx, "openai", "ai"): return await ctx.reply("command disabled", ephemeral=True)
    # async with ctx.typing():
    message = ctx.message
    info = await message.reply("Generating image…")
    old = round(time.time() * 1000)
    p = await get_guild_prefix(ctx)
    promptMsg = message.content.replace(f"{p}imagine ", "")
    if message.reference: # reply hack
        hey = await message.channel.fetch_message(message.reference.message_id)
        promptMsg = f"{promptMsg}: {hey.content.replace(f'{p}imagine ', '')}"
    promptMsg = "Generate something." if promptMsg == "" else promptMsg
    try:
        response = await client.images.generate(
            model="dall-e-2",
            prompt=promptMsg
        )
    except Exception as e:
        return await info.edit(content=f"**Error! :(**\n{e}")
    await message.reply(file=await discord_image(response.data[0].url, promptMsg))
    await info.edit(content=f"Took {round(time.time() * 1000)-old}ms")

async def gpt3(ctx: commands.Context):
    if await command_check(ctx, "openai", "ai"): return await ctx.reply("command disabled", ephemeral=True)
    # async with ctx.typing():
    message = ctx.message
    info = await message.reply("Generating response…")
    old = round(time.time() * 1000)
    content = message.content.replace(f"{await get_guild_prefix(ctx)}gpt ", "")
    content = "Generate 'Lorem ipsum…'" if content == "" else content
    try:
        completion = await client.completions.create(
            model="gpt-3.5-turbo-instruct",
            prompt=content
        )
    except Exception as e:
        return await info.edit(content=f"**Error! :(**\n{e}")
    text = completion.choices[0].text
    chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
    replyFirst = True
    for chunk in chunks:
        if replyFirst: 
            replyFirst = False
            await message.reply(chunk)
        else: await message.channel.send(chunk)
    await info.edit(content=f"Took {round(time.time() * 1000)-old}ms")

class CogOpenAI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ask(self, ctx: commands.Context):
        await chat(ctx, client, "gpt-3.5-turbo")

    @commands.command()
    async def imagine(self, ctx: commands.Context):
        await image(ctx)

    @commands.command()
    async def gpt(self, ctx: commands.Context):
        await gpt3(ctx)

    @commands.command()
    async def openai(self, ctx: commands.Context):
        await help_openai(ctx)

    # PAWAN (vps not allowed)
    # @commands.command()
    # async def cosmosrp(self, ctx: commands.Context):
    #     await chat(ctx, client_sus, "cosmosrp")

async def setup(bot: commands.Bot):
    await bot.add_cog(CogOpenAI(bot))