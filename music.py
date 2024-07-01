import wavelink
from discord.ext import commands
import discord
import json

async def setup_hook_music(bot: commands.Bot):
    servers = read_json_file("./res/lavalink_server_you_can_reload_when_shit_happens.json")
    nodes = []
    for lava in servers["nodes"]:
        nodes.append(wavelink.Node(uri=f'{"https://" if lava["https"] else "http://"}{lava["host"]}:{lava["port"]}', password=lava["password"]))
    await wavelink.Pool.connect(client=bot, nodes=nodes)
    
def music_embed(title: str, description: str):
    return discord.Embed(title=title, description=description, color=0x00ff00)

def music_now_playing_embed(track: wavelink.Playable):
    embed = discord.Embed(title="🎵 Now playing", description=track.title, color=0x00ff00)
    embed.add_field(name="Author", value=track.author)
    if track.album.name: embed.add_field(name="Album", value=track.album.name)
    embed.add_field(name="Duration", value=format_mil(track.length))

    if track.artwork: embed.set_thumbnail(url=track.artwork)
    elif track.album.url: embed.set_thumbnail(url=track.album.url)
    elif track.artist.url: embed.set_thumbnail(url=track.artist.url)

    if track.source == "spotify": 
        embed.set_author(name="Spotify", icon_url="https://gdjkhp.github.io/img/Spotify_App_Logo.svg.png")
    elif track.source == "youtube": 
        embed.set_author(name="YouTube", icon_url="https://gdjkhp.github.io/img/771384-512.png")
    else: print(track.source)
    return embed

def read_json_file(file_path):
    with open(file_path, 'r') as json_file:
        data = json.load(json_file)
    return data

def format_mil(milliseconds: int):
    seconds, milliseconds = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    return f"{days:02}:{hours:02}:{minutes:02}:{seconds:02}"