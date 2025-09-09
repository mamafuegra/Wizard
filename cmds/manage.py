import discord
from discord.ext import commands
from typing import Optional, Union
from utils.formatting import quote


def is_second_owner(guild_id: int, user_id: int) -> bool:
    import json
    try:
        with open('second_owners.json', 'r') as f:
            data = json.load(f)
        return str(user_id) == data.get(str(guild_id))
    except Exception:
        return False


def is_admin_owner_or_sso(ctx: commands.Context) -> bool:
    if ctx.guild is None:
        return False
    if ctx.author.id == ctx.guild.owner_id:
        return True
    if ctx.author.guild_permissions.administrator:
        return True
    if is_second_owner(ctx.guild.id, ctx.author.id):
        return True
    return False


class Manage(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ------------- Core helpers -------------
    @staticmethod
    def _target_channel(ctx: commands.Context, channel: Optional[Union[discord.TextChannel, discord.VoiceChannel]]) -> Optional[Union[discord.TextChannel, discord.VoiceChannel]]:
        if channel is not None:
            return channel
        if isinstance(ctx.channel, (discord.TextChannel, discord.VoiceChannel)):
            return ctx.channel
        return None

    @staticmethod
    async def _reply(ctx: commands.Context, title: str, message: str) -> None:
        embed = discord.Embed(title=title, color=0xFFFFFF)
        embed.description = quote(message)
        await ctx.send(embed=embed)

    # Hide: make @everyone cannot view the channel
    @commands.command(name='hide', help='Hide a text or voice channel from everyone. Usage: !hide [#channel] or !hide (current channel)')
    @commands.guild_only()
    async def hide(self, ctx: commands.Context, channel: Optional[Union[discord.TextChannel, discord.VoiceChannel]] = None) -> None:
        if not is_admin_owner_or_sso(ctx):
            await self._reply(ctx, 'Permission required', 'Only Admins, Guild Owner, or Second Owner can use this.')
            return
        target = self._target_channel(ctx, channel)
        if target is None:
            await self._reply(ctx, 'Channel required', 'Provide a text or voice channel to hide. Usage: !hide #channel or !hide (current channel)')
            return
        overwrites = target.overwrites_for(ctx.guild.default_role)
        overwrites.view_channel = False
        try:
            await target.set_permissions(ctx.guild.default_role, overwrite=overwrites, reason=f'Hide by {ctx.author}')
            await self._reply(ctx, 'Channel hidden', f'Hidden {target.mention} from everyone.')
        except discord.Forbidden:
            await self._reply(ctx, 'Missing permission', 'I lack permission to edit channel permissions.')

    # Unhide: allow @everyone to view the channel
    @commands.command(name='unhide', help='Unhide a text or voice channel for everyone. Usage: !unhide [#channel] or !unhide (current channel)')
    @commands.guild_only()
    async def unhide(self, ctx: commands.Context, channel: Optional[Union[discord.TextChannel, discord.VoiceChannel]] = None) -> None:
        if not is_admin_owner_or_sso(ctx):
            await self._reply(ctx, 'Permission required', 'Only Admins, Guild Owner, or Second Owner can use this.')
            return
        target = self._target_channel(ctx, channel)
        if target is None:
            await self._reply(ctx, 'Channel required', 'Provide a text or voice channel to unhide. Usage: !unhide #channel or !unhide (current channel)')
            return
        overwrites = target.overwrites_for(ctx.guild.default_role)
        overwrites.view_channel = True
        try:
            await target.set_permissions(ctx.guild.default_role, overwrite=overwrites, reason=f'Unhide by {ctx.author}')
            await self._reply(ctx, 'Channel unhidden', f'Unhidden {target.mention}.')
        except discord.Forbidden:
            await self._reply(ctx, 'Missing permission', 'I lack permission to edit channel permissions.')

    # Lock: block @everyone from sending messages (text channels) or connecting (voice channels)
    @commands.command(name='lock', help='Lock a text or voice channel. Text: blocks messages, Voice: blocks connections. Usage: !lock [#channel] or !lock (current channel)')
    @commands.guild_only()
    async def lock(self, ctx: commands.Context, channel: Optional[Union[discord.TextChannel, discord.VoiceChannel]] = None) -> None:
        if not is_admin_owner_or_sso(ctx):
            await self._reply(ctx, 'Permission required', 'Only Admins, Guild Owner, or Second Owner can use this.')
            return
        target = self._target_channel(ctx, channel)
        if target is None:
            await self._reply(ctx, 'Channel required', 'Provide a text or voice channel to lock. Usage: !lock #channel or !lock (current channel)')
            return
        overwrites = target.overwrites_for(ctx.guild.default_role)
        
        if isinstance(target, discord.TextChannel):
            overwrites.send_messages = False
            action = "sending messages"
        else:  # Voice channel
            overwrites.connect = False
            action = "connecting"
            
        try:
            await target.set_permissions(ctx.guild.default_role, overwrite=overwrites, reason=f'Lock by {ctx.author}')
            await self._reply(ctx, 'Channel locked', f'Locked {target.mention} from {action}.')
        except discord.Forbidden:
            await self._reply(ctx, 'Missing permission', 'I lack permission to edit channel permissions.')

    # Unlock: allow @everyone to send messages (text channels) or connect (voice channels)
    @commands.command(name='unlock', help='Unlock a text or voice channel. Text: allows messages, Voice: allows connections. Usage: !unlock [#channel] or !unlock (current channel)')
    @commands.guild_only()
    async def unlock(self, ctx: commands.Context, channel: Optional[Union[discord.TextChannel, discord.VoiceChannel]] = None) -> None:
        if not is_admin_owner_or_sso(ctx):
            await self._reply(ctx, 'Permission required', 'Only Admins, Guild Owner, or Second Owner can use this.')
            return
        target = self._target_channel(ctx, channel)
        if target is None:
            await self._reply(ctx, 'Channel required', 'Provide a text or voice channel to unlock. Usage: !unlock #channel or !unlock (current channel)')
            return
        overwrites = target.overwrites_for(ctx.guild.default_role)
        
        if isinstance(target, discord.TextChannel):
            overwrites.send_messages = True
            action = "sending messages"
        else:  # Voice channel
            overwrites.connect = True
            action = "connecting"
            
        try:
            await target.set_permissions(ctx.guild.default_role, overwrite=overwrites, reason=f'Unlock by {ctx.author}')
            await self._reply(ctx, 'Channel unlocked', f'Unlocked {target.mention} for {action}.')
        except discord.Forbidden:
            await self._reply(ctx, 'Missing permission', 'I lack permission to edit channel permissions.')


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Manage(bot))


