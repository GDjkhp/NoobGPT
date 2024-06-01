import aiohttp
import os
import discord
from discord.ext import commands
import time
from util_discord import command_check

# ugly
def strip_dash(text: str):
    words = text.split()
    for i, word in enumerate(words):
        if word.startswith("-") and i != len(words)-1:
            words = words[:i] + words[i+1:]
            break
    return " ".join(words)

# i really love this function, improved
async def loopMsg(message: discord.Message):
    role = "assistant" if message.author.bot else "user"
    content = message.content if message.author.bot else strip_dash(message.content)
    content = "Hello!" if content and content[0] == "-" else content
    base_data = [{"role": role, "content": content}]
    if not message.reference: return base_data
    repliedMessage = await message.channel.fetch_message(message.reference.message_id)
    previousMessages = await loopMsg(repliedMessage)
    return previousMessages + base_data

models = [
    "llama-2-70b-chat", # ll
    "codellama-70b-instruct", # cll
    "mistral-7b-instruct", # mis
    "mixtral-8x7b-instruct", # mix
    "sonar-small-chat", # ssc
    "sonar-small-online", # sso
    "sonar-medium-chat", # smc
    "sonar-medium-online", #smo
]
models_claude=[
    "claude-2.1", # cla
    "claude-3-opus-20240229", # c3o
    "claude-3-sonnet-20240229", #c3s
]
models_mistral=[
    "mistral-medium-latest", # mm
    "mistral-large-latest", # ml
]

async def help_perplexity(ctx: commands.Context):
    if await command_check(ctx, "perplex", "ai"): return
    text  =  f"`-ll`: {models[0]}\n"
    text += f"`-cll`: {models[1]}\n"
    text += f"`-mis`: {models[2]}\n"
    text += f"`-mix`: {models[3]}\n"
    text += f"`-ssc`: {models[4]}\n"
    text += f"`-sso`: {models[5]}\n"
    text += f"`-smc`: {models[6]}\n"
    text += f"`-smo`: {models[7]}"
    await ctx.reply(text)

async def help_claude(ctx: commands.Context):
    if await command_check(ctx, "claude", "ai"): return
    text  = f"`-cla`: {models_claude[0]}\n"
    text += f"`-c3o`: {models_claude[1]}\n"
    text += f"`-c3s`: {models_claude[2]}"
    await ctx.reply(text)

async def help_mistral(ctx: commands.Context):
    if await command_check(ctx, "mistral", "ai"): return
    text  = f"`-mm`: {models_mistral[0]}\n"
    text += f"`-ml`: {models_mistral[1]}"
    await ctx.reply(text)

async def the_real_req(url: str, payload: dict, headers: dict):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else: print(await response.content.read())

async def make_request(model: str, messages: list):
    url = "https://api.perplexity.ai/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Be precise and concise."
            }
        ] + messages
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {os.getenv('PERPLEXITY')}"
    }

    return await the_real_req(url, payload, headers)

async def make_request_claude(model: str, messages: list):
    url = "https://api.anthropic.com/v1/messages"
    payload = {
        "model": model, # claude-2.1, claude-instant-1.2
        "max_tokens": 1024,
        "messages": messages
    }
    headers = {
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "x-api-key": os.getenv('ANTHROPIC')
    }

    return await the_real_req(url, payload, headers)

async def make_request_mistral(model: str, messages: list):
    url = "https://api.mistral.ai/v1/chat/completions"
    payload = {
        "model": model,
        "messages": messages
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {os.getenv('MISTRAL')}"
    }

    return await the_real_req(url, payload, headers)

async def main_perplexity(ctx: commands.Context, model: int):
    if await command_check(ctx, "perplex", "ai"): return
    async with ctx.typing():
        msg = await ctx.reply("Generating response…")
        old = round(time.time() * 1000)
        try: 
            response = await make_request(models[model], await loopMsg(ctx.message)) # spicy
            text = response["choices"][0]["message"]["content"]
            if not text or text == "": return await msg.edit(content=f"**Error! :(**\nEmpty response.")
            chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
            replyFirst = True
            for chunk in chunks:
                if replyFirst: 
                    replyFirst = False
                    await ctx.reply(chunk)
                else: await ctx.send(chunk)
        except Exception as e:
            # bruh = response["detail"][0]["msg"] if response and response.get("detail") else e
            print(e)
            return await msg.edit(content=f"**Error! :(**")
        await msg.edit(content=f"**Took {round(time.time() * 1000)-old}ms**")

async def main_anthropic(ctx: commands.Context, model: int):
    if await command_check(ctx, "claude", "ai"): return
    async with ctx.typing():
        msg = await ctx.reply("Generating response…")
        old = round(time.time() * 1000)
        try:
            response = await make_request_claude(models_claude[model], await loopMsg(ctx.message)) # spicy
            text = response["content"][0]["text"]
            if not text or text == "": return await msg.edit(content=f"**Error! :(**\nEmpty response.")
            chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
            replyFirst = True
            for chunk in chunks:
                if replyFirst: 
                    replyFirst = False
                    await ctx.reply(chunk)
                else: await ctx.send(chunk)
        except Exception as e:
            # bruh = response["error"]["message"] if response and response.get("error") else e
            print(e)
            return await msg.edit(content=f"**Error! :(**")
        await msg.edit(content=f"**Took {round(time.time() * 1000)-old}ms**")

async def main_mistral(ctx: commands.Context, model: int):
    if await command_check(ctx, "mistral", "ai"): return
    async with ctx.typing():
        msg = await ctx.reply("Generating response…")
        old = round(time.time() * 1000)
        try: 
            response = await make_request_mistral(models_mistral[model], await loopMsg(ctx.message)) # spicy
            text = response["choices"][0]["message"]["content"]
            if not text or text == "": return await msg.edit(content=f"**Error! :(**\nEmpty response.")
            chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
            replyFirst = True
            for chunk in chunks:
                if replyFirst: 
                    replyFirst = False
                    await ctx.reply(chunk)
                else: await ctx.send(chunk)
        except Exception as e:
            print(e)
            return await msg.edit(content=f"**Error! :(**") # i can't assume here
        await msg.edit(content=f"**Took {round(time.time() * 1000)-old}ms**")