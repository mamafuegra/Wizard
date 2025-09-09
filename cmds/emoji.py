import discord
from discord.ext import commands
import aiohttp
import re
import json
from typing import Optional


def is_second_owner(guild_id: int, user_id: int) -> bool:
    try:
        with open('second_owners.json', 'r') as f:
            data = json.load(f)
        return str(user_id) == data.get(str(guild_id))
    except Exception:
        return False


class EmojiTools(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _can_manage_emojis(self, ctx: commands.Context) -> bool:
        if ctx.guild is None:
            return False
        if ctx.author.id == ctx.guild.owner_id:
            return True
        if is_second_owner(ctx.guild.id, ctx.author.id):
            return True
        return bool(ctx.author.guild_permissions.manage_emojis_and_stickers or ctx.author.guild_permissions.administrator)

    @commands.command(name='steal')
    @commands.guild_only()
    async def steal(self, ctx: commands.Context, emoji: Optional[str] = None, name: Optional[str] = None):
        """Steal a custom emoji from another server and add it here.

        Usage: <prefix>steal <emoji> [name]
        """
        if not self._can_manage_emojis(ctx):
            await ctx.send("You need Manage Emojis or be Owner/Second Owner to use this.")
            return

        me = ctx.guild.me
        if not me or not me.guild_permissions.manage_emojis_and_stickers:
            await ctx.send("I need the 'Manage Emojis and Stickers' permission.")
            return

        # Resolve source emoji: direct arg or from replied message
        e_name = None
        e_id = None
        animated = False
        source_str = emoji

        # If no argument provided, try to read from the replied message
        if source_str is None:
            ref = ctx.message.reference
            if ref and ref.message_id:
                try:
                    replied = await ctx.channel.fetch_message(ref.message_id)
                    # find first custom emoji in content
                    mm = re.findall(r"<a?:([A-Za-z0-9_]+):(\d{15,25})>", replied.content)
                    if mm:
                        e_name, e_id = mm[0][0], int(mm[0][1])
                        animated = replied.content.strip().startswith('<a:')
                    else:
                        await ctx.send("No custom emoji found in the replied message.")
                        return
                except Exception:
                    await ctx.send("Couldn't read the replied message.")
                    return
            else:
                await ctx.send("Provide a custom emoji or reply to a message containing one.")
                return

        if e_id is None:
            # Parse the emoji from the provided argument
            try:
                partial = discord.PartialEmoji.from_str(source_str)
            except Exception:
                partial = None
            if partial is None or partial.id is None:
                m = re.match(r"<a?:([A-Za-z0-9_]+):(\d{15,25})>", source_str or '')
                if not m:
                    await ctx.send("Provide a valid custom emoji like <:name:id> or <a:name:id> or reply to a message with one.")
                    return
                e_name, e_id = m.group(1), int(m.group(2))
                animated = bool(source_str and source_str.startswith('<a:'))
            else:
                e_name = partial.name or 'emoji'
                e_id = int(partial.id)
                animated = bool(partial.animated)

        final_name = (name or e_name or 'emoji')[:32]
        # Try gif first if animated, fall back to png
        ext = 'gif' if animated else 'png'
        url = f"https://cdn.discordapp.com/emojis/{e_id}.{ext}?quality=lossless"

        # Download bytes and create
        data = None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                    else:
                        # fallback to png if gif failed
                        fallback = f"https://cdn.discordapp.com/emojis/{e_id}.png?quality=lossless"
                        async with session.get(fallback) as r2:
                            if r2.status != 200:
                                await ctx.send("Failed to fetch the emoji image.")
                                return
                            data = await r2.read()
                            ext = 'png'
        except Exception as e:
            await ctx.send(f"Failed to download emoji: {e}")
            return

        # Prevent duplicate by name
        existing = discord.utils.get(ctx.guild.emojis, name=final_name)
        if existing:
            embed = discord.Embed(title="Emoji Exists", color=0xFFFFFF, description=f":{existing.name}: {existing}")
            embed.set_image(url=f"https://cdn.discordapp.com/emojis/{existing.id}.png?quality=lossless")
            await ctx.send(embed=embed)
            return
        try:
            new_emoji = await ctx.guild.create_custom_emoji(name=final_name, image=data, reason=f"Steal by {ctx.author}")
        except discord.Forbidden:
            await ctx.send("I don't have permission to add emojis here.")
            return
        except discord.HTTPException as e:
            await ctx.send(f"Failed to add emoji: {e}")
            return

        # Build a preview embed with the emoji image
        preview_url = f"https://cdn.discordapp.com/emojis/{e_id}.{ext}?quality=lossless"
        embed = discord.Embed(title="Emoji Added", color=0xFFFFFF, description=f"Created emoji: {new_emoji} (:{new_emoji.name}:)")
        embed.set_image(url=preview_url)
        await ctx.send(embed=embed)
        # Avoid double posting in case a different listener echoes command


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EmojiTools(bot))


