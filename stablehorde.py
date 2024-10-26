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
import random
from util_discord import command_check, get_guild_prefix, description_helper

emoji_peak = description_helper['peak']
class RequestData(object):
    def __init__(self, prompt: str, model: str, n: int, nsfw: bool, width: int, height: int, steps: int, 
                 seed: str, seed_variation: int, sampler_name: str, karras: bool, tiling: bool, post_processing: str,
                 source_processing: str, source_image: discord.Attachment, source_mask: discord.Attachment):
        self.submit_prepared = False
        self.api_key = os.getenv("HORDE")
        self.imgen_params = {
            "n": n,
            "width": width,
            "height": height,
            "steps": steps,
            "sampler_name": sampler_name,
            "seed": seed,
            "seed_variation": seed_variation,
            "karras": karras,
            "tiling": tiling,
            "post_processing": [post_processing] if post_processing else []
        }
        self.submit_dict = {
            "prompt": prompt,
            "nsfw": nsfw,
            "censor_nsfw": False,
            "trusted_workers": False,
            "models": [model],
            "r2": True,
            "dry_run": False
        }
        self.source_image = source_image
        self.extra_source_images = None
        self.source_processing = source_processing
        self.source_mask = source_mask

    async def get_submit_dict(self):
        if self.submit_prepared:
            return self.submit_dict
        submit_dict = self.submit_dict.copy()
        submit_dict["params"] = self.imgen_params
        submit_dict["source_processing"] = self.source_processing
        if self.source_image:
            final_src_img = await self.source_image.read()
            submit_dict["source_image"] = base64.b64encode(final_src_img).decode()
        if self.source_mask:
            final_src_mask = await self.source_mask.read()
            submit_dict["source_mask"] = base64.b64encode(final_src_mask).decode()
        if self.extra_source_images:
            for esi in self.extra_source_images:
                if not isinstance(esi, dict):
                    print(f"Bad extra_source_images payload. Type: {type(esi)} (should be dict)")
                    continue
                if "image" not in esi:
                    print(f"No image key in extra_source_image entry.")
                    continue
                final_esi = await esi["image"].read()
                esi["image"] = base64.b64encode(final_esi).decode()
            submit_dict["extra_source_images"] = self.extra_source_images
        self.submit_prepared = True
        self.submit_dict = submit_dict
        return submit_dict

class CancelButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.cancelled = False

    @discord.ui.button(style=discord.ButtonStyle.danger, emoji="💀")
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

def get_random_seed(start_point=0):
    return str(random.randint(start_point, 2**32 - 1))
    
async def generate(ctx: commands.Context | discord.Interaction, prompt: str=None, model: str="stable_diffusion",
                   negative: str=None, n: int=1, width: int=64*8, height: int=64*8, steps: int=30,
                   seed: str=get_random_seed(), seed_variation: int=1, sampler_name: str="k_euler_a",
                   karras: bool=True, tiling: bool=False, post_processing: str=None,
                   source_processing: str="img2img", source_image: discord.Attachment=None, source_mask: discord.Attachment=None):
    if await command_check(ctx, "horde", "ai"):
        if isinstance(ctx, commands.Context):
            return await ctx.reply("command disabled", ephemeral=True)
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message("command disabled", ephemeral=True)
    if not prompt:
        if ctx.message.attachments: source_image = ctx.message.attachments[0]
        p = await get_guild_prefix(ctx)
        prompt = strip_dash(ctx.message.content, p)
    if negative: prompt+=f" ### {negative}"
    nsfw = False
    if ctx.guild and ctx.channel.nsfw:
        nsfw = True
    request_data = RequestData(prompt, model, n, nsfw, width, height, steps,
                               seed, seed_variation, sampler_name, karras, tiling, post_processing,
                               source_processing, source_image, source_mask)
    view = CancelButton()
    old = round(time.time() * 1000)
    if isinstance(ctx, commands.Context): info = await ctx.reply("**Queue Position: N/A**", view=view)
    if isinstance(ctx, discord.Interaction): await ctx.response.send_message("**Queue Position: N/A**", view=view)
    headers = {"apikey": request_data.api_key}
    settings = f"{model} ({width}x{height}, {steps} steps, {sampler_name})"
    final_submit_dict = await request_data.get_submit_dict()
    async with aiohttp.ClientSession() as session:
        submit_results = None
        async with session.post(f'https://aihorde.net/api/v2/generate/async', 
                                json=final_submit_dict, headers=headers) as submit_req:
            if submit_req.status == 202: submit_results = await submit_req.json()
        if not submit_results:
            if isinstance(ctx, commands.Context):
                return await info.edit(content="error", view=None)
            if isinstance(ctx, discord.Interaction):
                return await ctx.edit_original_response(content="error", view=None)
        req_id = submit_results.get('id')
        is_done = False
        results_json = None
        count_emoji = 0
        while not is_done:
            if view.cancelled:
                async with session.delete(f'https://aihorde.net/api/v2/generate/status/{req_id}') as retrieve_req:
                    if retrieve_req.status == 200:
                        if isinstance(ctx, commands.Context):
                            return await info.edit(content="**Generation cancelled**", view=None)
                        if isinstance(ctx, discord.Interaction):
                            return await ctx.edit_original_response(content="**Generation cancelled**", view=None)
            chk_results = None
            async with session.get(f'https://aihorde.net/api/v2/generate/check/{req_id}') as chk_req:
                if chk_req.status == 200: chk_results = await chk_req.json()
            if not chk_results:
                if isinstance(ctx, commands.Context):
                    return await info.edit(content="error", view=None)
                if isinstance(ctx, discord.Interaction):
                    return await ctx.edit_original_response(content="error", view=None)
            check = [
                f"**Queue Position: {chk_results.get('queue_position')} ({chk_results.get('wait_time')}s remaining)**",
                settings,
                f"{chk_results.get('finished')}/{n} {emoji_peak[count_emoji]}",
            ]
            if isinstance(ctx, commands.Context):
                await info.edit(content="\n".join(check))
            if isinstance(ctx, discord.Interaction):
                await ctx.edit_original_response(content="\n".join(check))
            is_done = chk_results['done']
            count_emoji+=1
            if count_emoji == len(emoji_peak): count_emoji=0
            await asyncio.sleep(3)
        if not view.cancelled:
            async with session.get(f'https://aihorde.net/api/v2/generate/status/{req_id}') as retrieve_req:
                if retrieve_req.status == 200: results_json = await retrieve_req.json()
        if not results_json:
            if isinstance(ctx, commands.Context):
                return await info.edit(content="error", view=None)
            if isinstance(ctx, discord.Interaction):
                return await ctx.edit_original_response(content="error", view=None)
        if results_json['faulted']:
            if "source_image" in final_submit_dict:
                final_submit_dict["source_image"] = f"img2img request with size: {len(final_submit_dict['source_image'])}"
            print(f"Something went wrong when generating the request. Please contact the horde administrator with your request details: {final_submit_dict}")
            if isinstance(ctx, commands.Context):
                return await info.edit(content="error", view=None)
            if isinstance(ctx, discord.Interaction):
                return await ctx.edit_original_response(content="error", view=None)
        results = results_json['generations']
        for iter in range(len(results)):
            if final_submit_dict["r2"]:
                try:
                    async with session.get(results[iter]["img"]) as img:
                        if img.status == 200:
                            file = discord.File(BytesIO(await img.content.read()), f"{results[iter]['id']}.webp")
                            if isinstance(ctx, commands.Context):
                                await ctx.reply(file=file)
                            if isinstance(ctx, discord.Interaction):
                                await ctx.followup.send(file=file)
                except: print("Received b64 again")
            else:
                b64img = results[iter]["img"]
                base64_bytes = b64img.encode('utf-8')
                img_bytes = base64.b64decode(base64_bytes)
                file = discord.File(BytesIO(img_bytes), f"{results[iter]['id']}.webp")
                if isinstance(ctx, commands.Context):
                    await ctx.reply(file=file)
                if isinstance(ctx, discord.Interaction):
                    await ctx.followup.send(file=file)
        if not view.cancelled:
            result_text = [
                f"**Took {round(time.time() * 1000)-old}ms**",
                settings,
                f"{chk_results.get('finished')}/{n}",
            ]
            if isinstance(ctx, commands.Context):
                await info.edit(content="\n".join(result_text), view=None)
            if isinstance(ctx, discord.Interaction):
                await ctx.edit_original_response(content="\n".join(result_text), view=None)

async def model_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    async with aiohttp.ClientSession() as session:
        async with session.get("https://aihorde.net/api/v2/status/models") as response:
            if response.status == 200:
                data = await response.json()
                models = [item["name"] for item in data]
                return [
                    app_commands.Choice(name=model, value=model) for model in models if current.lower() in model.lower()
                ][:25]
            
async def mode_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=mode, value=mode) for mode in ["img2img", "inpainting", "outpainting"] if current.lower() in mode.lower()
    ]

async def sample_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    samples = [
        "k_dpm_2_a", "k_dpm_adaptive", "k_heun", "k_dpmpp_2s_a", "k_dpmpp_2m", "lcm", "DDIM", "k_euler_a", "dpmsolver", 
        "k_dpm_fast", "k_dpmpp_sde", "k_lms", "k_dpm_2", "k_euler"
    ]
    return [
        app_commands.Choice(name=sample, value=sample) for sample in samples if current.lower() in sample.lower()
    ]

async def post_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    posts = [
        "GFPGAN", "RealESRGAN_x4plus", "RealESRGAN_x2plus", "RealESRGAN_x4plus_anime_6B",
        "NMKD_Siax", "4x_AnimeSharp", "CodeFormers", "strip_background"
    ]
    return [
        app_commands.Choice(name=post, value=post) for post in posts if current.lower() in post.lower()
    ]

async def help_horde(ctx: commands.Context):
    if await command_check(ctx, "horde", "ai"): return await ctx.reply("command disabled", ephemeral=True)
    p = await get_guild_prefix(ctx)
    text  = [
        "**Note: Use `/dream` for more available models and settings**",
        f"`{p}stable` stable_diffusion",
        f"`{p}waifu` waifu_diffusion",
        f"`{p}sdxl` SDXL 1.0",
        f"`{p}dream` Dreamshaper",
        f"`{p}dreamxl` DreamShaper XL",
        f"`{p}any` Anything v5",
    ]
    await ctx.reply("\n".join(text))
                
class CogHorde(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def stable(self, ctx: commands.Context):
        await generate(ctx, None, "stable_diffusion")

    @commands.command()
    async def waifu(self, ctx: commands.Context):
        await generate(ctx, None, "waifu_diffusion")

    @commands.command()
    async def sdxl(self, ctx: commands.Context):
        await generate(ctx, None, "SDXL 1.0")

    @commands.command()
    async def dream(self, ctx: commands.Context):
        await generate(ctx, None, "Dreamshaper")

    @commands.command()
    async def dreamxl(self, ctx: commands.Context):
        await generate(ctx, None, "DreamShaper XL")

    @commands.command()
    async def any(self, ctx: commands.Context):
        await generate(ctx, None, "Anything v5")

    @app_commands.command(description=f"{description_helper['emojis']['ai']} stablehorde")
    @app_commands.describe(prompt="Text prompt", negative="Negative prompt", model="Image model", n="Number of images to generate",
                           width="Image width", height="Image height", steps="Number of steps", post_processing="Post-processing method",
                           seed="Generation seed", seed_variation="Generation seed increment value", sampler_name="Sampling method",
                           karras="Karras noise scheduling tweaks", tiling="Stitch together seamlessly",
                           source_processing="Source processing mode", source_image="Image source for img2img", 
                           source_mask="Image mask source for inpainting/outpainting")
    @app_commands.autocomplete(model=model_auto, source_processing=mode_auto, sampler_name=sample_auto, post_processing=post_auto)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def dream(self, ctx: discord.Interaction, prompt: str, negative: str=None, model: str="DreamShaper XL",
                    n: int=1, width: int=64*8, height: int=64*8, steps: int=30,
                    seed: str=get_random_seed(), seed_variation: int=1, sampler_name: str="k_euler_a", 
                    karras: bool=True, tiling: bool=False, post_processing: str=None,
                    source_processing: str="img2img", source_image: discord.Attachment=None, source_mask: discord.Attachment=None):
        await generate(ctx, prompt, model, negative, n, width, height, steps,
                       seed, seed_variation, sampler_name, karras, tiling, post_processing,
                       source_processing, source_image, source_mask)

    @commands.command()
    async def horde(self, ctx: commands.Context):
        await help_horde(ctx)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogHorde(bot))