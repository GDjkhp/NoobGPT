import wavelink
from discord.ext import commands
import discord
import json

async def setup_hook_music(bot: commands.Bot):
    lava = read_json_file("./res/lavalink_server_you_can_reload_when_shit_happens.json")
    node = wavelink.Node(uri=f'{"https://" if lava["https"] else "http://"}{lava["host"]}:{lava["port"]}', password=lava["password"])
    await wavelink.Pool.connect(client=bot, nodes=[node])
    
def music_embed(title: str, description: str):
    return discord.Embed(title=title, description=description, color=0x00ff00)

def music_now_playing_embed(track: wavelink.Playable):
    embed = discord.Embed(title=track.title, description=track.artist, color=0x00ff00)
    if track.artwork: embed.set_image(url=track.artwork)
    if track.source == "spotify": embed.set_thumbnail(url="https://gdjkhp.github.io/img/Spotify_App_Logo.svg.png")
    elif track.source == "youtube": embed.set_thumbnail(url="https://gdjkhp.github.io/img/771384-512.png")
    else: print(track.source)
    return embed

def read_json_file(file_path):
    with open(file_path, 'r') as json_file:
        data = json.load(json_file)
    return data