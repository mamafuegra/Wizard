import discord
from discord.ext import commands
from typing import Dict, Optional
import json
import os
from utils.formatting import quote
from discord.ext import tasks


CONFIG_FILE = 'vanity_config.json'


def load_config() -> Dict:
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(conf: Dict) -> None:
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(conf, f, indent=4)


class Vanity(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.config: Dict = load_config()
        self._vanity_last_sent: Dict[str, float] = {}
        self._booster_last_sent: Dict[str, float] = {}
        self._enforce_vanity_loop.start()

    # ------------------ Helpers ------------------
    @staticmethod
    def _is_guild_owner_or_second_owner(ctx: commands.Context) -> bool:
        if ctx.guild is None:
            return False
        if ctx.author.id == ctx.guild.owner_id:
            return True
        try:
            with open('second_owners.json', 'r') as f:
                data = json.load(f)
            return str(ctx.author.id) == data.get(str(ctx.guild.id))
        except Exception:
            return False

    def _get_guild_conf(self, guild_id: int) -> Dict:
        key = str(guild_id)
        if key not in self.config:
            self.config[key] = {
                'vanity_enabled': False,
                'vanity_role_id': None,
                'vanity_message_match': None,
                'vanity_announce_channel_id': None,
                'vanity_announce_text': None,
                'booster_enabled': False,
                'booster_channel_id': None,
                'booster_text': None,
            }
        return self.config[key]

    def _require_vanity_enabled(self, ctx: commands.Context, conf: Dict) -> bool:
        if conf.get('vanity_enabled'):
            return True
        embed = discord.Embed(title='Vanity not enabled', color=0xFFFFFF)
        embed.description = quote('Please enable vanity first with `{}vanity enable`.'.format(ctx.prefix))
        self.bot.loop.create_task(ctx.send(embed=embed))
        return False

    @staticmethod
    def _reply_embed(ctx: commands.Context, title: str, text: str):
        embed = discord.Embed(title=title, color=0xFFFFFF)
        embed.description = quote(text)
        return ctx.send(embed=embed)

    @staticmethod
    def _extract_custom_status_text(member: discord.Member) -> str:
        texts = []
        for act in getattr(member, 'activities', []) or []:
            try:
                if isinstance(act, discord.CustomActivity) and act.state:
                    texts.append(str(act.state))
            except Exception:
                continue
        return " \n".join(texts)

    # ------------------ Vanity commands ------------------
    @commands.group(name='vanity', invoke_without_command=True)
    @commands.guild_only()
    async def vanity_group(self, ctx: commands.Context) -> None:
        await ctx.send("Vanity help documentation is available on our website.")

    @vanity_group.command(name='enable')
    async def vanity_enable(self, ctx: commands.Context) -> None:
        if not self._is_guild_owner_or_second_owner(ctx):
            await self._reply_embed(ctx, 'Permission required', 'Only the guild owner or second owner can use this.')
            return
        conf = self._get_guild_conf(ctx.guild.id)
        conf['vanity_enabled'] = True
        save_config(self.config)
        await self._reply_embed(ctx, 'Vanity', 'Vanity tracking enabled.')

    @vanity_group.command(name='disable')
    async def vanity_disable(self, ctx: commands.Context) -> None:
        if not self._is_guild_owner_or_second_owner(ctx):
            await self._reply_embed(ctx, 'Permission required', 'Only the guild owner or second owner can use this.')
            return
        conf = self._get_guild_conf(ctx.guild.id)
        conf['vanity_enabled'] = False
        save_config(self.config)
        await self._reply_embed(ctx, 'Vanity', 'Vanity tracking disabled.')

    @vanity_group.command(name='role')
    async def vanity_role(self, ctx: commands.Context, role: discord.Role) -> None:
        if not self._is_guild_owner_or_second_owner(ctx):
            await self._reply_embed(ctx, 'Permission required', 'Only the guild owner or second owner can use this.')
            return
        conf = self._get_guild_conf(ctx.guild.id)
        if not self._require_vanity_enabled(ctx, conf):
            return
        conf['vanity_role_id'] = role.id
        save_config(self.config)
        await self._reply_embed(ctx, 'Vanity', f'Vanity role set to {role.mention}.')

    @vanity_group.group(name='message', invoke_without_command=True)
    async def vanity_message(self, ctx: commands.Context, *, text: Optional[str] = None) -> None:
        if not self._is_guild_owner_or_second_owner(ctx):
            await self._reply_embed(ctx, 'Permission required', 'Only the guild owner or second owner can use this.')
            return
        conf = self._get_guild_conf(ctx.guild.id)
        if not self._require_vanity_enabled(ctx, conf):
            return
        if not text:
            await self._reply_embed(ctx, 'Input required', 'Provide a message to match in user status, e.g. `discord.gg/vanity`.')
            return
        conf['vanity_message_match'] = text
        save_config(self.config)
        await self._reply_embed(ctx, 'Vanity', 'Vanity match message updated.')

    @vanity_message.command(name='send')
    async def vanity_message_send(self, ctx: commands.Context, channel: discord.TextChannel, *, text: str) -> None:
        if not self._is_guild_owner_or_second_owner(ctx):
            await self._reply_embed(ctx, 'Permission required', 'Only the guild owner or second owner can use this.')
            return
        conf = self._get_guild_conf(ctx.guild.id)
        if not self._require_vanity_enabled(ctx, conf):
            return
        conf['vanity_announce_channel_id'] = channel.id
        conf['vanity_announce_text'] = text
        save_config(self.config)
        await self._reply_embed(ctx, 'Vanity', f'Vanity announcement set for {channel.mention}.')

    @vanity_group.command(name='status')
    async def vanity_status(self, ctx: commands.Context) -> None:
        conf = self._get_guild_conf(ctx.guild.id)
        role = ctx.guild.get_role(conf.get('vanity_role_id')) if conf.get('vanity_role_id') else None
        channel = ctx.guild.get_channel(conf.get('vanity_announce_channel_id')) if conf.get('vanity_announce_channel_id') else None
        embed = discord.Embed(title='Vanity Status', color=0xFFFFFF)
        embed.add_field(name='Enabled', value=str(conf.get('vanity_enabled')), inline=True)
        embed.add_field(name='Role', value=(role.mention if role else 'None'), inline=True)
        embed.add_field(name='Announce Channel', value=(channel.mention if channel else 'None'), inline=True)
        message_match = conf.get('vanity_message_match') or 'None'
        embed.add_field(name='Match Text', value=quote(message_match), inline=False)
        announce_text = conf.get('vanity_announce_text') or 'None'
        embed.add_field(name='Announce Text', value=quote(announce_text), inline=False)
        await ctx.send(embed=embed)

    # ------------------ Booster commands ------------------
    @commands.group(name='booster', invoke_without_command=True)
    @commands.guild_only()
    async def booster_group(self, ctx: commands.Context) -> None:
        await ctx.send("Booster help documentation is available on our website.")

    @booster_group.command(name='enable')
    async def booster_enable(self, ctx: commands.Context) -> None:
        if not self._is_guild_owner_or_second_owner(ctx):
            await self._reply_embed(ctx, 'Permission required', 'Only the guild owner or second owner can use this.')
            return
        conf = self._get_guild_conf(ctx.guild.id)
        conf['booster_enabled'] = True
        save_config(self.config)
        await self._reply_embed(ctx, 'Booster', 'Booster messages enabled.')

    @booster_group.command(name='disable')
    async def booster_disable(self, ctx: commands.Context) -> None:
        if not self._is_guild_owner_or_second_owner(ctx):
            await self._reply_embed(ctx, 'Permission required', 'Only the guild owner or second owner can use this.')
            return
        conf = self._get_guild_conf(ctx.guild.id)
        conf['booster_enabled'] = False
        save_config(self.config)
        await self._reply_embed(ctx, 'Booster', 'Booster messages disabled.')

    @booster_group.command(name='message')
    async def booster_message(self, ctx: commands.Context, channel: discord.TextChannel, *, text: str) -> None:
        if not self._is_guild_owner_or_second_owner(ctx):
            await self._reply_embed(ctx, 'Permission required', 'Only the guild owner or second owner can use this.')
            return
        conf = self._get_guild_conf(ctx.guild.id)
        if not conf.get('booster_enabled'):
            embed = discord.Embed(title='Booster not enabled', color=0xFFFFFF)
            embed.description = quote('Please enable booster first with `{}booster enable`.'.format(ctx.prefix))
            await ctx.send(embed=embed)
            return
        conf['booster_channel_id'] = channel.id
        conf['booster_text'] = text
        save_config(self.config)
        await self._reply_embed(ctx, 'Booster', f'Booster message set for {channel.mention}.')

    @booster_group.command(name='status')
    async def booster_status(self, ctx: commands.Context) -> None:
        conf = self._get_guild_conf(ctx.guild.id)
        channel = ctx.guild.get_channel(conf.get('booster_channel_id')) if conf.get('booster_channel_id') else None
        embed = discord.Embed(title='Booster Status', color=0xFFFFFF)
        embed.add_field(name='Enabled', value=str(conf.get('booster_enabled')), inline=True)
        embed.add_field(name='Channel', value=(channel.mention if channel else 'None'), inline=True)
        text = conf.get('booster_text') or 'None'
        embed.add_field(name='Message', value=quote(text), inline=False)
        await ctx.send(embed=embed)

    # ------------------ Listeners ------------------
    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member) -> None:  # type: ignore[override]
        # Vanity: give role if custom status contains the configured text
        if after.guild is None:
            return
        conf = self._get_guild_conf(after.guild.id)
        if not conf.get('vanity_enabled'):
            return
        target_text = (conf.get('vanity_message_match') or '').strip()
        role_id = conf.get('vanity_role_id')
        if not target_text or not role_id:
            return
        role = after.guild.get_role(role_id)
        if role is None:
            return
        # Only fire when transitioning from not-matching to matching to avoid duplicates
        before_text = self._extract_custom_status_text(before).lower()
        after_text = self._extract_custom_status_text(after).lower()
        if not after_text:
            return
        if (target_text.lower() in after_text) and (target_text.lower() not in before_text):
            # Debounce per user for 30 seconds
            key = f"{after.guild.id}:{after.id}"
            import time
            now = time.monotonic()
            last = self._vanity_last_sent.get(key, 0)
            if now - last < 30:
                return
            self._vanity_last_sent[key] = now
            try:
                if role not in after.roles:
                    await after.add_roles(role, reason='Vanity status matched')
            except discord.Forbidden:
                pass
            # Send confirmation message if configured
            channel_id = conf.get('vanity_announce_channel_id')
            text_tmpl = conf.get('vanity_announce_text')
            if channel_id and text_tmpl:
                channel = after.guild.get_channel(channel_id)
                if isinstance(channel, (discord.TextChannel, discord.Thread)):
                    try:
                        await channel.send(text_tmpl.replace('{user.mention}', after.mention))
                    except Exception:
                        pass
        elif (target_text.lower() not in after_text) and role in after.roles:
            # User removed the vanity string; remove the role silently
            try:
                await after.remove_roles(role, reason='Vanity status removed')
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        # Booster: send message when a member starts boosting
        if after.guild is None:
            return
        conf = self._get_guild_conf(after.guild.id)
        if not conf.get('booster_enabled'):
            return
        if getattr(before, 'premium_since', None) is None and getattr(after, 'premium_since', None) is not None:
            # Debounce per user for 60 seconds
            key = f"boost:{after.guild.id}:{after.id}"
            import time
            now = time.monotonic()
            last = self._booster_last_sent.get(key, 0)
            if now - last < 60:
                return
            self._booster_last_sent[key] = now
            channel_id = conf.get('booster_channel_id')
            text_tmpl = conf.get('booster_text')
            if channel_id and text_tmpl:
                channel = after.guild.get_channel(channel_id)
                if isinstance(channel, (discord.TextChannel, discord.Thread)):
                    try:
                        await channel.send(text_tmpl.replace('{user.mention}', after.mention))
                    except Exception:
                        pass

    # Background enforcement to remove vanity role quickly if message is removed
    @tasks.loop(seconds=10)
    async def _enforce_vanity_loop(self):
        for guild in list(self.bot.guilds):
            conf = self._get_guild_conf(guild.id)
            if not conf.get('vanity_enabled'):
                continue
            role_id = conf.get('vanity_role_id')
            match_text = (conf.get('vanity_message_match') or '').lower().strip()
            if not role_id or not match_text:
                continue
            role = guild.get_role(role_id)
            if role is None:
                continue
            for member in list(role.members):
                status_text = self._extract_custom_status_text(member).lower()
                if match_text not in status_text:
                    try:
                        await member.remove_roles(role, reason='Vanity status no longer matches')
                    except Exception:
                        pass

    @_enforce_vanity_loop.before_loop
    async def _wait_for_ready(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Vanity(bot))


