import yt_dlp
from discord.ext import commands
import discord
import os

async def YTDLP(ctx: commands.Context, arg1: str, arg2: str):
    formats = ['mp3', 'm4a']
    if arg2 and not arg1 in formats: return await ctx.reply(f"Unsupported format :(")
    elif not arg2: arg2, arg1 = arg1, None
    ydl_opts = get_ydl_opts(arg1)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(arg2, download=False)
        filename = ydl.prepare_filename(info_dict) if not arg1 else f"{os.path.splitext(ydl.prepare_filename(info_dict))[0]}.{arg1}"
        await ctx.reply(f"Preparing `{filename}`\nLet me cook.")
        ydl.download(arg2) # this is faulty
        if os.path.isfile(filename):
            try: await ctx.reply(file=discord.File(filename))
            except: await ctx.reply(f"Error: An error occured while cooking `{filename}`\nFile too large!")
            os.remove(filename)
        else: 
            await ctx.reply(f"Error: An error occured while cooking `{filename}`\nFile too large!")

def checkSize(info, *, incomplete):
    filesize = info.get('filesize')
    if filesize and filesize > 25000000: # 25mb
        return f'File too large! {filesize} bytes'
    filesize = info.get('filesize_approx')
    if filesize and filesize > 25000000: # 25mb
        return f'File too large! {filesize} bytes'

def get_ydl_opts(arg):
    audio_formats = ["mp3", "m4a"]
    video_formats = ["mp4", "webm"]
    if arg in audio_formats:
        return {
            'format': 'm4a/bestaudio/best',
            'match_filter': checkSize,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': arg,
            }]
        }
    
    elif arg in video_formats: # disabled
        return {
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': arg,
            }]
        }
    else: 
        return {
            'match_filter': checkSize,
        }
