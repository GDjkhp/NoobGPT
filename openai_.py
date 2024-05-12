from openai import AsyncOpenAI
import discord
import time
import aiohttp
import io
from discord.ext import commands

client = AsyncOpenAI()

# i really love this function
async def loopMsg(message: discord.Message):
    role = "assistant" if message.author.bot else "user"
    content = message.content.replace("-ask ", "")
    content = "Hello!" if content == "" else content
    if not message.reference:
        return [{"role": role, "content": content}]
    repliedMessage = await message.channel.fetch_message(message.reference.message_id)
    previousMessages = await loopMsg(repliedMessage)
    return previousMessages + [{"role": role, "content": content}]

async def discord_image(link: str, prompt: str) -> discord.File:
    async with aiohttp.ClientSession() as session:
        async with session.get(link) as response:
            if response.status == 200:
                image_bytes = await response.read()
                image_data = io.BytesIO(image_bytes)
                return discord.File(fp=image_data, filename=f'{prompt}.png')
            
async def help_openai(ctx: commands.Context):
    text  = "`-ask`: gpt-3.5-turbo"
    text += "`-gpt`: gpt-3.5-turbo-instruct"
    text += "`-imagine`: dall-e-2"
    await ctx.reply(text)

async def chat(ctx: commands.Context):
    message = ctx.message
    info = await message.reply("Generating response…")
    old = round(time.time() * 1000)
    messagesArray = await loopMsg(message)
    try:
        completion = await client.chat.completions.create(
            model="gpt-3.5-turbo",
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
    message = ctx.message
    info = await message.reply("Generating image…")
    old = round(time.time() * 1000)
    promptMsg = message.content.replace("-imagine ", "")
    if message.reference: # reply hack
        hey = await message.channel.fetch_message(message.reference.message_id)
        promptMsg = f"{promptMsg}: {hey.content.replace('-imagine ', '')}"
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
    message = ctx.message
    info = await message.reply("Generating response…")
    old = round(time.time() * 1000)
    content = message.content.replace("-gpt ", "")
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