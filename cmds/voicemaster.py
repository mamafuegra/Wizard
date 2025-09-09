import discord
from discord.ext import commands
import json
import asyncio
from typing import Dict, Optional, Set, List
from utils.formatting import quote, grey_strip

CONFIG_FILE = 'voicemaster_config.json'

class VoicePanel(discord.ui.View):
    def __init__(self, owner_id: int, vm: 'VoiceMaster', channel_id: int, *, timeout: Optional[float] = None):
        # Keep the panel responsive for the lifetime of the process
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        self.vm = vm
        self.channel_id = channel_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Allow owner for everything
        if interaction.user.id == self.owner_id:
            return True
        # Permit claim when original owner is not in channel
        cid = (interaction.data or {}).get('custom_id')
        if cid == 'vm_claim':
            channel = interaction.channel
            if isinstance(channel, discord.VoiceChannel):
                if all(m.id != self.owner_id for m in channel.members):
                    return True
                await interaction.response.send_message("Original owner is still in the channel.", ephemeral=True)
                return False
        # Non-owners get a clear ephemeral notice
        try:
            owner_mention = f"<@{self.owner_id}>"
        except Exception:
            owner_mention = "the channel owner"
        await interaction.response.send_message(
            f"Only the VC owner can configure this channel. Ask {owner_mention} or use Claim if they're gone.",
            ephemeral=True,
        )
        return False

    @discord.ui.button(label='Lock', style=discord.ButtonStyle.secondary, custom_id='vm_lock')
    async def lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel: discord.VoiceChannel = interaction.channel  # type: ignore
        everyone = interaction.guild.default_role  # type: ignore
        overwrites = channel.overwrites_for(everyone)
        overwrites.connect = False
        await channel.set_permissions(everyone, overwrite=overwrites)
        await interaction.response.send_message("Channel locked (no one can connect).", ephemeral=True)

    @discord.ui.button(label='Unlock', style=discord.ButtonStyle.secondary, custom_id='vm_unlock')
    async def unlock(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel: discord.VoiceChannel = interaction.channel  # type: ignore
        everyone = interaction.guild.default_role  # type: ignore
        overwrites = channel.overwrites_for(everyone)
        overwrites.connect = True
        await channel.set_permissions(everyone, overwrite=overwrites)
        await interaction.response.send_message("Channel unlocked (everyone can connect).", ephemeral=True)

    @discord.ui.button(label='Reveal', style=discord.ButtonStyle.secondary, custom_id='vm_reveal')
    async def reveal(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel: discord.VoiceChannel = interaction.channel  # type: ignore
        everyone = interaction.guild.default_role  # type: ignore
        overwrites = channel.overwrites_for(everyone)
        overwrites.view_channel = True
        await channel.set_permissions(everyone, overwrite=overwrites)
        await interaction.response.send_message("Channel revealed.", ephemeral=True)

    @discord.ui.button(label='Hide', style=discord.ButtonStyle.secondary, custom_id='vm_hide')
    async def hide(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel: discord.VoiceChannel = interaction.channel  # type: ignore
        everyone = interaction.guild.default_role  # type: ignore
        overwrites = channel.overwrites_for(everyone)
        overwrites.view_channel = False
        await channel.set_permissions(everyone, overwrite=overwrites)
        await interaction.response.send_message("Channel hidden.", ephemeral=True)

    

    @discord.ui.button(label='Rename', style=discord.ButtonStyle.secondary, custom_id='vm_rename')
    async def rename(self, interaction: discord.Interaction, button: discord.ui.Button):
        class RenameModal(discord.ui.Modal, title="Rename Voice Channel"):
            def __init__(self) -> None:
                super().__init__()
                self.name_input = discord.ui.TextInput(
                    label="New channel name",
                    placeholder="Enter a new name",
                    required=True,
                    max_length=96
                )
                self.add_item(self.name_input)

            async def on_submit(self, inter: discord.Interaction) -> None:  # type: ignore[override]
                ch = inter.channel
                if not isinstance(ch, discord.VoiceChannel):
                    await inter.response.send_message("Not in a voice channel.", ephemeral=True)
                    return
                new_name = str(self.name_input.value).strip()[:96]
                await ch.edit(name=new_name)
                await inter.response.send_message("Channel renamed.", ephemeral=True)

        await interaction.response.send_modal(RenameModal())
    @discord.ui.button(label='Claim', style=discord.ButtonStyle.secondary, custom_id='vm_claim')
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Transfer ownership to the user
        # Only allow claim if the previous owner is not present
        channel = interaction.channel
        if isinstance(channel, discord.VoiceChannel):
            if any(m.id == self.owner_id for m in channel.members):
                await interaction.response.send_message("Original owner is still in the channel.", ephemeral=True)
                return
        self.owner_id = interaction.user.id
        self.vm.owner_by_channel[self.channel_id] = self.owner_id
        await interaction.response.send_message("You are now the channel owner.", ephemeral=True)

    @discord.ui.button(label='Transfer', style=discord.ButtonStyle.secondary, custom_id='vm_transfer')
    async def transfer(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Only current owner may transfer ownership
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Only the VC owner can transfer ownership.", ephemeral=True)
            return
        class TransferModal(discord.ui.Modal, title="Transfer VC Ownership"):
            def __init__(self) -> None:
                super().__init__()
                self.user_input = discord.ui.TextInput(
                    label="Mention or ID",
                    placeholder="@user or 1234567890",
                    required=True,
                    max_length=40,
                )
                self.add_item(self.user_input)

            async def on_submit(self, inter: discord.Interaction) -> None:  # type: ignore[override]
                ch = inter.channel
                if not isinstance(ch, discord.VoiceChannel):
                    await inter.response.send_message("Not in a voice channel.", ephemeral=True)
                    return
                import re
                raw = str(self.user_input.value).strip()
                m = re.search(r"(\d{15,25})", raw)
                uid = int(m.group(1)) if m else None
                if not uid:
                    await inter.response.send_message("Couldn't read that user.", ephemeral=True)
                    return
                member = ch.guild.get_member(uid)
                if not member or member not in ch.members:
                    await inter.response.send_message("Target must be in this voice channel.", ephemeral=True)
                    return
                view_ref: VoicePanel = inter.view  # type: ignore
                if member.id == view_ref.owner_id:
                    await inter.response.send_message("That user already owns this VC.", ephemeral=True)
                    return
                # Transfer ownership
                view_ref.owner_id = member.id
                view_ref.vm.owner_by_channel[view_ref.channel_id] = member.id
                await inter.response.send_message(f"Transferred ownership to {member.mention}.", ephemeral=True)

        await interaction.response.send_modal(TransferModal())

    @discord.ui.button(label='Delete', style=discord.ButtonStyle.secondary, custom_id='vm_delete')
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Only the channel owner can delete this VC.", ephemeral=True)
            return
        ch = interaction.channel
        self.vm.owner_by_channel.pop(self.channel_id, None)
        try:
            await interaction.response.send_message("Deleting...", ephemeral=True)
            await ch.delete(reason="VoiceMaster owner delete")  # type: ignore
        except Exception:
            pass

    # ---- member management (kick / ban / unban) ----
    def _channel_and_members(self, interaction: discord.Interaction) -> Optional[tuple[discord.VoiceChannel, List[discord.Member]]]:
        ch = interaction.channel
        if not isinstance(ch, discord.VoiceChannel):
            return None
        members = list(ch.members)
        return ch, members

    @discord.ui.button(label='Kick', style=discord.ButtonStyle.secondary, custom_id='vm_kick')
    async def kick_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        class KickModal(discord.ui.Modal, title="Kick Member from VC"):
            def __init__(self) -> None:
                super().__init__()
                self.user_input = discord.ui.TextInput(
                    label="Mention or ID",
                    placeholder="@user or 1234567890",
                    required=True,
                    max_length=40
                )
                self.add_item(self.user_input)

            async def on_submit(self, inter: discord.Interaction) -> None:  # type: ignore[override]
                ch = inter.channel
                if not isinstance(ch, discord.VoiceChannel):
                    await inter.response.send_message("Not in a voice channel.", ephemeral=True)
                    return
                raw = str(self.user_input.value).strip()
                uid = None
                import re
                m = re.search(r"(\d{15,25})", raw)
                if m:
                    uid = int(m.group(1))
                member = ch.guild.get_member(uid) if uid else None  # type: ignore
                if not member:
                    await inter.response.send_message("Couldn't find that user.", ephemeral=True)
                    return
                if member.id == getattr(inter.view, 'owner_id', 0):  # type: ignore[attr-defined]
                    await inter.response.send_message("You cannot kick the channel owner.", ephemeral=True)
                    return
                try:
                    await member.move_to(None, reason="VoiceMaster kick")
                except Exception:
                    pass
                embed = discord.Embed(description=f"Kicked {member.mention} from the VC.", color=0xFFFFFF)
                try:
                    embed.set_thumbnail(url=member.display_avatar.url)
                except Exception:
                    pass
                await inter.response.send_message(embed=embed, ephemeral=True)

        await interaction.response.send_modal(KickModal())

    @discord.ui.button(label='Ban', style=discord.ButtonStyle.secondary, custom_id='vm_ban')
    async def ban_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        class BanModal(discord.ui.Modal, title="Ban Member from this VC"):
            def __init__(self) -> None:
                super().__init__()
                self.user_input = discord.ui.TextInput(
                    label="Mention or ID",
                    placeholder="@user or 1234567890",
                    required=True,
                    max_length=40
                )
                self.add_item(self.user_input)

            async def on_submit(self, inter: discord.Interaction) -> None:  # type: ignore[override]
                ch = inter.channel
                if not isinstance(ch, discord.VoiceChannel):
                    await inter.response.send_message("Not in a voice channel.", ephemeral=True)
                    return
                raw = str(self.user_input.value).strip()
                import re
                m = re.search(r"(\d{15,25})", raw)
                uid = int(m.group(1)) if m else None
                member = ch.guild.get_member(uid) if uid else None  # type: ignore
                if not member:
                    await inter.response.send_message("Couldn't find that user.", ephemeral=True)
                    return
                if member.id == getattr(inter.view, 'owner_id', 0):  # type: ignore[attr-defined]
                    await inter.response.send_message("You cannot ban the channel owner.", ephemeral=True)
                    return
                ow = ch.overwrites_for(member)
                ow.connect = False
                await ch.set_permissions(member, overwrite=ow)
                try:
                    await member.move_to(None, reason="VoiceMaster VC ban")
                except Exception:
                    pass
                self_ref = getattr(inter.view, 'vm', None)  # type: ignore[attr-defined]
                if self_ref:
                    self_ref.banned_by_channel.setdefault(ch.id, set()).add(member.id)
                embed = discord.Embed(description=f"Banned {member.mention} from this VC.", color=0xFFFFFF)
                try:
                    embed.set_thumbnail(url=member.display_avatar.url)
                except Exception:
                    pass
                await inter.response.send_message(embed=embed, ephemeral=True)

        await interaction.response.send_modal(BanModal())

    @discord.ui.button(label='Unban', style=discord.ButtonStyle.secondary, custom_id='vm_unban')
    async def unban_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        class UnbanModal(discord.ui.Modal, title="Unban Member for this VC"):
            def __init__(self) -> None:
                super().__init__()
                self.user_input = discord.ui.TextInput(
                    label="Mention or ID",
                    placeholder="@user or 1234567890",
                    required=True,
                    max_length=40
                )
                self.add_item(self.user_input)

            async def on_submit(self, inter: discord.Interaction) -> None:  # type: ignore[override]
                ch = inter.channel
                if not isinstance(ch, discord.VoiceChannel):
                    await inter.response.send_message("Not in a voice channel.", ephemeral=True)
                    return
                import re
                raw = str(self.user_input.value).strip()
                m = re.search(r"(\d{15,25})", raw)
                uid = int(m.group(1)) if m else None
                if not uid:
                    await inter.response.send_message("Couldn't read that user.", ephemeral=True)
                    return
                member = ch.guild.get_member(uid)
                target = member or discord.Object(id=uid)
                try:
                    await ch.set_permissions(target, overwrite=None)
                except Exception:
                    pass
                s = getattr(inter.view, 'vm', None)
                if s and uid in s.banned_by_channel.get(ch.id, set()):
                    s.banned_by_channel.get(ch.id, set()).discard(uid)
                embed = discord.Embed(description=f"Unbanned <@{uid}> for this VC.", color=0xFFFFFF)
                if member:
                    try:
                        embed.set_thumbnail(url=member.display_avatar.url)
                    except Exception:
                        pass
                await inter.response.send_message(embed=embed, ephemeral=True)

        await interaction.response.send_modal(UnbanModal())

    # Set limit via modal
    @discord.ui.button(label='Set Limit', style=discord.ButtonStyle.secondary, custom_id='vm_set_limit')
    async def set_limit(self, interaction: discord.Interaction, button: discord.ui.Button):
        class SetLimitModal(discord.ui.Modal, title="Set User Limit"):
            def __init__(self) -> None:
                super().__init__()
                self.limit_input = discord.ui.TextInput(
                    label="Choose a limit for your voice channel",
                    placeholder="Leave blank to reset limit",
                    required=False,
                    max_length=3
                )
                self.add_item(self.limit_input)

            async def on_submit(self, inter: discord.Interaction) -> None:  # type: ignore[override]
                ch = inter.channel
                if not isinstance(ch, discord.VoiceChannel):
                    await inter.response.send_message("Not in a voice channel.", ephemeral=True)
                    return
                raw = str(self.limit_input.value or '').strip()
                if raw == "":
                    new_limit = 0
                else:
                    try:
                        new_limit = max(0, min(99, int(raw)))
                    except Exception:
                        await inter.response.send_message("Please provide a valid number between 0 and 99.", ephemeral=True)
                        return
                await ch.edit(user_limit=new_limit)
                await inter.response.send_message(f"User limit set to {ch.user_limit}.", ephemeral=True)

        await interaction.response.send_modal(SetLimitModal())

    @discord.ui.button(label='Increase', style=discord.ButtonStyle.secondary, custom_id='vm_increase')
    async def increase_limit(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel: discord.VoiceChannel = interaction.channel  # type: ignore
        if not isinstance(channel, discord.VoiceChannel):
            await interaction.response.send_message("Not in a voice channel.", ephemeral=True)
            return
        
        current_limit = channel.user_limit or 0
        if current_limit >= 99:
            await interaction.response.send_message("User limit is already at maximum (99).", ephemeral=True)
            return
        
        new_limit = min(99, current_limit + 1)
        await channel.edit(user_limit=new_limit)
        await interaction.response.send_message(f"User limit increased to {new_limit}.", ephemeral=True)

    @discord.ui.button(label='Decrease', style=discord.ButtonStyle.secondary, custom_id='vm_decrease')
    async def decrease_limit(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel: discord.VoiceChannel = interaction.channel  # type: ignore
        if not isinstance(channel, discord.VoiceChannel):
            await interaction.response.send_message("Not in a voice channel.", ephemeral=True)
            return
        
        current_limit = channel.user_limit or 0
        if current_limit <= 0:
            await interaction.response.send_message("User limit is already at minimum (0).", ephemeral=True)
            return
        
        new_limit = max(0, current_limit - 1)
        await channel.edit(user_limit=new_limit)
        await interaction.response.send_message(f"User limit decreased to {new_limit}.", ephemeral=True)

    @discord.ui.button(label='Information', style=discord.ButtonStyle.secondary, custom_id='vm_info')
    async def show_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel: discord.VoiceChannel = interaction.channel  # type: ignore
        if not isinstance(channel, discord.VoiceChannel):
            await interaction.response.send_message("Not in a voice channel.", ephemeral=True)
            return
        
        embed = discord.Embed(title="Voice Channel Information", color=0xFFFFFF)
        embed.add_field(name="Channel Name", value=channel.name, inline=True)
        embed.add_field(name="User Limit", value=f"{channel.user_limit or 'No limit'}", inline=True)
        embed.add_field(name="Current Members", value=f"{len(channel.members)}", inline=True)
        embed.add_field(name="Category", value=channel.category.name if channel.category else "None", inline=True)
        embed.add_field(name="Created At", value=f"<t:{int(channel.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="Owner", value=f"<@{self.owner_id}>", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class VoiceMaster(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.config: Dict[str, Dict] = self.load_config()
        self.owner_by_channel: Dict[int, int] = {}
        self.banned_by_channel: Dict[int, Set[int]] = {}

    # --------------- config ---------------
    @staticmethod
    def load_config() -> Dict[str, Dict]:
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def save_config(self) -> None:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)

    # --------------- helpers ---------------
    def build_panel(self, member: discord.Member, channel_id: int) -> tuple[discord.Embed, VoicePanel]:
        embed = discord.Embed(title="Voicemaster Menu", color=0xFFFFFF)
        try:
            embed.set_thumbnail(url=member.display_avatar.url)  # type: ignore[attr-defined]
        except Exception:
            pass
        embed.description = (
            "Welcome to the Voicemaster interface! Here you can manage your voice channels with ease. Below are the available options.\n\n"
            + grey_strip("**Lock** - Lock your voice channel") + "\n"
            + grey_strip("**Unlock** - Unlock your voice channel") + "\n"
            + grey_strip("**Hide** - Hide your voice channel") + "\n"
            + grey_strip("**Reveal** - Reveal your hidden voice channel") + "\n"
            + grey_strip("**Rename** - Rename your voice channel") + "\n"
            + grey_strip("**Claim** - Claim an unclaimed voice channel") + "\n"
            + grey_strip("**Increase** - Increase the user limit of your voice channel") + "\n"
            + grey_strip("**Decrease** - Decrease the user limit of your voice channel") + "\n"
            + grey_strip("**Delete** - Delete your voice channel") + "\n"
            + grey_strip("**Information** - View information on the current voice channel")
        )
        view = VoicePanel(owner_id=member.id, vm=self, channel_id=channel_id)
        return embed, view
    def get_join_channel_id(self, guild_id: int) -> Optional[int]:
        entry = self.config.get(str(guild_id))
        if not entry or not entry.get('enabled'):
            return None
        return int(entry.get('join_channel_id')) if entry.get('join_channel_id') else None

    # ---------- permission helpers ----------
    @staticmethod
    def _is_second_owner(guild_id: int, user_id: int) -> bool:
        try:
            with open('second_owners.json', 'r') as f:
                data = json.load(f)
            return str(user_id) == data.get(str(guild_id))
        except Exception:
            return False

    def _is_admin_owner_or_sso(self, ctx: commands.Context) -> bool:
        if ctx.guild is None:
            return False
        if ctx.author.id == ctx.guild.owner_id:
            return True
        if ctx.author.guild_permissions.administrator:
            return True
        if self._is_second_owner(ctx.guild.id, ctx.author.id):
            return True
        return False

    def _is_voice_power_enabled(self, guild_id: int) -> bool:
        entry = self.config.get(str(guild_id))
        return bool(entry and entry.get('power_enabled'))

    async def create_temporary_channel(self, member: discord.Member, join_channel: discord.VoiceChannel) -> Optional[discord.VoiceChannel]:
        category = join_channel.category
        name = f"{member.display_name}'s VC"
        # Some discord.py versions require overwrites to be a dict; use empty dict
        try:
            new_vc = await member.guild.create_voice_channel(name=name, category=category, reason="VoiceMaster create")
        except discord.Forbidden:
            return None
        # Move the member
        try:
            await member.move_to(new_vc, reason="VoiceMaster move")
        except Exception:
            pass
        self.owner_by_channel[new_vc.id] = member.id
        # Send the panel directly in the voice channel's chat if available; set minimal permission overwrites to allow posting if needed.
        embed, view = self.build_panel(member, new_vc.id)
        # Ensure the bot can speak in the VC chat; if not, grant view/send for the bot user only
        try:
            me = member.guild.me  # type: ignore
            if me is not None:
                perms = new_vc.permissions_for(me)
                if not (perms.view_channel and perms.send_messages):
                    ow = new_vc.overwrites_for(me)
                    ow.view_channel = True
                    ow.send_messages = True
                    ow.embed_links = True
                    await new_vc.set_permissions(me, overwrite=ow)
        except Exception:
            pass

        try:
            await new_vc.send(embed=embed, view=view)  # type: ignore[attr-defined]
        except Exception as e:
            # Fallback 1: a text channel in the same category
            fallback: Optional[discord.TextChannel] = None
            try:
                if category:
                    for ch in category.text_channels:  # type: ignore[attr-defined]
                        perms = ch.permissions_for(member.guild.me)  # type: ignore
                        if perms.send_messages and perms.view_channel:
                            fallback = ch
                            break
            except Exception:
                fallback = None
            # Fallback 1b: guild system channel
            if fallback is None:
                try:
                    sys_ch = member.guild.system_channel  # type: ignore
                    if sys_ch:
                        perms = sys_ch.permissions_for(member.guild.me)  # type: ignore
                        if perms.send_messages and perms.view_channel:
                            fallback = sys_ch
                except Exception:
                    pass
            # Fallback 1c: any text channel where the bot can speak
            if fallback is None:
                try:
                    for ch in member.guild.text_channels:  # type: ignore
                        perms = ch.permissions_for(member.guild.me)  # type: ignore
                        if perms.send_messages and perms.view_channel:
                            fallback = ch
                            break
                except Exception:
                    pass
            if fallback is not None:
                try:
                    note = f"Panel for {new_vc.mention} (couldn't post in the voice chat due to permissions or API limits)."
                    await fallback.send(content=note, embed=embed, view=view)
                except Exception as e2:
                    print(f"[VoiceMaster] Failed to send panel to fallback channel: {e2}")
            else:
                # Final fallback: DM the owner
                try:
                    await member.send(content="Here is your VoiceMaster panel (use it to control your VC):", embed=embed, view=view)
                except Exception as e3:
                    print(f"[VoiceMaster] Failed to DM panel: {e3}")
            print(f"[VoiceMaster] Failed to send panel in voice chat: {e}")
        return new_vc

    # --------------- events ---------------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # Joined a channel -> create new VC if it's the join channel
        try:
            join_id = self.get_join_channel_id(member.guild.id)
            if after.channel:
                # Debug log
                print(f"[VoiceMaster] {member} joined {after.channel} (join_id={join_id})")
                is_join = False
                if join_id is not None and after.channel.id == join_id:
                    is_join = True
                elif after.channel.name and after.channel.name.lower().startswith('join to create'):
                    is_join = True
                if is_join:
                    created = await self.create_temporary_channel(member, after.channel)
                    print(f"[VoiceMaster] created VC: {created}")
                    return
        except Exception as e:
            print(f"[VoiceMaster] on_voice_state_update error: {e}")
        # Left a temporary channel -> delete if empty after 3 seconds
        target_channel = before.channel
        if target_channel and target_channel.id in self.owner_by_channel:
            await asyncio.sleep(3)
            # If still empty, delete
            if target_channel and len(target_channel.members) == 0:
                try:
                    await target_channel.delete(reason="VoiceMaster auto-clean")
                except Exception:
                    pass
                self.owner_by_channel.pop(target_channel.id, None)

    # --------------- commands ---------------
    @commands.group(name='voice', invoke_without_command=True)
    async def voice_group(self, ctx: commands.Context):
        """VoiceMaster configuration and setup commands."""
        await ctx.send("VoiceMaster help documentation is available on our website.")

    @voice_group.command(name='set')
    @commands.has_permissions(administrator=True)
    async def voice_set(self, ctx: commands.Context):
        """Show VoiceMaster setup/config in an embed."""
        g = str(ctx.guild.id)
        entry = self.config.get(g)
        enabled = bool(entry and entry.get('enabled'))
        ch = None
        if enabled and entry.get('join_channel_id'):
            ch = ctx.guild.get_channel(int(entry['join_channel_id']))
        embed = discord.Embed(title="VoiceMaster — Setup", color=0xFFFFFF)
        embed.add_field(name="Enabled", value="Yes" if enabled else "No", inline=True)
        embed.add_field(name="Join Channel", value=(ch.mention if isinstance(ch, discord.VoiceChannel) else "None"), inline=True)
        guide_lines = [
            f"Run `{ctx.prefix}voice enable` to create the join channel in this category.",
            "Once enabled, members can join the 'Join to Create' channel to get their own VC.",
            "A control panel will be posted with buttons to rename, lock, hide, set limit, kick/ban, etc.",
            f"Use `{ctx.prefix}voice status` anytime to see current status.",
        ]
        embed.add_field(name="How it works", value="\n".join(guide_lines), inline=False)
        await ctx.send(embed=embed)

    @voice_group.command(name='enable')
    @commands.has_permissions(administrator=True)
    async def voice_enable(self, ctx: commands.Context):
        """Enable VoiceMaster by creating the join-to-create voice channel."""
        # Reuse the logic from vm_set
        await self.vm_set.callback(self, ctx)  # type: ignore[attr-defined]

    # accept common typo "enble"
    @voice_group.command(name='enble')
    @commands.has_permissions(administrator=True)
    async def voice_enble(self, ctx: commands.Context):
        await self.voice_enable(ctx)

    @voice_group.command(name='status')
    async def voice_status(self, ctx: commands.Context):
        """Show VoiceMaster status (no underscores)."""
        await self.vm_status.callback(self, ctx)  # type: ignore[attr-defined]

    # ----- Voice Power (mute/deafen/disconnect) -----
    @voice_group.command(name='power')
    @commands.has_permissions(manage_channels=True)
    async def voice_power_group(self, ctx: commands.Context, action: Optional[str] = None):
        """Enable/disable voice power tools for this guild.
        Usage: voice power enable|disable
        """
        if action is None:
            enabled = self._is_voice_power_enabled(ctx.guild.id)
            
            try:
                from utils.formatting import quote, grey_strip
                embed = discord.Embed(title="Voice Power Status", color=0xFFFFFF)
                embed.description = quote("Voice power tools allow moderators to control voice channel members.")
                embed.add_field(name="Status", value=grey_strip("Enabled" if enabled else "Disabled"), inline=True)
                embed.add_field(name="Server", value=grey_strip(ctx.guild.name), inline=True)
                if enabled:
                    embed.add_field(name="Available Commands", value=grey_strip("voice mute, voice unmute, voice defan, voice undefan, voice disconnect"), inline=False)
                else:
                    embed.add_field(name="To Enable", value=grey_strip("Use 'voice power enable' to activate voice power tools"), inline=False)
            except ImportError:
                embed = discord.Embed(title="Voice Power Status", color=0xFFFFFF)
                embed.add_field(name="Enabled", value="Yes" if enabled else "No", inline=False)
            
            await ctx.send(embed=embed)
            return
        action = action.lower()
        if action in ("enable", "enble"):
            g = str(ctx.guild.id)
            self.config.setdefault(g, {})
            self.config[g]['power_enabled'] = True
            self.save_config()
            
            try:
                from utils.formatting import quote, grey_strip
                embed = discord.Embed(title="Voice Power — Enabled", color=0xFFFFFF)
                embed.description = quote("Mute/Unmute/Deafen/Undeafen/Disconnect tools are now active.")
                embed.add_field(name="Status", value=grey_strip("Voice power tools are now enabled for this server."), inline=False)
                embed.add_field(name="Commands", value=grey_strip("voice mute, voice unmute, voice defan, voice undefan, voice disconnect"), inline=False)
            except ImportError:
                embed = discord.Embed(title="Voice Power — Enabled", color=0xFFFFFF)
                embed.description = "Mute/Unmute/Deafen/Undeafen/Disconnect tools are now active."
            
            await ctx.send(embed=embed)
            return
        if action in ("disable",):
            g = str(ctx.guild.id)
            self.config.setdefault(g, {})
            self.config[g]['power_enabled'] = False
            self.save_config()
            
            try:
                from utils.formatting import quote, grey_strip
                embed = discord.Embed(title="Voice Power — Disabled", color=0xFFFFFF)
                embed.description = quote("Voice power tools are now disabled.")
                embed.add_field(name="Status", value=grey_strip("Voice power tools are no longer available in this server."), inline=False)
            except ImportError:
                embed = discord.Embed(title="Voice Power — Disabled", color=0xFFFFFF)
                embed.description = "Voice power tools are now disabled."
            
            await ctx.send(embed=embed)
            return

    # core actions with per-permission enforcement
    def _power_check(self, ctx: commands.Context, needed: str) -> Optional[str]:
        if not self._is_voice_power_enabled(ctx.guild.id) and not self._is_admin_owner_or_sso(ctx):
            return "Voice power is disabled."
        perms = ctx.author.guild_permissions
        mapping = {
            'mute': perms.mute_members,
            'deafen': perms.deafen_members,
            'disconnect': perms.move_members,
        }
        if self._is_admin_owner_or_sso(ctx):
            return None
        allowed = mapping.get(needed, False)
        if not allowed:
            return f"You don't have {needed} permission."
        return None

    async def _reply_perm_error(self, ctx: commands.Context, text: str) -> None:
        try:
            from utils.formatting import quote, grey_strip
            embed = discord.Embed(title="Voice Power Error", color=0xFFFFFF)
            embed.description = quote(text)
            embed.add_field(name="Server", value=grey_strip(ctx.guild.name), inline=True)
            embed.add_field(name="User", value=grey_strip(ctx.author.display_name), inline=True)
        except ImportError:
            embed = discord.Embed(title="Voice Power Error", color=0xFFFFFF)
            embed.description = text
        
        await ctx.send(embed=embed)

    @voice_group.command(name='mute')
    async def voice_mute(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        err = self._power_check(ctx, 'mute')
        if err:
            await self._reply_perm_error(ctx, err)
            return
        if not member:
            await self._reply_perm_error(ctx, "Provide a member to mute.")
            return
        try:
            await member.edit(mute=True, reason=f"Voice mute by {ctx.author}")
            
            try:
                from utils.formatting import quote, grey_strip
                embed = discord.Embed(title="Voice Power — Muted", color=0xFFFFFF)
                embed.description = quote(f"Successfully muted {member.display_name}")
                embed.add_field(name="User", value=grey_strip(member.mention), inline=True)
                embed.add_field(name="Moderator", value=grey_strip(ctx.author.mention), inline=True)
                embed.add_field(name="Action", value=grey_strip("Voice Mute"), inline=True)
                await ctx.send(embed=embed)
            except ImportError:
                await ctx.message.add_reaction("✅")
        except Exception:
            await self._reply_perm_error(ctx, "Failed to mute this member.")

    @voice_group.command(name='unmute')
    async def voice_unmute(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        err = self._power_check(ctx, 'mute')
        if err:
            await self._reply_perm_error(ctx, err)
            return
        if not member:
            await self._reply_perm_error(ctx, "Provide a member to unmute.")
            return
        try:
            await member.edit(mute=False, reason=f"Voice unmute by {ctx.author}")
            
            try:
                from utils.formatting import quote, grey_strip
                embed = discord.Embed(title="Voice Power — Unmuted", color=0xFFFFFF)
                embed.description = quote(f"Successfully unmuted {member.display_name}")
                embed.add_field(name="User", value=grey_strip(member.mention), inline=True)
                embed.add_field(name="Moderator", value=grey_strip(ctx.author.mention), inline=True)
                embed.add_field(name="Action", value=grey_strip("Voice Unmute"), inline=True)
                await ctx.send(embed=embed)
            except ImportError:
                await ctx.message.add_reaction("✅")
        except Exception:
            await self._reply_perm_error(ctx, "Failed to unmute this member.")

    @voice_group.command(name='defan')
    async def voice_deafen(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        err = self._power_check(ctx, 'deafen')
        if err:
            await self._reply_perm_error(ctx, err)
            return
        if not member:
            await self._reply_perm_error(ctx, "Provide a member to deafen.")
            return
        try:
            await member.edit(deafen=True, reason=f"Voice deafen by {ctx.author}")
            
            try:
                from utils.formatting import quote, grey_strip
                embed = discord.Embed(title="Voice Power — Deafened", color=0xFFFFFF)
                embed.description = quote(f"Successfully deafened {member.display_name}")
                embed.add_field(name="User", value=grey_strip(member.mention), inline=True)
                embed.add_field(name="Moderator", value=grey_strip(ctx.author.mention), inline=True)
                embed.add_field(name="Action", value=grey_strip("Voice Deafen"), inline=True)
                await ctx.send(embed=embed)
            except ImportError:
                await ctx.message.add_reaction("✅")
        except Exception:
            await self._reply_perm_error(ctx, "Failed to deafen this member.")

    @voice_group.command(name='undefan')
    async def voice_undeafen(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        err = self._power_check(ctx, 'deafen')
        if err:
            await self._reply_perm_error(ctx, err)
            return
        if not member:
            await self._reply_perm_error(ctx, "Provide a member to undeafen.")
            return
        try:
            await member.edit(deafen=False, reason=f"Voice undeafen by {ctx.author}")
            
            try:
                from utils.formatting import quote, grey_strip
                embed = discord.Embed(title="Voice Power — Undeafened", color=0xFFFFFF)
                embed.description = quote(f"Successfully undeafened {member.display_name}")
                embed.add_field(name="User", value=grey_strip(member.mention), inline=True)
                embed.add_field(name="Moderator", value=grey_strip(ctx.author.mention), inline=True)
                embed.add_field(name="Action", value=grey_strip("Voice Undeafen"), inline=True)
                await ctx.send(embed=embed)
            except ImportError:
                await ctx.message.add_reaction("✅")
        except Exception:
            await self._reply_perm_error(ctx, "Failed to undeafen this member.")

    @voice_group.command(name='disconnect')
    async def voice_disconnect(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        err = self._power_check(ctx, 'disconnect')
        if err:
            await self._reply_perm_error(ctx, err)
            return
        if not member:
            await self._reply_perm_error(ctx, "Provide a member to disconnect.")
            return
        try:
            await member.move_to(None, reason=f"Voice disconnect by {ctx.author}")
            
            try:
                from utils.formatting import quote, grey_strip
                embed = discord.Embed(title="Voice Power — Disconnected", color=0xFFFFFF)
                embed.description = quote(f"Successfully disconnected {member.display_name}")
                embed.add_field(name="User", value=grey_strip(member.mention), inline=True)
                embed.add_field(name="Moderator", value=grey_strip(ctx.author.mention), inline=True)
                embed.add_field(name="Action", value=grey_strip("Voice Disconnect"), inline=True)
                await ctx.send(embed=embed)
            except ImportError:
                await ctx.message.add_reaction("✅")
        except Exception:
            await self._reply_perm_error(ctx, "Failed to disconnect this member.")
    @commands.command(name='vm_set', aliases=['set_vc'])
    @commands.has_permissions(administrator=True)
    async def vm_set(self, ctx: commands.Context):
        """Create a join-to-create voice channel and enable VoiceMaster."""
        guild = ctx.guild
        if guild is None:
            await ctx.send("This command can only be used in a server.")
            return
        # Create a join to create channel in current category if possible
        category = ctx.channel.category
        try:
            join_vc = await guild.create_voice_channel(name="Join to Create", category=category, reason="Enable VoiceMaster")
        except discord.Forbidden:
            await ctx.send("I don't have permission to create voice channels.")
            return
        gkey = str(guild.id)
        self.config.setdefault(gkey, {})
        self.config[gkey]['enabled'] = True
        self.config[gkey]['join_channel_id'] = str(join_vc.id)
        self.save_config()
        try:
            from utils.formatting import quote, grey_strip
            embed = discord.Embed(title="VoiceMaster — Enabled", color=0xFFFFFF)
            embed.description = quote(f"Join {join_vc.mention} to create your own voice channel.")
            embed.add_field(name="Status", value=grey_strip("VoiceMaster is now active"), inline=True)
            embed.add_field(name="Join Channel", value=grey_strip(join_vc.mention), inline=True)
            embed.add_field(name="Recreate", value=grey_strip(f"Use `{ctx.prefix}voice enable` again if deleted"), inline=False)
        except ImportError:
            embed = discord.Embed(title="VoiceMaster — Enabled", color=0xFFFFFF)
            lines = [
                f"Join {join_vc.mention} to create your own voice channel.",
                f"Use `{ctx.prefix}voice enable` again to recreate if deleted.",
            ]
            embed.description = "\n".join(lines)
        
        await ctx.send(embed=embed)

    @commands.command(name='vm_status')
    async def vm_status(self, ctx: commands.Context):
        g = str(ctx.guild.id)
        entry = self.config.get(g)
        
        try:
            from utils.formatting import quote, grey_strip
            embed = discord.Embed(title="VoiceMaster Status", color=0xFFFFFF)
            embed.description = quote("VoiceMaster voice channel management system")
            
            if not entry or not entry.get('enabled'):
                embed.add_field(name="Status", value=grey_strip("Disabled"), inline=True)
                embed.add_field(name="Server", value=grey_strip(ctx.guild.name), inline=True)
                embed.add_field(name="To Enable", value=grey_strip("Use vm_set command"), inline=False)
            else:
                ch = ctx.guild.get_channel(int(entry.get('join_channel_id'))) if entry.get('join_channel_id') else None
                embed.add_field(name="Status", value=grey_strip("Enabled"), inline=True)
                embed.add_field(name="Server", value=grey_strip(ctx.guild.name), inline=True)
                embed.add_field(name="Join Channel", value=grey_strip(ch.mention if ch else 'None'), inline=True)
        except ImportError:
            embed = discord.Embed(title="VoiceMaster Status", color=0xFFFFFF)
            if not entry or not entry.get('enabled'):
                embed.add_field(name="Enabled", value="No", inline=False)
            else:
                ch = ctx.guild.get_channel(int(entry.get('join_channel_id'))) if entry.get('join_channel_id') else None
                embed.add_field(name="Enabled", value="Yes", inline=False)
                embed.add_field(name="Join Channel", value=(ch.mention if ch else 'None'), inline=True)
        
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VoiceMaster(bot))
