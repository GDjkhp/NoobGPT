import requests
from discord.ext import commands
import asyncio

gde_guild_id = 1092112710667358218
gde_channel_id = 1201314997419130931
gds_guild_id = 398627612299362304
api = f"https://mee6.xyz/api/plugins/levels/leaderboard/{gds_guild_id}?limit=1000"

async def get_server_members(client_discord: commands.Bot, guild_id: int):
    guild = client_discord.get_guild(guild_id)
    members = []
    if guild:
        members = [member.id for member in guild.members]
    return members

async def check_and_send_level_up(client_discord: commands.Bot, old_data, new_data, server_members):
    old_players = old_data["players"]
    new_players = new_data["players"]
    for old_player, new_player in zip(old_data["players"], new_data["players"]):
        if new_player['id'] in server_members: # filter gde members
            # level
            old_level = old_player["level"]
            new_level = new_player["level"]
            # hundred_moment = new_level % 10 == 0 and new_level > old_level if old_level < 100 else new_level > old_level
            if new_level > old_level:
                channel = client_discord.get_channel(gde_channel_id)
                await channel.send(f"GG <@{new_player['id']}>, you just advanced to level {new_level}!") # GG @GDjkhp, you just advanced to level 100!
            # rank
            old_rank = old_players.index(old_player) + 1
            new_rank = new_players.index(new_player) + 1
            if old_rank > new_rank:
                channel = client_discord.get_channel(gde_channel_id)
                await channel.send(f"GG {new_player['username']}, you just advanced to rank #{new_rank}!")

async def main(client_discord: commands.Bot):
    data = requests.get(api).json()
    while True:
        await asyncio.sleep(60)
        new_data = requests.get(api).json()
        server_members = await get_server_members(client_discord, gde_guild_id)
        await check_and_send_level_up(client_discord, data, new_data, server_members)
        data = new_data