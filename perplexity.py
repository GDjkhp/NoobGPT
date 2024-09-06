import aiohttp
import os
import discord
from discord.ext import commands
import time
import base64
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

async def loopMsgGH(message: discord.Message):
    role = "assistant" if message.author.bot else "user"
    content = message.content if message.author.bot else strip_dash(message.content)
    
    # vision support?
    base64_data = None
    if len(message.attachments) > 0:
        attachment = message.attachments[0]
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                image_data = await resp.read()
                base64_data = base64.b64encode(image_data).decode('utf-8')
                content = "What’s in this image?" if content and content[0] == "-" else content
    content = "Hello!" if content and content[0] == "-" else content # if none is supplied

    base_data = [{
        "role": role, 
        "content": [
            {"type": "text", "text": content},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_data}"}} if base64_data else None
        ]
    }]

    if not message.reference: return base_data
    repliedMessage = await message.channel.fetch_message(message.reference.message_id)
    previousMessages = await loopMsgGH(repliedMessage)
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
    "open-mistral-7b", # m7b
    "open-mixtral-8x7b", # mx7b
    "open-mixtral-8x22b", # mx22b
    "mistral-small-latest", # ms
    "mistral-medium-latest", # mm
    "mistral-large-latest", # ml
    "codestral-latest" # mcode
]
models_groq=[
    "llama-3.1-405b-reasoning", # l31405
    "llama-3.1-70b-versatile", # l3170
    "llama-3.1-8b-instant", # l318
    "llama3-70b-8192", # l370
    "llama3-8b-8192", # l38
    "mixtral-8x7b-32768", # mix7b
    "gemma-7b-it", # g7b
    "gemma2-9b-it" # g29b
]
models_github=[
    "gpt-4o",
    "gpt-4o-mini",
    "Meta-Llama-3-70B-Instruct",
    "Meta-Llama-3-8B-Instruct",
    "Meta-Llama-3-1-405B-Instruct",
    "Meta-Llama-3-1-70B-Instruct",
    "Meta-Llama-3-1-8B-Instruct",
    "AI21-Jamba-Instruct",
    "Cohere-command-r",
    "Cohere-command-r-plus",
    "Mistral-large",
    "Mistral-large-2407",
    "Mistral-Nemo",
    "Mistral-small",
    "Phi-3-medium-128k-instruct",
    "Phi-3-medium-4k-instruct",
    "Phi-3-mini-128k-instruct",
    "Phi-3-mini-4k-instruct",
    "Phi-3-small-128k-instruct",
    "Phi-3-small-8k-instruct",
    "Phi-3.5-mini-instruct"
]

async def help_perplexity(ctx: commands.Context):
    if await command_check(ctx, "perplex", "ai"): return
    text = [
         f"`-ll` {models[0]}",
        f"`-cll` {models[1]}",
        f"`-mis` {models[2]}",
        f"`-mix` {models[3]}",
        f"`-ssc` {models[4]}",
        f"`-sso` {models[5]}",
        f"`-smc` {models[6]}",
        f"`-smo` {models[7]}"
    ]
    await ctx.reply("\n".join(text))

async def help_claude(ctx: commands.Context):
    if await command_check(ctx, "claude", "ai"): return
    text = [
        f"`-cla` {models_claude[0]}",
        f"`-c3o` {models_claude[1]}",
        f"`-c3s` {models_claude[2]}"
    ]
    await ctx.reply("\n".join(text))

async def help_mistral(ctx: commands.Context):
    if await command_check(ctx, "mistral", "ai"): return
    text = [
        f"`-m7b` {models_mistral[0]}",
        f"`-mx7b` {models_mistral[1]}",
        f"`-mx22b` {models_mistral[2]}",
        f"`-ms` {models_mistral[3]}",
        f"`-mm` {models_mistral[4]}",
        f"`-ml` {models_mistral[5]}",
        f"`-mcode` {models_mistral[6]}"
    ]
    await ctx.reply("\n".join(text))

async def help_groq(ctx: commands.Context):
    if await command_check(ctx, "groq", "ai"): return
    text = [
        f"`-l31405` {models_groq[0]}",
        f"`-l3170` {models_groq[1]}",
        f"`-l318` {models_groq[2]}",
        f"`-l370` {models_groq[3]}",
        f"`-l38` {models_groq[4]}",
        f"`-mix7b` {models_groq[5]}",
        f"`-g7b` {models_groq[6]}",
        f"`-g29b` {models_groq[7]}"
    ]
    await ctx.reply("\n".join(text))

async def the_real_req(url: str, payload: dict, headers: dict):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else: print(await response.content.read())

async def make_request(model: str, messages: list, url: str, key: str):
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
        "authorization": f"Bearer {key}"
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

async def make_request_mistral(model: str, messages: list, code: bool):
    url = f"https://api.mistral.ai/v1/{'fim' if code else 'chat'}/completions"
    payload = {
        "model": model,
        "prompt" if code else "messages": messages[0]["content"] if code else messages
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
        msg = await ctx.reply(f"{models[model]}\nGenerating response…")
        old = round(time.time() * 1000)
        try:
            url = "https://api.perplexity.ai/chat/completions"
            key = os.getenv('PERPLEXITY')
            response = await make_request(models[model], await loopMsg(ctx.message), url, key) # spicy
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

async def main_github(ctx: commands.Context, model: int):
    if await command_check(ctx, "github", "ai"): return
    async with ctx.typing():
        msg = await ctx.reply(f"{models_github[model]}\nGenerating response…")
        old = round(time.time() * 1000)
        try:
            url = "https://models.inference.ai.azure.com/chat/completions"
            key = os.getenv('GITHUB')
            response = await make_request(models_github[model], await loopMsgGH(ctx.message), url, key) # spicy
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

async def main_groq(ctx: commands.Context, model: int):
    if await command_check(ctx, "groq", "ai"): return
    async with ctx.typing():
        msg = await ctx.reply(f"{models_groq[model]}\nGenerating response…")
        old = round(time.time() * 1000)
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            key = os.getenv('GROQ')
            response = await make_request(models_groq[model], await loopMsg(ctx.message), url, key) # spicy
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
        msg = await ctx.reply(f"{models_claude[model]}\nGenerating response…")
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
        msg = await ctx.reply(f"{models_mistral[model]}\nGenerating response…")
        old = round(time.time() * 1000)
        try: 
            response = await make_request_mistral(models_mistral[model], await loopMsg(ctx.message), True if model == 6 else False)
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

class CogPerplex(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # HELP
    @commands.command()
    async def claude(ctx: commands.Context):
        await help_claude(ctx)

    @commands.command()
    async def mistral(ctx: commands.Context):
        await help_mistral(ctx)

    @commands.command()
    async def perplex(ctx: commands.Context):
        await help_perplexity(ctx)

    @commands.command()
    async def groq(ctx: commands.Context):
        await help_groq(ctx)

    # MISTRAL
    @commands.command()
    async def m7b(ctx: commands.Context):
        await main_mistral(ctx, 0)

    @commands.command()
    async def mx7b(ctx: commands.Context):
        await main_mistral(ctx, 1)

    @commands.command()
    async def mx22b(ctx: commands.Context):
        await main_mistral(ctx, 2)

    @commands.command()
    async def ms(ctx: commands.Context):
        await main_mistral(ctx, 3)

    @commands.command()
    async def mm(ctx: commands.Context):
        await main_mistral(ctx, 4)

    @commands.command()
    async def ml(ctx: commands.Context):
        await main_mistral(ctx, 5)

    @commands.command()
    async def mcode(ctx: commands.Context):
        await main_mistral(ctx, 6)

    # CLAUDE (DEAD AS FUCK)
    @commands.command()
    async def cla(ctx: commands.Context):
        await main_anthropic(ctx, 0)

    @commands.command()
    async def c3o(ctx: commands.Context):
        await main_anthropic(ctx, 1)

    @commands.command()
    async def c3s(ctx: commands.Context):
        await main_anthropic(ctx, 2)

    # PERPLEXITY (DEAD AS FUCK)
    @commands.command()
    async def ll(ctx: commands.Context):
        await main_perplexity(ctx, 0)

    @commands.command()
    async def cll(ctx: commands.Context):
        await main_perplexity(ctx, 1)

    @commands.command()
    async def mis(ctx: commands.Context):
        await main_perplexity(ctx, 2)

    @commands.command()
    async def mix(ctx: commands.Context):
        await main_perplexity(ctx, 3)

    @commands.command()
    async def ssc(ctx: commands.Context):
        await main_perplexity(ctx, 4)

    @commands.command()
    async def sso(ctx: commands.Context):
        await main_perplexity(ctx, 5)

    @commands.command()
    async def smc(ctx: commands.Context):
        await main_perplexity(ctx, 6)

    @commands.command()
    async def smo(ctx: commands.Context):
        await main_perplexity(ctx, 7)

    # GROQ
    @commands.command()
    async def l31405(ctx: commands.Context):
        await main_groq(ctx, 0)

    @commands.command()
    async def l3170(ctx: commands.Context):
        await main_groq(ctx, 1)

    @commands.command()
    async def l318(ctx: commands.Context):
        await main_groq(ctx, 2)

    @commands.command()
    async def l370(ctx: commands.Context):
        await main_groq(ctx, 3)

    @commands.command()
    async def l38(ctx: commands.Context):
        await main_groq(ctx, 4)

    @commands.command()
    async def mix7b(ctx: commands.Context):
        await main_groq(ctx, 5)

    @commands.command()
    async def g7b(ctx: commands.Context):
        await main_groq(ctx, 6)

    @commands.command()
    async def g29b(ctx: commands.Context):
        await main_groq(ctx, 7)

    # GITHUB BETA (WIP)
    @commands.command()
    async def gpt4o(ctx: commands.Context):
        await main_github(ctx, 0)

    @commands.command()
    async def gpt4om(ctx: commands.Context):
        await main_github(ctx, 1)

    @commands.command()
    async def ai21(ctx: commands.Context):
        await main_github(ctx, 7)

    @commands.command()
    async def ccr(ctx: commands.Context):
        await main_github(ctx, 8)

    @commands.command()
    async def ccrp(ctx: commands.Context):
        await main_github(ctx, 9)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogPerplex(bot))