import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import json
import os
import asyncio
import random
from typing import Optional, Union
from datetime import datetime, timedelta
import re

class Giveaway(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.giveaways_file = "giveaways.json"
        self.giveaways = self.load_giveaways()

    def load_giveaways(self):
        """Load giveaways from JSON file."""
        if os.path.exists(self.giveaways_file):
            try:
                with open(self.giveaways_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_giveaways(self):
        """Save giveaways to JSON file."""
        with open(self.giveaways_file, 'w') as f:
            json.dump(self.giveaways, f, indent=2)

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

    def parse_duration(self, duration_str: str) -> Optional[timedelta]:
        """Parse duration string like '1h', '2d', '1y', '1min', '1second', etc."""
        duration_str = duration_str.lower().strip()
        
        # Handle full word formats first
        if duration_str.endswith('min'):
            try:
                value = float(duration_str[:-3])
                return timedelta(minutes=value)
            except ValueError:
                return None
        elif duration_str.endswith('second'):
            try:
                value = float(duration_str[:-6])
                return timedelta(seconds=value)
            except ValueError:
                return None
        elif duration_str.endswith('minute'):
            try:
                value = float(duration_str[:-6])
                return timedelta(minutes=value)
            except ValueError:
                return None
        elif duration_str.endswith('seconds'):
            try:
                value = float(duration_str[:-7])
                return timedelta(seconds=value)
            except ValueError:
                return None
        elif duration_str.endswith('minutes'):
            try:
                value = float(duration_str[:-7])
                return timedelta(minutes=value)
            except ValueError:
                return None
        elif duration_str.endswith('hour'):
            try:
                value = float(duration_str[:-4])
                return timedelta(hours=value)
            except ValueError:
                return None
        elif duration_str.endswith('hours'):
            try:
                value = float(duration_str[:-5])
                return timedelta(hours=value)
            except ValueError:
                return None
        elif duration_str.endswith('day'):
            try:
                value = float(duration_str[:-3])
                return timedelta(days=value)
            except ValueError:
                return None
        elif duration_str.endswith('days'):
            try:
                value = float(duration_str[:-4])
                return timedelta(days=value)
            except ValueError:
                return None
        elif duration_str.endswith('week'):
            try:
                value = float(duration_str[:-4])
                return timedelta(weeks=value)
            except ValueError:
                return None
        elif duration_str.endswith('weeks'):
            try:
                value = float(duration_str[:-5])
                return timedelta(weeks=value)
            except ValueError:
                return None
        elif duration_str.endswith('year'):
            try:
                value = float(duration_str[:-4])
                return timedelta(days=value * 365)
            except ValueError:
                return None
        elif duration_str.endswith('years'):
            try:
                value = float(duration_str[:-5])
                return timedelta(days=value * 365)
            except ValueError:
                return None
        
        # Define time units for short format
        units = {
            's': 1,           # seconds
            'm': 60,          # minutes
            'h': 3600,        # hours
            'd': 86400,       # days
            'w': 604800,      # weeks
            'y': 31536000     # years (365 days)
        }
        
        # Match pattern like "1h", "2d", "30m", etc.
        pattern = r'^(\d+(?:\.\d+)?)([smhdwy])$'
        match = re.match(pattern, duration_str)
        
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            seconds = value * units[unit]
            return timedelta(seconds=seconds)
        
        return None

    def format_duration(self, duration: timedelta) -> str:
        """Format duration for display."""
        total_seconds = int(duration.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            return f"{minutes}m"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            return f"{hours}h"
        elif total_seconds < 604800:
            days = total_seconds // 86400
            return f"{days}d"
        elif total_seconds < 31536000:
            weeks = total_seconds // 604800
            return f"{weeks}w"
        else:
            years = total_seconds // 31536000
            return f"{years}y"

    @app_commands.command(name="giveaway", description="Create a new giveaway")
    @app_commands.describe(
        title="Title of the giveaway",
        description="Description of the giveaway",
        footer="Footer text",
        footer_url="URL for footer image",
        banner_url="URL for banner image",
        winner_count="Number of winners (1-10, or 'unlimited')",
        duration="Duration like '1h', '2d', '1y', etc.",
        leave_option="Enable leave button (on/off)"
    )
    async def create_giveaway(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        winner_count: str = "1",
        duration: str = "1h",
        footer: Optional[str] = None,
        footer_url: Optional[str] = None,
        banner_url: Optional[str] = None,
        leave_option: str = "off"
    ):
        """Create a new giveaway with the specified options."""
        # Check permissions
        if not self.is_owner_or_sso(interaction.user):
            await interaction.response.send_message("Only guild owners and second owners can create giveaways.", ephemeral=True)
            return

        # Parse winner count
        if winner_count.lower() == "unlimited":
            winner_count = "∞"
            winner_limit = -1
        else:
            try:
                winner_limit = int(winner_count)
                if winner_limit < 1 or winner_limit > 10:
                    await interaction.response.send_message("Winner count must be between 1-10 or 'unlimited'.", ephemeral=True)
                    return
            except ValueError:
                await interaction.response.send_message("Winner count must be a number or 'unlimited'.", ephemeral=True)
                return

        # Parse duration
        duration_delta = self.parse_duration(duration)
        if not duration_delta:
            await interaction.response.send_message("Invalid duration format. Use: 1s/1second, 2m/2min, 3h/3hour, 4d/4day, 1w/1week, 1y/1year", ephemeral=True)
            return

        # Calculate end time
        end_time = datetime.utcnow() + duration_delta
        end_timestamp = int(end_time.timestamp())

        # Create embed
        embed = discord.Embed(
            title=title,
            description=description,
            color=0xFFFFFF
        )

        # Add banner image
        if banner_url:
            embed.set_image(url=banner_url)

        # Add footer
        if footer:
            if footer_url:
                embed.set_footer(text=footer, icon_url=footer_url)
            else:
                embed.set_footer(text=footer)

        # Add giveaway info
        embed.add_field(
            name="Prize",
            value=title,
            inline=True
        )
        embed.add_field(
            name="Winners",
            value=winner_count,
            inline=True
        )
        embed.add_field(
            name="Ends",
            value=f"<t:{end_timestamp}:R>",
            inline=True
        )

        # Create buttons
        view = View()

        # Participate button (always present)
        participate_button = Button(
            label="Participate",
            style=discord.ButtonStyle.secondary,
            custom_id="giveaway_join"
        )
        view.add_item(participate_button)

        # Leave button (optional)
        if leave_option.lower() == "on":
            leave_button = Button(
                label="Leave",
                style=discord.ButtonStyle.secondary,
                custom_id="giveaway_leave"
            )
            view.add_item(leave_button)

        # Send the giveaway
        message = await interaction.channel.send(embed=embed, view=view)

        # Store giveaway data
        giveaway_id = str(message.id)
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.giveaways:
            self.giveaways[guild_id] = {}
        
        self.giveaways[guild_id][giveaway_id] = {
            "title": title,
            "description": description,
            "winner_count": winner_count,
            "winner_limit": winner_limit,
            "end_time": end_timestamp,
            "participants": [],
            "ended": False,
            "winners": [],
            "creator_id": interaction.user.id,
            "channel_id": interaction.channel.id,
            "leave_enabled": leave_option.lower() == "on"
        }
        
        self.save_giveaways()

        # Schedule giveaway end
        self.bot.loop.create_task(self.end_giveaway(guild_id, giveaway_id, duration_delta))

        await interaction.response.send_message("Giveaway created successfully!", ephemeral=True)

    async def end_giveaway(self, guild_id: str, giveaway_id: str, duration: timedelta):
        """End a giveaway after the specified duration."""
        await asyncio.sleep(duration.total_seconds())
        
        if guild_id not in self.giveaways or giveaway_id not in self.giveaways[guild_id]:
            return
        
        giveaway = self.giveaways[guild_id][giveaway_id]
        if giveaway["ended"]:
            return
        
        # Mark as ended
        giveaway["ended"] = True
        
        # Get participants
        participants = giveaway["participants"]
        
        if not participants:
            # No participants
            try:
                channel = self.bot.get_channel(giveaway["channel_id"])
                if channel:
                    await channel.send("No one entered this giveaway!")
            except:
                pass
        else:
            # Select winners
            winner_limit = giveaway["winner_limit"]
            if winner_limit == -1:  # Unlimited
                winners = participants
            else:
                winners = random.sample(participants, min(winner_limit, len(participants)))
            
            giveaway["winners"] = winners
            
            # Create simple winner announcement message
            winner_mentions = " ".join([f"<@{winner_id}>" for winner_id in winners])
            winner_message = f"{winner_mentions} won the giveaway!"
            
            # Send winner announcement
            try:
                channel = self.bot.get_channel(giveaway["channel_id"])
                if channel:
                    await channel.send(winner_message)
            except:
                pass
        
        self.save_giveaways()

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button interactions for giveaways."""
        if not interaction.type == discord.InteractionType.component:
            return
        
        custom_id = interaction.data.get("custom_id", "")
        
        if custom_id == "giveaway_join":
            await self.handle_join(interaction)
        elif custom_id == "giveaway_leave":
            await self.handle_leave(interaction)

    async def handle_join(self, interaction: discord.Interaction):
        """Handle join giveaway button."""
        guild_id = str(interaction.guild.id)
        message_id = str(interaction.message.id)
        
        if guild_id not in self.giveaways or message_id not in self.giveaways[guild_id]:
            await interaction.response.send_message("This giveaway is no longer active.", ephemeral=True)
            return
        
        giveaway = self.giveaways[guild_id][message_id]
        
        if giveaway["ended"]:
            await interaction.response.send_message("This giveaway has already ended.", ephemeral=True)
            return
        
        user_id = str(interaction.user.id)
        
        if user_id in giveaway["participants"]:
            await interaction.response.send_message("You're already in this giveaway!", ephemeral=True)
            return
        
        # Add participant
        giveaway["participants"].append(user_id)
        self.save_giveaways()
        
        await interaction.response.send_message("You've joined the giveaway! Good luck! 🍀", ephemeral=True)

    async def handle_leave(self, interaction: discord.Interaction):
        """Handle leave giveaway button."""
        guild_id = str(interaction.guild.id)
        message_id = str(interaction.message.id)
        
        if guild_id not in self.giveaways or message_id not in self.giveaways[guild_id]:
            await interaction.response.send_message("This giveaway is no longer active.", ephemeral=True)
            return
        
        giveaway = self.giveaways[guild_id][message_id]
        
        if giveaway["ended"]:
            await interaction.response.send_message("This giveaway has already ended.", ephemeral=True)
            return
        
        user_id = str(interaction.user.id)
        
        if user_id not in giveaway["participants"]:
            await interaction.response.send_message("You're not in this giveaway!", ephemeral=True)
            return
        
        # Remove participant
        giveaway["participants"].remove(user_id)
        self.save_giveaways()
        
        await interaction.response.send_message("You've left the giveaway.", ephemeral=True)

    @commands.command(name="reroll")
    async def reroll_giveaway(self, ctx: commands.Context, message_id: int):
        """Reroll a giveaway to select new winners."""
        # Check permissions
        if not self.is_owner_or_sso(ctx.author):
            await ctx.send("Only guild owners and second owners can reroll giveaways.")
            return
        
        guild_id = str(ctx.guild.id)
        giveaway_id = str(message_id)
        
        if guild_id not in self.giveaways or giveaway_id not in self.giveaways[guild_id]:
            await ctx.send("Giveaway not found.")
            return
        
        giveaway = self.giveaways[guild_id][giveaway_id]
        
        if not giveaway["ended"]:
            await ctx.send("This giveaway hasn't ended yet.")
            return
        
        participants = giveaway["participants"]
        if not participants:
            await ctx.send("No participants to reroll from.")
            return
        
        # Select new winners
        winner_limit = giveaway["winner_limit"]
        if winner_limit == -1:  # Unlimited
            new_winners = participants
        else:
            new_winners = random.sample(participants, min(winner_limit, len(participants)))
        
        # Update winners
        giveaway["winners"] = new_winners
        self.save_giveaways()
        
        # Announce new winners
        winner_mentions = " ".join([f"<@{winner_id}>" for winner_id in new_winners])
        reroll_message = f"Reroll winner {winner_mentions}"
        
        await ctx.send(reroll_message)

    @commands.command(name="giveawayinfo", aliases=["gwinfo"])
    async def giveaway_info(self, ctx: commands.Context, message_id: int):
        """Get information about a giveaway."""
        guild_id = str(ctx.guild.id)
        giveaway_id = str(message_id)
        
        if guild_id not in self.giveaways or giveaway_id not in self.giveaways[guild_id]:
            await ctx.send("Giveaway not found.")
            return
        
        giveaway = self.giveaways[guild_id][giveaway_id]
        
        embed = discord.Embed(
            title=f"Giveaway: {giveaway['title']}",
            description=giveaway["description"],
            color=0xFFFFFF
        )
        
        embed.add_field(
            name="Status",
            value="Ended" if giveaway["ended"] else "Active",
            inline=True
        )
        embed.add_field(
            name="Winners",
            value=giveaway["winner_count"],
            inline=True
        )
        embed.add_field(
            name="Participants",
            value=str(len(giveaway["participants"])),
            inline=True
        )
        
        if giveaway["ended"]:
            if giveaway["winners"]:
                winner_mentions = " ".join([f"<@{winner_id}>" for winner_id in giveaway["winners"]])
                embed.add_field(
                    name="Winners",
                    value=winner_mentions,
                    inline=False
                )
            else:
                embed.add_field(
                    name="Winners",
                    value="No participants",
                    inline=False
                )
        else:
            embed.add_field(
                name="Ends",
                value=f"<t:{giveaway['end_time']}:R>",
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Giveaway(bot))
    print("✅ Giveaway cog loaded: /giveaway slash commands available")
