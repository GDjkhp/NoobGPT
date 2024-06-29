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

def read_json_file(file_path):
    with open(file_path, 'r') as json_file:
        data = json.load(json_file)
    return data