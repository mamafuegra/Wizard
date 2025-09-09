import discord
from discord.ext import commands
import json
import os

class Jail(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.jailed_file = 'jailed_users.json'
        self.jail_config_file = 'jail_config.json'
        self.jailed_users = self.load_jailed_users()
        self.jail_config = self.load_jail_config()
        
    def load_jailed_users(self):
        """Load jailed users from JSON file"""
        try:
            if os.path.exists(self.jailed_file):
                with open(self.jailed_file, 'r') as f:
                    return json.load(f)
            return {}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def save_jailed_users(self):
        """Save jailed users to JSON file"""
        with open(self.jailed_file, 'w') as f:
            json.dump(self.jailed_users, f, indent=4)
    
    def load_jail_config(self):
        """Load jail configuration from JSON file"""
        try:
            if os.path.exists(self.jail_config_file):
                with open(self.jail_config_file, 'r') as f:
                    return json.load(f)
            return {}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def save_jail_config(self):
        """Save jail configuration to JSON file"""
        with open(self.jail_config_file, 'w') as f:
            json.dump(self.jail_config, f, indent=4)
    
    @commands.group(name='jail', invoke_without_command=True)
    async def jail_user(self, ctx, target: str = None, *, reason="No reason provided"):
        """Jail a user by removing their roles and adding them to a jail role"""
        guild_id = str(ctx.guild.id)
        
        # If subcommand (e.g., status), don't run base action
        if ctx.invoked_subcommand is not None:
            return
        
        # If the user asked for status explicitly
        if target is not None and target.lower() == 'status':
            await self.jail_status(ctx)
            return

        # If no member provided show usage
        if target is None:
            await ctx.send(f"Usage: `{ctx.prefix}jail @user [reason]` or `{ctx.prefix}jail status`")
            return
        
        # Require Manage Roles unless invoker is bot owner (JSK covers owners, but allow here too)
        bot_owner_ids = {386889350010634252, 164202861356515328}
        if not (ctx.author.guild_permissions.manage_roles or ctx.author.id in bot_owner_ids):
            await ctx.send("You need 'Manage Roles' permission to jail users!")
            return
        
        # Check if jail system is enabled
        if guild_id not in self.jail_config or not self.jail_config[guild_id].get("enabled", False):
            await ctx.send(f"Jail system is not enabled! Use `{ctx.prefix}set jail` to enable it.")
            return
        
        # Try to resolve target to a Member
        try:
            member: discord.Member = await commands.MemberConverter().convert(ctx, target)
        except commands.MemberNotFound:
            await ctx.send("User not found! Please mention a valid user.")
            return

        if member.bot:
            await ctx.send("You cannot jail a bot!")
            return
            
        if member.guild_permissions.administrator:
            await ctx.send("You cannot jail an administrator!")
            return
            
        # Check if user's highest role is above bot's highest role
        bot_member = ctx.guild.get_member(self.bot.user.id)
        if bot_member and member.top_role >= bot_member.top_role:
            await ctx.send("I cannot jail someone with a role higher than or equal to my highest role!")
            return
            
        user_id = str(member.id)
        
        # Check if user is already jailed
        if guild_id in self.jailed_users and user_id in self.jailed_users[guild_id]:
            await ctx.send(f"{member.mention} is already jailed!")
            return
        
        # Get or create jail role
        jail_role = discord.utils.get(ctx.guild.roles, name="Jailed")
        if not jail_role:
            try:
                jail_role = await ctx.guild.create_role(
                    name="Jailed",
                    color=discord.Color.dark_red(),
                    reason="Jail system role"
                )
            except discord.Forbidden:
                await ctx.send("I don't have permission to create the jail role!")
                return
        
        # Get jail channel
        jail_channel_id = self.jail_config[guild_id].get("jail_channel_id")
        jail_channel = None
        if jail_channel_id:
            jail_channel = ctx.guild.get_channel(int(jail_channel_id))
        
        if not jail_channel:
            await ctx.send("Jail channel not found! Please set up the jail system first.")
            return
        
        # Store original roles
        original_roles = [role.id for role in member.roles if role.name != "@everyone"]
        
        # Initialize guild in jailed_users if not exists
        if guild_id not in self.jailed_users:
            self.jailed_users[guild_id] = {}
        
        # Store user data
        self.jailed_users[guild_id][user_id] = {
            "roles": original_roles,
            "reason": reason,
            "jailed_by": ctx.author.id,
            "jailed_at": str(ctx.message.created_at)
        }
        
        # Remove all roles and add jail role
        try:
            await member.remove_roles(*member.roles[1:])  # Keep @everyone role
            await member.add_roles(jail_role)
        except discord.Forbidden:
            await ctx.send("I don't have permission to modify this user's roles!")
            return
        
        # Set up channel permissions for jailed user
        try:
            # Hide all channels from jailed user except jail channel
            for channel in ctx.guild.channels:
                if channel != jail_channel:
                    # Hide all other channels from jailed users
                    await channel.set_permissions(jail_role, view_channel=False, send_messages=False, read_messages=False)
                else:
                    # Jail channel: only jailed users and admins can see
                    await channel.set_permissions(jail_role, view_channel=True, send_messages=True, read_messages=True)
                    # Hide jail channel from everyone else (non-admins)
                    await channel.set_permissions(ctx.guild.default_role, view_channel=False, send_messages=False, read_messages=False)
        except discord.Forbidden:
            await ctx.send("Warning: I don't have permission to set channel permissions!")
        
        self.save_jailed_users()
        
        embed = discord.Embed(
            title="🔒 User Jailed",
            description=f"{member.mention} has been jailed!",
            color=0xFFFFFF
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Jailed by", value=ctx.author.mention, inline=True)
        embed.add_field(name="User ID", value=member.id, inline=True)
        embed.add_field(name="Jail Channel", value=jail_channel.mention, inline=True)
        embed.set_footer(text=f"Use {ctx.prefix}unjail {member.mention} to unjail them")
        
        await ctx.send(embed=embed)
        
        # Send message to jail channel
        jail_embed = discord.Embed(
            title="🔒 You have been jailed!",
            description=f"{member.mention}, you have been jailed by {ctx.author.mention}",
            color=0xFFFFFF
        )
        jail_embed.add_field(name="Reason", value=reason, inline=False)
        jail_embed.add_field(name="Jail Channel", value="You can only see and use this channel while jailed.", inline=False)
        await jail_channel.send(embed=jail_embed)

    @jail_user.command(name='status')
    async def jail_status(self, ctx):
        """Show whether jail system is enabled and its settings"""
        guild_id = str(ctx.guild.id)
        cfg = self.jail_config.get(guild_id, {})
        enabled = cfg.get("enabled", False)
        role_id = cfg.get("jail_role_id")
        channel_id = cfg.get("jail_channel_id")
        jail_role = ctx.guild.get_role(int(role_id)) if role_id else None
        jail_channel = ctx.guild.get_channel(int(channel_id)) if channel_id else None

        try:
            from utils.formatting import quote
        except Exception:
            def quote(t: str) -> str:
                return t
        embed = discord.Embed(
            title="Jail System Status",
            color=0xFFFFFF
        )
        desc = quote(f"Status: {'Enabled' if enabled else 'Disabled'}\nJail Role: {jail_role.mention if jail_role else 'Not set'}\nJail Channel: {jail_channel.mention if jail_channel else 'Not set'}")
        embed.description = desc
        embed.set_footer(text=f"Guild ID: {ctx.guild.id}")
        await ctx.send(embed=embed)

    @commands.command(name='unjail')
    @commands.has_permissions(manage_roles=True)
    async def unjail_user(self, ctx, member: discord.Member):
        """Unjail a user by restoring their original roles"""
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        
        # Check if user is jailed
        if guild_id not in self.jailed_users or user_id not in self.jailed_users[guild_id]:
            await ctx.send(f"{member.mention} is not jailed!")
            return
        
        # Get jail role
        jail_role = discord.utils.get(ctx.guild.roles, name="Jailed")
        if not jail_role:
            await ctx.send("Jail role not found! Creating a new one...")
            try:
                jail_role = await ctx.guild.create_role(name="Jailed")
            except discord.Forbidden:
                await ctx.send("I don't have permission to create the jail role!")
                return
        
        # Get user data
        user_data = self.jailed_users[guild_id][user_id]
        original_role_ids = user_data["roles"]
        
        # Remove jail role
        try:
            await member.remove_roles(jail_role)
        except discord.Forbidden:
            await ctx.send("I don't have permission to remove the jail role!")
            return
        
        # Restore channel permissions for unjailed user
        try:
            # Reset channel permissions for the user
            for channel in ctx.guild.channels:
                await channel.set_permissions(member, overwrite=None)
            # Make sure jail channel is hidden from regular users
            jail_channel_id = self.jail_config[guild_id].get("jail_channel_id")
            if jail_channel_id:
                jail_channel = ctx.guild.get_channel(int(jail_channel_id))
                if jail_channel:
                    await jail_channel.set_permissions(ctx.guild.default_role, view_channel=False, send_messages=False, read_messages=False)
        except discord.Forbidden:
            await ctx.send("Warning: I don't have permission to reset channel permissions!")
        
        # Restore original roles
        restored_roles = []
        failed_roles = []
        
        for role_id in original_role_ids:
            role = ctx.guild.get_role(role_id)
            if role and role.name != "Jailed":
                try:
                    await member.add_roles(role)
                    restored_roles.append(role.name)
                except discord.Forbidden:
                    failed_roles.append(role.name)
        
        # Remove from jailed users
        del self.jailed_users[guild_id][user_id]
        if not self.jailed_users[guild_id]:  # Remove guild if no jailed users
            del self.jailed_users[guild_id]
        
        self.save_jailed_users()
        
        embed = discord.Embed(
            title="🔓 User Unjailed",
            description=f"{member.mention} has been unjailed!",
            color=0xFFFFFF
        )
        embed.add_field(name="Unjailed by", value=ctx.author.mention, inline=True)
        embed.add_field(name="Original reason", value=user_data["reason"], inline=True)
        
        if restored_roles:
            embed.add_field(name="Restored roles", value=", ".join(restored_roles[:10]), inline=False)
        if failed_roles:
            embed.add_field(name="Failed to restore", value=", ".join(failed_roles[:10]), inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='jailed')
    @commands.has_permissions(manage_roles=True)
    async def list_jailed(self, ctx):
        """List all currently jailed users"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.jailed_users or not self.jailed_users[guild_id]:
            await ctx.send("No users are currently jailed in this server.")
            return
        
        embed = discord.Embed(
            title="🔒 Jailed Users",
            description=f"Currently jailed users in {ctx.guild.name}",
            color=0xFFFFFF
        )
        
        for user_id, user_data in self.jailed_users[guild_id].items():
            member = ctx.guild.get_member(int(user_id))
            if member:
                jailed_by = ctx.guild.get_member(user_data["jailed_by"])
                jailed_by_mention = jailed_by.mention if jailed_by else "Unknown"
                
                embed.add_field(
                    name=f"👤 {member.display_name}",
                    value=f"**Reason:** {user_data['reason']}\n**Jailed by:** {jailed_by_mention}\n**User ID:** {user_id}",
                    inline=False
                )
        
            embed.set_footer(text=f"Use {ctx.prefix}unjail @user to unjail someone")
        await ctx.send(embed=embed)
    
    @commands.command(name='set')
    @commands.has_permissions(administrator=True)
    async def setup_jail(self, ctx, action: str = None):
        """Set up the jail system for this server"""
        guild_id = str(ctx.guild.id)
        
        if action is None:
            embed = discord.Embed(
                title="🔒 Jail System Setup",
                description="Configure the jail system for this server",
                color=0xFFFFFF
            )
            embed.add_field(name="Usage", value=f"`{ctx.prefix}set jail` - Enable jail system\n`{ctx.prefix}unset jail` - Disable and delete jail system", inline=False)
            embed.add_field(name="Current Status", value="Enabled" if guild_id in self.jail_config and self.jail_config[guild_id].get("enabled", False) else "Disabled", inline=True)
            if guild_id in self.jail_config and self.jail_config[guild_id].get("jail_channel_id"):
                jail_channel = ctx.guild.get_channel(int(self.jail_config[guild_id]["jail_channel_id"]))
                embed.add_field(name="Jail Channel", value=jail_channel.mention if jail_channel else "Not found", inline=True)
            await ctx.send(embed=embed)
            return
        
        if action.lower() == "jail":
            # Enable jail system
            if guild_id not in self.jail_config:
                self.jail_config[guild_id] = {}
            
            # Get or create jail role
            jail_role = discord.utils.get(ctx.guild.roles, name="Jailed")
            if not jail_role:
                try:
                    jail_role = await ctx.guild.create_role(
                        name="Jailed",
                        color=discord.Color.dark_red(),
                        reason="Jail system role"
                    )
                except discord.Forbidden:
                    await ctx.send("I don't have permission to create the jail role!")
                    return
            
            # Check if jail channel exists
            jail_channel = discord.utils.get(ctx.guild.channels, name="jail")
            if not jail_channel:
                # Create jail channel with proper permissions
                try:
                    jail_channel = await ctx.guild.create_text_channel(
                        name="jail",
                        topic="Jail channel for jailed users",
                        reason="Jail system setup"
                    )
                    # Set permissions: only admins can see by default
                    await jail_channel.set_permissions(ctx.guild.default_role, view_channel=False, send_messages=False, read_messages=False)
                except discord.Forbidden:
                    await ctx.send("I don't have permission to create the jail channel!")
                    return
            
            # Update config
            self.jail_config[guild_id]["enabled"] = True
            self.jail_config[guild_id]["jail_channel_id"] = str(jail_channel.id)
            self.jail_config[guild_id]["jail_role_id"] = str(jail_role.id)
            self.save_jail_config()
            
            embed = discord.Embed(
                title="✅ Jail System Enabled",
                description="The jail system has been set up successfully!",
                color=0xFFFFFF
            )
            embed.add_field(name="Jail Role", value=jail_role.mention, inline=True)
            embed.add_field(name="Jail Channel", value=jail_channel.mention, inline=True)
            embed.add_field(name="Status", value="Enabled", inline=True)
            embed.add_field(name="Usage", value=f"`{ctx.prefix}jail @user [reason]` - Jail a user\n`{ctx.prefix}unjail @user` - Unjail a user", inline=False)
            await ctx.send(embed=embed)
    
    @commands.command(name='unset')
    @commands.has_permissions(administrator=True)
    async def unset_jail(self, ctx, action: str = None):
        """Unset the jail system for this server"""
        guild_id = str(ctx.guild.id)
        
        if action is None:
            await ctx.send(f"Usage: `{ctx.prefix}unset jail` - Delete jail role and channel")
            return
            
        if action.lower() == "jail":
            # Check if jail system is configured
            if guild_id not in self.jail_config or not self.jail_config[guild_id].get("enabled", False):
                await ctx.send("Jail system is not enabled for this server.")
                return
            
            # Get jail role and channel
            jail_role = None
            jail_channel = None
            
            if "jail_role_id" in self.jail_config[guild_id]:
                jail_role = ctx.guild.get_role(int(self.jail_config[guild_id]["jail_role_id"]))
            
            if "jail_channel_id" in self.jail_config[guild_id]:
                jail_channel = ctx.guild.get_channel(int(self.jail_config[guild_id]["jail_channel_id"]))
            
            # Check if there are jailed users
            if guild_id in self.jailed_users and self.jailed_users[guild_id]:
                jailed_count = len(self.jailed_users[guild_id])
                await ctx.send(f"⚠️ Warning: There are {jailed_count} jailed users. Please unjail them first before deleting the jail system!")
                return
            
            # Delete jail channel
            if jail_channel:
                try:
                    await jail_channel.delete(reason="Jail system unset")
                except discord.Forbidden:
                    await ctx.send("I don't have permission to delete the jail channel!")
                    return
                except discord.NotFound:
                    pass  # Channel already deleted
            
            # Delete jail role
            if jail_role:
                try:
                    await jail_role.delete(reason="Jail system unset")
                except discord.Forbidden:
                    await ctx.send("I don't have permission to delete the jail role!")
                    return
                except discord.NotFound:
                    pass  # Role already deleted
            
            # Remove from config
            if guild_id in self.jail_config:
                del self.jail_config[guild_id]
                self.save_jail_config()
            
            embed = discord.Embed(
                title="🗑️ Jail System Deleted",
                description="The jail system has been completely removed!",
                color=0xFFFFFF
            )
            embed.add_field(name="Deleted", value="Jail role and jail channel", inline=True)
            embed.add_field(name="Status", value="Disabled", inline=True)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Unknown action: {action}. Use `{ctx.prefix}unset jail` to delete the jail system.")
    
    @jail_user.error
    async def jail_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You need 'Manage Roles' permission to jail users!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Please specify a user to jail! Usage: `{ctx.prefix}jail @user [reason]`")
        elif isinstance(error, commands.MemberNotFound):
            # If the user ran the status subcommand (e.g., ",jail status"),
            # the group should not complain about a missing member.
            # Suppress this specific case where the argument equals 'status'.
            arg = getattr(error, 'argument', '')
            if isinstance(arg, str) and arg.lower() == 'status':
                return
            await ctx.send("User not found! Please mention a valid user.")
    
    @unjail_user.error
    async def unjail_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You need 'Manage Roles' permission to unjail users!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Please specify a user to unjail! Usage: `{ctx.prefix}unjail @user`")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("User not found! Please mention a valid user.")
    
    @setup_jail.error
    async def setup_jail_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You need 'Administrator' permission to set up the jail system!")
        elif isinstance(error, commands.CommandError):
            await ctx.send(f"An error occurred: {error}")
    
    @unset_jail.error
    async def unset_jail_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You need 'Administrator' permission to unset the jail system!")
        elif isinstance(error, commands.CommandError):
            await ctx.send(f"An error occurred: {error}")

async def setup(bot):
    await bot.add_cog(Jail(bot))
