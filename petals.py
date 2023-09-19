from discord.ext import commands
import time
import aiohttp
import requests

async def petal(ctx: commands.Context, arg: str, model: str):
    async with ctx.typing():  # Use async ctx.typing() to indicate the bot is working on it.
        msg = await ctx.reply("Generating response…")
        old = round(time.time() * 1000)
        if not arg:
            arg = "Explain who you are, your functions, capabilities, limitations, and purpose."
        
        data = {
            'model': model,
            'inputs': arg,
            'max_length': 512,
            'do_sample': 1,
            'temperature': 0.9,
            'top_p': 0.6,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post('https://chat.petals.dev/api/v1/generate', data=data) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["ok"]:
                        if not data["outputs"]:
                            return await msg.edit(content=f"**Error! :(**\nEmpty response.")
                        chunks = [data["outputs"][i:i+2000] for i in range(0, len(data["outputs"]), 2000)]
                        replyFirst = True
                        for chunk in chunks:
                            if replyFirst: 
                                replyFirst = False
                                await ctx.reply(chunk)
                            else:
                                await ctx.send(chunk)
                        await msg.edit(content=f"**Took {round(time.time() * 1000)-old}ms**")
                    else:
                        await msg.edit(content=f"**Error! :(**\n{PETALS()}")
                else:
                    await msg.edit(content=f"**Error! :(**")

async def BELUGA2(ctx: commands.Context, arg: str):
    await petal(ctx, arg, 'stabilityai/StableBeluga2')

async def LLAMA2(ctx: commands.Context, arg: str):
    await petal(ctx, arg, 'meta-llama/Llama-2-70b-chat-hf') # meta-llama/Llama-2-70b-hf

async def GUANACO(ctx: commands.Context, arg: str):
    await petal(ctx, arg, 'timdettmers/guanaco-65b')

async def LLAMA(ctx: commands.Context, arg: str):
    await petal(ctx, arg, 'huggyllama/llama-65b')

async def BLOOMZ(ctx: commands.Context, arg: str):
    await petal(ctx, arg, 'bigscience/bloomz')

async def CODELLAMA(ctx: commands.Context, arg: str):
    await petal(ctx, arg, 'codellama/CodeLlama-34b-Instruct-hf')

def PETALS() -> str:
    status = requests.get("https://health.petals.dev/api/v1/state").json()
    text = "# [Petals](https://petals.dev/)\nRun large language models at home, BitTorrent‑style.\n\n"
    text += "Commands:\n`-beluga2, -llama2, -guanaco, -llama, -bloomz, -codellama`\n\nModels:```diff\n"
    for i in status["model_reports"]: 
        text += f"{'+ ' if i['state'] == 'healthy' else '- '}{i['name']}: {i['state']}\n"
    text += "```"
    return text