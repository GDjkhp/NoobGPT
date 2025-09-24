from discord.ext.commands import Bot
from quart import Quart, jsonify, request
from quart_cors import cors
from gpt4free import get_models
from time import time
from util_geometryjump import gj_song_info

app = Quart('')
app = cors(app, allow_origin="*")
bot_instances: dict[str, Bot] = {}
bot_starttime: dict[str, int] = {}

def register_bot(identifier: str, bot: Bot):
    bot_instances[identifier] = bot
    bot_starttime[identifier] = int(time())

@app.route('/')
async def main():
    return "Bot by GDjkhp"

@app.route('/bot/<identifier>', methods=['GET'])
async def get_bot_info(identifier):
    if not identifier:
        return jsonify({'error': 'No identifier provided'}), 400

    bot = bot_instances.get(identifier)
    if not bot:
        return jsonify({'error': 'Bot not found'}), 404

    app_info = await bot.application_info()
    return jsonify({
        'start_time': bot_starttime.get(identifier),
        'guild_count': len(bot.guilds),
        'user_count': len(bot.users),
        'user_install_count': app_info.approximate_user_install_count or 0,
        'latency': f"{round(bot.latency * 1000) if bot.latency != float('inf') else '♾️'}ms",
        'prefix_commands': [command.name for command in bot.commands],
        'slash_commands': [command.name for command in bot.tree.get_commands()],
        'cogs': [
            {
                cog_id: {
                    'prefix': [command.name for command in cog.get_commands()],
                    'slash': [command.name for command in cog.get_app_commands()],
                }
            } for cog_id, cog in bot.cogs.items()
        ],
    })

@app.route('/models', methods=['GET'])
async def get_models_info():
    models_text, models_image = await get_models()
    return jsonify({
        "TEXT": models_text,
        "IMAGE": models_image,
    })

@app.route('/song-info', methods=['GET'])
async def song_info_endpoint():
    song_id = request.args.get('song_id')
    if not song_id:
        return jsonify({'error': 'Missing song_id parameter'}), 400
    info = await gj_song_info(song_id)
    if not info or not info.get('ID'):
        return jsonify({'error': 'Song not found'}), 404
    return jsonify(info)

async def serve():
    await app.run_task(host="0.0.0.0", port=20129)