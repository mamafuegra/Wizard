import discord
from discord.ext import commands
import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Deque, Optional
from collections import deque, defaultdict


CONFIG_FILE = 'automod_config.json'
BOT_OWNER_IDS = {386889350010634252, 164202861356515328}


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


def parse_duration(text: str) -> Optional[timedelta]:
    if not text:
        return None
    try:
        s = text.strip().lower().replace(' ', '')
        # accept forms like 1m, 1h, 1d, 2min, 3hour, 4day, etc.
        m = re.match(r'^(\d+)(s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days)$', s)
        if not m:
            return None
        value = int(m.group(1))
        unit = m.group(2)
        if unit.startswith('s'):
            return timedelta(seconds=value)
        if unit.startswith('m'):
            return timedelta(minutes=value)
        if unit.startswith('h'):
            return timedelta(hours=value)
        if unit.startswith('d'):
            return timedelta(days=value)
    except Exception:
        return None
    return None


def is_second_owner(guild_id: int, user_id: int) -> bool:
    try:
        with open('second_owners.json', 'r') as f:
            data = json.load(f)
        return str(user_id) == data.get(str(guild_id))
    except Exception:
        return False


class AutoMod(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.config = load_config()
        # spam tracker: per guild -> per user -> deque of timestamps
        self._spam_cache: Dict[int, Dict[int, Deque[datetime]]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=20)))
        # message cache for deletion: per guild -> per user -> deque of messages
        self._spam_msg_cache: Dict[int, Dict[int, Deque[discord.Message]]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=20)))
        # tuning constants
        self.default_spam_threshold = 5
        self.default_spam_window_seconds = 7
        self.default_repeat_threshold = 5
        self.default_timeout = timedelta(minutes=10)

    # ---------- permissions ----------
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
        # optional automod mod role
        conf = self.config.get(str(ctx.guild.id)) or {}
        mod_role_id = conf.get('mod_role')
        if mod_role_id:
            role = ctx.guild.get_role(int(mod_role_id))
            if role and role in ctx.author.roles:
                return True
        return False

    # ---------- helpers ----------
    def guild_conf(self, guild_id: int) -> Dict:
        g = str(guild_id)
        self.config.setdefault(g, {})
        self.config[g].setdefault('words', {'enabled': False, 'list': []})
        self.config[g].setdefault('spam', {
            'enabled': False,
            'threshold': self.default_spam_threshold,
            'timeout_seconds': int(self.default_timeout.total_seconds()),
            'delete_max': 50
        })
        self.config[g].setdefault('repeat', {'enabled': False, 'threshold': self.default_repeat_threshold})
        self.config[g].setdefault('bypass_staff', True)
        return self.config[g]

    # ---------- commands group ----------
    @commands.group(name='automod', invoke_without_command=True)
    @commands.guild_only()
    async def automod_group(self, ctx: commands.Context):
        await ctx.send("AutoMod help documentation is available on our website.")

    # ----- words -----
    @automod_group.group(name='words', invoke_without_command=True)
    async def automod_words(self, ctx: commands.Context):
        await ctx.send("Words filter help documentation is available on our website.")

    @automod_words.command(name='enable')
    async def words_enable(self, ctx: commands.Context):
        if not self.can_configure(ctx):
            return
        conf = self.guild_conf(ctx.guild.id)
        conf['words']['enabled'] = True
        save_config(self.config)
        await ctx.message.add_reaction('✅')

    @automod_words.command(name='disable')
    async def words_disable(self, ctx: commands.Context):
        if not self.can_configure(ctx):
            return
        conf = self.guild_conf(ctx.guild.id)
        conf['words']['enabled'] = False
        save_config(self.config)
        await ctx.message.add_reaction('✅')

    @automod_words.command(name='add')
    async def words_add(self, ctx: commands.Context, *, word: str):
        if not self.can_configure(ctx):
            return
        conf = self.guild_conf(ctx.guild.id)
        if not conf['words'].get('enabled'):
            await ctx.send(f"Enable words filter first: `{ctx.prefix}automod words enable`")
            return
        lst = conf['words'].setdefault('list', [])
        w = word.strip().lower()
        if w and w not in lst:
            lst.append(w)
            save_config(self.config)
        await ctx.message.add_reaction('✅')

    @automod_words.command(name='remove')
    async def words_remove(self, ctx: commands.Context, *, word: str):
        if not self.can_configure(ctx):
            return
        conf = self.guild_conf(ctx.guild.id)
        if not conf['words'].get('enabled'):
            await ctx.send(f"Enable words filter first: `{ctx.prefix}automod words enable`")
            return
        lst = conf['words'].setdefault('list', [])
        w = word.strip().lower()
        if w in lst:
            lst.remove(w)
            save_config(self.config)
        await ctx.message.add_reaction('✅')

    @automod_words.command(name='list')
    async def words_list(self, ctx: commands.Context):
        conf = self.guild_conf(ctx.guild.id)
        words = conf['words'].get('list', [])
        shown = ", ".join(words[:50]) if words else "None"
        await ctx.send(f"Blacklist ({len(words)}): {shown}")

    # ----- spam -----
    @automod_group.group(name='spam', invoke_without_command=True)
    async def automod_spam(self, ctx: commands.Context):
        await ctx.send("Spam filter help documentation is available on our website.")

    @automod_spam.command(name='enable')
    async def spam_enable(self, ctx: commands.Context):
        if not self.can_configure(ctx):
            return
        self.guild_conf(ctx.guild.id)['spam']['enabled'] = True
        save_config(self.config)
        await ctx.message.add_reaction('✅')

    @automod_spam.command(name='disable')
    async def spam_disable(self, ctx: commands.Context):
        if not self.can_configure(ctx):
            return
        self.guild_conf(ctx.guild.id)['spam']['enabled'] = False
        save_config(self.config)
        await ctx.message.add_reaction('✅')

    @automod_spam.command(name='rate')
    async def spam_rate(self, ctx: commands.Context, threshold: int):
        if not self.can_configure(ctx):
            return
        if not self.guild_conf(ctx.guild.id)['spam'].get('enabled'):
            await ctx.send(f"Enable spam filter first: `{ctx.prefix}automod spam enable`")
            return
        threshold = max(2, min(50, int(threshold)))
        self.guild_conf(ctx.guild.id)['spam']['threshold'] = threshold
        save_config(self.config)
        await ctx.message.add_reaction('✅')

    @automod_spam.command(name='timeout')
    async def spam_timeout(self, ctx: commands.Context, *, duration: str):
        if not self.can_configure(ctx):
            return
        if not self.guild_conf(ctx.guild.id)['spam'].get('enabled'):
            await ctx.send(f"Enable spam filter first: `{ctx.prefix}automod spam enable`")
            return
        delta = parse_duration(duration)
        if not delta:
            await ctx.send("Provide a valid duration, e.g. 1m, 10m, 2h, 1d")
            return
        self.guild_conf(ctx.guild.id)['spam']['timeout_seconds'] = int(delta.total_seconds())
        save_config(self.config)
        await ctx.message.add_reaction('✅')

    @automod_spam.command(name='set')
    async def spam_set(self, ctx: commands.Context, threshold: int):
        if not self.can_configure(ctx):
            return
        conf = self.guild_conf(ctx.guild.id)
        if not conf['spam'].get('enabled'):
            await ctx.send(f"Enable spam filter first: `{ctx.prefix}automod spam enable`")
            return
        conf['spam']['threshold'] = max(2, min(50, int(threshold)))
        save_config(self.config)
        await ctx.message.add_reaction('✅')

    @automod_spam.command(name='purge')
    async def spam_purge(self, ctx: commands.Context, count: int):
        if not self.can_configure(ctx):
            return
        conf = self.guild_conf(ctx.guild.id)
        if not conf['spam'].get('enabled'):
            await ctx.send(f"Enable spam filter first: `{ctx.prefix}automod spam enable`")
            return
        conf['spam']['delete_max'] = max(1, min(100, int(count)))
        save_config(self.config)
        await ctx.message.add_reaction('✅')

    # convenience: automod spams enable | automod spams <threshold>
    @automod_group.group(name='spams', invoke_without_command=True)
    async def automod_spams(self, ctx: commands.Context, value: Optional[int] = None):
        if value is None:
            await self.automod_spam(ctx)
            return
        if not self.can_configure(ctx):
            return
        conf = self.guild_conf(ctx.guild.id)
        if not conf['spam'].get('enabled'):
            await ctx.send(f"Enable spam filter first: `{ctx.prefix}automod spams enable`")
            return
        conf['spam']['threshold'] = max(2, min(50, int(value)))
        save_config(self.config)
        await ctx.message.add_reaction('✅')

    @automod_spams.command(name='enable')
    async def automod_spams_enable(self, ctx: commands.Context):
        await self.spam_enable(ctx)

    # ----- repeat -----
    @automod_group.group(name='repeat', invoke_without_command=True)
    async def automod_repeat(self, ctx: commands.Context):
        await ctx.send("Repeat filter help documentation is available on our website.")

    @automod_repeat.command(name='enable')
    async def repeat_enable(self, ctx: commands.Context):
        if not self.can_configure(ctx):
            return
        self.guild_conf(ctx.guild.id)['repeat']['enabled'] = True
        save_config(self.config)
        await ctx.message.add_reaction('✅')

    @automod_repeat.command(name='disable')
    async def repeat_disable(self, ctx: commands.Context):
        if not self.can_configure(ctx):
            return
        self.guild_conf(ctx.guild.id)['repeat']['enabled'] = False
        save_config(self.config)
        await ctx.message.add_reaction('✅')

    @automod_repeat.command(name='threshold')
    async def repeat_threshold(self, ctx: commands.Context, value: int):
        if not self.can_configure(ctx):
            return
        conf = self.guild_conf(ctx.guild.id)
        if not conf['repeat'].get('enabled'):
            await ctx.send(f"Enable repeat filter first: `{ctx.prefix}automod repeat enable`")
            return
        conf['repeat']['threshold'] = max(2, min(15, int(value)))
        save_config(self.config)
        await ctx.message.add_reaction('✅')

    # convenience: automod repeats enable | automod repeats <threshold>
    @automod_group.group(name='repeats', invoke_without_command=True)
    async def automod_repeats(self, ctx: commands.Context, value: Optional[int] = None):
        if value is None:
            await self.automod_repeat(ctx)
            return
        if not self.can_configure(ctx):
            return
        conf = self.guild_conf(ctx.guild.id)
        if not conf['repeat'].get('enabled'):
            await ctx.send(f"Enable repeat filter first: `{ctx.prefix}automod repeats enable`")
            return
        conf['repeat']['threshold'] = max(2, min(15, int(value)))
        save_config(self.config)
        await ctx.message.add_reaction('✅')

    @automod_repeats.command(name='enable')
    async def automod_repeats_enable(self, ctx: commands.Context):
        await self.repeat_enable(ctx)

    @automod_group.command(name='mod')
    async def automod_mod(self, ctx: commands.Context, role: discord.Role):
        if not self.can_configure(ctx):
            return
        self.guild_conf(ctx.guild.id)['mod_role'] = role.id
        save_config(self.config)
        await ctx.send(f"✅ Automod moderator set to {role.mention}")

    @automod_group.command(name='bypass')
    async def automod_bypass(self, ctx: commands.Context, state: str):
        if not self.can_configure(ctx):
            return
        val = state.strip().lower() in ("on", "true", "yes", "enable", "enabled", "1")
        self.guild_conf(ctx.guild.id)['bypass_staff'] = val
        save_config(self.config)
        await ctx.message.add_reaction('✅')

    @automod_group.command(name='status')
    async def automod_status(self, ctx: commands.Context):
        conf = self.guild_conf(ctx.guild.id)
        words = conf.get('words', {})
        spam = conf.get('spam', {})
        repeat = conf.get('repeat', {})
        bypass = conf.get('bypass_staff', True)
        try:
            from utils.formatting import quote
        except Exception:
            def quote(t: str) -> str:
                return t
        embed = discord.Embed(title="AutoMod Status", color=0xFFFFFF)
        embed.add_field(name="Words", value=quote(
            f"on — {len(words.get('list', []))} terms" if words.get('enabled') else "off"
        ), inline=False)
        spam_val = (
            f"on — rate {spam.get('threshold', self.default_spam_threshold)}/{self.default_spam_window_seconds}s, "
            f"timeout {spam.get('timeout_seconds', int(self.default_timeout.total_seconds()))}s, "
            f"purge {spam.get('delete_max', 50)}"
            if spam.get('enabled') else "off"
        )
        embed.add_field(name="Spam", value=quote(spam_val), inline=False)
        embed.add_field(name="Repeat", value=quote(
            f"on — threshold {repeat.get('threshold', self.default_repeat_threshold)}" if repeat.get('enabled') else "off"
        ), inline=False)
        embed.add_field(name="Bypass staff", value=quote("on" if bypass else "off"), inline=False)
        await ctx.send(embed=embed)

    # ---------- listeners ----------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        guild = message.guild
        conf = self.guild_conf(guild.id)

        # Staff bypass (configurable)
        try:
            if self.guild_conf(guild.id).get('bypass_staff', True):
                if (message.author.id in BOT_OWNER_IDS or
                    message.author.id == guild.owner_id or
                    message.author.guild_permissions.manage_messages):
                    return
        except Exception:
            pass

        # Words filter
        words_conf = conf.get('words', {})
        if words_conf.get('enabled') and words_conf.get('list'):
            content_lower = message.content.lower()
            for bad in words_conf.get('list', []):
                if bad and bad in content_lower:
                    try:
                        await message.delete()
                    except Exception:
                        pass
                    return

        # Repeat detection: any token repeated >= threshold in a single message
        repeat_conf = conf.get('repeat', {})
        if repeat_conf.get('enabled'):
            threshold = int(repeat_conf.get('threshold', self.default_repeat_threshold))
            try:
                tokens = [t for t in re.split(r"\s+", message.content.strip()) if t]
                counts = defaultdict(int)
                for t in tokens:
                    counts[t.lower()] += 1
                if counts and max(counts.values()) >= threshold:
                    try:
                        await message.delete()
                    except Exception:
                        pass
                    return
            except Exception:
                pass

        # Spam detection: track per-user within fixed window
        spam_conf = conf.get('spam', {})
        if spam_conf.get('enabled'):
            threshold = int(spam_conf.get('threshold', self.default_spam_threshold))
            window = self.default_spam_window_seconds
            now = datetime.now(timezone.utc)
            dq = self._spam_cache[guild.id][message.author.id]
            dq.append(now)
            dq_msgs = self._spam_msg_cache[guild.id][message.author.id]
            dq_msgs.append(message)
            # purge old
            while dq and (now - dq[0]).total_seconds() > window:
                dq.popleft()
            while dq_msgs and (now - dq_msgs[0].created_at).total_seconds() > window:
                dq_msgs.popleft()
            # Debug print to help tune in production if needed
            try:
                print(f"[AutoMod] Spam check guild={guild.id} user={message.author.id} len={len(dq)} threshold={threshold}")
            except Exception:
                pass
            if len(dq) >= threshold:
                # Delete the user's recent messages within the window using cached messages
                recent_msgs = list(dq_msgs)
                # Ensure only messages from this author and channel
                recent_msgs = [m for m in recent_msgs if m.author.id == message.author.id and m.channel.id == message.channel.id]
                # Cap deletion to configured delete_max (default 50)
                delete_cap = int(conf.get('spam', {}).get('delete_max', 50))
                if len(recent_msgs) > delete_cap:
                    recent_msgs = recent_msgs[-delete_cap:]
                if recent_msgs:
                    try:
                        if len(recent_msgs) >= 2:
                            await message.channel.delete_messages(recent_msgs)
                        else:
                            await recent_msgs[0].delete()
                    except Exception:
                        for m in recent_msgs:
                            try:
                                await m.delete()
                            except Exception:
                                pass
                else:
                    try:
                        await message.delete()
                    except Exception:
                        pass

                # Timeout user if configured
                seconds = int(spam_conf.get('timeout_seconds', int(self.default_timeout.total_seconds())))
                if seconds > 0:
                    try:
                        me = guild.me
                        can_mod = False
                        if me:
                            perms = message.channel.permissions_for(me)
                            can_mod = bool(getattr(me.guild_permissions, 'moderate_members', False)) and (message.author.top_role < me.top_role if isinstance(message.author, discord.Member) else True)
                        until = now + timedelta(seconds=seconds)
                        if can_mod:
                            # discord.py expects a positional 'until' argument
                            await message.author.timeout(until, reason=f"AutoMod spam threshold {threshold}/{window}s")
                        else:
                            print(f"[AutoMod] Skip timeout: insufficient permissions or role hierarchy for user={message.author.id}")
                    except Exception as e:
                        try:
                            print(f"[AutoMod] Failed to timeout user={message.author.id}: {e}")
                        except Exception:
                            pass
                # Reset their window to avoid cascading
                dq.clear()
                dq_msgs.clear()
                return


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoMod(bot))


