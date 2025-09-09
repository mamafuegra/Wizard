import discord
from discord.ext import commands
import random
from typing import Optional, Dict, List
import os
import aiohttp
from urllib.parse import quote_plus
import io
import json
import re
from utils.formatting import quote

BULLY_MEDIA = [
    # Stable giphy CDN links (used as fallback when Tenor not available)
    "https://media.giphy.com/media/3o6Zt8MgUuvSbkZYWc/giphy.gif",
    "https://media.giphy.com/media/3o6ZtpxSZbQRRnwCKQ/giphy.gif",
    "https://media.giphy.com/media/26tPplGWjN0xLybiU/giphy.gif",
    "https://media.giphy.com/media/xUPGcMzwkOY01nj6A8/giphy.gif",
    "https://media.giphy.com/media/l2Je0l6E6QF6UVxZ2/giphy.gif",
    "https://media.giphy.com/media/3o6Zt8qkW2UbPLsZfa/giphy.gif",
]

BULLY_ROASTS = [
    "Look at you, discount NPC with a lagging brain tick!",
    "You’ve got the aim of a stormtrooper and the timing of dial‑up.",
    "Even your shadow alt‑F4’d from embarrassment.",
    "If common sense were RAM, you’d still be swapping to disk.",
    "That brain ping? Constant 999ms.",
    "You’re the human equivalent of a semicolon missing in production.",
]

class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.tenor_key = os.getenv("TENOR_API_KEY")
        self._nsfw_conf_path = 'nsfw_config.json'
        self._nsfw_media_path = 'nsfw_media.json'
        self._nsfw_conf: Dict = self._load_json(self._nsfw_conf_path, default={})
        self._nsfw_media: Dict[str, List[str]] = self._load_json(self._nsfw_media_path, default={
            "straight": [],
            "gay": [],
            "trans": [],
            "lesbian": [],
            "hentai": [],
            "slap": [
                "https://media.giphy.com/media/Gf3AUz3eBNbTW/giphy.gif",
                "https://media.giphy.com/media/jLeyZWgtwgr2U/giphy.gif"
            ],
            "punch": [
                "https://media.giphy.com/media/l2JJKs3I69qfaQleE/giphy.gif",
                "https://media.giphy.com/media/xT9IgIc0lryrxvqVGM/giphy.gif"
            ],
            "gore": [
                "https://media.giphy.com/media/3o7aCTfyhYawdOXcFW/giphy.gif"
            ]
        })

    @staticmethod
    def _load_json(path: str, default):
        if not os.path.exists(path):
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(default, f, indent=4)
            except Exception:
                pass
            return default
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return default

    def _save_nsfw_conf(self):
        try:
            with open(self._nsfw_conf_path, 'w', encoding='utf-8') as f:
                json.dump(self._nsfw_conf, f, indent=4)
        except Exception:
            pass

    def _guild_nsfw(self, guild_id: int) -> Dict:
        key = str(guild_id)
        if key not in self._nsfw_conf:
            self._nsfw_conf[key] = {"enabled": False}
        return self._nsfw_conf[key]

    async def _reply_embed(self, ctx: commands.Context, title: str, text: str):
        embed = discord.Embed(title=title, color=0xFFFFFF)
        embed.description = quote(text)
        await ctx.send(embed=embed)

    def _pick(self, bucket: str) -> Optional[str]:
        items = list(self._nsfw_media.get(bucket) or [])
        return random.choice(items) if items else None

    def _is_nsfw_allowed(self, ctx: commands.Context) -> bool:
        if not isinstance(ctx.channel, (discord.TextChannel, discord.Thread)):
            return False
        guild = ctx.guild
        if guild is None:
            return False
        conf = self._guild_nsfw(guild.id)
        return bool(conf.get("enabled") and getattr(ctx.channel, "is_nsfw", lambda: False)())

    # ------- validators -------
    _VIDEO_EXTS = (".mp4", ".webm", ".mov", ".m4v")

    @staticmethod
    def _looks_like_video(url: str) -> bool:
        lowered = url.lower().split("?")[0]
        return any(lowered.endswith(ext) for ext in Fun._VIDEO_EXTS)

    async def _validate_video_url(self, url: str) -> bool:
        if self._looks_like_video(url):
            return True
        # Try HEAD to verify content-type
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, timeout=8, allow_redirects=True) as resp:
                    if resp.status != 200:
                        return False
                    ctype = resp.headers.get("Content-Type", "").lower()
                    return ctype.startswith("video/")
        except Exception:
            return False

    async def _fetch_tenor_gif(self) -> Optional[str]:
        if not self.tenor_key:
            return None
        queries = ["bonk meme", "anime slap", "anime punch", "bully meme"]
        query = random.choice(queries)
        api = f"https://tenor.googleapis.com/v2/search?q={quote_plus(query)}&key={self.tenor_key}&client_key=wizard-bot&limit=25&random=true&media_filter=gif"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api, timeout=10) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
        except Exception:
            return None
        results = data.get("results") or []
        if not results:
            return None
        pick = random.choice(results)
        media = pick.get("media_formats") or {}
        for key in ("gif", "tinygif"):
            if key in media and isinstance(media[key], dict):
                url = media[key].get("url")
                if url:
                    return url
        return None

    async def _download_bytes(self, url: str) -> Optional[bytes]:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; WizardBot/1.0)"}
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=20, allow_redirects=True) as resp:
                    if resp.status != 200:
                        return None
                    # Cap download size to ~8MB to be safe
                    data = await resp.read()
                    if len(data) > 8 * 1024 * 1024:
                        return None
                    return data
        except Exception:
            return None

    @commands.command(name="bully", aliases=["bullt"]) 
    async def bully(self, ctx: commands.Context, member: Optional[discord.Member] = None) -> None:
        """Send a random bully GIF/image targeting the mentioned user."""
        if member is None:
            await ctx.send(f"Usage: `{ctx.prefix}bully @user` (alias: `{ctx.prefix}bullt`) or owners can use `jsk bully @user`.")
            return
        if member.id == ctx.author.id:
            await ctx.send("You can't bully yourself... but nice try.")
            return
        if member.bot:
            await ctx.send("Leave the bots alone. Bonk the humans instead!")
            return

        # Prefer Tenor API if available; otherwise use fallback list
        url = await self._fetch_tenor_gif() or random.choice(BULLY_MEDIA)
        roast = random.choice(BULLY_ROASTS)
        # Try to download and upload as attachment so it always renders
        data = await self._download_bytes(url)
        if data:
            file = discord.File(io.BytesIO(data), filename="bully.gif")
            await ctx.send(content=f"{ctx.author.mention} bullies {member.mention}! {roast}", file=file)
        else:
            # Fallback to direct URL if download fails
            await ctx.send(f"{ctx.author.mention} bullies {member.mention}! {roast}\n{url}")

    # ---------- SFW action gifs ----------
    @commands.command(name="slap")
    async def slap(self, ctx: commands.Context, member: Optional[discord.Member] = None) -> None:
        if member is None:
            await self._reply_embed(ctx, "Slap", f"Usage: `{ctx.prefix}slap @user`")
            return
        url = self._pick("slap") or await self._fetch_tenor_gif()
        embed = discord.Embed(title="Slap", color=0xFFFFFF, description=quote(f"{ctx.author.mention} slapped {member.mention}"))
        if url:
            embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.command(name="punch")
    async def punch(self, ctx: commands.Context, member: Optional[discord.Member] = None) -> None:
        if member is None:
            await self._reply_embed(ctx, "Punch", f"Usage: `{ctx.prefix}punch @user`")
            return
        url = self._pick("punch") or await self._fetch_tenor_gif()
        embed = discord.Embed(title="Punch", color=0xFFFFFF, description=quote(f"{ctx.author.mention} punched {member.mention}"))
        if url:
            embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.command(name="gore")
    async def gore(self, ctx: commands.Context, attacker: Optional[discord.Member] = None, victim: Optional[discord.Member] = None) -> None:
        # Requires NSFW restrictions per user's request
        if not self._is_nsfw_allowed(ctx):
            await self._reply_embed(ctx, "NSFW required", "Enable NSFW and use an age-restricted channel: `!nsfw enable` in an NSFW channel.")
            return
        attacker = attacker or ctx.author
        victim = victim or ctx.author
        url = self._pick("gore")
        embed = discord.Embed(title="Gore", color=0xFFFFFF, description=quote(f"{attacker.mention} kills {victim.mention}"))
        if url:
            embed.set_image(url=url)
        await ctx.send(embed=embed)

    # ---------- NSFW system ----------
    @commands.group(name="nsfw", invoke_without_command=True)
    async def nsfw(self, ctx: commands.Context) -> None:
        await self._reply_embed(ctx, "NSFW", "NSFW help documentation is available on our website.")

    @nsfw.command(name="enable")
    async def nsfw_enable(self, ctx: commands.Context) -> None:
        if not isinstance(ctx.channel, (discord.TextChannel, discord.Thread)):
            await self._reply_embed(ctx, "NSFW", "Use this in a server channel.")
            return
        if not ctx.channel.is_nsfw():
            await self._reply_embed(ctx, "NSFW", "Please enable age restriction on this channel first (channel settings → Age-Restricted).")
            return
        conf = self._guild_nsfw(ctx.guild.id)
        conf["enabled"] = True
        self._save_nsfw_conf()
        await self._reply_embed(ctx, "NSFW", "NSFW system enabled for this server.")

    @nsfw.command(name="send")
    async def nsfw_send(self, ctx: commands.Context) -> None:
        if not self._is_nsfw_allowed(ctx):
            await self._reply_embed(ctx, "NSFW", "NSFW is disabled or this channel is not age-restricted.")
            return
        # Straight random media
        url = self._pick("straight")
        if not url:
            await self._reply_embed(ctx, "NSFW", "No media configured. Add URLs to `nsfw_media.json` under 'straight'.")
            return
        await ctx.send(url)

    # ---- NSFW media management (owner/admin only) ----
    def _is_admin_owner_or_sso(self, ctx: commands.Context) -> bool:
        if ctx.guild is None:
            return False
        if ctx.author.id == ctx.guild.owner_id:
            return True
        if ctx.author.guild_permissions.administrator:
            return True
        try:
            with open('second_owners.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            return str(ctx.author.id) == data.get(str(ctx.guild.id))
        except Exception:
            return False

    @nsfw.command(name="add")
    async def nsfw_add(self, ctx: commands.Context, category: str, url: str) -> None:
        if not self._is_admin_owner_or_sso(ctx):
            await self._reply_embed(ctx, "NSFW", "Only Admins, Guild Owner, or Second Owner can modify NSFW media.")
            return
        if not self._is_nsfw_allowed(ctx):
            await self._reply_embed(ctx, "NSFW", "Enable NSFW and use an age-restricted channel to add media.")
            return
        category = category.lower()
        if category not in ("straight", "gay", "trans", "lesbian", "hentai"):
            await self._reply_embed(ctx, "NSFW", "Category must be one of: straight, gay, trans, lesbian, hentai.")
            return
        if not (url.startswith("http://") or url.startswith("https://")):
            await self._reply_embed(ctx, "NSFW", "Provide a valid URL starting with http(s)://")
            return
        if not await self._validate_video_url(url):
            await self._reply_embed(ctx, "NSFW", "Only direct video links are allowed (.mp4, .webm, .mov, .m4v).")
            return
        self._nsfw_media.setdefault(category, [])
        if url not in self._nsfw_media[category]:
            self._nsfw_media[category].append(url)
            try:
                with open(self._nsfw_media_path, 'w', encoding='utf-8') as f:
                    json.dump(self._nsfw_media, f, indent=4)
            except Exception:
                pass
        await self._reply_embed(ctx, "NSFW", f"Video added in {category} porn. Total now {len(self._nsfw_media[category])}.")

    @nsfw.command(name="bulk")
    async def nsfw_bulk(self, ctx: commands.Context, category: str, *, blob: str = "") -> None:
        if not self._is_admin_owner_or_sso(ctx):
            await self._reply_embed(ctx, "NSFW", "Only Admins, Guild Owner, or Second Owner can modify NSFW media.")
            return
        if not self._is_nsfw_allowed(ctx):
            await self._reply_embed(ctx, "NSFW", "Enable NSFW and use an age-restricted channel to add media.")
            return
        category = category.lower()
        if category not in ("straight", "gay", "trans", "lesbian", "hentai"):
            await self._reply_embed(ctx, "NSFW", "Category must be one of: straight, gay, trans, lesbian, hentai.")
            return
        # Collect candidates from attachment (txt) or message body
        candidates: List[str] = []
        if ctx.message.attachments:
            for att in ctx.message.attachments:
                if att.filename.lower().endswith(('.txt', '.list')):
                    try:
                        text = await att.read()
                        text = text.decode('utf-8', errors='ignore')
                        candidates.extend(text.splitlines())
                    except Exception:
                        continue
        if blob:
            candidates.extend(blob.split())
        # Extract URLs
        url_re = re.compile(r"https?://\S+")
        urls: List[str] = []
        for line in candidates:
            for m in url_re.findall(line):
                urls.append(m)
        if not urls:
            await self._reply_embed(ctx, "NSFW", "No URLs found. Attach a .txt with links or paste links in the message.")
            return
        # Filter to probable video URLs
        urls = [u for u in urls if self._looks_like_video(u)]
        bucket = self._nsfw_media.setdefault(category, [])
        before = len(bucket)
        # Deduplicate
        for u in urls:
            if u not in bucket:
                bucket.append(u)
        try:
            with open(self._nsfw_media_path, 'w', encoding='utf-8') as f:
                json.dump(self._nsfw_media, f, indent=4)
        except Exception:
            pass
        added = len(bucket) - before
        await self._reply_embed(ctx, "NSFW", f"Added {added} videos to {category} porn (total {len(bucket)}).")

    @nsfw.command(name="list")
    async def nsfw_list(self, ctx: commands.Context, category: str) -> None:
        category = category.lower()
        if category not in ("straight", "gay", "trans", "lesbian", "hentai"):
            await self._reply_embed(ctx, "NSFW", "Category must be one of: straight, gay, trans, lesbian, hentai.")
            return
        arr = self._nsfw_media.get(category) or []
        lines = [f"{i+1}. {u}" for i, u in enumerate(arr[:20])]
        more = "" if len(arr) <= 20 else f"\n... and {len(arr)-20} more"
        text = ("\n".join(lines) or "(empty)") + more
        await self._reply_embed(ctx, "NSFW", f"{category} has {len(arr)} URLs:\n{text}")

    # Specific categories
    @commands.command(name="gayporn", aliases=["gay_porn"]) 
    async def gay_porn(self, ctx: commands.Context) -> None:
        if not self._is_nsfw_allowed(ctx):
            await self._reply_embed(ctx, "NSFW", "NSFW is disabled or this channel is not age-restricted.")
            return
        url = self._pick("gay")
        if not url:
            await self._reply_embed(ctx, "NSFW", "No media configured. Add URLs to `nsfw_media.json` under 'gay'.")
            return
        await ctx.send(url)

    @commands.command(name="lesbianporn", aliases=["lesbian_porn"]) 
    async def lesbian_porn(self, ctx: commands.Context) -> None:
        if not self._is_nsfw_allowed(ctx):
            await self._reply_embed(ctx, "NSFW", "NSFW is disabled or this channel is not age-restricted.")
            return
        url = self._pick("lesbian")
        if not url:
            await self._reply_embed(ctx, "NSFW", "No media configured. Add URLs to `nsfw_media.json` under 'lesbian'.")
            return
        await ctx.send(url)

    @commands.command(name="transporn", aliases=["trans_porn"]) 
    async def transporn(self, ctx: commands.Context) -> None:
        if not self._is_nsfw_allowed(ctx):
            await self._reply_embed(ctx, "NSFW", "NSFW is disabled or this channel is not age-restricted.")
            return
        url = self._pick("trans")
        if not url:
            await self._reply_embed(ctx, "NSFW", "No media configured. Add URLs to `nsfw_media.json` under 'trans'.")
            return
        await ctx.send(url)

    @commands.command(name="hentai")
    async def hentai(self, ctx: commands.Context) -> None:
        if not self._is_nsfw_allowed(ctx):
            await self._reply_embed(ctx, "NSFW", "NSFW is disabled or this channel is not age-restricted.")
            return
        url = self._pick("hentai")
        if not url:
            await self._reply_embed(ctx, "NSFW", "No media configured. Add URLs to `nsfw_media.json` under 'hentai'.")
            return
        await ctx.send(url)

    # Rating commands (as embeds)
    @commands.command(name="gay")
    async def gay_rate(self, ctx: commands.Context, member: Optional[discord.Member] = None) -> None:
        if not self._is_nsfw_allowed(ctx):
            await self._reply_embed(ctx, "NSFW", "Enable NSFW and use an age-restricted channel to use this command.")
            return
        if member is None:
            await self._reply_embed(ctx, "Gay Meter", f"Usage: `{ctx.prefix}gay @user`")
            return
        percent = random.randint(0, 100)
        url = self._pick("gay") or self._pick("straight")
        embed = discord.Embed(title="Gay Meter", color=0xFFFFFF, description=quote(f"{member.mention} is {percent}%"))
        if url:
            embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.command(name="trans")
    async def trans_rate(self, ctx: commands.Context, member: Optional[discord.Member] = None) -> None:
        if not self._is_nsfw_allowed(ctx):
            await self._reply_embed(ctx, "NSFW", "Enable NSFW and use an age-restricted channel to use this command.")
            return
        if member is None:
            await self._reply_embed(ctx, "Trans Meter", f"Usage: `{ctx.prefix}trans @user`")
            return
        percent = random.randint(0, 100)
        url = self._pick("trans") or self._pick("straight")
        embed = discord.Embed(title="Trans Meter", color=0xFFFFFF, description=quote(f"{member.mention} is {percent}%"))
        if url:
            embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.command(name="fuck")
    async def fuck(self, ctx: commands.Context, member: Optional[discord.Member] = None) -> None:
        if not self._is_nsfw_allowed(ctx):
            await self._reply_embed(ctx, "NSFW", "NSFW is disabled or this channel is not age-restricted.")
            return
        if member is None:
            await self._reply_embed(ctx, "Sex", f"Usage: `{ctx.prefix}fuck @user`")
            return
        url = self._pick("straight")
        if not url:
            await self._reply_embed(ctx, "NSFW", "No media configured. Add URLs to `nsfw_media.json` under 'straight'.")
            return
        embed = discord.Embed(title="Sex", color=0xFFFFFF, description=quote(f"{ctx.author.mention} fucks {member.mention}"))
        embed.set_image(url=url)
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Fun(bot))
