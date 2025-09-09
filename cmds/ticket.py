import discord
from discord.ext import commands
from discord import ui
import json
import re
import os
from utils.formatting import quote
from typing import Optional, Dict
from datetime import datetime, timezone
import asyncio

CONFIG_FILE = 'ticket_config.json'
OWNER_IDS = [386889350010634252, 164202861356515328]  # Update as needed

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)

class TicketSelectMenu(ui.Select):
    def __init__(self, options):
        select_options = [discord.SelectOption(label=opt, value=opt) for opt in options]
        super().__init__(placeholder="Select ticket type", options=select_options, custom_id="ticket_option")

    async def callback(self, interaction: discord.Interaction):
        # Get the selected option
        selected_option = self.values[0]
        
        # Create a new view with just the create button and update the message
        new_view = ui.View(timeout=None)
        new_view.add_item(ui.Button(label="Create Ticket", style=discord.ButtonStyle.blurple, custom_id='ticket_create'))
        
        # Update the message to show the selected option
        embed = interaction.message.embeds[0]
        embed.add_field(name="Selected Type", value=selected_option, inline=False)
        
        await interaction.response.edit_message(embed=embed, view=new_view)

class TicketPanel(ui.View):
    def __init__(self, config: Dict, custom_options=None):
        super().__init__(timeout=None)
        self.config = config
        self.custom_options = custom_options or []
        
        # If there are custom options, show the dropdown
        if self.custom_options:
            self.add_item(TicketSelectMenu(self.custom_options))
        else:
            # If no custom options, show the create button directly
            self.add_item(ui.Button(label=config.get('button_label', 'Create Ticket'), style=discord.ButtonStyle.blurple, custom_id='ticket_create'))

class TicketActionView(ui.View):
    def __init__(self, cog, conf, user, reason, mod_role, second_owner, owner, ticket_channel):
        super().__init__(timeout=None)
        self.cog = cog
        self.conf = conf
        self.user = user
        self.reason = reason
        self.mod_role = mod_role
        self.second_owner = second_owner
        self.owner = owner
        self.ticket_channel = ticket_channel
        self.claimed_by = None
        self.creation_time = datetime.now(timezone.utc)
        # Buttons are declared via @ui.button decorators below

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only allow ticket mod, second owner, or guild owner
        allowed = False
        if self.mod_role and self.mod_role in interaction.user.roles:
            allowed = True
        if self.second_owner and interaction.user.id == self.second_owner.id:
            allowed = True
        if self.owner and interaction.user.id == self.owner.id:
            allowed = True
        # Allow the ticket creator to use Close and Transcript buttons
        if not allowed:
            try:
                custom_id = interaction.data.get("custom_id") if interaction.data else None
            except Exception:
                custom_id = None
            if interaction.user.id == self.user.id and custom_id in ("ticket_close", "ticket_transcript"):
                allowed = True
        if not allowed:
            await interaction.response.send_message("You are not allowed to use this button.", ephemeral=True)
        return allowed

    @ui.button(label="Delete", style=discord.ButtonStyle.danger, custom_id="ticket_delete")
    async def delete_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Deleting ticket...", ephemeral=True)
        
        # Log ticket deletion
        await self.log_ticket_action("deleted", interaction.user)
        
        await interaction.channel.delete(reason=f"Ticket deleted by {interaction.user}")

    @ui.button(label="Claim", style=discord.ButtonStyle.success, custom_id="ticket_claim")
    async def claim_button(self, interaction: discord.Interaction, button: ui.Button):
        if self.claimed_by:
            await interaction.response.send_message(f"Already claimed by {self.claimed_by.mention}.", ephemeral=True)
            return
        
        self.claimed_by = interaction.user
        await interaction.response.send_message(f"Ticket claimed by {interaction.user.mention}. Please wait until they show up for help.", ephemeral=False)
        
        # Log ticket claim
        await self.log_ticket_action("claimed", interaction.user)
        
        # Disable the claim button for others
        button.disabled = True
        await interaction.message.edit(view=self)

    @ui.button(label="Close", style=discord.ButtonStyle.secondary, custom_id="ticket_close")
    async def close_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Ticket will close in 10 minutes.", ephemeral=True)
        await interaction.channel.send(f"⚠️ This ticket will close in 10 minutes by {interaction.user.mention}.")
        
        # Log ticket close
        await self.log_ticket_action("closed", interaction.user)
        
        # Wait 10 minutes then delete
        await asyncio.sleep(600)  # 10 minutes
        
        # Generate transcript before deletion
        await self.generate_transcript(interaction.user, "closed")
        
        await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")

    @ui.button(label="Transcript", style=discord.ButtonStyle.primary, custom_id="ticket_transcript")
    async def transcript_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Generating transcript and sending to your DMs...", ephemeral=True)
        # Build transcript embed and DM to the clicking staff member
        try:
            embed = await self.build_transcript_embed(interaction.user, "transcript")
            await interaction.user.send(embed=embed)
        except discord.Forbidden:
            await interaction.followup.send("I couldn't DM you. Please enable DMs from server members.", ephemeral=True)
        except Exception:
            await interaction.followup.send("Failed to deliver transcript via DM.", ephemeral=True)
        # Also log to the configured log channel if set
        await self.generate_transcript(interaction.user, "transcript")

    async def log_ticket_action(self, action: str, user: discord.Member):
        """Log ticket actions to the configured log channel"""
        log_channel_id = self.conf.get("log_channel_id")
        if not log_channel_id:
            return
            
        log_channel = self.ticket_channel.guild.get_channel(log_channel_id)
        if not log_channel:
            return
            
        embed = discord.Embed(
            title=f"Ticket {action.title()}",
            description=f"**Ticket:** {self.ticket_channel.mention}\n**User:** {self.user.mention}",
            color=0xFFFFFF,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="Reason", value=self.reason, inline=False)
        embed.add_field(name="Created by", value=self.user.mention, inline=True)
        embed.add_field(name="Created at", value=self.creation_time.strftime('%Y-%m-%d %H:%M:%S UTC'), inline=True)
        
        if action == "claimed":
            embed.add_field(name="Claimed by", value=user.mention, inline=True)
            embed.add_field(name="Claimed at", value=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'), inline=True)
        elif action == "closed":
            embed.add_field(name="Closed by", value=user.mention, inline=True)
            embed.add_field(name="Closed at", value=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'), inline=True)
        elif action == "deleted":
            embed.add_field(name="Deleted by", value=user.mention, inline=True)
            embed.add_field(name="Deleted at", value=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'), inline=True)
        
        if self.claimed_by:
            embed.add_field(name="Was claimed by", value=self.claimed_by.mention, inline=True)
        
        await log_channel.send(embed=embed)

    async def build_transcript_embed(self, user: discord.Member, action: str) -> discord.Embed:
        """Build the transcript embed without sending it anywhere."""
        # Gather ticket info
        embed = discord.Embed(
            title="Ticket Transcript",
            description=f"**Ticket:** {self.ticket_channel.mention}\n**User:** {self.user.mention}",
            color=0xFFFFFF,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Reason", value=self.reason, inline=False)
        embed.add_field(name="Opened by", value=self.user.mention, inline=True)
        embed.add_field(name="Opened at", value=self.creation_time.strftime('%Y-%m-%d %H:%M:%S UTC'), inline=True)
        if self.claimed_by:
            embed.add_field(name="Claimed by", value=self.claimed_by.mention, inline=True)
        if action == "closed":
            embed.add_field(name="Closed by", value=user.mention, inline=True)
            embed.add_field(name="Closed at", value=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'), inline=True)
        # Add ticket messages (last 100 messages)
        try:
            messages = []
            async for message in self.ticket_channel.history(limit=100):
                if not message.author.bot:
                    messages.append(f"**{message.author.name}** ({message.created_at.strftime('%H:%M:%S')}): {message.content}")
            if messages:
                message_text = "\n".join(reversed(messages))
                if len(message_text) > 1024:
                    chunks = [message_text[i:i+1024] for i in range(0, len(message_text), 1024)]
                    for i, chunk in enumerate(chunks):
                        embed.add_field(name=f"Messages (Part {i+1})" if len(chunks) > 1 else "Messages", value=chunk, inline=False)
                else:
                    embed.add_field(name="Messages", value=message_text, inline=False)
        except Exception:
            embed.add_field(name="Messages", value="Could not retrieve messages", inline=False)
        return embed

    async def generate_transcript(self, user: discord.Member, action: str):
        """Generate and send transcript to log channel"""
        log_channel_id = self.conf.get("log_channel_id")
        if not log_channel_id:
            return
            
        log_channel = self.ticket_channel.guild.get_channel(log_channel_id)
        if not log_channel:
            return
        embed = await self.build_transcript_embed(user, action)
        await log_channel.send(embed=embed)

class Ticket(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = load_config()
        self._panel_update_locks: Dict[str, asyncio.Lock] = {}
    
    @staticmethod
    async def _reply_embed(ctx: commands.Context, title: str, text: str) -> None:
        embed = discord.Embed(title=title, color=0xFFFFFF)
        embed.description = quote(text)
        await ctx.send(embed=embed)

    def save(self):
        save_config(self.config)

    def is_admin_owner_or_sso(self, ctx):
        if ctx.author.id in OWNER_IDS:
            return True
        if ctx.guild and ctx.author.id == ctx.guild.owner_id:
            return True
        if ctx.author.guild_permissions.administrator:
            return True
        # Second owner check
        try:
            with open('second_owners.json', 'r') as f:
                data = json.load(f)
            if str(ctx.author.id) == data.get(str(ctx.guild.id)):
                return True
        except Exception:
            pass
        return False

    async def send_permission_error(self, ctx, command_name):
        """Send a standardized permission error embed"""
        embed = discord.Embed(
            title="```Permission Denied```",
            description=f"You are not a guild owner or second owner to use this command.",
            color=0xe74c3c
        )
        await ctx.send(embed=embed)

    async def create_ticket_with_reason(self, interaction, reason, selected_option=None):
        """Create a ticket with the given reason and optional selected option"""
        guild_id = str(interaction.guild.id)
        conf = self.config.get(guild_id)
        if not conf:
            await interaction.response.send_message("Ticket system not configured.", ephemeral=True)
            return

        # Ensure the configured category exists
        category = interaction.guild.get_channel(conf.get("category_id")) if conf.get("category_id") else None
        if category is None or not isinstance(category, discord.CategoryChannel):
            try:
                category = await interaction.guild.create_category("Tickets")
                conf["category_id"] = category.id
                self.save()
            except Exception:
                await interaction.response.send_message("I couldn't find or create the tickets category. Please have an admin try again.", ephemeral=True)
                return

        ticket_mod_id = conf.get("ticket_mod")
        
        # Build a safe, unique channel name and check for an existing ticket
        def slugify_username(name: str) -> str:
            safe = name.lower()
            safe = re.sub(r"[^a-z0-9-]+", "-", safe)
            safe = re.sub(r"-+", "-", safe).strip("-")
            return safe or "user"

        safe_name = slugify_username(interaction.user.name)
        desired_name_with_id = f"{safe_name}-ticket-{interaction.user.id}"
        desired_name_legacy = f"{safe_name}-ticket"

        existing = None
        for ch in category.text_channels:
            if ch.name == desired_name_with_id or ch.name == desired_name_legacy or ch.name.endswith(f"-ticket-{interaction.user.id}"):
                existing = ch
                break
            try:
                if ch.topic and str(interaction.user.id) in ch.topic:
                    existing = ch
                    break
            except Exception:
                pass
        if existing:
            await interaction.response.send_message(f"⚠️ You already have an open ticket: {existing.mention}", ephemeral=True)
            return

        # Create channel
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True)
        }
        
        # Add ticket mod, second owner, guild owner
        mod_role = interaction.guild.get_role(ticket_mod_id) if ticket_mod_id else None
        if mod_role:
            overwrites[mod_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        
        # Second owner
        try:
            with open('second_owners.json', 'r') as f:
                data = json.load(f)
            second_owner_id = int(data.get(str(interaction.guild.id)))
            second_owner = interaction.guild.get_member(second_owner_id)
            if second_owner:
                overwrites[second_owner] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        except Exception:
            second_owner = None
        
        # Guild owner
        owner = interaction.guild.get_member(interaction.guild.owner_id)
        if owner:
            overwrites[owner] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        
        channel_name = desired_name_with_id
        ticket_channel = await interaction.guild.create_text_channel(channel_name, category=category, overwrites=overwrites, topic=f"Ticket for {interaction.user.id}")
        
        # Create ticket info embed
        ticket_reason = f"@{interaction.user.name} created ticket for: {selected_option}" if selected_option else reason
        embed = discord.Embed(
            title="🎫 New Ticket Created",
            description=f"**User:** {interaction.user.mention}\n**Reason:** {ticket_reason}",
            color=0xFFFFFF,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Ticket Creator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=ticket_reason, inline=False)
        embed.add_field(name="Ticket Opened", value=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'), inline=True)
        
        # Determine who to ping
        ping_target = None
        if mod_role:
            ping_target = mod_role.mention
        elif second_owner:
            ping_target = second_owner.mention
        else:
            ping_target = owner.mention
        
        # Send ticket info
        await ticket_channel.send(f"{ping_target}", embed=embed)
        
        # Add action buttons
        view = TicketActionView(self, conf, interaction.user, ticket_reason, mod_role, second_owner, owner, ticket_channel)
        await ticket_channel.send("**Ticket Actions:**", view=view)
        
        # Log ticket creation
        if conf.get("log_channel_id"):
            log_channel = interaction.guild.get_channel(conf["log_channel_id"])
            if log_channel:
                log_embed = discord.Embed(
                    title="🎫 Ticket Created",
                    description=f"**Ticket:** {ticket_channel.mention}\n**User:** {interaction.user.mention}",
                    color=0xFFFFFF,
                    timestamp=datetime.now(timezone.utc)
                )
                log_embed.add_field(name="Reason", value=ticket_reason, inline=False)
                log_embed.add_field(name="Created by", value=interaction.user.mention, inline=True)
                log_embed.add_field(name="Created at", value=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'), inline=True)
                log_embed.add_field(name="Category", value=category.name, inline=True)
                await log_channel.send(embed=log_embed)
        
        await interaction.response.send_message(f"✅ Ticket created: {ticket_channel.mention}", ephemeral=True)

    @commands.group(name="ticket", invoke_without_command=True)
    @commands.guild_only()
    async def ticket_group(self, ctx, *args):
        # Intentionally silent to avoid usage spam
        return

    @ticket_group.command(name="set")
    async def ticket_set(self, ctx, category: Optional[discord.CategoryChannel] = None, channel: Optional[discord.TextChannel] = None):
        if not self.is_admin_owner_or_sso(ctx):
            await self.send_permission_error(ctx, "ticket set")
            return
            
        guild_id = str(ctx.guild.id)
        
        # Check if ticket panel already exists
        if guild_id in self.config:
            existing_conf = self.config[guild_id]
            if existing_conf.get("panel_message_id"):
                try:
                    existing_channel = ctx.guild.get_channel(existing_conf["panel_channel_id"])
                    if existing_channel:
                        await self._reply_embed(ctx, "Ticket", f"Ticket panel already exists in {existing_channel.mention}. Use `{ctx.prefix}ticket send #channel` to move it or delete the existing one first.")
                        return
                except Exception:
                    pass
        
        # Auto-create if not provided
        if not category:
            category = await ctx.guild.create_category("Tickets")
        if not channel:
            channel = await ctx.guild.create_text_channel("ticket-panel", category=category)
        
        # Default config for auto-setup
        self.config[guild_id] = {
            "category_id": category.id,
            "panel_channel_id": channel.id,
            "title": "Ticket Help",
            "description": "Wizard ticket help menu!",
            "button_label": "Create Ticket",
            "color": 0x5865F2,
            "options": [],
            "intents": [],
            "ticket_mod": None,
            "log_channel_id": None,
            "panel_message_id": None
        }
        
        self.save()
        await self.send_or_update_panel(ctx.guild, channel, self.config[guild_id])
        await self._reply_embed(ctx, "Ticket", f"Ticket panel set up in {channel.mention}")

    @ticket_group.command(name="status")
    async def ticket_status(self, ctx):
        guild_id = str(ctx.guild.id)
        conf = self.config.get(guild_id)
        if not conf:
            await ctx.send("Ticket system is not configured. Run ticket set.")
            return
        category = ctx.guild.get_channel(conf.get("category_id")) if conf.get("category_id") else None
        panel_ch = ctx.guild.get_channel(conf.get("panel_channel_id")) if conf.get("panel_channel_id") else None
        log_ch = ctx.guild.get_channel(conf.get("log_channel_id")) if conf.get("log_channel_id") else None
        embed = discord.Embed(title="Ticket Status", color=0xFFFFFF)
        embed.add_field(name="Category", value=(category.mention if category else 'None'), inline=True)
        embed.add_field(name="Panel Channel", value=(panel_ch.mention if panel_ch else 'None'), inline=True)
        embed.add_field(name="Log Channel", value=(log_ch.mention if log_ch else 'None'), inline=True)
        embed.add_field(name="Title", value=conf.get('title', 'Support Ticket'), inline=True)
        embed.add_field(name="Description", value=conf.get('description', 'None'), inline=False)
        embed.add_field(name="Button", value=conf.get('button_label', 'Create Ticket'), inline=True)
        mod_role = ctx.guild.get_role(conf.get('ticket_mod')) if conf.get('ticket_mod') else None
        embed.add_field(name="Ticket Mod", value=(mod_role.mention if mod_role else 'None'), inline=True)
        await ctx.send(embed=embed)

    @ticket_group.command(name="send")
    async def ticket_send(self, ctx, channel: discord.TextChannel):
        """Send or update the ticket panel in the specified channel."""
        guild_id = str(ctx.guild.id)
        if guild_id not in self.config:
            await self._reply_embed(ctx, "Ticket", "Run ticket set first.")
            return
        conf = self.config[guild_id]
        old_channel_id = conf.get("panel_channel_id")
        old_message_id = conf.get("panel_message_id")
        conf["panel_channel_id"] = channel.id
        self.save()
        # If moving to a new channel, try to delete the old panel message from the old channel
        if old_channel_id and old_message_id and old_channel_id != channel.id:
            try:
                old_ch = ctx.guild.get_channel(old_channel_id)
                if old_ch:
                    old_msg = await old_ch.fetch_message(old_message_id)
                    await old_msg.delete()
            except Exception:
                pass
        await self.send_or_update_panel(ctx.guild, channel, conf)
        await self._reply_embed(ctx, "Ticket", f"Ticket panel sent to {channel.mention}")

    async def send_or_update_panel(self, guild, channel, conf):
        guild_id = str(guild.id)
        if guild_id not in self._panel_update_locks:
            self._panel_update_locks[guild_id] = asyncio.Lock()
        async with self._panel_update_locks[guild_id]:
            # Try to edit existing panel in this channel; if missing, send new
            existing_msg = None
            if conf.get("panel_message_id"):
                try:
                    existing_msg = await channel.fetch_message(conf["panel_message_id"])
                except Exception:
                    existing_msg = None
            
            embed = discord.Embed(
            title=conf.get('title', 'Support Ticket'), 
            description=conf.get('description', ''), 
            color=0xFFFFFF
            )
            view = TicketPanel(conf, custom_options=conf.get('options'))
            if existing_msg:
                await existing_msg.edit(embed=embed, view=view)
                msg_id = existing_msg.id
            else:
                msg = await channel.send(embed=embed, view=view)
                msg_id = msg.id
            conf["panel_message_id"] = msg_id
            self.save()

    @ticket_group.command(name="mod")
    async def ticket_mod(self, ctx, mod: discord.Role):
        if not self.is_admin_owner_or_sso(ctx):
            await self.send_permission_error(ctx, "ticket mod")
            return
            
        guild_id = str(ctx.guild.id)
        if guild_id not in self.config:
            await ctx.send("Please run !ticket set first.")
            return
            
        self.config[guild_id]["ticket_mod"] = mod.id
        self.save()
        await self._reply_embed(ctx, "Ticket", f"Ticket mod set to {mod.mention}")

    @ticket_group.command(name="log")
    async def ticket_log(self, ctx, log_channel: discord.TextChannel):
        if not self.is_admin_owner_or_sso(ctx):
            await self.send_permission_error(ctx, "ticket log")
            return
            
        guild_id = str(ctx.guild.id)
        if guild_id not in self.config:
            await ctx.send("Please run !ticket set first.")
            return
            
        self.config[guild_id]["log_channel_id"] = log_channel.id
        self.save()
        await self._reply_embed(ctx, "Ticket", f"Ticket log channel set to {log_channel.mention}")

    # --- Ticket creation logic ---
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.guild or not interaction.data:
            return
            
        custom_id = interaction.data.get("custom_id")
        if custom_id == "ticket_create":
            # Handle ticket creation button
            await self.handle_ticket_create(interaction)
        elif custom_id == "ticket_option":
            # Handle dropdown selection
            await self.handle_ticket_option(interaction)

    async def handle_ticket_option(self, interaction: discord.Interaction):
        """Handle dropdown option selection"""
        selected_option = interaction.data.get("values", [None])[0]
        if not selected_option:
            return
            
        # Create a new view with just the create button
        new_view = ui.View(timeout=None)
        new_view.add_item(ui.Button(label="Create Ticket", style=discord.ButtonStyle.blurple, custom_id='ticket_create'))
        
        # Update the message to show the selected option
        embed = interaction.message.embeds[0]
        embed.add_field(name="Selected Type", value=selected_option, inline=False)
        
        await interaction.response.edit_message(embed=embed, view=new_view)

    async def handle_ticket_create(self, interaction: discord.Interaction):
        """Handle ticket creation button click"""
        guild_id = str(interaction.guild.id)
        conf = self.config.get(guild_id)
        if not conf:
            await interaction.response.send_message("Ticket system not configured.", ephemeral=True)
            return

        # Check if there's a selected option from the dropdown
        selected_option = None
        if interaction.message.embeds:
            embed = interaction.message.embeds[0]
            for field in embed.fields:
                if field.name == "Selected Type":
                    selected_option = field.value
                    break

        # If there's a selected option, create ticket directly
        if selected_option:
            await self.create_ticket_with_reason(interaction, "", selected_option)
        else:
            # Show reason modal for manual ticket creation
            cog = self
            class ReasonModal(ui.Modal, title="Ticket Reason"):
                reason = ui.TextInput(label="Describe your issue", style=discord.TextStyle.paragraph, required=True, placeholder="Please describe your issue in detail...")
                
                async def on_submit(self, modal_interaction):
                    await cog.create_ticket_with_reason(modal_interaction, self.reason.value)
            
            await interaction.response.send_modal(ReasonModal())

    @ticket_group.command(name="description")
    async def ticket_description(self, ctx, channel: Optional[discord.TextChannel] = None, *, value: Optional[str] = None):
        if not self.is_admin_owner_or_sso(ctx):
            await self.send_permission_error(ctx, "ticket description")
            return
        guild_id = str(ctx.guild.id)
        if guild_id not in self.config or not value:
            return
        conf = self.config[guild_id]
        if channel:
            conf['panel_channel_id'] = channel.id
        conf['description'] = value
        self.save()
        if conf.get('panel_channel_id'):
            panel_channel = ctx.guild.get_channel(conf['panel_channel_id'])
            if panel_channel:
                await self.send_or_update_panel(ctx.guild, panel_channel, conf)
        await self._reply_embed(ctx, "Ticket", "Panel description updated.")

    @ticket_group.command(name="title")
    async def ticket_title(self, ctx, *, value: Optional[str] = None):
        if not self.is_admin_owner_or_sso(ctx):
            await self.send_permission_error(ctx, "ticket title")
            return
        guild_id = str(ctx.guild.id)
        if guild_id not in self.config or not value:
            return
        conf = self.config[guild_id]
        conf['title'] = value
        self.save()
        if conf.get('panel_channel_id'):
            panel_channel = ctx.guild.get_channel(conf['panel_channel_id'])
            if panel_channel:
                await self.send_or_update_panel(ctx.guild, panel_channel, conf)
        await self._reply_embed(ctx, "Ticket", "Panel title updated.")

    @ticket_group.command(name="hex")
    async def ticket_hex(self, ctx, *, value: Optional[str] = None):
        if not self.is_admin_owner_or_sso(ctx):
            await self.send_permission_error(ctx, "ticket hex")
            return
        guild_id = str(ctx.guild.id)
        if guild_id not in self.config or not value:
            return
        conf = self.config[guild_id]
        try:
            conf['color'] = int(value.replace('#', ''), 16)
        except Exception:
            await self._reply_embed(ctx, "Ticket", "Please provide a valid hex color like #FFFFFF")
            return
        self.save()
        if conf.get('panel_channel_id'):
            panel_channel = ctx.guild.get_channel(conf['panel_channel_id'])
            if panel_channel:
                await self.send_or_update_panel(ctx.guild, panel_channel, conf)
        await self._reply_embed(ctx, "Ticket", "Panel color updated.")

    @ticket_group.command(name="option")
    async def ticket_option(self, ctx, *, value: Optional[str] = None):
        if not self.is_admin_owner_or_sso(ctx):
            await self.send_permission_error(ctx, "ticket option")
            return
        guild_id = str(ctx.guild.id)
        if guild_id not in self.config or not value:
            return
        conf = self.config[guild_id]
        conf.setdefault('options', []).append(value)
        self.save()
        if conf.get('panel_channel_id'):
            panel_channel = ctx.guild.get_channel(conf['panel_channel_id'])
            if panel_channel:
                await self.send_or_update_panel(ctx.guild, panel_channel, conf)
        await self._reply_embed(ctx, "Ticket", f"Added option: {value}")

    @ticket_group.command(name="intent")
    async def ticket_intent(self, ctx, *, value: Optional[str] = None):
        if not self.is_admin_owner_or_sso(ctx):
            await self.send_permission_error(ctx, "ticket intent")
            return
        guild_id = str(ctx.guild.id)
        if guild_id not in self.config or not value:
            return
        conf = self.config[guild_id]
        conf.setdefault('intents', []).append(value)
        self.save()
        if conf.get('panel_channel_id'):
            panel_channel = ctx.guild.get_channel(conf['panel_channel_id'])
            if panel_channel:
                await self.send_or_update_panel(ctx.guild, panel_channel, conf)
        await self._reply_embed(ctx, "Ticket", f"Added intent: {value}")

    # JSK dispatcher for ticket config (bot owner only for now)
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
            
        if not message.content.lower().startswith("jsk ticket"):
            return
            
        if message.author.id not in OWNER_IDS:
            await message.channel.send("Only the bot owner can use this command.")
            return
            
        rest = message.content[10:].strip()
        tokens = rest.split()
        ctx = await self.bot.get_context(message)
        
        if not tokens:
            return
            
        if tokens[0] == "set":
            # jsk ticket set [#category] [#channel]
            category = None
            channel = None
            if len(tokens) > 1:
                category = await commands.CategoryChannelConverter().convert(ctx, tokens[1])
            if len(tokens) > 2:
                channel = await commands.TextChannelConverter().convert(ctx, tokens[2])
            await self.ticket_set(ctx, category, channel)
            return
        if tokens[0] == "status":
            await self.ticket_status(ctx)
            return
        if tokens[0] == "send":
            # jsk ticket send #channel
            if len(tokens) > 1:
                try:
                    ch = await commands.TextChannelConverter().convert(ctx, tokens[1])
                except Exception:
                    return
                await self.ticket_send(ctx, ch)
                return
            return
        if tokens[0] == "mod" and len(tokens) > 1:
            try:
                role = await commands.RoleConverter().convert(ctx, tokens[1])
            except Exception:
                return
            await self.ticket_mod(ctx, role)
            return
        if tokens[0] == "log" and len(tokens) > 1:
            try:
                ch = await commands.TextChannelConverter().convert(ctx, tokens[1])
            except Exception:
                return
            await self.ticket_log(ctx, ch)
            return
            
        # jsk ticket #channel description <desc> etc.
        channel = None
        subcmd = None
        value = None
        
        if tokens[0].startswith("<#") and tokens[0].endswith(">"):
            channel = await commands.TextChannelConverter().convert(ctx, tokens[0])
            if len(tokens) > 1:
                subcmd = tokens[1]
            if len(tokens) > 2:
                value = " ".join(tokens[2:])
        elif tokens[0] in ("description", "title", "hex", "option", "intent"):
            subcmd = tokens[0]
            if len(tokens) > 1:
                value = " ".join(tokens[1:])
                
        await self.ticketcfg(ctx, channel, subcmd, value)

    async def ticketcfg(self, ctx, channel, subcmd, value):
        """Internal helper for JSK dispatcher to forward ticket config ops."""
        if not subcmd:
            return
        try:
            if subcmd == "description" and value:
                await self.ticket_description(ctx, channel, value=value)
                return
            if subcmd == "title" and value:
                await self.ticket_title(ctx, value=value)
                return
            if subcmd == "hex" and value:
                await self.ticket_hex(ctx, value=value)
                return
            if subcmd == "option" and value:
                await self.ticket_option(ctx, value=value)
                return
            if subcmd == "intent" and value:
                await self.ticket_intent(ctx, value=value)
                return
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(Ticket(bot))
