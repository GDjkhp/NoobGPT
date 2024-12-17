import shutil
from streamrip.config import Config
from streamrip.db import Dummy, Database
from streamrip.client import DeezerClient
from streamrip.rip.parse_url import parse_url
from discord.ext import commands
from discord import app_commands
import discord
from concurrent.futures import ThreadPoolExecutor # new hack
from api_gdrive import DriveUploader
from util_discord import description_helper, command_check, check_if_not_owner
from util_database import myclient
mycol = myclient["utils"]["cant_do_json_shit_dynamically_on_docker"]
link_null = "https://youtube.com/watch?v=dQw4w9WgXcQ"

async def get_deez():
    cursor = mycol.find()
    data = await cursor.to_list(None)
    return data[0]["deez"]

async def set_deez(ctx: commands.Context, arg: str):
    await mycol.update_one({}, {"$set": {"deez": arg}})
    await ctx.reply(await get_deez())

async def cook_deez(ctx: commands.Context, links: str):
    if await command_check(ctx, "deez", "media"): return await ctx.reply("command disabled", ephemeral=True)
    info = await ctx.reply("Logging in")
    config = Config("./res/config.toml")
    config.session.downloads.folder = f"./{ctx.author.id}"
    config.session.deezer.arl = await get_deez()
    client = DeezerClient(config)
    db = Database(downloads=Dummy(), failed=Dummy())
    await client.login()
    if not links: return await info.edit(content=":(")
    urls = links.split()
    par, dl, er = 0, 0, 0
    queue = [
        f"Parsed: {par}/{len(urls)}",
        f"Downloaded: {dl}/{len(urls)}",
        f"Errors: {er}/{len(urls)}",
        "Logged in",
    ]
    await info.edit(content="\n".join(queue))
    for url in urls:
        try:
            # parse flow
            queue[3] = f"Parsing `{url}`"
            await info.edit(content="\n".join(queue))
            parsed_url = parse_url(url)
            pending = await parsed_url.into_pending(client, config, db)
            resolved = await pending.resolve()
            par += 1
            queue[0] = f"Parsed: {par}/{len(urls)}"
            # download flow
            queue[3] = f"Downloading `{url}`"
            await info.edit(content="\n".join(queue))
            await resolved.rip()
            dl += 1
            queue[1] = f"Downloaded: {dl}/{len(urls)}"
        except Exception as e:
            # give up, let go, go fuck yourself and go die
            print(f"Exception in cook_deez: {e}")
            er += 1
            queue[2] = f"Errors: {er}/{len(urls)}"
    await client.session.close()

    await info.edit(content="Uploading to Google Drive. This may take a while.")
    uploader = DriveUploader('./res/token.json')
    with ThreadPoolExecutor() as pool:
        bot: commands.Bot = ctx.bot
        results = await bot.loop.run_in_executor(pool, uploader.batch_upload, [str(ctx.author.id)], 'NOOBGPT', True, True)
    collect_urls = []
    for result in results:
        if result['type'] == 'folder':
            folder_printer(result, ctx, collect_urls)
        # else:
        #     print(f"File: {result['name']}")
        #     print(f"Public Link: {result.get('link', 'No link')}")
        # print("---")
    shutil.rmtree(f"./{ctx.author.id}")
    await info.edit(content="i'm done.", view=LinksView(collect_urls, ctx),
                    embed=blud_folded_under_zero_pressure(ctx, collect_urls))

def folder_printer(result, ctx: commands.Context, collect_urls: list):
    if result['name'] != "__artwork": # check if not artwork folder
        if result['name'] == str(ctx.author.id) and not sub_root_cheeks(result): # check if sub-root folder
            data = {"label": "Root", "url": result.get('link', link_null), "emoji": "🫚",
                    "name": "Root", "size": result['size_human_readable']}
        else: # album folder
            data = {"label": len(collect_urls), "url": result.get('link', link_null), "emoji": None,
                    "name": result['name'], "size": result['size_human_readable']}
        collect_urls.append(data)

    # print(f"Folder: {result['name']}")
    # print(f"Public Link: {result.get('link', 'No link')}")
    # print("Files:")
    for file in result.get('files', []):
        if file['type'] == 'folder':
            folder_printer(file, ctx, collect_urls)
        # else:
        #     print(f"File: {file['name']}")
        #     print(f"Public Link: {result.get('link', 'No link')}")
        # print("---")
            
def blud_folded_under_zero_pressure(ctx: commands.Context, url_list: list) -> discord.Embed:
    e = discord.Embed(color=0x8000ff, title="deezdownloader9000", description="by GDjkhp")
    e.set_thumbnail(url="https://gdjkhp.github.io/img/kagura-yay-hd.gif")
    e.set_author(name=ctx.author, icon_url=ctx.author.avatar.url)
    for url in url_list:
        if url['name'] != "Root": 
            e.add_field(name=url['name'], value=url['size'], inline=False)
        else: e.set_footer(text=f"Total size: {url['size']}")
    return e

def sub_root_cheeks(folder):
    for f in folder.get('files', []):
        if folder['name'] == f['name']:
            return True
    return False

class CancelButton(discord.ui.Button):
    def __init__(self, ctx: commands.Context):
        super().__init__(emoji="❌", style=discord.ButtonStyle.success)
        self.ctx = ctx
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"Only <@{self.ctx.author.id}> can interact with this message.", 
                                                           ephemeral=True)
        await interaction.response.defer()
        await interaction.delete_original_response()
            
class LinksView(discord.ui.View):
    def __init__(self, links: list, ctx: commands.Context):
        super().__init__(timeout=None)
        for x in links[:24]:
            self.add_item(discord.ui.Button(style=discord.ButtonStyle.link, url=x['url'], label=x['label'], emoji=x['emoji']))
        self.add_item(CancelButton(ctx))

class CogDeez(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def rdeez(self, ctx: commands.Context, arg=None):
        if check_if_not_owner(ctx): return
        await set_deez(ctx, arg)

    @commands.hybrid_command(description=f"{description_helper['emojis']['media']} {description_helper["media"]["deez"]}")
    @app_commands.describe(links="Link queries")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def deez(self, ctx: commands.Context, *, links:str=None):
        await cook_deez(ctx, links)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogDeez(bot))