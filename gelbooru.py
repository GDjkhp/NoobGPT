from pygelbooru import Gelbooru
from discord.ext import commands
import re
import discord
from discord import app_commands
import random
import aiohttp
from bs4 import BeautifulSoup
from util_database import myclient
from util_discord import command_check, description_helper, get_guild_prefix

# API configuration
API_CONFIGS = {
    "safe": "https://safebooru.org/",
    "gel": "https://gelbooru.com/",
    "r34": "https://api.rule34.xxx/"
}

async def get_total_posts(tags: list, api: str) -> int:
    """Fetch total number of posts for given tags by parsing the pagination."""
    tags_str = "+".join(tag.replace(" ", "_") for tag in tags)

    if api in API_CONFIGS:
        url = f"{API_CONFIGS[api]}index.php?page=post&s=list&tags={tags_str}"
    else:
        return 0

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return 0
                html = await response.text()

        soup = BeautifulSoup(html, 'html.parser')
        pagination = soup.find('div', class_='pagination')

        if not pagination:
            # If no pagination, check if there are any posts
            posts = soup.find_all('span', class_='thumb')
            return len(posts) if posts else 0

        # Find the "last page" link (>>)
        last_link = pagination.find('a', alt='last page')
        if last_link:
            # Extract pid from the last page link
            href = last_link.get('href', '')
            pid_match = re.search(r'pid=(\d+)', href)
            if pid_match:
                last_pid = int(pid_match.group(1))
                # Each page shows 42 posts, pid is 0-indexed
                return min(last_pid + 42, 1302) # magic number: page 32 limit (pid[31]) / api limitation / 42 x 31

        # If no last page link, count all page links
        page_links = pagination.find_all('a', href=re.compile(r'pid=\d+'))
        if page_links:
            max_pid = 0
            for link in page_links:
                href = link.get('href', '')
                pid_match = re.search(r'pid=(\d+)', href)
                if pid_match:
                    max_pid = max(max_pid, int(pid_match.group(1)))
            return max_pid + 42

        # Fallback: if only one page exists
        return 42
    except Exception as e:
        print(f"Error fetching total posts: {e}")
        return 0

async def fetch_post(post_id: int, api: str):
    """Fetch a single post by ID."""
    try:
        if api in API_CONFIGS:
            return await Gelbooru(api=API_CONFIGS[api]).get_post(post_id)
    except Exception as e:
        print(f"Error fetching post {post_id}: {e}")
        return None

async def fetch_posts_page(tags: list, page: int, api: str):
    """Fetch a single page of posts."""
    try:
        if api in API_CONFIGS:
            return await Gelbooru(api=API_CONFIGS[api]).search_posts(tags=tags, page=page, limit=42)
    except Exception as e:
        print(f"Error fetching page {page}: {e}")
        return []

async def help_booru(ctx: commands.Context):
    if await command_check(ctx, "booru", "media"): 
        return await ctx.reply("command disabled", ephemeral=True)
    p = await get_guild_prefix(ctx)
    text = [f"`{p}gel` gelbooru", f"`{p}safe` safebooru", f"`{p}r34` rule34"]
    await ctx.reply("\n".join(text))

async def R34(ctx: commands.Context, arg: str):
    if await command_check(ctx, "booru", "media"): 
        return await ctx.reply("command disabled", ephemeral=True)
    if not ctx.guild or not ctx.channel.nsfw: 
        return await ctx.reply("**No.**")
    if arg: 
        await search_posts(ctx, arg, "r34")
    else: 
        await view_collection(ctx, "r34")

async def GEL(ctx: commands.Context, arg: str):
    if await command_check(ctx, "booru", "media"): 
        return await ctx.reply("command disabled", ephemeral=True)
    if not ctx.guild or not ctx.channel.nsfw: 
        return await ctx.reply("**No.**")
    if arg: 
        await search_posts(ctx, arg, "gel")
    else: 
        await view_collection(ctx, "gel")

async def SAFE(ctx: commands.Context, arg: str):
    if await command_check(ctx, "booru", "media"): 
        return await ctx.reply("command disabled", ephemeral=True)
    if arg: 
        await search_posts(ctx, arg, "safe")
    else: 
        await view_collection(ctx, "safe")

async def view_collection(ctx: commands.Context, api: str):
    """View user's favorited posts."""
    mycol = myclient["gel"][api]
    user = await mycol.find_one({"user": ctx.author.id})

    if not user or not user.get("favorites"):
        return await ctx.reply("**No results found**")

    # Create a SearchContext for favorites
    search_ctx = SearchContext(
        tags=f"Favorites ({ctx.author.name})",
        api=api,
        total_posts=len(user["favorites"]),
        is_favorites=True,
        favorite_ids=user["favorites"]
    )

    # Fetch first post
    message = await ctx.reply("Loading…")
    first_post = await fetch_post(user["favorites"][0], api)
    embed = await BuildEmbed(search_ctx, first_post, 0, api == "safe", ctx)
    view = ImageView(search_ctx, 0, api == "safe", [False, False], ctx, api)
    await message.edit(content=None if first_post else "**Error loading post**",
                       embed=embed if first_post else None, view=view)

async def search_posts(ctx: commands.Context, arg: str, api: str):
    """Search posts with given tags."""
    tags = re.split(r'\s*,\s*', arg.strip())
    message = await ctx.reply(f"Fetching total posts for tags `{tags}`…")

    # Get total post count
    total = await get_total_posts(tags, api)

    if total == 0:
        return await message.edit(content="**No results found**")

    # Create search context
    search_ctx = SearchContext(
        tags=tags,
        api=api,
        total_posts=total,
        is_favorites=False
    )

    # Fetch first page to get first post
    await message.edit(content="Loading first post…")
    first_page = await fetch_posts_page(tags, 0, api)

    if not first_page:
        return await message.edit(content="**No results found**")

    embed = await BuildEmbed(search_ctx, first_page[0], 0, api == "safe", ctx)
    view = ImageView(search_ctx, 0, api == "safe", [False, False], ctx, api)

    await message.edit(content=None, embed=embed, view=view)

class SearchContext:
    """Holds search state for lazy loading."""
    def __init__(self, tags, api: str, total_posts: int, is_favorites: bool = False, favorite_ids: list = None):
        self.tags = tags
        self.api = api
        self.total_posts = total_posts
        self.is_favorites = is_favorites
        self.favorite_ids = favorite_ids or []
        self._cache = {}  # Cache fetched posts {index: post}
        self._page_cache = {}  # Cache entire pages {page_num: [posts]}

    async def get_post(self, index: int):
        """Get post at index, fetching if necessary."""
        if index in self._cache:
            return self._cache[index]

        if self.is_favorites:
            # Fetch from favorites
            if 0 <= index < len(self.favorite_ids):
                post = await fetch_post(self.favorite_ids[index], self.api)
                if post:
                    self._cache[index] = post
                return post
        else:
            # Calculate which page this index is on (42 posts per page)
            page = index // 42
            page_offset = index % 42

            # Check if we have this page cached
            if page not in self._page_cache:
                posts = await fetch_posts_page(self.tags, page, self.api)
                if posts:
                    self._page_cache[page] = posts
                    # Cache individual posts
                    for i, post in enumerate(posts):
                        self._cache[page * 42 + i] = post

            # Get from page cache
            if page in self._page_cache and page_offset < len(self._page_cache[page]):
                return self._page_cache[page][page_offset]

        return None

async def BuildEmbed(search_ctx: SearchContext, post, index: int, safe: bool, ctx: commands.Context) -> discord.Embed:
    """Build embed for a post."""
    tags_display = search_ctx.tags if isinstance(search_ctx.tags, str) else f"`{search_ctx.tags}`"
    embed = discord.Embed(
        title=f"Search results: {tags_display}", 
        description=f"{index+1}/{search_ctx.total_posts} found", 
        color=0x00ff00
    )

    if post:
        embed.add_field(name="Tags", value=f"`{post.tags}`"[:1024], inline=False)
        embed.add_field(name="Source", value=post.source or "N/A", inline=False)

        if post.file_url.endswith(".mp4"):
            embed.add_field(name="Video link:", value=post.file_url)
        else:
            embed.set_image(url=post.file_url)
    else:
        embed.add_field(name="Error", value="Failed to load post")

    embed.set_footer(text=f"{index+1}/{search_ctx.total_posts}")
    return embed

class ImageView(discord.ui.View):
    def __init__(self, search_ctx: SearchContext, index: int, safe: bool, lock: list, ctx: commands.Context, db: str):
        super().__init__(timeout=None)
        self.search_ctx = search_ctx
        self.current_index = index

        # Add numbered buttons (show 8 per page)
        column, row, pagelimit = 0, -1, 8
        i = (index // pagelimit) * pagelimit
        end = min(i + pagelimit, search_ctx.total_posts)

        while i < end:
            if column % 4 == 0: 
                row += 1
            self.add_item(ButtonAction(search_ctx, i, None, row, lock, ctx, db, str(i+1)))
            i += 1
            column += 1

        # Navigation buttons
        if index > 0:
            self.add_item(ButtonAction(search_ctx, 0, "⏪", 2, lock, ctx, db, ""))
            self.add_item(ButtonAction(search_ctx, index - 1, "◀️", 2, lock, ctx, db, ""))
        else:
            self.add_item(DisabledButton("⏪", 2))
            self.add_item(DisabledButton("◀️", 2))

        if index + 1 < search_ctx.total_posts:
            self.add_item(ButtonAction(search_ctx, index + 1, "▶️", 2, lock, ctx, db, ""))
            self.add_item(ButtonAction(search_ctx, search_ctx.total_posts - 1, "⏩", 2, lock, ctx, db, ""))
        else:
            self.add_item(DisabledButton("▶️", 2))
            self.add_item(DisabledButton("⏩", 2))

        # Special buttons
        self.add_item(ButtonShuffle(search_ctx, 3, lock, ctx, db))
        self.add_item(ButtonHeart(ctx, db, index, search_ctx, 3))
        self.add_item(ButtonAction(search_ctx, index, "🔐" if lock[1] else "🔓", 3, [lock[1], not lock[1]], ctx, db, ""))
        self.add_item(ButtonEnd(ctx, lock[1], 3))

class DisabledButton(discord.ui.Button):
    def __init__(self, e: str, r: int):
        super().__init__(emoji=e, style=discord.ButtonStyle.success, disabled=True, row=r)

class ButtonEnd(discord.ui.Button):
    def __init__(self, ctx: commands.Context, lock: bool, row: int):
        super().__init__(style=discord.ButtonStyle.success, emoji="🛑", row=row)
        self.ctx, self.lock = ctx, lock

    async def callback(self, interaction: discord.Interaction):
        if self.lock and interaction.user != self.ctx.author:
            return await interaction.response.send_message(
                f"Only <@{self.ctx.author.id}> can delete this message.", 
                ephemeral=True
            )
        await interaction.response.defer()
        await interaction.delete_original_response()
        # if you are thinking of 🤨 that gets deleted in 5 seconds, its incompatible with user commands
        # await interaction.message.delete(delay=5) / await interaction.response.edit_message(content="🤨", embed=None, view=None, delete_after=5)

class ButtonHeart(discord.ui.Button):
    def __init__(self, ctx: commands.Context, db: str, index: int, search_ctx: SearchContext, row: int):
        super().__init__(style=discord.ButtonStyle.success, emoji="❤️", row=row)
        self.db, self.ctx, self.index, self.search_ctx = db, ctx, index, search_ctx
        self.mycol = myclient["gel"][db]

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # Get current post
        post = await self.search_ctx.get_post(self.index)
        if not post:
            return await interaction.followup.send("**Error loading post**", ephemeral=True)

        # Update favorites
        if not await self.mycol.find_one({"user": interaction.user.id}):
            await self.mycol.insert_one({"user": interaction.user.id, "favorites": []})

        p = await get_guild_prefix(self.ctx)

        if not await self.mycol.find_one({"user": interaction.user.id, "favorites": post.id}):
            await self.mycol.update_one(
                {"user": interaction.user.id}, 
                {"$push": {"favorites": post.id}}
            )
            await interaction.followup.send(
                f"❤️ Added to favorites ❤️\nUse `{p}{self.db}` to view your collection.", 
                ephemeral=True
            )
        else:
            await self.mycol.update_one(
                {"user": interaction.user.id}, 
                {"$pull": {"favorites": post.id}}
            )
            await interaction.followup.send(
                f"💔 Removed from favorites 💔\nUse `{p}{self.db}` to view your collection.", 
                ephemeral=True
            )

class ButtonShuffle(discord.ui.Button):
    def __init__(self, search_ctx: SearchContext, row: int, lock: list, ctx: commands.Context, db: str):
        super().__init__(style=discord.ButtonStyle.success, emoji="🔀", row=row)
        self.search_ctx, self.lock, self.ctx, self.db = search_ctx, lock, ctx, db

    async def callback(self, interaction: discord.Interaction):
        if self.lock[1] and interaction.user != self.ctx.author:
            return await interaction.response.send_message(
                f"<@{self.ctx.author.id}> locked this message.", 
                ephemeral=True
            )

        await interaction.response.defer()
        random_index = random.randrange(0, self.search_ctx.total_posts)

        # Fetch random post
        post = await self.search_ctx.get_post(random_index)
        embed = await BuildEmbed(self.search_ctx, post, random_index, self.db == "safe", self.ctx)
        view = ImageView(self.search_ctx, random_index, self.db == "safe", self.lock, self.ctx, self.db)
        await interaction.edit_original_response(content=None if post else "**Error loading post**", embed=embed if post else None, view=view)

class ButtonAction(discord.ui.Button):
    def __init__(self, search_ctx: SearchContext, index: int, emoji: str, row: int, lock: list, ctx: commands.Context, db: str, label: str):
        super().__init__(emoji=emoji, style=discord.ButtonStyle.success, row=row, label=label)
        self.search_ctx, self.index, self.lock, self.ctx, self.db = search_ctx, index, lock, ctx, db

    async def callback(self, interaction: discord.Interaction):
        # Handle lock toggle
        if self.lock[0] != self.lock[1]:
            if interaction.user != self.ctx.author:
                return await interaction.response.send_message(
                    f"Only <@{self.ctx.author.id}> can lock/unlock this message.", 
                    ephemeral=True
                )
            self.lock = [self.lock[1], self.lock[1]]

        # Check if locked
        if self.lock[1] and interaction.user != self.ctx.author:
            return await interaction.response.send_message(
                f"<@{self.ctx.author.id}> locked this message.", 
                ephemeral=True
            )

        await interaction.response.defer()

        # Fetch post at index
        post = await self.search_ctx.get_post(self.index)
        embed = await BuildEmbed(self.search_ctx, post, self.index, self.db == "safe", self.ctx)
        view = ImageView(self.search_ctx, self.index, self.db == "safe", self.lock, self.ctx, self.db)
        await interaction.edit_original_response(content=None if post else "**Error loading post**", embed=embed if post else None, view=view)

class CogSus(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.hybrid_command(description=f'{description_helper["emojis"]["media"]} {description_helper["media"]["booru"]}')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def booru(self, ctx: commands.Context):
        await help_booru(ctx)

    @commands.command() # discord doesnt allow nsfw slash commands
    async def r34(self, ctx: commands.Context, *, tags: str = None):
        await R34(ctx, tags)

    @commands.hybrid_command(description=f"{description_helper['emojis']['booru']} gelbooru")
    @app_commands.describe(tags="Search tags (e.g. `hatsune miku, school uniform`)")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def gel(self, ctx: commands.Context, *, tags: str = None):
        await GEL(ctx, tags)

    @commands.hybrid_command(description=f"{description_helper['emojis']['booru']} safebooru")
    @app_commands.describe(tags="Search tags (e.g. `hatsune miku, school uniform`)")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def safe(self, ctx: commands.Context, *, tags: str = None):
        await SAFE(ctx, tags)

async def setup(bot: commands.Bot):
    await bot.add_cog(CogSus(bot))