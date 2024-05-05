import discord
from discord.ext import commands
import json

# this is a deed that i should've done a long time ago
async def HALP(ctx: commands.Context, av: discord.Asset):
    await ctx.reply(embed=create_embed(0x00ff00, av), view=HelpView(av))

def read_json_file(file_path):
    with open(file_path, 'r') as json_file:
        data = json.load(json_file)
    return data

class HelpView(discord.ui.View):
    def __init__(self, av: discord.Asset):
        super().__init__(timeout=None)
        self.add_item(ButtonSelect("AI", "🤖", 0, av, discord.ButtonStyle.success))
        self.add_item(ButtonSelect("GAMES", "🎲", 0, av, discord.ButtonStyle.primary))
        self.add_item(ButtonSelect("MEDIA", "💽", 0, av, discord.ButtonStyle.danger))
        self.add_item(ButtonSelect("UTILS", "🔧", 0, av, discord.ButtonStyle.secondary))

class ButtonSelect(discord.ui.Button):
    def __init__(self, l: str, e: str, row: int, av: discord.Asset, s: discord.ButtonStyle):
        super().__init__(label=l, emoji=e, style=s, row=row)
        self.l, self.av = l, av
    
    async def callback(self, interaction: discord.Interaction):
        if self.l == "AI":
            await interaction.response.send_message(embed=await ai_embed(self.av), ephemeral=True)
        if self.l == "GAMES":
            await interaction.response.send_message(embed=await games_embed(self.av), ephemeral=True)
        if self.l == "MEDIA":
            await interaction.response.send_message(embed=await media_embed(self.av), ephemeral=True)
        if self.l == "UTILS":
            await interaction.response.send_message(embed=await utils_embed(self.av), ephemeral=True)

def create_embed(color: int, av: discord.Asset) -> discord.Embed:
    emby = discord.Embed(title="NoobGPT", 
                         description="A **very simple yet complicated** multi-purpose Discord bot that does pretty much nothing but insult you.", 
                         url="https://gdjkhp.github.io/NoobGPT/", color=color) # 0x00ff00
    emby.set_thumbnail(url='https://i.imgur.com/ZbnJAHI.gif')
    emby.set_footer(text='Bot by GDjkhp\n© The Karakters Kompany, 2024', icon_url=av)
    return emby

def create_embed_cat(color: int, cat: str, av: discord.Asset) -> discord.Embed:
    emby = discord.Embed(title=cat, color=color) # 0x00ff00
    emby.set_thumbnail(url='https://i.imgur.com/ZbnJAHI.gif')
    emby.set_footer(text='Bot by GDjkhp\n© The Karakters Kompany, 2024', icon_url=av)
    return emby

async def ai_embed(av: discord.Asset) -> discord.Embed:
    emby = create_embed_cat(0x00ff00, "AI 🤖", av)
    emby.add_field(name='`-ask [prompt]`', 
                   value='OpenAI GPT-3.5-Turbo (ChatGPT) chat completion.', 
                   inline=False)
    emby.add_field(name='`-gpt [prompt]`', 
                   value='OpenAI GPT-3 text completion.', 
                   inline=False)
    emby.add_field(name='`-imagine [prompt]`', 
                   value='OpenAI Dall-E image generation.', 
                   inline=False)
    # emby.add_field(name='`-bard [prompt]`', 
    #                value='[Google Bard](https://bard.google.com) chat completion. (Deprecated)', 
    #                inline=False)
    emby.add_field(name='`-palm [prompt]`', 
                   value='Google AI PaLM language model. (Legacy)', 
                   inline=False)
    emby.add_field(name='`-ge [text/image]`', 
                   value='Google AI Gemini language model.', 
                   inline=False)
    emby.add_field(name='`-petals`', 
                   value='Run large language models at home, BitTorrent‑style.', 
                   inline=False)
    emby.add_field(name='`-perplex`', 
                   value='Perplexity AI unlocks the power of knowledge with information discovery and sharing.', 
                   inline=False)
    emby.add_field(name='`-chelp`', 
                   value='Character.ai is an American neural language model chatbot service that can generate human-like text responses and participate in contextual conversation.', 
                   inline=False)
    return emby

async def games_embed(av: discord.Asset) -> discord.Embed:
    emby = create_embed_cat(0x00ffff, "Games 🎲", av)
    emby.add_field(name='`-aki (optional: category = [people/animals/objects] [language])`', 
                   value='Play a guessing game of [Akinator](https://akinator.com).', 
                   inline=False)
    emby.add_field(name='`-tic`', 
                   value='Play tic-tac-toe with someone. (Deprecated)', 
                   inline=False)
    emby.add_field(name='`-hang (optional: mode = [all/hardcore/me] count = [1-50] [type = any/word/quiz] category = [any/9-32] difficulty = [any/easy/medium/hard])`', 
                   value='Play the word puzzle game of hangman.', 
                   inline=False)
    # emby.add_field(name='`-place (optional: x = [0-499] y = [0-499] zoom = [16x])`', 
    #                value='Play the Reddit social experiment event about placing pixels on a canvas.', 
    #                inline=False)
    emby.add_field(name='`-quiz (optional: mode = [all/anon/me] version = [any/v1/v2] count = [1-50] category = [any/9-32] difficulty = [any/easy/medium/hard] type = [any/multiple/boolean])`', 
                   value='Play a game of quiz.', 
                   inline=False)
    emby.add_field(name='`-word (optional: stats = [rank/lead/global] OR mode = [all/hardcore/me] count = [1-50])`', 
                   value='Play a game of wordle.', 
                   inline=False)
    emby.add_field(name='`-rps`', 
                   value='Play rock-paper-scissors.',
                   inline=False)
    return emby
    
async def media_embed(av: discord.Asset) -> discord.Embed:
    data = read_json_file("./res/mandatory_settings_and_splashes.json")
    emby = create_embed_cat(0xff0000, "Media 💽", av)
    emby.add_field(name='`/help`', 
                   value='Show music commands help page.', 
                   inline=False)
    emby.add_field(name='`-anime [query]`', 
                   value=f'Search and watch Anime using [Gogoanime]({data["gogoanime"]}).', 
                   inline=False)
    emby.add_field(name='`-tv [query]`', 
                   value='Search and watch TV shows and movies using [SFlix](https://sflix.se).', 
                   inline=False)
    emby.add_field(name='`-ytdlp (optional: format = [mp3/m4a]) [link]`', 
                   value='Download or convert a YouTube video under 25MB discord limit using [yt-dlp](https://github.com/yt-dlp/yt-dlp). See [supported sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).', 
                   inline=False)
    emby.add_field(name='`-cob [link]`', 
                   value='[cobalt](https://cobalt.tools) is a media downloader that doesn\'t piss you off. See [supported sites](https://github.com/wukko/cobalt?tab=readme-ov-file#supported-services).', 
                   inline=False)
    return emby

async def utils_embed(av: discord.Asset) -> discord.Embed:
    emby = create_embed_cat(0x0000ff, "Utils 🔧", av)
    emby.add_field(name='`-quote`', 
                   value='Reply to a message to make it a quote.', 
                   inline=False)
    emby.add_field(name='`-weather [query]`', 
                   value='Check weather forecast using [weather-api](https://github.com/robertoduessmann/weather-api).', 
                   inline=False)
    emby.add_field(name='`-av [userid]`', 
                   value='Return a user\'s Discord profile avatar.', 
                   inline=False)
    emby.add_field(name='`-ban [userid]`', 
                   value='Return a user\'s Discord profile banner.', 
                   inline=False)
    # emby.add_field(name='`-lex [prompt]`', 
    #                value='Search AI Generated art (Stable Diffusion) made by the prompts of the community using Lexica', 
    #                inline=False)
    return emby