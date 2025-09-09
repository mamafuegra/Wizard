import discord
from discord.ext import commands
import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Deque, Optional
from collections import defaultdict, deque


CONFIG_FILE = 'antinuke_config.json'
BOT_OWNER_IDS = {386889350010634252, 164202861356515328}


CATEGORY_ALIASES = {
    'mass mention': 'mass_mention',
    'mass kick': 'mass_kick',
    'mass ban': 'mass_ban',
    'link': 'link_post',
    'creating channel': 'create_channel',
    'deleting channel': 'delete_channel',
    'giving role': 'give_role',
    'creating role': 'create_role',
    'deleting role': 'delete_role',
    'creating webhook': 'create_webhook',
    'deleting webhook': 'delete_webhook',
    'bot add': 'bot_add',
}

DEFAULTS = {
    'mass_mention': {'enabled': True, 'threshold': 2, 'action': 'kick', 'timeout_seconds': 600},
    'mass_kick': {'enabled': True, 'threshold': 1, 'action': 'kick', 'timeout_seconds': 600},
    'mass_ban': {'enabled': True, 'threshold': 1, 'action': 'kick', 'timeout_seconds': 600},
    # Link posting: default timeout 2 minutes
    'link_post': {'enabled': True, 'threshold': 1, 'action': 'timeout', 'timeout_seconds': 120},
    'create_channel': {'enabled': True, 'threshold': 1, 'action': 'kick', 'timeout_seconds': 600},
    'delete_channel': {'enabled': True, 'threshold': 1, 'action': 'kick', 'timeout_seconds': 600},
    'give_role': {'enabled': True, 'threshold': 1, 'action': 'kick', 'timeout_seconds': 600},
    'create_role': {'enabled': True, 'threshold': 1, 'action': 'kick', 'timeout_seconds': 600},
    'delete_role': {'enabled': True, 'threshold': 1, 'action': 'kick', 'timeout_seconds': 600},
    'create_webhook': {'enabled': True, 'threshold': 1, 'action': 'kick', 'timeout_seconds': 600},
    'delete_webhook': {'enabled': True, 'threshold': 1, 'action': 'kick', 'timeout_seconds': 600},
    'bot_add': {'enabled': True, 'threshold': 1, 'action': 'kick', 'timeout_seconds': 600},
}


def load_config() -> Dict[str, Dict]:
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_config(config: Dict[str, Dict]) -> None:
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass


def is_second_owner(guild_id: int, user_id: int) -> bool:
    try:
        with open('second_owners.json', 'r') as f:
            data = json.load(f)
        return str(user_id) == data.get(str(guild_id))
    except Exception:
        return False


class AntiNuke(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.config = load_config()
        # Simple rate counters per category/executor within small window
        self._counters: Dict[int, Dict[str, Dict[int, Deque[datetime]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: deque(maxlen=10))))
        self._window_seconds = 12

    # ---------- helpers ----------
    def guild_conf(self, guild_id: int) -> Dict:
        g = str(guild_id)
        self.config.setdefault(g, {'enabled': False, 'categories': DEFAULTS.copy(), 'whitelist': []})
        # Ensure all categories exist
        cats = self.config[g].setdefault('categories', {})
        for k, v in DEFAULTS.items():
            cats.setdefault(k, dict(v))
        return self.config[g]

    def can_configure(self, ctx: commands.Context) -> bool:
        if ctx.guild is None:
            return False
        if ctx.author.id in BOT_OWNER_IDS:
            return True
        if ctx.author.id == ctx.guild.owner_id:
            return True
        if ctx.author.guild_permissions.administrator:
            return True
        if is_second_owner(ctx.guild.id, ctx.author.id):
            return True
        return False

    async def send_permission_error(self, ctx: commands.Context, command_name: str):
        """Send a standardized permission error embed"""
        embed = discord.Embed(
            title="```Permission Denied```",
            description=f"You are not a guild owner or second owner to use this command.",
            color=0xe74c3c
        )
        await ctx.send(embed=embed)

    def is_antinuke_mod(self, guild: discord.Guild, user: discord.Member) -> bool:
        """Check if user is an antinuke mod"""
        conf = self.guild_conf(guild.id)
        mod_role_id = conf.get('antinuke_mod_role')
        if mod_role_id:
            mod_role = guild.get_role(mod_role_id)
            if mod_role and mod_role in user.roles:
                return True
        return False

    def is_specific_mod(self, guild: discord.Guild, user: discord.Member, category: str) -> bool:
        """Check if user is a specific category mod"""
        conf = self.guild_conf(guild.id)
        specific_mods = conf.get('specific_mods', {})
        mod_role_id = specific_mods.get(category)
        if mod_role_id:
            mod_role = guild.get_role(mod_role_id)
            if mod_role and mod_role in user.roles:
                return True
        return False

    def is_whitelisted(self, guild: discord.Guild, user: discord.abc.User) -> bool:
        if user.id in BOT_OWNER_IDS:
            return True
        if user.id == guild.owner_id:
            return True
        if is_second_owner(guild.id, user.id):
            return True
        # Always allow this bot
        me = guild.me
        if me and user.id == me.id:
            return True
        # Check if user is an antinuke mod
        if isinstance(user, discord.Member) and self.is_antinuke_mod(guild, user):
            return True
        # Guild-specific extra whitelist
        wl = self.guild_conf(guild.id).get('whitelist', [])
        if str(user.id) in {str(x) for x in wl}:
            return True
        return False

    async def punish(self, guild: discord.Guild, member: discord.Member, action: str, *, timeout_seconds: Optional[int] = None) -> None:
        if member is None or member.bot and action != 'bot_add':
            # still allow bot_add flow to kick bot
            pass
        # Skip if above bot in hierarchy
        me = guild.me
        if me and isinstance(member, discord.Member) and member.top_role >= me.top_role:
            return
        try:
            if action == 'ban':
                await guild.ban(member, reason='AntiNuke', delete_message_days=0)
            elif action == 'kick':
                await guild.kick(member, reason='AntiNuke')
            elif action == 'strip':
                roles = [r for r in member.roles if r.name != '@everyone' and (not me or r < me.top_role)]
                if roles:
                    await member.remove_roles(*roles, reason='AntiNuke strip')
            elif action == 'timeout':
                if timeout_seconds is None or timeout_seconds <= 0:
                    timeout_seconds = 600
                until = datetime.now(timezone.utc) + timedelta(seconds=int(timeout_seconds))
                try:
                    await member.timeout(until, reason='AntiNuke')
                except Exception:
                    pass
        except Exception:
            pass

    def bump_counter(self, guild_id: int, category: str, user_id: int) -> int:
        q = self._counters[guild_id][category][user_id]
        now = datetime.now(timezone.utc)
        q.append(now)
        # prune
        while q and (now - q[0]).total_seconds() > self._window_seconds:
            q.popleft()
        return len(q)

    # ---------- commands ----------
    @commands.group(name='antinuke', invoke_without_command=True)
    @commands.guild_only()
    async def antinuke_group(self, ctx: commands.Context, *args):
        await ctx.send("AntiNuke help documentation is available on our website.")

    @antinuke_group.command(name='enable')
    async def antinuke_enable(self, ctx: commands.Context):
        if not self.can_configure(ctx):
            await self.send_permission_error(ctx, "antinuke enable")
            return
        conf = self.guild_conf(ctx.guild.id)
        conf['enabled'] = True
        # seed defaults if missing
        conf['categories'] = {k: dict(v) for k, v in DEFAULTS.items()}
        save_config(self.config)
        await ctx.message.add_reaction('✅')

    @antinuke_group.command(name='disable')
    async def antinuke_disable(self, ctx: commands.Context):
        if not self.can_configure(ctx):
            await self.send_permission_error(ctx, "antinuke disable")
            return
        conf = self.guild_conf(ctx.guild.id)
        conf['enabled'] = False
        save_config(self.config)
        await ctx.message.add_reaction('✅')

    @antinuke_group.command(name='status')
    async def antinuke_status(self, ctx: commands.Context):
        conf = self.guild_conf(ctx.guild.id)
        cats = conf.get('categories', {})
        try:
            from utils.formatting import quote
        except Exception:
            def quote(t: str) -> str:
                return t
        embed = discord.Embed(title="AntiNuke Status", color=0xFFFFFF)
        embed.add_field(name="Enabled", value=quote("Yes" if conf.get('enabled') else "No"), inline=False)
        extra = conf.get('whitelist', [])
        if extra:
            view_ids = ", ".join(f"<@{int(i)}>" for i in extra[:10])
            embed.add_field(name="Whitelist", value=quote(view_ids), inline=False)
        for human, key in CATEGORY_ALIASES.items():
            c = cats.get(key, {})
            val = f"on | thr={c.get('threshold', '-') } | act={c.get('action', '-') }" if c.get('enabled') else "off"
            embed.add_field(name=human.title(), value=quote(val), inline=True)
        embed.set_footer(text=f"Guild ID: {ctx.guild.id}")
        await ctx.send(embed=embed)

    # free-form config: antinuke <category> enable [threshold] [punishment [duration]]
    @antinuke_group.command(name='config')
    async def antinuke_config_cmd(self, ctx: commands.Context, *, text: str):
        await self._handle_freeform_config(ctx, text)

    @antinuke_group.command(name='set')
    async def antinuke_set_alias(self, ctx: commands.Context, *, text: str):
        await self._handle_freeform_config(ctx, text)

    async def _handle_freeform_config(self, ctx: commands.Context, text: str):
        if not self.can_configure(ctx):
            await self.send_permission_error(ctx, "antinuke config")
            return
        conf = self.guild_conf(ctx.guild.id)
        if not conf.get('enabled'):
            await ctx.send(f"Enable AntiNuke first: `{ctx.prefix}antinuke enable`")
            return
        raw = text.strip().lower()
        # find category
        target_key = None
        for human, key in CATEGORY_ALIASES.items():
            if human in raw:
                target_key = key
                break
        if target_key is None:
            available_categories = ", ".join(CATEGORY_ALIASES.keys())
            await ctx.send(f"Provide a valid category name. Available categories: {available_categories}")
            return
        tokens = raw.split()
        action = None
        threshold = None
        timeout_seconds = None
        enable_state = None
        # parse tokens
        if 'enable' in tokens:
            enable_state = True
        if 'disable' in tokens:
            enable_state = False
        m = re.search(r"\b(\d+)\b", raw)
        if m:
            threshold = int(m.group(1))
        for a in ('ban', 'kick', 'strip', 'timeout'):
            if a in tokens:
                action = a
                break
        if action == 'timeout':
            # look for duration like 30s, 2m, 1h, 1d
            dm = re.search(r"(\d+\s*(s|sec|secs|second|seconds|m|min|minute|minutes|h|hr|hour|hours|d|day|days))", raw)
            if dm:
                timeout_seconds = self.parse_duration_seconds(dm.group(1))
        # apply
        cat = conf['categories'].setdefault(target_key, dict(DEFAULTS.get(target_key, {'enabled': True, 'threshold': 1, 'action': 'kick'})))
        if enable_state is not None:
            cat['enabled'] = enable_state
        if threshold is not None:
            cat['threshold'] = max(1, min(100, threshold))
        if action is not None:
            cat['action'] = action
        if timeout_seconds is not None:
            cat['timeout_seconds'] = int(timeout_seconds)
        save_config(self.config)
        await ctx.message.add_reaction('✅')

    # ----- whitelist management -----
    @antinuke_group.group(name='whitelist', invoke_without_command=True)
    async def antinuke_whitelist(self, ctx: commands.Context):
        await ctx.send("AntiNuke whitelist help documentation is available on our website.")

    @antinuke_whitelist.command(name='add')
    async def antinuke_whitelist_add(self, ctx: commands.Context, member: discord.Member):
        if not self.can_configure(ctx):
            await self.send_permission_error(ctx, "antinuke whitelist add")
            return
        conf = self.guild_conf(ctx.guild.id)
        wl = conf.setdefault('whitelist', [])
        if str(member.id) not in {str(x) for x in wl}:
            wl.append(str(member.id))
            save_config(self.config)
        await ctx.message.add_reaction('✅')

    @antinuke_whitelist.command(name='remove')
    async def antinuke_whitelist_remove(self, ctx: commands.Context, member: discord.Member):
        if not self.can_configure(ctx):
            await self.send_permission_error(ctx, "antinuke whitelist remove")
            return
        conf = self.guild_conf(ctx.guild.id)
        wl = conf.setdefault('whitelist', [])
        try:
            wl.remove(str(member.id))
            save_config(self.config)
        except ValueError:
            pass
        await ctx.message.add_reaction('✅')

    @antinuke_group.command(name='setmod')
    async def antinuke_mod(self, ctx: commands.Context, role: discord.Role):
        """Set antinuke mod role"""
        if not self.can_configure(ctx):
            await self.send_permission_error(ctx, "antinuke mod")
            return
        conf = self.guild_conf(ctx.guild.id)
        conf['antinuke_mod_role'] = role.id
        save_config(self.config)
        
        embed = discord.Embed(
            title="```Antinuke Mod Set```",
            description=f"{ctx.author.mention} who is getting modded in antinuke is mod for ping, role etc selected antinuke cmd",
            color=0x1DB954
        )
        await ctx.send(embed=embed)

    @antinuke_group.group(name='mod')
    async def antinuke_mod_group(self, ctx: commands.Context):
        """Antinuke mod management commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Use `!antinuke mod <role>` to set general mod, `!antinuke mod link <role>` for link mod, or `!antinuke mod list` to view mods.")

    @antinuke_mod_group.command(name='link')
    async def antinuke_mod_link(self, ctx: commands.Context, role: discord.Role):
        """Set link posting mod role"""
        if not self.can_configure(ctx):
            await self.send_permission_error(ctx, "antinuke mod link")
            return
        conf = self.guild_conf(ctx.guild.id)
        specific_mods = conf.setdefault('specific_mods', {})
        specific_mods['link_post'] = role.id
        save_config(self.config)
        
        embed = discord.Embed(
            title="```Link Mod Set```",
            description=f"{role.mention} is now a mod for link posting only",
            color=0x1DB954
        )
        await ctx.send(embed=embed)

    @antinuke_mod_group.command(name='list')
    async def antinuke_mod_list(self, ctx: commands.Context):
        """List all antinuke mods"""
        if not self.can_configure(ctx):
            await self.send_permission_error(ctx, "antinuke mod list")
            return
        conf = self.guild_conf(ctx.guild.id)
        
        embed = discord.Embed(
            title="```Antinuke Mods```",
            color=0xFFFFFF
        )
        
        # General antinuke mod
        antinuke_mod_role_id = conf.get('antinuke_mod_role')
        if antinuke_mod_role_id:
            antinuke_mod_role = ctx.guild.get_role(antinuke_mod_role_id)
            if antinuke_mod_role:
                embed.add_field(name="General Antinuke Mod", value=antinuke_mod_role.mention, inline=False)
        
        # Specific mods
        specific_mods = conf.get('specific_mods', {})
        if specific_mods:
            for category, role_id in specific_mods.items():
                role = ctx.guild.get_role(role_id)
                if role:
                    category_name = category.replace('_', ' ').title()
                    embed.add_field(name=f"{category_name} Mod", value=role.mention, inline=True)
        
        if not antinuke_mod_role_id and not specific_mods:
            embed.description = "No antinuke mods configured"
        
        await ctx.send(embed=embed)

    @staticmethod
    def parse_duration_seconds(text: str) -> Optional[int]:
        try:
            s = text.strip().lower().replace(' ', '')
            m = re.match(r'^(\d+)(s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days)$', s)
            if not m:
                return None
            value = int(m.group(1))
            unit = m.group(2)
            if unit.startswith('s'):
                return value
            if unit.startswith('m'):
                return value * 60
            if unit.startswith('h'):
                return value * 3600
            if unit.startswith('d'):
                return value * 86400
        except Exception:
            return None
        return None

    # ---------- listeners ----------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        conf = self.guild_conf(message.guild.id)
        if not conf.get('enabled'):
            return
        if self.is_whitelisted(message.guild, message.author):
            return
        # Link posting detection
        link_cat = conf['categories'].get('link_post', DEFAULTS['link_post'])
        try:
            if link_cat.get('enabled'):
                if re.search(r"https?://|discord\.gg/|discord\.com/invite/", message.content, re.IGNORECASE):
                    # Delete immediately
                    try:
                        await message.delete()
                    except Exception:
                        pass
                    n = self.bump_counter(message.guild.id, 'link_post', message.author.id)
                    if n >= int(link_cat.get('threshold', 1)):
                        await self.punish(message.guild, message.author, link_cat.get('action', 'timeout'), timeout_seconds=link_cat.get('timeout_seconds'))
                        return
        except Exception:
            pass

        # Mass mention detection
        mm_cat = conf['categories'].get('mass_mention', DEFAULTS['mass_mention'])
        if mm_cat.get('enabled'):
            count = len(message.mentions) + len(message.role_mentions) + (1 if message.mention_everyone else 0)
            if count >= int(mm_cat.get('threshold', 2)):
                await self.punish(message.guild, message.author, mm_cat.get('action', 'kick'), timeout_seconds=mm_cat.get('timeout_seconds'))
                try:
                    await message.delete()
                except Exception:
                    pass

    async def _maybe_punish_audit(self, guild: discord.Guild, action: discord.AuditLogAction, category_key: str, target_id: Optional[int] = None):
        conf = self.guild_conf(guild.id)
        if not conf.get('enabled'):
            return
        cat = conf['categories'].get(category_key, DEFAULTS.get(category_key, {}))
        if not cat.get('enabled'):
            return
        try:
            async for entry in guild.audit_logs(limit=3, action=action):
                if target_id is not None and getattr(entry.target, 'id', None) != target_id:
                    continue
                executor = entry.user
                if executor and isinstance(executor, discord.Member) and not self.is_whitelisted(guild, executor):
                    n = self.bump_counter(guild.id, category_key, executor.id)
                    if n >= int(cat.get('threshold', 1)):
                        await self.punish(guild, executor, cat.get('action', 'kick'), timeout_seconds=cat.get('timeout_seconds'))
                break
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        conf = self.guild_conf(guild.id)
        cat = conf['categories'].get('create_channel', DEFAULTS['create_channel'])
        if not conf.get('enabled') or not cat.get('enabled'):
            return
        try:
            async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.channel_create):
                executor = entry.user
                if executor and isinstance(executor, discord.Member) and not self.is_whitelisted(guild, executor):
                    n = self.bump_counter(guild.id, 'create_channel', executor.id)
                    if n >= int(cat.get('threshold', 1)):
                        await self.punish(guild, executor, cat.get('action', 'kick'), timeout_seconds=cat.get('timeout_seconds'))
                        # remediation: delete created channel
                        try:
                            await channel.delete(reason='AntiNuke: unauthorized channel creation')
                        except Exception:
                            pass
                break
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        conf = self.guild_conf(guild.id)
        cat = conf['categories'].get('delete_channel', DEFAULTS['delete_channel'])
        if not conf.get('enabled') or not cat.get('enabled'):
            return
        # capture metadata for restore
        name = getattr(channel, 'name', 'restored-channel')
        category = getattr(channel, 'category', None)
        is_voice = isinstance(channel, discord.VoiceChannel)
        try:
            async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.channel_delete):
                executor = entry.user
                if executor and isinstance(executor, discord.Member) and not self.is_whitelisted(guild, executor):
                    n = self.bump_counter(guild.id, 'delete_channel', executor.id)
                    if n >= int(cat.get('threshold', 1)):
                        await self.punish(guild, executor, cat.get('action', 'kick'), timeout_seconds=cat.get('timeout_seconds'))
                        # remediation: restore channel best-effort
                        try:
                            if is_voice:
                                await guild.create_voice_channel(name=name, category=category, reason='AntiNuke restore')
                            else:
                                await guild.create_text_channel(name=name, category=category, reason='AntiNuke restore')
                        except Exception:
                            pass
                break
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        guild = role.guild
        conf = self.guild_conf(guild.id)
        cat = conf['categories'].get('create_role', DEFAULTS['create_role'])
        if not conf.get('enabled') or not cat.get('enabled'):
            return
        try:
            async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.role_create):
                executor = entry.user
                if executor and isinstance(executor, discord.Member) and not self.is_whitelisted(guild, executor):
                    n = self.bump_counter(guild.id, 'create_role', executor.id)
                    if n >= int(cat.get('threshold', 1)):
                        await self.punish(guild, executor, cat.get('action', 'kick'), timeout_seconds=cat.get('timeout_seconds'))
                        # remediation: delete created role
                        try:
                            await role.delete(reason='AntiNuke: unauthorized role creation')
                        except Exception:
                            pass
                break
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        guild = role.guild
        conf = self.guild_conf(guild.id)
        cat = conf['categories'].get('delete_role', DEFAULTS['delete_role'])
        if not conf.get('enabled') or not cat.get('enabled'):
            return
        # capture metadata
        name = role.name
        colour = role.colour
        hoist = role.hoist
        mentionable = role.mentionable
        try:
            async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.role_delete):
                executor = entry.user
                if executor and isinstance(executor, discord.Member) and not self.is_whitelisted(guild, executor):
                    n = self.bump_counter(guild.id, 'delete_role', executor.id)
                    if n >= int(cat.get('threshold', 1)):
                        await self.punish(guild, executor, cat.get('action', 'kick'), timeout_seconds=cat.get('timeout_seconds'))
                        # remediation: restore role best-effort
                        try:
                            await guild.create_role(name=name, colour=colour, hoist=hoist, mentionable=mentionable, reason='AntiNuke restore')
                        except Exception:
                            pass
                break
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # role additions
        if after.guild is None:
            return
        added = [r for r in after.roles if r not in before.roles]
        if not added:
            return
        try:
            async for entry in after.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_role_update):
                if getattr(entry.target, 'id', None) != after.id:
                    continue
                executor = entry.user
                if executor and isinstance(executor, discord.Member) and not self.is_whitelisted(after.guild, executor):
                    conf = self.guild_conf(after.guild.id)
                    cat = conf['categories'].get('give_role', DEFAULTS['give_role'])
                    if cat.get('enabled'):
                        n = self.bump_counter(after.guild.id, 'give_role', executor.id)
                        if n >= int(cat.get('threshold', 1)):
                            await self.punish(after.guild, executor, cat.get('action', 'kick'), timeout_seconds=cat.get('timeout_seconds'))
                break
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        # check for both create and delete
        # create
        conf = self.guild_conf(guild.id)
        if conf.get('enabled'):
            # create webhook event
            cat_c = conf['categories'].get('create_webhook', DEFAULTS['create_webhook'])
            if cat_c.get('enabled'):
                try:
                    async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.webhook_create):
                        executor = entry.user
                        if executor and isinstance(executor, discord.Member) and not self.is_whitelisted(guild, executor):
                            n = self.bump_counter(guild.id, 'create_webhook', executor.id)
                            if n >= int(cat_c.get('threshold', 1)):
                                await self.punish(guild, executor, cat_c.get('action', 'kick'), timeout_seconds=cat_c.get('timeout_seconds'))
                                # remediation: delete created webhook
                                try:
                                    hook = entry.target
                                    if isinstance(hook, discord.Webhook):
                                        await hook.delete(reason='AntiNuke: unauthorized webhook creation')
                                except Exception:
                                    pass
                        break
                except Exception:
                    pass
            # delete webhook event
            cat_d = conf['categories'].get('delete_webhook', DEFAULTS['delete_webhook'])
            if cat_d.get('enabled'):
                try:
                    async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.webhook_delete):
                        executor = entry.user
                        if executor and isinstance(executor, discord.Member) and not self.is_whitelisted(guild, executor):
                            n = self.bump_counter(guild.id, 'delete_webhook', executor.id)
                            if n >= int(cat_d.get('threshold', 1)):
                                await self.punish(guild, executor, cat_d.get('action', 'kick'), timeout_seconds=cat_d.get('timeout_seconds'))
                                # remediation: recreate webhook name in this channel
                                try:
                                    name = getattr(entry.target, 'name', 'restored-webhook')
                                    await channel.create_webhook(name=name)
                                except Exception:
                                    pass
                        break
                except Exception:
                    pass

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # If a bot joins, find who added it and punish according to config
        if not member.bot:
            return
        guild = member.guild
        conf = self.guild_conf(guild.id)
        if not conf.get('enabled'):
            return
        cat = conf['categories'].get('bot_add', DEFAULTS['bot_add'])
        if not cat.get('enabled'):
            return
        try:
            async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.bot_add):
                if getattr(entry.target, 'id', None) != member.id:
                    continue
                adder = entry.user
                if adder and isinstance(adder, discord.Member) and not self.is_whitelisted(guild, adder):
                    # punish the adder
                    await self.punish(guild, adder, cat.get('action', 'kick'), timeout_seconds=cat.get('timeout_seconds'))
                    # and remove the added bot
                    try:
                        await guild.kick(member, reason='AntiNuke bot add')
                    except Exception:
                        pass
                break
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        # punish mass ban executor
        await self._maybe_punish_audit(guild, discord.AuditLogAction.ban, 'mass_ban', target_id=user.id)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        # Try to detect kick via audit log (users can also leave voluntarily)
        try:
            await self._maybe_punish_audit(member.guild, discord.AuditLogAction.kick, 'mass_kick', target_id=member.id)
        except Exception:
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AntiNuke(bot))


