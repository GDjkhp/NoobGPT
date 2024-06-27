import wavelink
from wavelink.ext import spotify
from discord.ext import commands
import discord
import os
import json

async def setup_hook_music(bot: commands.Bot):
    sc = spotify.SpotifyClient(
        client_id=os.getenv("SPOT_ID"),
        client_secret=os.getenv("SPOT_SECRET")
    )
    lava = read_json_file("./res/lavalink_server_you_can_reload_when_shit_happens.json")
    await wavelink.NodePool.create_node(bot=bot, host=lava["host"],
                                        port=lava["port"], password=lava["password"],
                                        https=lava["https"], spotify_client=sc)
    
def music_embed(title: str, description: str):
    return discord.Embed(title=title, description=description, color=0x00ff00)

def read_json_file(file_path):
    with open(file_path, 'r') as json_file:
        data = json.load(json_file)
    return data