import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import os
from typing import Optional, Union

class ButtonRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.button_roles_file = "button_roles.json"
        self.button_roles = self.load_button_roles()

    def load_button_roles(self):
        """Load button roles from JSON file."""
        if os.path.exists(self.button_roles_file):
            try:
                with open(self.button_roles_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_button_roles(self):
        """Save button roles to JSON file."""
        with open(self.button_roles_file, 'w') as f:
            json.dump(self.button_roles, f, indent=2)

    @commands.command(name="setbutton", aliases=["setbtn"])
    @commands.guild_only()
    async def set_button(self, ctx: commands.Context, message_id: int, role: discord.Role, emoji: Union[discord.Emoji, str]):
        """Set up a button role reaction system."""
        # Check permissions
        if not ctx.author.guild_permissions.manage_roles:
            await ctx.send("You need Manage Roles permission to use this command.")
            return
        
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send("I need Manage Roles permission to use this command.")
            return

        # Check if role is manageable
        if role >= ctx.guild.me.top_role:
            await ctx.send("I cannot manage that role.")
            return

        try:
            # Try to fetch the message
            message = await ctx.channel.fetch_message(message_id)
        except:
            await ctx.send("Could not find a message with that ID in this channel.")
            return

        # Store button role info
        guild_id = str(ctx.guild.id)
        if guild_id not in self.button_roles:
            self.button_roles[guild_id] = {}
        
        # Convert emoji to string if it's a custom emoji
        emoji_str = str(emoji.id) if hasattr(emoji, 'id') else str(emoji)
        
        self.button_roles[guild_id][str(message_id)] = {
            "role_id": role.id,
            "emoji": emoji_str,
            "channel_id": ctx.channel.id
        }
        
        self.save_button_roles()

        # Add reaction to the message
        try:
            await message.add_reaction(emoji)
            embed = discord.Embed(
                title="Button Role Set",
                description=f"Users who react with {emoji} will get the {role.mention} role.",
                color=0xFFFFFF
            )
            await ctx.send(embed=embed)
        except:
            embed = discord.Embed(
                title="Button Role Set",
                description=f"Button role configured, but I couldn't add the reaction. Users who react with {emoji} will get the {role.mention} role.",
                color=0xFFFFFF
            )
            await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle reaction adds for button roles."""
        if payload.user_id == self.bot.user.id:
            return

        guild_id = str(payload.guild_id)
        message_id = str(payload.message_id)
        
        if guild_id not in self.button_roles or message_id not in self.button_roles[guild_id]:
            return

        button_data = self.button_roles[guild_id][message_id]
        role_id = button_data["role_id"]
        emoji_str = button_data["emoji"]
        
        # Check if the reaction matches
        if str(payload.emoji.id) == emoji_str or str(payload.emoji) == emoji_str:
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                return
                
            role = guild.get_role(role_id)
            if not role:
                return
                
            member = guild.get_member(payload.user_id)
            if not member:
                return
                
            try:
                await member.add_roles(role, reason="Button role reaction")
            except:
                pass  # Silently fail if we can't add the role

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Handle reaction removes for button roles."""
        if payload.user_id == self.bot.user.id:
            return

        guild_id = str(payload.guild_id)
        message_id = str(payload.message_id)
        
        if guild_id not in self.button_roles or message_id not in self.button_roles[guild_id]:
            return

        button_data = self.button_roles[guild_id][message_id]
        role_id = button_data["role_id"]
        emoji_str = button_data["emoji"]
        
        # Check if the reaction matches
        if str(payload.emoji.id) == emoji_str or str(payload.emoji) == emoji_str:
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                return
                
            role = guild.get_role(role_id)
            if not role:
                return
                
            member = guild.get_member(payload.user_id)
            if not member:
                return
                
            try:
                await member.remove_roles(role, reason="Button role reaction removed")
            except:
                pass  # Silently fail if we can't remove the role

    @commands.command(name="removebutton", aliases=["removebtn"])
    @commands.guild_only()
    async def remove_button(self, ctx: commands.Context, message_id: int):
        """Remove a button role setup."""
        if not ctx.author.guild_permissions.manage_roles:
            await ctx.send("You need Manage Roles permission to use this command.")
            return

        guild_id = str(ctx.guild.id)
        if guild_id in self.button_roles and str(message_id) in self.button_roles[guild_id]:
            del self.button_roles[guild_id][str(message_id)]
            self.save_button_roles()
            embed = discord.Embed(
                title="Button Role Removed",
                description=f"Button role removed from message {message_id}.",
                color=0xFFFFFF
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Button Role Not Found",
                description="No button role found for that message ID.",
                color=0xFFFFFF
            )
            await ctx.send(embed=embed)

    @commands.command(name="listbuttons", aliases=["listbtn"])
    @commands.guild_only()
    async def list_buttons(self, ctx: commands.Context):
        """List all button roles in the server."""
        guild_id = str(ctx.guild.id)
        if guild_id not in self.button_roles or not self.button_roles[guild_id]:
            embed = discord.Embed(
                title="No Button Roles",
                description="No button roles set up in this server.",
                color=0xFFFFFF
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(title="Button Roles", color=0xFFFFFF)
        for message_id, data in self.button_roles[guild_id].items():
            role = ctx.guild.get_role(data["role_id"])
            role_name = role.name if role else "Unknown Role"
            embed.add_field(
                name=f"Message {message_id}",
                value=f"Role: {role_name}\nEmoji: {data['emoji']}",
                inline=True
            )

        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(ButtonRole(bot))
    print("✅ ButtonRole cog loaded: setbutton/removebutton available")
