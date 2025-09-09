import discord
from discord.ext import commands
import json
import asyncio
from typing import Optional, Union

# JSK compatibility is handled in owner_tools.py


def is_second_owner(guild_id: int, user_id: int) -> bool:
    """Check if user is a second owner of the guild."""
    try:
        with open('second_owners.json', 'r') as f:
            data = json.load(f)
        return str(user_id) == data.get(str(guild_id))
    except Exception:
        return False


class RoleManagement(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def is_admin_owner_or_sso(self, ctx: commands.Context) -> bool:
        """Check if user has permission to use role commands."""
        if ctx.guild is None:
            return False
        if ctx.author.id == ctx.guild.owner_id:
            return True
        if ctx.author.guild_permissions.administrator:
            return True
        if is_second_owner(ctx.guild.id, ctx.author.id):
            return True
        return False

    @commands.group(name='role', aliases=['r'])
    @commands.guild_only()
    async def role_group(self, ctx: commands.Context):
        """Role management commands."""
        if ctx.invoked_subcommand is None:
            await ctx.send("Use `role all @role/ID`, `role human @role/ID`, `role bot @role/ID`, `role remove all @role/ID`, `role remove human @role/ID`, or `role remove bot @role/ID`")

    @role_group.command(name='all')
    @commands.guild_only()
    async def role_all(self, ctx: commands.Context, role: Union[discord.Role, str]):
        """Give a role to all members in the server."""
        if not self.is_admin_owner_or_sso(ctx):
            await ctx.send("Only Guild Owner, Second Owner, or Administrators can use this command.")
            return

        # Handle role ID if string is provided
        if isinstance(role, str):
            try:
                role_id = int(role)
                role = ctx.guild.get_role(role_id)
                if role is None:
                    await ctx.send("Role not found. Please provide a valid role mention or ID.")
                    return
            except ValueError:
                await ctx.send("Invalid role format. Please provide a valid role mention or ID.")
                return

        if role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            await ctx.send("You cannot assign a role higher than or equal to your highest role.")
            return

        if role.managed:
            await ctx.send("Cannot assign managed roles (bot or integration roles).")
            return

        # Check if bot has permission to manage the role
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send("I don't have permission to manage roles.")
            return

        if role >= ctx.guild.me.top_role:
            await ctx.send("I cannot assign a role higher than or equal to my highest role.")
            return

        members = ctx.guild.members
        total_members = len(members)
        success_count = 0
        failed_count = 0

        embed = discord.Embed(
            title="Role Assignment in Progress",
            description=f"Adding role {role.mention} to all members...",
            color=0xFFFFFF  # White hex color
        )
        embed.add_field(name="Progress", value=f"0/{total_members}", inline=True)
        embed.add_field(name="Status", value="Processing...", inline=True)
        embed.set_footer(text="Role Management System", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        
        progress_msg = await ctx.send(embed=embed)

        for i, member in enumerate(members, 1):
            try:
                if role not in member.roles:
                    await member.add_roles(role, reason=f"Role command by {ctx.author}")
                    success_count += 1
                else:
                    # Member already has the role
                    pass
                
                # Update progress every 10 members or at the end
                if i % 10 == 0 or i == total_members:
                    embed.description = f"Adding role {role.mention} to all members..."
                    embed.set_field_at(0, name="Progress", value=f"{i}/{total_members}", inline=True)
                    embed.set_field_at(1, name="Status", value="Processing...", inline=True)
                    await progress_msg.edit(embed=embed)
                    await asyncio.sleep(0.1)  # Small delay to prevent rate limiting
                    
            except discord.Forbidden:
                failed_count += 1
            except discord.HTTPException:
                failed_count += 1

        # Final result embed
        result_embed = discord.Embed(
            title="Role Assignment Complete",
            description=f"Role {role.mention} has been processed for all members",
            color=0xFFFFFF  # White hex color
        )
        result_embed.add_field(name="Successfully Added", value=f"**{success_count}** members", inline=True)
        result_embed.add_field(name="Failed", value=f"**{failed_count}** members", inline=True)
        result_embed.add_field(name="Total Processed", value=f"**{total_members}** members", inline=False)
        result_embed.set_footer(text="Role Management System", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        
        await progress_msg.edit(embed=result_embed)

    @role_group.command(name='human')
    @commands.guild_only()
    async def role_human(self, ctx: commands.Context, role: Union[discord.Role, str]):
        """Give a role to all human members in the server."""
        if not self.is_admin_owner_or_sso(ctx):
            await ctx.send("Only Guild Owner, Second Owner, or Administrators can use this command.")
            return

        # Handle role ID if string is provided
        if isinstance(role, str):
            try:
                role_id = int(role)
                role = ctx.guild.get_role(role_id)
                if role is None:
                    await ctx.send("Role not found. Please provide a valid role mention or ID.")
                    return
            except ValueError:
                await ctx.send("Invalid role format. Please provide a valid role mention or ID.")
                return

        if role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            await ctx.send("You cannot assign a role higher than or equal to your highest role.")
            return

        if role.managed:
            await ctx.send("Cannot assign managed roles (bot or integration roles).")
            return

        # Check if bot has permission to manage the role
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send("I don't have permission to manage roles.")
            return

        if role >= ctx.guild.me.top_role:
            await ctx.send("I cannot assign a role higher than or equal to my highest role.")
            return

        # Filter for human members only
        members = [m for m in ctx.guild.members if not m.bot]
        total_members = len(members)
        if total_members == 0:
            await ctx.send("No human members found in this server.")
            return

        success_count = 0
        failed_count = 0

        embed = discord.Embed(
            title="Role Assignment in Progress",
            description=f"Adding role {role.mention} to all human members...",
            color=0xFFFFFF  # White hex color
        )
        embed.add_field(name="Progress", value=f"0/{total_members}", inline=True)
        embed.add_field(name="Status", value="Processing...", inline=True)
        embed.add_field(name="Target", value="Human members", inline=True)
        embed.set_footer(text="Role Management System", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        
        progress_msg = await ctx.send(embed=embed)

        for i, member in enumerate(members, 1):
            try:
                if role not in member.roles:
                    await member.add_roles(role, reason=f"Role command by {ctx.author}")
                    success_count += 1
                else:
                    # Member already has the role
                    pass
                
                # Update progress every 10 members or at the end
                if i % 10 == 0 or i == total_members:
                    embed.description = f"Adding role {role.mention} to all human members..."
                    embed.set_field_at(0, name="Progress", value=f"{i}/{total_members}", inline=True)
                    embed.set_field_at(1, name="Status", value="Processing...", inline=True)
                    await progress_msg.edit(embed=embed)
                    await asyncio.sleep(0.1)  # Small delay to prevent rate limiting
                    
            except discord.Forbidden:
                failed_count += 1
            except discord.HTTPException:
                failed_count += 1

        # Final result embed
        result_embed = discord.Embed(
            title="Role Assignment Complete",
            description=f"Role {role.mention} has been processed for all human members",
            color=0xFFFFFF  # White hex color
        )
        result_embed.add_field(name="Successfully Added", value=f"**{success_count}** human members", inline=True)
        result_embed.add_field(name="Failed", value=f"**{failed_count}** human members", inline=True)
        result_embed.add_field(name="Total Processed", value=f"**{total_members}** human members", inline=False)
        result_embed.set_footer(text="Role Management System", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        
        await progress_msg.edit(embed=result_embed)

    @role_group.command(name='bot')
    @commands.guild_only()
    async def role_bot(self, ctx: commands.Context, role: Union[discord.Role, str]):
        """Give a role to all bot members in the server."""
        if not self.is_admin_owner_or_sso(ctx):
            await ctx.send("Only Guild Owner, Second Owner, or Administrators can use this command.")
            return

        # Handle role ID if string is provided
        if isinstance(role, str):
            try:
                role_id = int(role)
                role = ctx.guild.get_role(role_id)
                if role is None:
                    await ctx.send("Role not found. Please provide a valid role mention or ID.")
                    return
            except ValueError:
                await ctx.send("Invalid role format. Please provide a valid role mention or ID.")
                return

        if role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            await ctx.send("You cannot assign a role higher than or equal to your highest role.")
            return

        if role.managed:
            await ctx.send("Cannot assign managed roles (bot or integration roles).")
            return

        # Check if bot has permission to manage the role
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send("I don't have permission to manage roles.")
            return

        if role >= ctx.guild.me.top_role:
            await ctx.send("I cannot assign a role higher than or equal to my highest role.")
            return

        # Filter for bot members only
        members = [m for m in ctx.guild.members if m.bot]
        total_members = len(members)
        if total_members == 0:
            await ctx.send("No bot members found in this server.")
            return

        success_count = 0
        failed_count = 0

        embed = discord.Embed(
            title="Role Assignment in Progress",
            description=f"Adding role {role.mention} to all bot members...",
            color=0xFFFFFF  # White hex color
        )
        embed.add_field(name="Progress", value=f"0/{total_members}", inline=True)
        embed.add_field(name="Status", value="Processing...", inline=True)
        embed.add_field(name="Target", value="Bot members", inline=True)
        embed.set_footer(text="Role Management System", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        
        progress_msg = await ctx.send(embed=embed)

        for i, member in enumerate(members, 1):
            try:
                if role not in member.roles:
                    await member.add_roles(role, reason=f"Role command by {ctx.author}")
                    success_count += 1
                else:
                    # Member already has the role
                    pass
                
                # Update progress every 10 members or at the end
                if i % 10 == 0 or i == total_members:
                    embed.description = f"Adding role {role.mention} to all bot members..."
                    embed.set_field_at(0, name="Progress", value=f"{i}/{total_members}", inline=True)
                    embed.set_field_at(1, name="Status", value="Processing...", inline=True)
                    await progress_msg.edit(embed=embed)
                    await asyncio.sleep(0.1)  # Small delay to prevent rate limiting
                    
            except discord.Forbidden:
                failed_count += 1
            except discord.HTTPException:
                failed_count += 1

        # Final result embed
        result_embed = discord.Embed(
            title="Role Assignment Complete",
            description=f"Role {role.mention} has been processed for all bot members",
            color=0xFFFFFF  # White hex color
        )
        result_embed.add_field(name="Successfully Added", value=f"**{success_count}** bot members", inline=True)
        result_embed.add_field(name="Failed", value=f"**{failed_count}** bot members", inline=True)
        result_embed.add_field(name="Total Processed", value=f"**{total_members}** bot members", inline=False)
        result_embed.set_footer(text="Role Management System", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        
        await progress_msg.edit(embed=result_embed)

    @role_group.group(name='remove')
    @commands.guild_only()
    async def role_remove(self, ctx: commands.Context):
        """Remove role management commands."""
        if ctx.invoked_subcommand is None:
            await ctx.send("Use `role remove all @role`, `role remove all human @role`, or `role remove all bot @role`")

    @role_remove.command(name='all')
    @commands.guild_only()
    async def role_remove_all(self, ctx: commands.Context, role: Union[discord.Role, str]):
        """Remove a role from all members in the server."""
        if not self.is_admin_owner_or_sso(ctx):
            await ctx.send("Only Guild Owner, Second Owner, or Administrators can use this command.")
            return

        # Handle role ID if string is provided
        if isinstance(role, str):
            try:
                role_id = int(role)
                role = ctx.guild.get_role(role_id)
                if role is None:
                    await ctx.send("Role not found. Please provide a valid role mention or ID.")
                    return
            except ValueError:
                await ctx.send("Invalid role format. Please provide a valid role mention or ID.")
                return

        if role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            await ctx.send("You cannot remove a role higher than or equal to your highest role.")
            return

        if role.managed:
            await ctx.send("Cannot remove managed roles (bot or integration roles).")
            return

        # Check if bot has permission to manage the role
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send("I don't have permission to manage roles.")
            return

        if role >= ctx.guild.me.top_role:
            await ctx.send("I cannot remove a role higher than or equal to my highest role.")
            return

        members = [m for m in ctx.guild.members if role in m.roles]
        total_members = len(members)
        
        if total_members == 0:
            await ctx.send(f"No members currently have the role {role.mention}.")
            return

        success_count = 0
        failed_count = 0

        embed = discord.Embed(
            title="Role Removal in Progress",
            description=f"Removing role {role.mention} from all members...",
            color=0xFFFFFF  # White hex color
        )
        embed.add_field(name="Progress", value=f"0/{total_members}", inline=True)
        embed.add_field(name="Status", value="Processing...", inline=True)
        embed.set_footer(text="Role Management System", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        
        progress_msg = await ctx.send(embed=embed)

        for i, member in enumerate(members, 1):
            try:
                await member.remove_roles(role, reason=f"Role removal command by {ctx.author}")
                success_count += 1
                
                # Update progress every 10 members or at the end
                if i % 10 == 0 or i == total_members:
                    embed.description = f"Removing role {role.mention} from all members..."
                    embed.set_field_at(0, name="Progress", value=f"{i}/{total_members}", inline=True)
                    embed.set_field_at(1, name="Status", value="Processing...", inline=True)
                    await progress_msg.edit(embed=embed)
                    await asyncio.sleep(0.1)  # Small delay to prevent rate limiting
                    
            except discord.Forbidden:
                failed_count += 1
            except discord.HTTPException:
                failed_count += 1

        # Final result embed
        result_embed = discord.Embed(
            title="Role Removal Complete",
            description=f"Role {role.mention} has been removed from all members",
            color=0xFFFFFF  # White hex color
        )
        result_embed.add_field(name="Successfully Removed", value=f"**{success_count}** members", inline=True)
        result_embed.add_field(name="Failed", value=f"**{failed_count}** members", inline=True)
        result_embed.add_field(name="Total Processed", value=f"**{total_members}** members", inline=False)
        result_embed.set_footer(text="Role Management System", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        
        await progress_msg.edit(embed=result_embed)

    @role_remove.command(name='human')
    @commands.guild_only()
    async def role_remove_human(self, ctx: commands.Context, role: Union[discord.Role, str]):
        """Remove a role from all human members in the server."""
        if not self.is_admin_owner_or_sso(ctx):
            await ctx.send("Only Guild Owner, Second Owner, or Administrators can use this command.")
            return

        # Handle role ID if string is provided
        if isinstance(role, str):
            try:
                role_id = int(role)
                role = ctx.guild.get_role(role_id)
                if role is None:
                    await ctx.send("Role not found. Please provide a valid role mention or ID.")
                    return
            except ValueError:
                await ctx.send("Invalid role format. Please provide a valid role mention or ID.")
                return

        if role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            await ctx.send("You cannot remove a role higher than or equal to your highest role.")
            return

        if role.managed:
            await ctx.send("Cannot remove managed roles (bot or integration roles).")
            return

        # Check if bot has permission to manage the role
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send("I don't have permission to manage roles.")
            return

        if role >= ctx.guild.me.top_role:
            await ctx.send("I cannot remove a role higher than or equal to my highest role.")
            return

        # Filter for human members only who have the role
        members = [m for m in ctx.guild.members if not m.bot and role in m.roles]
        total_members = len(members)
        
        if total_members == 0:
            await ctx.send(f"No human members currently have the role {role.mention}.")
            return

        success_count = 0
        failed_count = 0

        embed = discord.Embed(
            title="Role Removal in Progress",
            description=f"Removing role {role.mention} from all human members...",
            color=0xFFFFFF  # White hex color
        )
        embed.add_field(name="Progress", value=f"0/{total_members}", inline=True)
        embed.add_field(name="Status", value="Processing...", inline=True)
        embed.add_field(name="Target", value="Human members", inline=True)
        embed.set_footer(text="Role Management System", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        
        progress_msg = await ctx.send(embed=embed)

        for i, member in enumerate(members, 1):
            try:
                await member.remove_roles(role, reason=f"Role removal command by {ctx.author}")
                success_count += 1
                
                # Update progress every 10 members or at the end
                if i % 10 == 0 or i == total_members:
                    embed.description = f"Removing role {role.mention} from all human members..."
                    embed.set_field_at(0, name="Progress", value=f"{i}/{total_members}", inline=True)
                    embed.set_field_at(1, name="Status", value="Processing...", inline=True)
                    await progress_msg.edit(embed=embed)
                    await asyncio.sleep(0.1)  # Small delay to prevent rate limiting
                    
            except discord.Forbidden:
                failed_count += 1
            except discord.HTTPException:
                failed_count += 1

        # Final result embed
        result_embed = discord.Embed(
            title="Role Removal Complete",
            description=f"Role {role.mention} has been removed from all human members",
            color=0xFFFFFF  # White hex color
        )
        result_embed.add_field(name="Successfully Removed", value=f"**{success_count}** human members", inline=True)
        result_embed.add_field(name="Failed", value=f"**{failed_count}** human members", inline=True)
        result_embed.add_field(name="Total Processed", value=f"**{total_members}** human members", inline=False)
        result_embed.set_footer(text="Role Management System", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        
        await progress_msg.edit(embed=result_embed)

    @role_remove.command(name='bot')
    @commands.guild_only()
    async def role_remove_bot(self, ctx: commands.Context, role: Union[discord.Role, str]):
        """Remove a role from all bot members in the server."""
        if not self.is_admin_owner_or_sso(ctx):
            await ctx.send("Only Guild Owner, Second Owner, or Administrators can use this command.")
            return

        # Handle role ID if string is provided
        if isinstance(role, str):
            try:
                role_id = int(role)
                role = ctx.guild.get_role(role_id)
                if role is None:
                    await ctx.send("Role not found. Please provide a valid role mention or ID.")
                    return
            except ValueError:
                await ctx.send("Invalid role format. Please provide a valid role mention or ID.")
                return

        if role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            await ctx.send("You cannot remove a role higher than or equal to your highest role.")
            return

        if role.managed:
            await ctx.send("Cannot remove managed roles (bot or integration roles).")
            return

        # Check if bot has permission to manage the role
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send("I don't have permission to manage roles.")
            return

        if role >= ctx.guild.me.top_role:
            await ctx.send("I cannot remove a role higher than or equal to my highest role.")
            return

        # Filter for bot members only who have the role
        members = [m for m in ctx.guild.members if m.bot and role in m.roles]
        total_members = len(members)
        
        if total_members == 0:
            await ctx.send(f"No bot members currently have the role {role.mention}.")
            return

        success_count = 0
        failed_count = 0

        embed = discord.Embed(
            title="Role Removal in Progress",
            description=f"Removing role {role.mention} from all bot members...",
            color=0xFFFFFF  # White hex color
        )
        embed.add_field(name="Progress", value=f"0/{total_members}", inline=True)
        embed.add_field(name="Status", value="Processing...", inline=True)
        embed.add_field(name="Target", value="Bot members", inline=True)
        embed.set_footer(text="Role Management System", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        
        progress_msg = await ctx.send(embed=embed)

        for i, member in enumerate(members, 1):
            try:
                await member.remove_roles(role, reason=f"Role removal command by {ctx.author}")
                success_count += 1
                
                # Update progress every 10 members or at the end
                if i % 10 == 0 or i == total_members:
                    embed.description = f"Removing role {role.mention} from all bot members..."
                    embed.set_field_at(0, name="Progress", value=f"{i}/{total_members}", inline=True)
                    embed.set_field_at(1, name="Status", value="Processing...", inline=True)
                    await progress_msg.edit(embed=embed)
                    await asyncio.sleep(0.1)  # Small delay to prevent rate limiting
                    
            except discord.Forbidden:
                failed_count += 1
            except discord.HTTPException:
                failed_count += 1

        # Final result embed
        result_embed = discord.Embed(
            title="Role Removal Complete",
            description=f"Role {role.mention} has been removed from all bot members",
            color=0xFFFFFF  # White hex color
        )
        result_embed.add_field(name="Successfully Removed", value=f"**{success_count}** bot members", inline=True)
        result_embed.add_field(name="Failed", value=f"**{failed_count}** bot members", inline=True)
        result_embed.add_field(name="Total Processed", value=f"**{total_members}** bot members", inline=False)
        result_embed.set_footer(text="Role Management System", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        
        await progress_msg.edit(embed=result_embed)

    # JSK compatibility command
    @commands.command(name='roleinfo', aliases=['ri'])
    @commands.guild_only()
    async def role_info(self, ctx: commands.Context, role: Union[discord.Role, str]):
        """Get detailed information about a role (JSK compatible)."""
        if not self.is_admin_owner_or_sso(ctx):
            await ctx.send("Only Guild Owner, Second Owner, or Administrators can use this command.")
            return

        # Handle role ID if string is provided
        if isinstance(role, str):
            try:
                role_id = int(role)
                role = ctx.guild.get_role(role_id)
                if role is None:
                    await ctx.send("Role not found. Please provide a valid role mention or ID.")
                    return
            except ValueError:
                await ctx.send("Invalid role format. Please provide a valid role mention or ID.")
                return

        embed = discord.Embed(
            title=f"Role Information: {role.name}",
            description=f"Detailed information about {role.mention}",
            color=0xFFFFFF  # White hex color
        )
        
        # Basic role info
        embed.add_field(name="Role ID", value=f"`{role.id}`", inline=True)
        embed.add_field(name="Color", value=f"`{str(role.color)}`", inline=True)
        embed.add_field(name="Created", value=f"<t:{int(role.created_at.timestamp())}:R>", inline=True)
        
        # Position and permissions
        embed.add_field(name="Position", value=f"`{role.position}`", inline=True)
        embed.add_field(name="Hoisted", value="Yes" if role.hoist else "No", inline=True)
        embed.add_field(name="Mentionable", value="Yes" if role.mentionable else "No", inline=True)
        
        # Member count
        member_count = len(role.members)
        embed.add_field(name="Members", value=f"**{member_count}** members", inline=True)
        
        # Key permissions
        key_perms = []
        if role.permissions.administrator:
            key_perms.append("Administrator")
        if role.permissions.manage_guild:
            key_perms.append("Manage Server")
        if role.permissions.manage_roles:
            key_perms.append("Manage Roles")
        if role.permissions.manage_channels:
            key_perms.append("Manage Channels")
        if role.permissions.ban_members:
            key_perms.append("Ban Members")
        if role.permissions.kick_members:
            key_perms.append("Kick Members")
        
        if key_perms:
            embed.add_field(name="Key Permissions", value=", ".join(key_perms), inline=False)
        
        embed.set_footer(text="Role Management System | JSK Compatible", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Setup function for the RoleManagement cog."""
    await bot.add_cog(RoleManagement(bot))
    print("RoleManagement cog loaded")
