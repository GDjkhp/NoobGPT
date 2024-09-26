import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import aiohttp
import time
from imagetext_py import *
import asyncio
from util_discord import command_check, description_helper

font_reg = './res/font/AmaticSC-Regular.ttf'
font_bold = './res/font/AmaticSC-Bold.ttf'

FontDB.SetDefaultEmojiOptions(EmojiOptions(parse_discord_emojis=True))
FontDB.LoadFromDir("./res/font")
font_real_bold = FontDB.Query("AmaticSC-Bold NotoSansJP-Bold")
font_real_reg = FontDB.Query("AmaticSC-Regular NotoSansJP-Regular")

async def quote_this(ctx: commands.Context, msg_id: str):
    if await command_check(ctx, "quote", "utils"): return
    if ctx.message.reference or msg_id:
        if not msg_id: msg_id: int = ctx.message.reference.message_id
        elif not msg_id.isdigit(): return await ctx.reply("not a digit :(")
        msg_id: int = int(msg_id)
        try:
            referenced_message = await ctx.channel.fetch_message(msg_id)
        except:
            print("Exception in quote_this[0]")
            return await ctx.reply("**Error! :(**")
    else:
        if isinstance(ctx.channel, discord.DMChannel):
            return await ctx.reply("good job! i don't have access to this channel.")
        if not ctx.channel.last_message_id:
            return await ctx.reply("⁉️")
        try:
            if isinstance(ctx, discord.Interaction):
                referenced_message = await ctx.channel.fetch_message(ctx.channel.last_message_id)
            if isinstance(ctx, commands.Context):
                messages = [message async for message in ctx.history(limit=2)]
                if len(messages) == 2:
                    referenced_message = messages[1]
                else: return ctx.reply("maybe i'm blind")
        except:
            print("Exception in quote_this[1]")
            return await ctx.reply("**Error! :(**")

    info = await ctx.reply("Quoting…")
    old = round(time.time() * 1000)
    content = replace_mentions(referenced_message)
    render_canvas = RenderCanvas()
    try:
        attach = referenced_message.attachments[0].url if referenced_message.attachments else None
        user = f'- {referenced_message.author.name}'
        avatar_url = "https://cdn.discordapp.com/embed/avatars/4.png"
        if referenced_message.author.avatar:
            avatar_url = referenced_message.author.avatar.url
        image_data = await render_canvas.build_word(content, attach, user, avatar_url)
    except Exception as e: 
        print(e)
        return await info.edit(content=f"⁉️")
    await ctx.reply(file=discord.File(image_data, 'quote.png'))
    return await info.edit(content=f"Took {round(time.time() * 1000)-old}ms")

def replace_mentions(message: discord.Message):
    content = message.content
    if message.mentions:
        for mention in message.mentions:
            content = content.replace(
                f'<@{mention.id}>',
                f'@{mention.name}'
            )
    if message.role_mentions:
        for role_mention in message.role_mentions:
            content = content.replace(
                f'<@&{role_mention.id}>',
                f'@{role_mention.name}'
            )
    return content

class RenderCanvas:
    async def build_word(self, text: str, attach: str, user: str, avatar_url: str):
        # load image and text anything
        # if text: text = f"“{text}”"
        img = await asyncio.to_thread(self.wrap_text, text, user, 200, 200, 100) # slow

        # TODO: draw anything
        try:
            if attach:
                png = Image.open(await self.load_image(attach)) # bad
                img.paste(png.resize((int(png.width / 2), int(png.height / 2))), (200, 25))
        except Exception as e: print(e)

        # draw circle
        # draw.ellipse((50, 50, 250, 250), fill='black', outline='black')

        # draw clipped avatar
        # avatar = Image.open(await self.load_image(avatar_url))
        # avatar = avatar.resize((200, 200))
        # avatar_mask = Image.new('L', (200, 200), 0)
        # draw_avatar_mask = ImageDraw.Draw(avatar_mask)
        # draw_avatar_mask.ellipse((0, 0, 200, 200), fill=255)
        # avatar.putalpha(avatar_mask)
        # img.paste(avatar, (50, 50), avatar)

        # draw avatar
        avatar = Image.open(await self.load_image(avatar_url))
        img.paste(avatar.resize((200, 200)), (50, 50))

        # return everything all at once
        img_byte_array = BytesIO()
        img.save(img_byte_array, format='PNG')
        img_byte_array.seek(0)
        return img_byte_array

    async def load_image(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    return BytesIO(image_data)
                else:
                    raise OSError(f"Failed to load image from URL: {url}")
    
    # disappointingly disgusting
    def wrap_text(self, text: str, user: str, max_width: int, max_height: int, max_font_size: int) -> Image.Image:
        img = Image.new('RGBA', (600, 300), color='black') # create fake Image instance
        draw = ImageDraw.Draw(img)

        min_font_size = 10
        font_size_step = 1

        font_size = max_font_size
        lines = []

        while font_size >= min_font_size:
            font = ImageFont.truetype(font_bold, size=font_size)
            words = text.split(' ')
            lines = []
            current_line = words[0]

            for word in words[1:]:
                bbox = draw.multiline_textbbox((0, 0), current_line + ' ' + word, font=font)

                if '\n' in word:
                    current_line += ' ' + word[:word.index('\n')]
                    lines.append(current_line)
                    current_line = word[word.index('\n')+1:]
                elif bbox[2] < max_width:
                    current_line += ' ' + word
                else:
                    lines.append(current_line)
                    current_line = word

            lines.append(current_line)
            lines.append(user)

            line_height = font_size * 1.2
            total_height = line_height * len(lines)

            if total_height <= max_height:
                break

            font_size -= font_size_step

        # real canvas
        cv = Canvas(600, 300, (0, 0, 0, 255))
        white = Paint.Color((255, 255, 255, 255))
        x, y = 425, 50

        # for i, line in enumerate(lines):
        #     if i == len(lines) - 1:
        #         font = ImageFont.truetype(font_reg, size=25)
        #     draw.multiline_text((x, y + (i * line_height)), line, font=font, fill='white', anchor="ma")

        for i, line in enumerate(lines):
            if i == len(lines) - 1:
                draw_text_wrapped(
                    canvas=cv,
                    text=line,
                    x=x, y=y + (i * line_height),
                    ax=0.5, ay=0,
                    size=25,
                    width=200,
                    font=font_real_reg,
                    fill=white,
                    align=TextAlign.Center,
                    draw_emojis=True
                )
        lines.remove(user)
        draw_text_multiline(
            canvas=cv,
            lines=lines,
            x=x, y=y,
            ax=0.5, ay=0,
            size=font_size,
            width=200,
            font=font_real_bold,
            fill=white,
            align=TextAlign.Center,
            draw_emojis=True
        )
        return cv.to_image()
    
class CogQuote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description=f"{description_helper['emojis']['utils']} {description_helper['utils']['quote']}")
    @app_commands.describe(msg_id="Message ID of the message you want to quote")
    async def quote(self, ctx: commands.Context, msg_id: str=None):
        await quote_this(ctx, msg_id)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogQuote(bot))