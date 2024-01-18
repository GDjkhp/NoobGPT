import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import aiohttp
import time

async def quote_this(ctx: commands.Context):
    if ctx.message.reference:
        info = await ctx.reply("Quoting…")
        old = round(time.time() * 1000)
        referenced_message = await ctx.message.channel.fetch_message(ctx.message.reference.message_id)
        content_with_usernames = replace_mentions(referenced_message)
        render_canvas = RenderCanvas()
        image_data = await render_canvas.build_word(content_with_usernames, referenced_message.attachments[0].url if referenced_message.attachments else None,
                                                   f'- {referenced_message.author.name}',
                                                   referenced_message.author.avatar.url)
        await ctx.reply(file=discord.File(image_data, 'quote.png'))
        return await info.edit(content=f"Took {round(time.time() * 1000)-old}ms")
    await ctx.reply("⁉️")

def replace_mentions(message: discord.Message):
    content_with_usernames = message.content
    if message.mentions:
        mentions = message.mentions
        for m in mentions:
            content_with_usernames = content_with_usernames.replace(
                '<@{}>'.format(m.id),
                '@{}'.format(m.name)
            )
    return content_with_usernames

class RenderCanvas:
    async def build_word(self, text, attach, user, avatar_url):
        # create Image instance
        img = Image.new('RGBA', (600, 300), color='black')
        draw = ImageDraw.Draw(img)

        # draw anything
        try:
            if attach:
                png = Image.open(await self.load_image(attach))
                img.paste(png.resize((int(png.width / 2), int(png.height / 2))), (200, 25))
        except Exception as e:
            print(e)

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

        # text anything
        font_path = './res/AmaticSC-Regular.ttf'
        amogus_font_size = 100
        draw.font = ImageFont.truetype(font_path, size=amogus_font_size)
        if text: text = f"“{text}”"
        await self.wrap_text(draw, text, user, 200, 200, font_path, amogus_font_size)

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
    async def wrap_text(self, draw: ImageDraw.ImageDraw, text, user, max_width, max_height, font_path, max_font_size):
        min_font_size = 10
        font_size_step = 1

        font_size = max_font_size
        lines = []

        while font_size >= min_font_size:
            font = ImageFont.truetype(font_path, size=font_size)
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

        x = 425  # Adjust x-coordinate as needed
        y = 50   # Adjust y-coordinate as needed
        
        for i, line in enumerate(lines):
            if i == len(lines) - 1:
                font = ImageFont.truetype(font_path, size=25)
            draw.multiline_text((x, y + (i * line_height)), line, font=font, fill='white', anchor="ma")