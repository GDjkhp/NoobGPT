from yt_dlp import YoutubeDL
from discord.ext import commands
from discord import app_commands
import discord
import os
import asyncio
import time
from util_discord import command_check, description_helper
from api_gdrive import AsyncDriveUploader

async def ytdlp_thumb(ctx: commands.Context, url: str):
    if await command_check(ctx, "thumb", "media"):
        return await ctx.reply("command disabled", ephemeral=True)
    if not url:
        return await ctx.reply("Please provide a YouTube URL!")
    info = await ctx.reply("checking url")
    with YoutubeDL({'cookiefile': './res/cookies.txt'}) as ydl:
        try:
            res = await asyncio.to_thread(ydl.extract_info, url, download=False)
        except:
            return await info.edit(content=":(")
        thumbnail_url = res.get('thumbnail')
        if not thumbnail_url:
            return await info.edit(content="Couldn't fetch the thumbnail. Is this a valid YouTube URL?")
        await info.edit(content=thumbnail_url)

async def YTDLP(ctx: commands.Context | discord.Interaction, arg1: str, arg2: str):
    if await command_check(ctx, "ytdlp", "media"):
        if isinstance(ctx, commands.Context):
            return await ctx.reply("command disabled", ephemeral=True)
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message("command disabled", ephemeral=True)
    # async with ctx.typing():  # Use async ctx.typing() to indicate the bot is working on it.
    old = round(time.time() * 1000)
    if not arg1:
        arg1, arg2 = "mp3", "dQw4w9WgXcQ"
    formats = ['mp3', 'm4a']
    if arg2 and arg1 not in formats:
        if isinstance(ctx, commands.Context):
            return await ctx.reply(f"Unsupported format :(\nAvailable conversion formats: `{formats}`")
        if isinstance(ctx, discord.Interaction):
            return await ctx.response.send_message(f"Unsupported format :(\nAvailable conversion formats: `{formats}`")
    elif not arg2:
        arg2, arg1 = arg1, None
    ydl_opts = get_ydl_opts(arg1)
    if isinstance(ctx, commands.Context):
        msg = await ctx.reply("Cooking…")
    if isinstance(ctx, discord.Interaction):
        await ctx.response.send_message("Cooking…")

    with YoutubeDL(ydl_opts) as ydl:
        try:
            # fixme: broken if generic
            info_dict = ydl.extract_info(arg2, download=False)
            filename = ydl.prepare_filename(info_dict) if not arg1 else f"{os.path.splitext(ydl.prepare_filename(info_dict))[0]}.{arg1}"
            if isinstance(ctx, commands.Context):
                await msg.edit(content=f"Preparing `{filename}`\nLet me cook.")
            if isinstance(ctx, discord.Interaction):
                await ctx.edit_original_response(content=f"Preparing `{filename}`\nLet me cook.")
            await asyncio.to_thread(ydl.download, [arg2]) # old hack
            if os.path.isfile(filename):
                try:
                    uploader = AsyncDriveUploader('./res/token.json')
                    results = await uploader.batch_upload([filename], 'NOOBGPT', True, True)
                    links = [{'label': 'Download', 'emoji': '⬇️', 'url': results[0].get('link')}]
                    # file = discord.File(filename)
                    if isinstance(ctx, commands.Context):
                        # await ctx.reply(file=file)
                        await ctx.reply(filename, view=LinksView(links, ctx))
                        await msg.edit(content=f"`{filename}` has been prepared successfully!\nTook {round(time.time() * 1000)-old}ms")
                    if isinstance(ctx, discord.Interaction):
                        # await ctx.followup.send(file=file)
                        await ctx.followup.send(filename, view=LinksView(links, ctx))
                        await ctx.edit_original_response(content=f"`{filename}` has been prepared successfully!\nTook {round(time.time() * 1000)-old}ms")
                except:
                    error_message = f"Error: An error occurred while cooking `{filename}`\nFile too large!"
                    if isinstance(ctx, commands.Context):
                        await msg.edit(content=error_message)
                    if isinstance(ctx, discord.Interaction):
                        await ctx.edit_original_response(content=error_message)
                os.remove(filename)
            else:
                error_message = f"Error: An error occurred while cooking `{filename}`"
                if isinstance(ctx, commands.Context):
                    await msg.edit(content=error_message)
                if isinstance(ctx, discord.Interaction):
                    await ctx.edit_original_response(content=error_message)
        except Exception as e:
            error_message = f"**Error! :(**\n{str(e)}"
            if isinstance(ctx, commands.Context):
                await msg.edit(content=error_message)
            if isinstance(ctx, discord.Interaction):
                await ctx.edit_original_response(content=error_message)

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

def checkSize(info, *, incomplete):
    filesize = info.get('filesize') if info.get('filesize') else info.get('filesize_approx')
    if filesize and filesize > 25000000: # 25mb
        return f'File too large! {filesize} bytes'

def get_ydl_opts(arg):
    audio_formats = ["mp3", "m4a"]
    video_formats = ["mp4", "webm"]
    options = {
        'cookiefile': './res/cookies.txt',
        'outtmpl': '%(title).200s.%(ext)s',
        'noplaylist': True,
        # 'match_filter': checkSize,
    }
    if arg in audio_formats:
        options.update({
            'format': 'm4a/bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': arg,
                'preferredquality': '320',
            }]
        })
    elif arg in video_formats: # disabled
        options.update({
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': arg,
            }]
        })
    return options

class CogYT(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ytdlp(self, ctx: commands.Context, arg1: str = None, arg2: str = None):
        await YTDLP(ctx, arg1, arg2)

    @app_commands.command(name="ytdlp", description=f'{description_helper["emojis"]["media"]} {description_helper["media"]["ytdlp"]}'[:100])
    @app_commands.describe(link="Video link")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ytdlp_basic(self, ctx: discord.Interaction, link: str = None):
        await YTDLP(ctx, link, None)

    @app_commands.command(name="ytdlp-mp3", description=f'{description_helper["emojis"]["media"]} {description_helper["media"]["ytdlp"]}'[:100])
    @app_commands.describe(link="Video link")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ytdlp_mp3(self, ctx: discord.Interaction, link: str = None):
        await YTDLP(ctx, "mp3", link)

    @app_commands.command(name="ytdlp-m4a", description=f'{description_helper["emojis"]["media"]} {description_helper["media"]["ytdlp"]}'[:100])
    @app_commands.describe(link="Video link")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ytdlp_m4a(self, ctx: discord.Interaction, link: str = None):
        await YTDLP(ctx, "m4a", link)
        
    @commands.hybrid_command(description=f'{description_helper["emojis"]["media"]} {description_helper["media"]["thumb"]}')
    @app_commands.describe(url="YouTube video URL")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def thumb(self, ctx: commands.Context, url: str = None):
        await ytdlp_thumb(ctx, url)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogYT(bot))