import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import base64
from PIL import Image
from io import BytesIO
import os
import asyncio
import time
from util_discord import command_check, get_guild_prefix

class RequestData(object):
    def __init__(self, prompt: str, model: str, n: int):
        self.submit_prepared = False
        self.api_key = os.getenv("HORDE")
        self.filename = None
        self.imgen_params = {
            "n": n,
            "width": 64*8,
            "height": 64*8,
            "steps": 20,
            "sampler_name": "k_euler_a",
            "cfg_scale": 7.5,
            "denoising_strength": 0.6,
            "hires_fix_denoising_strength": 0.5,
        }
        self.submit_dict = {
            "prompt": prompt,
            "nsfw": False,
            "censor_nsfw": False,
            "trusted_workers": False,
            "models": [model],
            "r2": True,
            "dry_run": False
        }
        self.source_image = None
        self.extra_source_images = None
        self.source_processing = "img2img"
        self.source_mask = None

    def get_submit_dict(self):
        if self.submit_prepared:
            return self.submit_dict
        submit_dict = self.submit_dict.copy()
        submit_dict["params"] = self.imgen_params
        submit_dict["source_processing"] = self.source_processing
        if self.source_image:
            final_src_img = Image.open(self.source_image)
            buffer = BytesIO()
            # We send as WebP to avoid using all the horde bandwidth
            final_src_img.save(buffer, format="Webp", quality=95, exact=True)
            submit_dict["source_image"] = base64.b64encode(
                buffer.getvalue()).decode("utf8")
        if self.source_mask:
            final_src_mask = Image.open(self.source_mask)
            buffer = BytesIO()
            # We send as WebP to avoid using all the horde bandwidth
            final_src_mask.save(buffer, format="Webp", quality=95, exact=True)
            submit_dict["source_mask"] = base64.b64encode(
                buffer.getvalue()).decode("utf8")
        if self.extra_source_images:
            for esi in self.extra_source_images:
                if not isinstance(esi, dict):
                    print(f"Bad extra_source_images payload. Type: {type(esi)} (should be dict)")
                    continue
                if "image" not in esi:
                    print(f"No image key in extra_source_image entry.")
                    continue
                final_esi = Image.open(esi["image"])
                buffer = BytesIO()
                # We send as WebP to avoid using all the horde bandwidth
                final_esi.save(buffer, format="Webp", quality=95, exact=True)
                esi["image"] = base64.b64encode(
                    buffer.getvalue()).decode("utf8")
            submit_dict["extra_source_images"] = self.extra_source_images
        self.submit_prepared = True
        self.submit_dict = submit_dict
        return submit_dict

class CancelButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.cancelled = False

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="💀")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.cancelled = True
        button.disabled = True
        await interaction.response.edit_message(view=self)

# ugly
def strip_dash(text: str, prefix: str):
    words = text.split()
    for i, word in enumerate(words):
        if word.startswith(prefix) and i != len(words)-1:
            words = words[:i] + words[i+1:]
            break
    return " ".join(words)
    
async def generate(ctx: commands.Context | discord.Interaction, prompt: str, model: str, n: int):
    if await command_check(ctx, "horde", "ai"):
        if isinstance(ctx, commands.Context):
            return await ctx.reply("command disabled", ephemeral=True)
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message("command disabled", ephemeral=True)
    if not prompt:
        p = await get_guild_prefix(ctx)
        prompt = strip_dash(ctx.message.content, p)
    request_data = RequestData(prompt, model, n)
    view = CancelButton()
    old = round(time.time() * 1000)
    if isinstance(ctx, commands.Context): info = await ctx.reply("Queue Position: N/A", view=view)
    if isinstance(ctx, discord.Interaction): await ctx.response.send_message("Queue Position: N/A", view=view)
    headers = {"apikey": request_data.api_key}
    async with aiohttp.ClientSession() as session:
        async with session.post(f'https://aihorde.net/api/v2/generate/async', 
                                json=request_data.get_submit_dict(), headers=headers) as submit_req:
            if submit_req.status == 202: submit_results = await submit_req.json()
            else:
                if isinstance(ctx, commands.Context):
                    return await info.edit("error", view=None)
                if isinstance(ctx, discord.Interaction):
                    return await ctx.edit_original_response("error", view=None)
            req_id = submit_results.get('id')
            is_done = False
            retry = 0
            results_json = None
            while not is_done:
                if view.cancelled:
                    async with session.delete(f'https://aihorde.net/api/v2/generate/status/{req_id}') as retrieve_req:
                        if retrieve_req.status == 200:
                            results_json = await retrieve_req.json()
                            if isinstance(ctx, commands.Context):
                                await info.edit(content="Generation cancelled.", view=None)
                            if isinstance(ctx, discord.Interaction):
                                await ctx.edit_original_response(content="Generation cancelled.", view=None)
                            break
                try:
                    async with session.get(f'https://aihorde.net/api/v2/generate/check/{req_id}') as chk_req:
                        if chk_req.status == 200: chk_results = await chk_req.json()
                        else: 
                            if isinstance(ctx, commands.Context):
                                return await info.edit("error", view=None)
                            if isinstance(ctx, discord.Interaction):
                                return await ctx.edit_original_response("error", view=None)
                        check = f"Queue Position: {chk_results.get('queue_position')} ({chk_results.get('wait_time')}s remaining)"
                        if isinstance(ctx, commands.Context):
                            await info.edit(content=check)
                        if isinstance(ctx, discord.Interaction):
                            await ctx.edit_original_response(content=check)
                        is_done = chk_results['done']
                        await asyncio.sleep(3)
                except ConnectionError as e:
                    retry += 1
                    print(f"Error {e} when retrieving status. Retry {retry}/10")
                    if retry < 10:
                        await asyncio.sleep(3)
                        continue
                    raise
            if not view.cancelled:
                async with session.get(f'https://aihorde.net/api/v2/generate/status/{req_id}') as retrieve_req:
                    if retrieve_req.status == 200: results_json = await retrieve_req.json()
            if not results_json:
                if isinstance(ctx, commands.Context):
                    return await info.edit("error", view=None)
                if isinstance(ctx, discord.Interaction):
                    return await ctx.edit_original_response("error", view=None)
            if results_json['faulted']:
                final_submit_dict = request_data.get_submit_dict()
                if "source_image" in final_submit_dict:
                    final_submit_dict["source_image"] = f"img2img request with size: {len(final_submit_dict['source_image'])}"
                print(f"Something went wrong when generating the request. Please contact the horde administrator with your request details: {final_submit_dict}")
                if isinstance(ctx, commands.Context):
                    return await info.edit("error", view=None)
                if isinstance(ctx, discord.Interaction):
                    return await ctx.edit_original_response("error", view=None)
            results = results_json['generations']
            for iter in range(len(results)):
                if request_data.get_submit_dict()["r2"]:
                    try:
                        async with session.get(results[iter]["img"]) as img:
                            if img.status == 200:
                                if isinstance(ctx, commands.Context):
                                    await ctx.reply(file=discord.File(BytesIO(await img.content.read()), f"{results[iter]['id']}.webp"))
                                if isinstance(ctx, discord.Interaction):
                                    await ctx.followup.send(file=discord.File(BytesIO(await img.content.read()), f"{results[iter]['id']}.webp"))
                    except: print("Received b64 again")
                else:
                    b64img = results[iter]["img"]
                    base64_bytes = b64img.encode('utf-8')
                    img_bytes = base64.b64decode(base64_bytes)
                    if isinstance(ctx, commands.Context):
                        await ctx.reply(file=discord.File(BytesIO(img_bytes), f"{results[iter]['id']}.webp"))
                    if isinstance(ctx, discord.Interaction):
                        await ctx.followup.send(file=discord.File(BytesIO(img_bytes), f"{results[iter]['id']}.webp"))
            if not view.cancelled:
                if isinstance(ctx, commands.Context):
                    await info.edit(content=f"**Took {round(time.time() * 1000)-old}ms**", view=None)
                if isinstance(ctx, discord.Interaction):
                    await ctx.edit_original_response(content=f"**Took {round(time.time() * 1000)-old}ms**", view=None)

async def model_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    async with aiohttp.ClientSession() as session:
        async with session.get("https://aihorde.net/api/v2/status/models") as response:
            if response.status == 200:
                data = await response.json()
                models = [item["name"] for item in data]
                return [
                    app_commands.Choice(name=model, value=model) for model in models if current.lower() in model.lower()
                ][:25]
                
class CogHorde(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def stable(self, ctx: commands.Context):
        await generate(ctx, None, "stable_diffusion", 1)

    @commands.command()
    async def waifu(self, ctx: commands.Context):
        await generate(ctx, None, "waifu_diffusion", 1)

    @app_commands.command(description="beta: stablehorde")
    @app_commands.describe(prompt="Text prompt", model="Image model", n="Number of images to generate")
    @app_commands.autocomplete(model=model_auto)
    async def dream(self, ctx: discord.Interaction, prompt: str, model: str="stable_diffusion", n: int=1):
        await generate(ctx, prompt, model, n)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogHorde(bot))