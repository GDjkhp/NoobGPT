import discord
from discord.ext import commands
from util_discord import command_check

model_master = [
    "gpt4o", "gemini", "gemini_flash", "mistral", "llama"
]

async def ai_respond_mode(ctx: commands.Context, model: str):
    return