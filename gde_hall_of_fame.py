import requests
from discord.ext import commands
import asyncio

async def get_server_members(client_discord: commands.Bot, guild_id: int):
    guild = client_discord.get_guild(guild_id)
    members = []
    if guild:
        members = [member.id for member in guild.members]
    return members

async def check_and_send_level_up(client_discord: commands.Bot, old_data, new_data, server_members):
    for old_player, new_player in zip(old_data["players"], new_data["players"]):
        if new_player['id'] in server_members: # filter gde members
            old_level = old_player["level"]
            new_level = new_player["level"]
            hundred_moment = new_level % 10 == 0 and new_level > old_level if old_level < 100 else new_level > old_level
            if hundred_moment:
                channel_id = 1201314997419130931 # change this to target channel soon
                channel = client_discord.get_channel(channel_id)
                await channel.send(f"GG <@{new_player['id']}>, you just advanced to level {new_level}!") # GG @GDjkhp, you just advanced to level 100!

async def main(client_discord: commands.Bot):
    data = requests.get("https://mee6.xyz/api/plugins/levels/leaderboard/398627612299362304?limit=1000").json()
    while True:
        await asyncio.sleep(60)
        new_data = requests.get("https://mee6.xyz/api/plugins/levels/leaderboard/398627612299362304?limit=1000").json()
        guild_id = 1092112710667358218
        server_members = await get_server_members(client_discord, guild_id)
        await check_and_send_level_up(client_discord, data, new_data, server_members)
        data = new_data