from flask import Flask, jsonify
from discord.ext.commands import Bot
from threading import Thread

app = Flask('')
bot_instances: dict[str, Bot] = {}

def register_bot(identifier: str, bot: Bot):
    bot_instances[identifier] = bot

@app.route('/')
def main():
    return "Bot by GDjkhp"

@app.route('/bot/<identifier>', methods=['GET'])
def get_bot_info(identifier):
    if not identifier:
        return jsonify({'error': 'No identifier provided'}), 400

    bot = bot_instances.get(identifier)
    if not bot:
        return jsonify({'error': 'Bot not found'}), 404

    return jsonify({
        'identifier': identifier,
        'guild_count': len(bot.guilds)
    })

def run():
    app.run(host="0.0.0.0", port=20129)

def serve():
    server = Thread(target=run)
    server.start()