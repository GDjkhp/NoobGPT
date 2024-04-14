import discord
from discord.ext import commands
import pymongo
import os
from PIL import Image, ImageDraw
import re
import io

myclient = pymongo.MongoClient(os.getenv('MONGO'))
width, height = 500, 500
mycol = myclient["place"]["pixels"]

def draw_image(x: int, y: int, zoom: float) -> io.BytesIO:
    canvas = Image.new("RGB", (width, height), color="black")
    draw = ImageDraw.Draw(canvas)
    all_pixels = mycol.find()
    for pixel in all_pixels:
        draw.point((pixel['x'], pixel['y']), fill=rgb_string_to_tuple(pixel['color']))
    
    zoomed_canvas = zoom_canvas(canvas, zoom, (x, y))
    resized_canvas = resize_image(zoomed_canvas)

    image_buffer = io.BytesIO()
    resized_canvas.save(image_buffer, format="PNG")
    image_buffer.seek(0)
    return image_buffer

def PlaceEmbed(x: int, y: int, z: float, ctx: commands.Context, status: str) -> discord.Embed:
    d = mycol.find_one({"x": x, "y": y})
    e = discord.Embed(title=f"({x}, {y}) [{z}x]", description=f"{d['author']}: {d['color']}", 
                      color=rgb_tuple_to_hex(rgb_string_to_tuple(d['color'])))
    if ctx.message.author.avatar: e.set_author(name=ctx.author, icon_url=ctx.message.author.avatar.url) 
    else: e.set_author(name=ctx.author)
    e.set_footer(text=status)
    return e

async def PLACE(ctx: commands.Context, x: str, y: str, z: str):
    params = f"```-place [x: <0-{width-1}>, y: <0-{height-1}>, zoom:<16x>]```"
    msg = await ctx.reply("Drawing canvas…")
    if x and y:
        if x.isdigit() and y.isdigit():
            if int(x) > -1 and int(x) < width and int(y) > -1 and int(y) < height: pass
            else: return await ctx.reply(f"Must be {width}x{height}")
        else: return await ctx.reply(f"Must be integer and {width}x{height}")
    else: x, y = 0, 0
    if z:
        z = extract_number(z)
        if not z: return await ctx.reply("Invalid zoom format.\nTry `2x` or `2`.")
    else: z = 16
    file = discord.File(draw_image(int(x), int(y), z), filename=f"{x}x{y}.png")
    await msg.edit(content="r/place")
    await ctx.reply(view=ViewPlace(int(x), int(y), z, ctx), file=file,
                    embed=PlaceEmbed(int(x), int(y), z, ctx, "Idle"))

def zoom_canvas(canvas, zoom_multiplier, center_pixel):
    # Calculate the region to crop based on the scale factor and center pixel
    cropped_width = int(width / zoom_multiplier)
    cropped_height = int(height / zoom_multiplier)
    
    left = center_pixel[0] - cropped_width // 2
    top = center_pixel[1] - cropped_height // 2
    right = left + cropped_width
    bottom = top + cropped_height
    
    # Crop the region around the center pixel
    cropped_image = canvas.crop((left, top, right, bottom))
    
    # Resize the cropped image to the original size
    zoomed_image = cropped_image.resize((width, height), Image.BOX)
    return zoomed_image

def resize_image(canvas):
    resized_image = canvas.resize((1000, 1000), Image.BOX)
    return resized_image

def rgb_string_to_tuple(rgb_string):
    # Use regular expression to extract three groups of digits, with or without "#"
    match = re.match(r"#?(\w{2})(\w{2})(\w{2})", rgb_string)

    if match:
        # Convert the hexadecimal digits to integers using base 16
        red = int(match.group(1), 16)
        green = int(match.group(2), 16)
        blue = int(match.group(3), 16)
        return (red, green, blue)
    else:
        # Check if the input is in the format "255, 255, 255"
        match = re.match(r"(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})", rgb_string)
        if match:
            red = int(match.group(1))
            green = int(match.group(2))
            blue = int(match.group(3))
            if 0 <= red <= 255 and 0 <= green <= 255 and 0 <= blue <= 255:
                return (red, green, blue)
        return None

def rgb_tuple_to_hex(rgb_tuple):
    # Check if the RGB values are integers within the valid range (0-255)
    red, green, blue = rgb_tuple
    if not (0 <= red <= 255 and 0 <= green <= 255 and 0 <= blue <= 255):
        raise ValueError("Invalid RGB values. Each value should be between 0 and 255.")

    # Convert the RGB values to their hexadecimal representation and combine them into a single integer
    hex_color_code = (red << 16) + (green << 8) + blue

    return hex_color_code

def extract_number(input_str):
    pattern = r'^(-?\d+(\.\d+)?)(x.*)?$'
    match = re.match(pattern, input_str)
    if match:
        if match.group(1):
            number = float(match.group(1)) if '.' in match.group(1) else int(match.group(1))
            return 1 if number <= 0 else number
    return None
    
class ViewPlace(discord.ui.View):
    def __init__(self, x: int, y: int, z: float, ctx: commands.Context):
        super().__init__(timeout=None)
        if x-1 > -1: 
            self.add_item(ButtonChoice(x, y, z, ctx, 0, "◀️", "LEFT"))
        if y+1 < height: 
            self.add_item(ButtonChoice(x, y, z, ctx, 0, "🔽", "DOWN"))
        if y-1 > -1: 
            self.add_item(ButtonChoice(x, y, z, ctx, 0, "🔼", "UP"))
        if x+1 < width: 
            self.add_item(ButtonChoice(x, y, z, ctx, 0, "▶️", "RIGHT"))
        if x-10 > -1: 
            self.add_item(ButtonChoice(x, y, z, ctx, 1, "⏪", "LEFTLEFT"))
        if y+10 < height: 
            self.add_item(ButtonChoice(x, y, z, ctx, 1, "⏬", "DOWNDOWN"))
        if y-10 > -1: 
            self.add_item(ButtonChoice(x, y, z, ctx, 1, "⏫", "UPUP"))
        if x+10 < width: 
            self.add_item(ButtonChoice(x, y, z, ctx, 1, "⏩", "RIGHTRIGHT"))

        self.add_item(ButtonChoice(x, y, z, ctx, 2, "🪧", "PLACE"))
        self.add_item(ButtonChoice(x, y, z, ctx, 2, "🧭", "LOCATE"))
        self.add_item(ButtonChoice(x, y, z, ctx, 2, "🔍", "ZOOM"))

class ButtonChoice(discord.ui.Button):
    def __init__(self, x: int, y: int, z: float, ctx: commands.Context, r: int, e: str, l: str):
        self.x, self.y, self.z, self.ctx, self.l = x, y, z, ctx, l
        labels = ["PLACE", "ZOOM", "LOCATE"]
        if not l in labels: l = None
        super().__init__(label=l, emoji=e, row=r)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: 
            return await interaction.response.send_message(f"{self.ctx.author.mention} is using this view. Use `-place` to create your own.", 
                                                           ephemeral=True)
        
        if self.l == "PLACE": return await interaction.response.send_modal(ModalPlace(self.x, self.y, self.z, self.ctx))
        if self.l == "ZOOM": return await interaction.response.send_modal(ModalZoom(self.x, self.y, self.z, self.ctx))
        if self.l == "LOCATE": return await interaction.response.send_modal(ModalLocate(self.x, self.y, self.z, self.ctx))
        
        if self.l == "LEFTLEFT": self.x += -10
        if self.l == "LEFT": self.x += -1
        if self.l == "RIGHTRIGHT": self.x += 10
        if self.l == "RIGHT": self.x += 1
        if self.l == "UPUP": self.y += -10
        if self.l == "UP": self.y += -1
        if self.l == "DOWNDOWN": self.y += 10
        if self.l == "DOWN": self.y += 1

        await interaction.response.defer()
        await interaction.message.remove_attachments(interaction.message.attachments[0])
        await interaction.message.edit(embed=PlaceEmbed(self.x, self.y, self.z, self.ctx, f"Processing {self.l}, syncing…"),
                                       view=None)
        f = discord.File(draw_image(self.x, self.y, self.z), filename=f"{self.x}x{self.y}.png")
        await interaction.message.edit(embed=PlaceEmbed(self.x, self.y, self.z, self.ctx, f"Synced"), view=None)
        await interaction.followup.send(view=ViewPlace(self.x, self.y, self.z, self.ctx), file=f,
                                        embed=PlaceEmbed(self.x, self.y, self.z, self.ctx, "Idle"))
    
class ModalPlace(discord.ui.Modal):
    def __init__(self, x: int, y: int, z: float, ctx: commands.Context):
        super().__init__(title="Place")
        self.i = discord.ui.TextInput(label=f"Color ({mycol.find_one({'x': x, 'y': y})['color']})")
        self.add_item(self.i)
        self.x, self.y, self.z, self.ctx, = x, y, z, ctx

    async def on_submit(self, interaction: discord.Interaction):
        col = rgb_string_to_tuple(self.i.value)
        if not col: return await interaction.response.send_message("Invalid color format.\nMust be `#00ff00`", ephemeral=True)
        mycol.update_one({"x": self.x, "y": self.y}, {"$set": {"author": interaction.user.name, "color": self.i.value}})

        await interaction.response.defer()
        await interaction.message.remove_attachments(interaction.message.attachments[0])
        await interaction.message.edit(embed=PlaceEmbed(self.x, self.y, self.z, self.ctx, 
                                                        f"Placing {col}, syncing…"), view=None)
        f = discord.File(draw_image(self.x, self.y, self.z), filename=f"{self.x}x{self.y}.png")
        await interaction.message.edit(embed=PlaceEmbed(self.x, self.y, self.z, self.ctx, f"Synced"), view=None)
        await interaction.followup.send(view=ViewPlace(self.x, self.y, self.z, self.ctx), file=f,
                                        embed=PlaceEmbed(self.x, self.y, self.z, self.ctx, "Idle"))

class ModalZoom(discord.ui.Modal):
    def __init__(self, x: int, y: int, z: float, ctx: commands.Context):
        super().__init__(title="Zoom")
        self.i = discord.ui.TextInput(label=f"Value ({z}x)")
        self.add_item(self.i)
        self.x, self.y, self.z, self.ctx, = x, y, z, ctx

    async def on_submit(self, interaction: discord.Interaction):
        self.z = extract_number(self.i.value)
        if not self.z: return await interaction.response.send_message("Invalid zoom format.\nTry `2x` or `2`.", ephemeral=True)

        await interaction.response.defer()
        await interaction.message.remove_attachments(interaction.message.attachments[0])
        await interaction.message.edit(embed=PlaceEmbed(self.x, self.y, self.z, self.ctx, f"Zooming {self.z}x, syncing…"), view=None)
        f = discord.File(draw_image(self.x, self.y, self.z), filename=f"{self.x}x{self.y}.png")
        await interaction.message.edit(embed=PlaceEmbed(self.x, self.y, self.z, self.ctx, f"Synced"), view=None)
        await interaction.followup.send(view=ViewPlace(self.x, self.y, self.z, self.ctx), file=f,
                                        embed=PlaceEmbed(self.x, self.y, self.z, self.ctx, "Idle"))
        
class ModalLocate(discord.ui.Modal):
    def __init__(self, x: int, y: int, z: float, ctx: commands.Context):
        super().__init__(title="Locate")
        self.iX = discord.ui.TextInput(label="x")
        self.iY = discord.ui.TextInput(label="y")
        self.add_item(self.iX)
        self.add_item(self.iY)
        self.x, self.y, self.z, self.ctx, = x, y, z, ctx

    async def on_submit(self, interaction: discord.Interaction):
        self.x, self.y = locate_integer(self.iX.value, self.iY.value)
        if self.x == -1 or self.y == -1: return await interaction.response.send_message("Invalid coordinates.", ephemeral=True)

        await interaction.response.defer()
        await interaction.message.remove_attachments(interaction.message.attachments[0])
        await interaction.message.edit(embed=PlaceEmbed(self.x, self.y, self.z, self.ctx, 
                                                        f"Locating ({self.x}, {self.y}), syncing…"), view=None)
        f = discord.File(draw_image(self.x, self.y, self.z), filename=f"{self.x}x{self.y}.png")
        await interaction.message.edit(embed=PlaceEmbed(self.x, self.y, self.z, self.ctx, f"Synced"), view=None)
        await interaction.followup.send(view=ViewPlace(self.x, self.y, self.z, self.ctx), file=f,
                                        embed=PlaceEmbed(self.x, self.y, self.z, self.ctx, "Idle"))

def locate_integer(x, y):
    try:
        if int(x) > -1 and int(x) < width and int(y) > -1 and int(y) < height: return int(x), int(y)
        else: return -1, -1
    except: return -1, -1