from flask import Flask, jsonify
from gunicorn.app.base import BaseApplication
from discord.ext.commands import Bot
from threading import Thread

app = Flask('')
bot_instances: dict[str, Bot] = {}

class StandaloneApplication(BaseApplication):
    def init(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().init()

    def load_config(self):
        for key, value in self.options.items():
            self.cfg.set(key, value)

    def load(self):
        return self.application

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
        'guild_count': len(bot.guilds),
        'user_count': len(bot.users),
        'latency': f"{round(bot.latency * 1000) if bot.latency != float('inf') else '♾️'}ms",
        'commands': [command.name for command in bot.tree.get_commands()],
    })

def run():
    options = {
        "bind": "0.0.0.0:20129", # Keep the same port
        "workers": 4, # Increase workers based on CPU cores
        "worker_class": "gevent", # Async workers for better concurrency
        "worker_connections": 10000, # Allow more connections
        "timeout": 30, # Adjust timeout
        "keepalive": 15, # Reduce dropped connections
    }
    StandaloneApplication(app, options).run()

def serve():
    server = Thread(target=run)
    server.start()