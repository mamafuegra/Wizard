import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
from typing import Optional, Union
import json

class EmbedCreator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def is_owner_or_sso(self, user: discord.Member) -> bool:
        """Check if user is guild owner or second owner."""
        if user.guild_permissions.administrator:
            return True
        
        # Check if user is second owner using the existing system
        try:
            with open('second_owners.json', 'r') as f:
                second_owners = json.load(f)
                if str(user.guild.id) in second_owners:
                    second_owner_id = second_owners[str(user.guild.id)]
                    if str(user.id) == second_owner_id:
                        return True
        except:
            pass
        
        return False

    def is_bot_owner(self, user: discord.User) -> bool:
        """Check if user is bot owner."""
        OWNER_IDS = [386889350010634252, 164202861356515328]
        return user.id in OWNER_IDS

    @commands.group(name="message", invoke_without_command=True)
    async def message_group(self, ctx: commands.Context):
        """Message management commands"""
        await ctx.send("Usage: `!message send <message>` or `!message send #channel <message>`")

    @message_group.command(name="send")
    async def message_send(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None, *, message: str):
        """Send a message as the bot (Guild Owner, Second Owner, or Bot Owner only)
        
        Usage:
        !message send <message> - Send message in current channel
        !message send #channel <message> - Send message in specified channel
        """
        # Check permissions
        if not (self.is_owner_or_sso(ctx.author) or self.is_bot_owner(ctx.author)):
            await ctx.send("❌ Only guild owners, second owners, or bot owners can use this command.")
            return
        
        # Determine target channel
        target_channel = channel if channel else ctx.channel
        
        try:
            # Delete the command message
            await ctx.message.delete()
            
            # Send the message to target channel
            await target_channel.send(message)
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to send messages in that channel.")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")

    @app_commands.command(name="embed", description="Create a custom embed")
    @app_commands.describe(
        title="Title of the embed",
        description="Description of the embed",
        footer="Footer text (use 'on' to show your avatar)",
        footer_url="URL for footer image",
        banner_url="URL for banner image",
        button_name="Button name or emoji ID",
        button_url="URL for button to visit",
        hex_color="Hex color code (e.g., #FFFFFF)",
        ping_message="Message to ping users with"
    )
    async def create_embed(
        self,
        interaction: discord.Interaction,
        title: Optional[str] = None,
        description: Optional[str] = None,
        footer: Optional[str] = None,
        footer_url: Optional[str] = None,
        banner_url: Optional[str] = None,
        button_name: Optional[str] = None,
        button_url: Optional[str] = None,
        hex_color: Optional[str] = None,
        ping_message: Optional[str] = None
    ):
        """Create a custom embed with the specified options."""
        # Check permissions
        if not self.is_owner_or_sso(interaction.user):
            await interaction.response.send_message("Only guild owners and second owners can use this command.", ephemeral=True)
            return

        # Create embed
        embed = discord.Embed()
        
        # Set title
        if title:
            embed.title = title
        
        # Set description
        if description:
            embed.description = description
        
        # Set color
        if hex_color:
            try:
                # Remove # if present
                hex_color = hex_color.lstrip('#')
                color = int(hex_color, 16)
                embed.color = color
            except:
                embed.color = 0xFFFFFF  # Default white
        else:
            embed.color = 0xFFFFFF
        
        # Set banner image
        if banner_url:
            embed.set_image(url=banner_url)
        
        # Set footer
        if footer:
            if footer.lower() == "on":
                # Use user's avatar
                embed.set_footer(text=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            else:
                if footer_url:
                    embed.set_footer(text=footer, icon_url=footer_url)
                else:
                    embed.set_footer(text=footer)
        
        # Create view with button if specified
        view = None
        if button_name and button_url:
            view = View()
            
            # Check if button_name is an emoji ID
            try:
                emoji_id = int(button_name)
                # Try to get the emoji from the guild
                emoji = interaction.guild.get_emoji(emoji_id)
                if emoji:
                    button = Button(
                        label="",
                        emoji=emoji,
                        url=button_url,
                        style=discord.ButtonStyle.secondary
                    )
                else:
                    # Fallback to text button
                    button = Button(
                        label=button_name,
                        url=button_url,
                        style=discord.ButtonStyle.secondary
                    )
            except ValueError:
                # Not an emoji ID, use as text
                button = Button(
                    label=button_name,
                    url=button_url,
                    style=discord.ButtonStyle.secondary
                )
            
            view.add_item(button)
        
        # Send the embed
        if ping_message:
            await interaction.channel.send(content=ping_message, embed=embed, view=view)
        else:
            await interaction.channel.send(embed=embed, view=view)
        
        await interaction.response.send_message("Embed created successfully!", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(EmbedCreator(bot))
    print("✅ EmbedCreator cog loaded: /embed slash commands and !message send command available")
