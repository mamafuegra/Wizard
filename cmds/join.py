import discord
from discord.ext import commands
from typing import Dict, List
import json
import os
from utils.formatting import quote


CONFIG_FILE = 'join_config.json'


def load_config() -> Dict:
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(data: Dict) -> None:
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)


def is_second_owner(guild_id: int, user_id: int) -> bool:
    try:
        with open('second_owners.json', 'r') as f:
            data = json.load(f)
        return str(user_id) == data.get(str(guild_id))
    except Exception:
        return False


def is_owner_or_sso(ctx: commands.Context) -> bool:
    if ctx.guild is None:
        return False
    if ctx.author.id == ctx.guild.owner_id:
        return True
    if ctx.author.guild_permissions.administrator:
        return True
    if is_second_owner(ctx.guild.id, ctx.author.id):
        return True
    return False


class JoinRoles(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.config: Dict = load_config()

    # --------------- helpers ---------------
    def _guild_conf(self, guild_id: int) -> Dict:
        key = str(guild_id)
        if key not in self.config:
            self.config[key] = {
                'human_enabled': False,
                'bot_enabled': False,
                'human_role_ids': [],
                'bot_role_ids': [],
            }
        return self.config[key]

    @staticmethod
    async def _reply(ctx: commands.Context, title: str, desc: str) -> None:
        embed = discord.Embed(title=title, color=0xFFFFFF)
        embed.description = quote(desc)
        await ctx.send(embed=embed)

    # --------------- commands ---------------
    @commands.group(name='join', invoke_without_command=True)
    @commands.guild_only()
    async def join_group(self, ctx: commands.Context) -> None:
        await self._reply(ctx, 'Join', "Join help documentation is available on our website.")

    @join_group.group(name='human', invoke_without_command=True)
    async def join_human(self, ctx: commands.Context) -> None:
        await self._reply(ctx, 'Join', "Join help documentation is available on our website.")

    @join_human.command(name='add')
    async def join_human_add(self, ctx: commands.Context, *, roles: commands.Greedy[discord.Role]):
        if not is_owner_or_sso(ctx):
            await self._reply(ctx, 'Permission required', 'Only Admins, Guild Owner, or Second Owner can use this.')
            return
        if not roles:
            await self._reply(ctx, 'Join', 'Mention one or more roles to add.')
            return
        conf = self._guild_conf(ctx.guild.id)
        conf['human_enabled'] = True
        for role in roles:
            if role.id not in conf['human_role_ids']:
                conf['human_role_ids'].append(role.id)
        save_config(self.config)
        names = ", ".join(r.mention for r in roles)
        await self._reply(ctx, 'Join', f'Human join roles updated: {names}')

    @join_human.command(name='remove')
    async def join_human_remove(self, ctx: commands.Context, *, roles: commands.Greedy[discord.Role]):
        if not is_owner_or_sso(ctx):
            await self._reply(ctx, 'Permission required', 'Only Admins, Guild Owner, or Second Owner can use this.')
            return
        if not roles:
            await self._reply(ctx, 'Join', 'Mention one or more roles to remove.')
            return
        conf = self._guild_conf(ctx.guild.id)
        conf['human_role_ids'] = [rid for rid in conf['human_role_ids'] if rid not in {r.id for r in roles}]
        save_config(self.config)
        names = ", ".join(r.mention for r in roles)
        await self._reply(ctx, 'Join', f'Removed from human join: {names}')

    @join_human.command(name='disable')
    async def join_human_disable(self, ctx: commands.Context):
        if not is_owner_or_sso(ctx):
            await self._reply(ctx, 'Permission required', 'Only Admins, Guild Owner, or Second Owner can use this.')
            return
        conf = self._guild_conf(ctx.guild.id)
        conf['human_enabled'] = False
        save_config(self.config)
        await self._reply(ctx, 'Join', 'Human join roles disabled.')

    @join_group.group(name='bot', invoke_without_command=True)
    async def join_bot(self, ctx: commands.Context) -> None:
        await self._reply(ctx, 'Join', "Join help documentation is available on our website.")

    @join_bot.command(name='add')
    async def join_bot_add(self, ctx: commands.Context, *, roles: commands.Greedy[discord.Role]):
        if not is_owner_or_sso(ctx):
            await self._reply(ctx, 'Permission required', 'Only Admins, Guild Owner, or Second Owner can use this.')
            return
        if not roles:
            await self._reply(ctx, 'Join', 'Mention one or more roles to add.')
            return
        conf = self._guild_conf(ctx.guild.id)
        conf['bot_enabled'] = True
        for role in roles:
            if role.id not in conf['bot_role_ids']:
                conf['bot_role_ids'].append(role.id)
        save_config(self.config)
        names = ", ".join(r.mention for r in roles)
        await self._reply(ctx, 'Join', f'Bot join roles updated: {names}')

    @join_bot.command(name='remove')
    async def join_bot_remove(self, ctx: commands.Context, *, roles: commands.Greedy[discord.Role]):
        if not is_owner_or_sso(ctx):
            await self._reply(ctx, 'Permission required', 'Only Admins, Guild Owner, or Second Owner can use this.')
            return
        if not roles:
            await self._reply(ctx, 'Join', 'Mention one or more roles to remove.')
            return
        conf = self._guild_conf(ctx.guild.id)
        conf['bot_role_ids'] = [rid for rid in conf['bot_role_ids'] if rid not in {r.id for r in roles}]
        save_config(self.config)
        names = ", ".join(r.mention for r in roles)
        await self._reply(ctx, 'Join', f'Removed from bot join: {names}')

    @join_bot.command(name='disable')
    async def join_bot_disable(self, ctx: commands.Context):
        if not is_owner_or_sso(ctx):
            await self._reply(ctx, 'Permission required', 'Only Admins, Guild Owner, or Second Owner can use this.')
            return
        conf = self._guild_conf(ctx.guild.id)
        conf['bot_enabled'] = False
        save_config(self.config)
        await self._reply(ctx, 'Join', 'Bot join roles disabled.')

    @join_group.command(name='status')
    async def join_status(self, ctx: commands.Context):
        conf = self._guild_conf(ctx.guild.id)
        embed = discord.Embed(title='Join Status', color=0xFFFFFF)
        human_roles = [ctx.guild.get_role(rid) for rid in conf.get('human_role_ids', [])]
        bot_roles = [ctx.guild.get_role(rid) for rid in conf.get('bot_role_ids', [])]
        embed.add_field(name='Human enabled', value=str(conf.get('human_enabled')), inline=True)
        embed.add_field(name='Bot enabled', value=str(conf.get('bot_enabled')), inline=True)
        embed.add_field(name='Human roles', value=quote(" ".join(r.mention for r in human_roles if r) or 'None'), inline=False)
        embed.add_field(name='Bot roles', value=quote(" ".join(r.mention for r in bot_roles if r) or 'None'), inline=False)
        await ctx.send(embed=embed)

    # --------------- listener ---------------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild is None:
            return
        conf = self._guild_conf(member.guild.id)
        if member.bot:
            if not conf.get('bot_enabled'):
                return
            role_ids: List[int] = conf.get('bot_role_ids', [])
        else:
            if not conf.get('human_enabled'):
                return
            role_ids = conf.get('human_role_ids', [])
        roles = [member.guild.get_role(rid) for rid in role_ids]
        roles = [r for r in roles if r is not None]
        if not roles:
            return
        try:
            await member.add_roles(*roles, reason='Auto join roles')
        except discord.Forbidden:
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(JoinRoles(bot))


