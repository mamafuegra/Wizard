import discord
from discord.ext import commands
from typing import Optional
try:
    from utils.formatting import quote
except Exception:
    def quote(t: str) -> str:
        return t

OWNER_IDS = [386889350010634252, 164202861356515328]  # Update as needed

def is_admin_owner_or_sso(ctx: commands.Context) -> bool:
    if ctx.guild is None:
        return False
    if ctx.author.id in OWNER_IDS:
        return True
    if ctx.author.id == ctx.guild.owner_id:
        return True
    if ctx.author.guild_permissions.administrator:
        return True
    # Second owner check
    try:
        import json
        with open('second_owners.json', 'r') as f:
            data = json.load(f)
        if str(ctx.author.id) == data.get(str(ctx.guild.id)):
            return True
    except Exception:
        pass
    return False

class Purge(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="purge")
    @commands.guild_only()
    async def purge_cmd(self, ctx: commands.Context, *args: str):
        """Purge messages with report.

        Usage:
        - !purge 100
        - !purge 100 @user
        - !purge 100 bot
        - !purge @user 100
        - !purge bot 100
        """
        if not is_admin_owner_or_sso(ctx):
            await ctx.send("Only Admins, Guild Owner, Second Owner, or Bot Owner can use this.")
            return
        if not args:
            await ctx.send("Usage: !purge 100 | !purge 100 @user | !purge 100 bot")
            return

        # Parse tokens order-agnostic
        count = None
        target_token: Optional[str] = None
        for tok in args:
            if tok.isdigit():
                count = int(tok)
            else:
                target_token = tok
        if count is None:
            await ctx.send("Provide a count (1-200).")
            return
        if count < 1 or count > 200:
            await ctx.send("Count must be between 1 and 200.")
            return

        # Determine filter
        user_id: Optional[int] = None
        filter_kind = "all"
        if target_token:
            if target_token.lower() == "bot":
                filter_kind = "bot"
            else:
                try:
                    member = await commands.MemberConverter().convert(ctx, target_token)
                    user_id = member.id
                    filter_kind = "user"
                except Exception:
                    await ctx.send("Could not resolve user. Please mention a valid user or use 'bot'.")
                    return

        def check(msg: discord.Message) -> bool:
            if filter_kind == "all":
                return True
            if filter_kind == "bot":
                return msg.author.bot
            if filter_kind == "user" and user_id is not None:
                return msg.author.id == user_id
            return False

        # Collect up to 'count' matching messages (scan recent history up to 2000)
        to_delete: list[discord.Message] = []
        async for m in ctx.channel.history(limit=2000):
            if check(m):
                to_delete.append(m)
            if len(to_delete) >= count:
                break
        if not to_delete:
            await ctx.send("No messages matched your criteria.")
            return

        # Build transcript before deletion
        lines: list[str] = []
        for m in reversed(to_delete):
            snippet = (m.content or "").replace("`", "'")
            if len(snippet) > 150:
                snippet = snippet[:147] + "..."
            parts = []
            if snippet:
                parts.append(snippet)
            if m.attachments:
                parts.append(f"[attachments: {len(m.attachments)}]")
            if m.stickers:
                parts.append(f"[stickers: {len(m.stickers)}]")
            line = f"{m.author} — {m.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC: {' '.join(parts) if parts else '[no content]'}"
            lines.append(line)
        transcript = "\n".join(lines)

        # Delete
        try:
            if len(to_delete) >= 2:
                await ctx.channel.delete_messages(to_delete)
            else:
                await to_delete[0].delete()
        except Exception:
            # Fallback to built-in purge (best effort)
            await ctx.channel.purge(limit=count, check=check)

        # Report embed
        title_target = {
            "all": "all messages",
            "bot": "bot messages",
            "user": f"messages by <@{user_id}>" if user_id else "user messages"
        }[filter_kind]
        embed = discord.Embed(title="Purge Report", color=0xFFFFFF,
                              description=quote(f"Moderator: {ctx.author.mention}\nChannel: {ctx.channel.mention}\nDeleted: {len(to_delete)} {title_target}"))
        # Attach transcript as file if it is large
        if transcript and len(transcript) <= 1000:
            embed.add_field(name="Messages", value=transcript, inline=False)
            await ctx.send(embed=embed)
        elif transcript:
            try:
                from io import StringIO
                fp = StringIO(transcript)
                file = discord.File(fp=fp, filename="purge_transcript.txt")
                embed.add_field(name="Messages", value="Transcript attached as file.", inline=False)
                await ctx.send(embed=embed, file=file)
            except Exception:
                embed.add_field(name="Messages", value=(transcript[:1000] + "..."), inline=False)
                await ctx.send(embed=embed)
        else:
            await ctx.send(embed=embed)

    # JSK dispatcher support for bot owner only
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        if message.content.lower().startswith("jsk purge"):
            if message.author.id not in OWNER_IDS:
                return
            rest = message.content[9:].strip()
            tokens = rest.split()
            ctx = await self.bot.get_context(message)
            cmd = self.bot.get_command("purge")
            if cmd:
                await ctx.invoke(cmd, *tokens)

async def setup(bot: commands.Bot):
    await bot.add_cog(Purge(bot))
