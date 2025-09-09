import discord
from discord.ext import commands
from typing import Optional
import json


OWNER_IDS = [386889350010634252, 164202861356515328]  # Update as needed


def is_admin_owner_or_sso(ctx: commands.Context) -> bool:
    if ctx.guild is None:
        return False
    if ctx.author.id in OWNER_IDS:
        return True
    if ctx.author.id == ctx.guild.owner_id:
        return True
    if ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.manage_nicknames:
        return True
    try:
        with open('second_owners.json', 'r') as f:
            data = json.load(f)
        if str(ctx.author.id) == data.get(str(ctx.guild.id)):
            return True
    except Exception:
        pass
    return False


class Nickname(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name='nick')
    @commands.guild_only()
    async def change_nick(self, ctx: commands.Context, member: discord.Member, *, new_nick: str):
        """Change a member's server nickname.

        Usage: <prefix>nick @user <new nickname>
        """
        def send_embed(title: str, desc: str) -> None:
            # Fire-and-forget helper to send an embed
            emb = discord.Embed(title=title, description=desc, color=0xFFFFFF)
            return emb

        if not is_admin_owner_or_sso(ctx):
            emb = send_embed("Permission Required", "Only Admins, Guild Owner, Second Owner, or Bot Owner can use this.")
            await ctx.send(embed=emb)
            return
        # Bot permission and hierarchy checks
        me = ctx.guild.me
        if not me or not me.guild_permissions.manage_nicknames:
            emb = send_embed("Missing Permission", "I need the 'Manage Nicknames' permission.")
            await ctx.send(embed=emb)
            return
        if member.id == ctx.guild.owner_id:
            emb = send_embed("Action Blocked", "I cannot change the guild owner's nickname.")
            await ctx.send(embed=emb)
            return
        if me.top_role <= member.top_role:
            emb = send_embed("Action Blocked", "My role must be above the target member to change their nickname.")
            await ctx.send(embed=emb)
            return
        # Bound nickname length
        nick = new_nick.strip()
        if len(nick) > 32:
            nick = nick[:32]
        try:
            await member.edit(nick=nick, reason=f"Nickname change by {ctx.author}")
        except discord.Forbidden:
            emb = send_embed("Forbidden", "I don't have permission to change that member's nickname.")
            await ctx.send(embed=emb)
            return
        except discord.HTTPException as e:
            emb = send_embed("Failed", f"Failed to change nickname: {e}")
            await ctx.send(embed=emb)
            return
        embed = discord.Embed(title="Nickname Updated", color=0xFFFFFF,
                              description=f"User: {member.mention}\nNew Nickname: `{nick}`\nBy: {ctx.author.mention}")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Nickname(bot))


