import os
import json
from datetime import datetime, timezone
from typing import Dict, Optional

import discord
from discord.ext import commands


PREMIUM_FILE = 'premium_config.json'


def _load_premium() -> Dict[str, Dict]:
    try:
        if os.path.exists(PREMIUM_FILE):
            with open(PREMIUM_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_premium(cfg: Dict[str, Dict]) -> None:
    try:
        with open(PREMIUM_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


def _now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _is_premium_guild(guild_id: int) -> bool:
    cfg = _load_premium()
    entry = cfg.get(str(guild_id))
    if not entry:
        return False
    expires_at = int(entry.get('expires_at', 0) or 0)
    return _now_ts() < expires_at


def _is_second_owner(guild_id: int, user_id: int) -> bool:
    try:
        with open('second_owners.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return str(user_id) == data.get(str(guild_id))
    except Exception:
        return False


def _is_admin_owner_or_sso(ctx: commands.Context) -> bool:
    if ctx.guild is None:
        return False
    if ctx.author.id == ctx.guild.owner_id:
        return True
    if (hasattr(ctx.author, 'guild_permissions') and
            ctx.author.guild_permissions.administrator):
        return True
    if _is_second_owner(ctx.guild.id, ctx.author.id):
        return True
    return False


class Premium(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # -------- AI Commands (Coming Soon with Llama) --------
    @commands.group(name='ai', invoke_without_command=True)
    async def ai_group(self, ctx: commands.Context, 
                      *, question: Optional[str] = None):
        if question is None:
            await ctx.send(
                "AI features are coming soon with Llama integration! "
                "Stay tuned."
            )
            return
        
        await ctx.send(
            "🦙 **AI Features Coming Soon!**\n\n"
            "We're integrating Llama AI models. "
            "Check back tomorrow for full AI capabilities!"
        )

    @ai_group.command(name='enable')
    async def ai_enable(self, ctx: commands.Context):
        if not _is_admin_owner_or_sso(ctx):
            await ctx.send(
                "Only Admins, Guild Owner, or Second Owner can enable AI here."
            )
            return
        if not _is_premium_guild(ctx.guild.id):
            await ctx.send(
                "This server does not have premium active. "
                "Ask the bot owner to activate it."
            )
            return
        
        await ctx.send(
            "🦙 **AI Coming Soon!**\n\n"
            "AI features will be available tomorrow with Llama integration. "
            "Stay tuned!"
        )

    @ai_group.command(name='llama')
    async def ai_llama(self, ctx: commands.Context, *, question: str):
        """Ask Llama AI (coming soon)"""
        await ctx.send(
            "🦙 **Llama AI Coming Tomorrow!**\n\n"
            "We're setting up Llama models for you. "
            "Check back tomorrow for full AI capabilities!"
        )

    @ai_group.command(name='breathe')
    async def ai_breathe(self, ctx: commands.Context):
        try:
            from utils.formatting import quote
        except Exception:
            def quote(s: str) -> str:  # type: ignore
                return s
        msg = (
            "Let's do a short 30s breathing reset together:\n"
            "1) Breathe in through your nose for 4 seconds\n"
            "2) Hold for 4 seconds\n"
            "3) Exhale slowly for 6 seconds\n"
            "4) Repeat 4–5 cycles\n\n"
            "Tip: Relax your jaw and shoulders while you exhale."
        )
        await ctx.send(quote(msg))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Premium(bot))
