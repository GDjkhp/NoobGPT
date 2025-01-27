from PIL import Image
from discord.ext import commands
import discord
from discord import app_commands
import io
import aiohttp
from typing import Union
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import A4
from util_discord import description_helper, command_check

supported_formats = {
    'png', 'webp', 'jpeg', 'gif', 
    'bmp', 'tiff', 'pdf', 'svg',
    # 'ico', 'avif', 'apng', 
}
# Formats that can handle animation
animated_formats = {'gif', 'apng', 'webp'}
# Formats requiring special handling
special_formats = {
    'ico': {'sizes': [(16, 16), (32, 32), (48, 48), (64, 64)]},
    'avif': {'quality': 80},  # Default AVIF quality
    'pdf': {'compress': True}
}

async def img_converter(ctx: commands.Context, format: str, images: str):
    if await command_check(ctx, "img", "media"):
        return await ctx.reply("command disabled", ephemeral=True)
    if format == "help":
        formats_list = ", ".join(sorted(supported_formats))
        await ctx.send(f"Supported formats: {formats_list}\nYou can provide multiple images as attachments or URLs (space-separated)")
        return

    # Check if format is supported
    format = format.lower()
    if format not in supported_formats:
        await ctx.send(f"Unsupported format.")
        return

    # Collect all images from attachments and URLs
    image_data_list = []

    # Check additional attachments
    if ctx.message.attachments:
        for attachment in ctx.message.attachments:
            if attachment.content_type.startswith('image/'):
                image_data_list.append(await attachment.read())
            else:
                await ctx.send(f"Skipping {attachment.filename} as it's not an image.")

    # Check additional URLs if provided
    if images:
        urls = images.split()
        for url in urls:
            try:
                image_data = await download_image(url)
                image_data_list.append(image_data)
            except:
                await ctx.send(f"Failed to download image from {url}")
            else:
                await ctx.send(f"Skipping invalid image URL: {url}")

    if not image_data_list:
        await ctx.send("No valid images provided. Please attach images or provide valid image URLs.")
        return

    try:
        # Convert all image data to PIL Images
        pil_images = [Image.open(io.BytesIO(data)) for data in image_data_list]

        # Special handling for SVG format
        if format == 'svg':
            await ctx.send("SVG conversion is not supported as it requires vector graphics conversion.")
            return

        # Process the images
        outputs = process_images(pil_images, format)

        # Handle single PDF output
        if format == 'pdf':
            await ctx.send(
                content=f"Converted {len(pil_images)} images to PDF:",
                file=discord.File(fp=outputs, filename="converted.pdf")
            )
        else:
            # Handle multiple outputs for other formats
            files = []
            for i, output in enumerate(outputs):
                filename = f"converted_{i+1}.{format}"
                files.append(discord.File(fp=output, filename=filename))
            
            await ctx.send(
                content=f"Converted {len(files)} images to {format.upper()}:",
                files=files
            )

    except Exception as e:
        await ctx.send(f"An error occurred while converting the images: {str(e)}")

async def download_image(url: str) -> bytes:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise commands.BadArgument("Failed to download image from URL.")
            return await response.read()
    
def is_animated(img: Image.Image) -> bool:
    try:
        img.seek(1)
        return True
    except EOFError:
        return False
    finally:
        img.seek(0)
        
def convert_multiple_to_pdf(images: list[Image.Image]) -> io.BytesIO:
    output = io.BytesIO()
    # Use A4 as default page size
    c = canvas.Canvas(output, pagesize=A4)
    page_width, page_height = A4
    
    for img in images:
        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        
        # If image is animated, use first frame
        if is_animated(img):
            img.seek(0)
        
        # Calculate scaling to fit image on page while preserving aspect ratio
        img_width, img_height = img.size
        width_ratio = page_width / img_width
        height_ratio = page_height / img_height
        scale = min(width_ratio, height_ratio) * 0.9  # 90% of page size for margins
        
        scaled_width = img_width * scale
        scaled_height = img_height * scale
        
        # Center image on page
        x_offset = (page_width - scaled_width) / 2
        y_offset = (page_height - scaled_height) / 2
        
        # Draw the image
        c.drawImage(
            ImageReader(img),
            x_offset, y_offset,
            width=scaled_width,
            height=scaled_height,
            preserveAspectRatio=True
        )
        
        c.showPage()  # Add a new page
    
    c.save()
    output.seek(0)
    return output
        
def process_images(images: list[Image.Image], format: str) -> Union[io.BytesIO, list[io.BytesIO]]:
    if format == 'pdf':
        return convert_multiple_to_pdf(images)
    
    # For non-PDF formats, process each image separately
    outputs = []
    for img in images:
        output = io.BytesIO()
        
        if format == 'jpeg':
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background
            img.save(output, format='JPEG', quality=95)

        elif format == 'tiff':
            img.save(output, format='TIFF', compression='lzw')
        
        elif format == 'ico': # bug: windows can't read (corrupted)
            img.save(output, format='ICO', sizes=special_formats['ico']['sizes'])
        
        elif format == 'avif': # no support (see pillow-avif-plugin)
            img.save(output, format='AVIF', quality=special_formats['avif']['quality'])

        elif format == 'apng': # cannot access local variable 'colors' where it is not associated with a value (gif -> apng)
            if is_animated(img):
                frames = []
                try:
                    while True:
                        frames.append(img.copy())
                        img.seek(img.tell() + 1)
                except EOFError:
                    pass
                
                frames[0].save(
                    output,
                    format='PNG',
                    save_all=True,
                    append_images=frames[1:],
                    duration=img.info.get('duration', 100),
                    loop=0
                )
            else:
                img.save(output, format='PNG')
        
        else:
            if format in animated_formats and is_animated(img):
                img.save(
                    output,
                    format=format.upper(),
                    save_all=True,
                    duration=img.info.get('duration', 100),
                    loop=0
                )
            else:
                img.save(output, format=format.upper())
        
        output.seek(0)
        outputs.append(output)
    
    return outputs

async def fmt_auto(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=fmt, value=fmt) for fmt in supported_formats if current.lower() in fmt.lower()
    ]

class ImageConverter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description=f'{description_helper["media"]["img"]}')
    @app_commands.describe(images="Image sources (Only space-separated URLs are supported)", format="Output format")
    @app_commands.autocomplete(format=fmt_auto)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def img(self, ctx: commands.Context, format: str = "png", *, images: str = None):
        await img_converter(ctx, format, images)

async def setup(bot: commands.Bot):
    await bot.add_cog(ImageConverter(bot))