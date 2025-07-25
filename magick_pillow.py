from PIL import Image
from discord.ext import commands
import discord
from discord import app_commands
import io, time
import aiohttp
from typing import Union
import fitz
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
        await ctx.send(f"Supported formats: {formats_list}\nYou can provide multiple images/PDFs as attachments or URLs (space-separated)")
        return

    # Check if format is supported
    format = format.lower()
    if format not in supported_formats:
        await ctx.send(f"Unsupported format.")
        return

    # Collect all files from attachments and URLs
    file_data_list = []
    file_types = []  # Track whether each file is an image or PDF

    # Check additional attachments
    if ctx.message.attachments:
        for attachment in ctx.message.attachments:
            if attachment.content_type.startswith('image/'):
                file_data_list.append(await attachment.read())
                file_types.append('image')
            elif attachment.content_type == 'application/pdf':
                file_data_list.append(await attachment.read())
                file_types.append('pdf')
            else:
                await ctx.send(f"Skipping {attachment.filename} as it's not an image or PDF.")

    # Check additional URLs if provided
    if images:
        urls = images.split()
        for url in urls:
            try:
                file_data, file_type = await download_file(url)
                file_data_list.append(file_data)
                file_types.append(file_type)
            except Exception as e:
                await ctx.send(f"Failed to download file from {url}: {str(e)}")

    if not file_data_list:
        await ctx.send("No valid images or PDFs provided. Please attach files or provide valid URLs.")
        return

    # Special handling for SVG format
    if format == 'svg':
        await ctx.send("SVG conversion is not supported as it requires vector graphics conversion.")
        return

    info = await ctx.send("please wait")
    old = round(time.time() * 1000)
    try:
        # If output format is PDF and we have PDFs to merge
        if format == 'pdf' and 'pdf' in file_types:
            merged_pdf = await merge_pdfs_and_images(file_data_list, file_types)
            await ctx.send(
                content=f"Merged {len(file_data_list)} files into PDF:",
                file=discord.File(fp=merged_pdf, filename="merged.pdf")
            )
        else:
            # Convert all file data to PIL Images (including PDF pages)
            pil_images = []
            for i, (data, file_type) in enumerate(zip(file_data_list, file_types)):
                if file_type == 'pdf':
                    # Convert PDF pages to images
                    pdf_images = pdf_to_images(data)
                    pil_images.extend(pdf_images)
                else:
                    # Regular image
                    pil_images.append(Image.open(io.BytesIO(data)))

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
        await info.edit(content=f"Took {round(time.time() * 1000)-old}ms")
    except Exception as e:
        await info.edit(content=f"An error occurred while processing the files: {str(e)}")

async def download_file(url: str) -> tuple[bytes, str]:
    """Download file and determine if it's an image or PDF"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise commands.BadArgument("Failed to download file from URL.")

            content_type = response.headers.get('content-type', '').lower()
            data = await response.read()

            if content_type.startswith('image/'):
                return data, 'image'
            elif content_type == 'application/pdf' or url.lower().endswith('.pdf'):
                return data, 'pdf'
            else:
                # Try to detect based on file signature
                if data.startswith(b'%PDF'):
                    return data, 'pdf'
                else:
                    return data, 'image'  # Assume image if unknown

def pdf_to_images(pdf_data: bytes) -> list[Image.Image]:
    """Convert PDF pages to PIL Images using PyMuPDF"""
    images = []
    pdf_doc = fitz.open(stream=pdf_data, filetype="pdf")

    for page_num in range(pdf_doc.page_count):
        page = pdf_doc[page_num]
        # Render page to image (300 DPI for good quality)
        pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
        img_data = pix.tobytes("png")
        images.append(Image.open(io.BytesIO(img_data)))

    pdf_doc.close()
    return images

async def merge_pdfs_and_images(file_data_list: list[bytes], file_types: list[str]) -> io.BytesIO:
    """Merge PDFs and images into one PDF using PyMuPDF"""
    output_pdf = fitz.open()  # Create new empty PDF

    for data, file_type in zip(file_data_list, file_types):
        if file_type == 'pdf':
            # Open existing PDF and copy all pages
            input_pdf = fitz.open(stream=data, filetype="pdf")
            output_pdf.insert_pdf(input_pdf)
            input_pdf.close()
        else:
            # Convert image to PDF page
            img = Image.open(io.BytesIO(data))
            add_image_to_pdf(output_pdf, img)

    # Save to bytes
    output = io.BytesIO()
    output.write(output_pdf.tobytes())
    output_pdf.close()
    output.seek(0)
    return output

def add_image_to_pdf(pdf_doc: fitz.Document, img: Image.Image):
    """Add an image as a new page to the PDF document"""
    # Convert RGBA to RGB if necessary
    if img.mode in ('RGBA', 'LA'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        img = background

    # If image is animated, use first frame
    if is_animated(img):
        img.seek(0)

    # Convert PIL image to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    # Create a new page with A4 size (595 x 842 points)
    page_width, page_height = 595, 842
    page = pdf_doc.new_page(width=page_width, height=page_height)

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

    # Insert image into the page
    rect = fitz.Rect(x_offset, y_offset, x_offset + scaled_width, y_offset + scaled_height)
    page.insert_image(rect, stream=img_bytes.getvalue())

def convert_single_image_to_pdf(img: Image.Image) -> io.BytesIO:
    """Convert a single image to PDF using PyMuPDF"""
    pdf_doc = fitz.open()  # Create new empty PDF
    add_image_to_pdf(pdf_doc, img)

    # Save to bytes
    output = io.BytesIO()
    output.write(pdf_doc.tobytes())
    pdf_doc.close()
    output.seek(0)
    return output

def is_animated(img: Image.Image) -> bool:
    try:
        img.seek(1)
        return True
    except EOFError:
        return False
    finally:
        img.seek(0)

def convert_multiple_to_pdf(images: list[Image.Image]) -> io.BytesIO:
    """Convert multiple images to PDF using PyMuPDF"""
    pdf_doc = fitz.open()  # Create new empty PDF

    for img in images:
        add_image_to_pdf(pdf_doc, img)

    # Save to bytes
    output = io.BytesIO()
    output.write(pdf_doc.tobytes())
    pdf_doc.close()
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

class CogImageConverter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description=f'{description_helper["media"]["img"]}')
    @app_commands.describe(images="File sources (Only space-separated URLs are supported)", format="Output format")
    @app_commands.autocomplete(format=fmt_auto)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def img(self, ctx: commands.Context, format: str = "png", *, images: str = None):
        await img_converter(ctx, format, images)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogImageConverter(bot))