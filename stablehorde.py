import discord
from discord.ext import commands
import aiohttp
import base64
from PIL import Image
from io import BytesIO
import os
import asyncio

class RequestData(object):
    def __init__(self, prompt: str, model: str, n: int):
        self.submit_prepared = False
        self.client_agent = "cli_request_dream.py:1.1.0:(discord)db0#1625"
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
    
async def the_real_req(url: str, payload: dict = None, headers: dict = None, method: str="POST", data: str="JSON"):
    async with aiohttp.ClientSession() as session:
        if method=="POST":
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 202:
                    return await response.json()
                else: print(await response.content.read())
        if method=="GET":
            async with session.get(url) as response:
                content = await response.content.read()
                print(f"GET {response.status}")
                print(await response.content.read())
                if response.status == 200:
                    if data=="JSON": return await response.json()
                    if data=="CONTENT": return content
                # else: print(content.decode())
        if method=="DELETE":
            async with session.delete(url) as response:
                if response.status == 200:
                    return await response.json()
                else: print(await response.content.read())
    
async def generate(ctx: commands.Context, prompt: str, model: str, n: int):
    request_data = RequestData(prompt, model, n)
    # final_submit_dict["source_image"] = 'Test'

    progress_bar = True
    if progress_bar:
        pbar_queue_position = await ctx.reply("Queue Position: N/A | Wait Time: N/A")
        # pbar_progress = tqdm(
        #     total=request_data.imgen_params.get('n'), desc="progress")

    headers = {
        "apikey": request_data.api_key,
        "Client-Agent": request_data.client_agent,
    }
    # logger.debug(request_data.get_submit_dict())
    # logger.debug(json.dumps(request_data.get_submit_dict(), indent=4))
    async with aiohttp.ClientSession() as session:
        async with session.post(f'https://aihorde.net/api/v2/generate/async', 
                                json=request_data.get_submit_dict(), headers=headers) as submit_req:
            if submit_req.status==202:
                submit_results = await submit_req.json()
                # print(submit_results)
                req_id = submit_results.get('id')
                if not req_id:
                    print(submit_results)
                    return
                is_done = False
                retry = 0
                cancelled = False
                retrieve_req = None
                try:
                    while not is_done:
                        try:
                            async with session.get(f'https://aihorde.net/api/v2/generate/check/{req_id}') as chk_req:
                                if not chk_req.status==200:
                                    print(chk_req)
                                    return
                                chk_results = await chk_req.json()
                                print(chk_results)

                                if progress_bar:
                                    print(
                                        f"Wait:{chk_results.get('waiting')} "
                                        f"Proc:{chk_results.get('processing')} "
                                        f"Res:{chk_results.get('restarted')} "
                                        f"Fin:{chk_results.get('finished')}"
                                    )
                                    await pbar_queue_position.edit(content = f"Queue Position: {chk_results.get('queue_position')} | ETA: {chk_results.get('wait_time')}s")

                                is_done = chk_results['done']
                                await asyncio.sleep(0.8)
                        except ConnectionError as e:
                            retry += 1
                            print(
                                f"Error {e} when retrieving status. Retry {retry}/10")
                            if retry < 10:
                                await asyncio.sleep(0.8)
                                continue
                            raise
                except KeyboardInterrupt:
                    print(f"Cancelling {req_id}...")
                    cancelled = True
                    async with session.delete(f'https://aihorde.net/api/v2/generate/status/{req_id}') as retrieve_req_s:
                        if retrieve_req_s.status==200: retrieve_req = await retrieve_req_s.json()
                if not cancelled:
                    async with session.get(f'https://aihorde.net/api/v2/generate/status/{req_id}') as retrieve_req_s:
                        if retrieve_req_s.status==200: retrieve_req = await retrieve_req_s.json()
                if not retrieve_req:
                    return
                results_json = retrieve_req
                # logger.debug(results_json)
                if results_json['faulted']:
                    final_submit_dict = request_data.get_submit_dict()
                    if "source_image" in final_submit_dict:
                        final_submit_dict[
                            "source_image"] = f"img2img request with size: {len(final_submit_dict['source_image'])}"
                    print(
                        f"Something went wrong when generating the request. Please contact the horde administrator with your request details: {final_submit_dict}")
                    return
                results = results_json['generations']
                for iter in range(len(results)):
                    final_filename = request_data.filename
                    if len(results) > 1:
                        final_filename = f"{iter}_{request_data.filename}"
                    if request_data.get_submit_dict()["r2"]:
                        print(
                            f"Downloading '{results[iter]['id']}' from {results[iter]['img']}")
                        img_data = None
                        try:
                            async with session.get(results[iter]["img"]) as img:
                                if img.status==200: img_data = await img.content.read()
                        except:
                            print("Received b64 again")
                        if img_data: await ctx.reply(file=discord.File(BytesIO(img_data), f"{results[iter]['id']}.webp"))
                    else:
                        b64img = results[iter]["img"]
                        base64_bytes = b64img.encode('utf-8')
                        img_bytes = base64.b64decode(base64_bytes)
                        await ctx.reply(file=discord.File(BytesIO(img_bytes), f"{results[iter]['id']}.webp"))
                    censored = ''
                    if results[iter]["censored"]:
                        censored = " (censored)"
                    await pbar_queue_position.edit(content = 
                        f"Saved{censored} {final_filename} for {results_json['kudos']} kudos (via {results[iter]['worker_name']} - {results[iter]['worker_id']})")
                
class CogHorde(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def dream(self, ctx: commands.Context, *, prompt: str):
        await generate(ctx, prompt, "stable_diffusion", 1)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogHorde(bot))