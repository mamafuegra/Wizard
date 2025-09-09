import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import os
from typing import Dict, Optional


CONFIG_FILE = 'welcome_config.json'


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.config: Dict[str, Dict] = self.load_config()

    # --------------- config helpers ---------------
    @staticmethod
    def load_config() -> Dict[str, Dict]:
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    @staticmethod
    def save_config(config: Dict[str, Dict]) -> None:
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except Exception:
            pass

    # --------------- templating ---------------
    @staticmethod
    def format_template(template: str, member: discord.Member) -> str:
        if not template:
            return ''
        guild = member.guild
        safe = template
        try:
            replacements = {
                '{user.mention}': member.mention,
                '{user.name}': member.name,
                '{user.display_name}': member.display_name,
                '{user.id}': str(member.id),
                '{guild.name}': guild.name,
                '{guild.id}': str(guild.id),
                '{member_count}': str(guild.member_count or 0),
            }
            for key, val in replacements.items():
                safe = safe.replace(key, val)
        except Exception:
            pass
        return safe

    def get_guild_conf(self, guild_id: int) -> Optional[Dict]:
        return self.config.get(str(guild_id))

    # --------------- event ---------------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            # Reload latest config in case it was changed at runtime via commands
            self.config = self.load_config()
            conf = self.get_guild_conf(member.guild.id)
            if not conf or not conf.get('enabled'):
                return
            channel_id = conf.get('channel_id')
            if not channel_id:
                return
            channel = member.guild.get_channel(int(channel_id))
            if not isinstance(channel, (discord.TextChannel, discord.Thread)):
                channel = None

            # Determine a channel we can actually send in
            def can_send(ch: discord.abc.GuildChannel) -> bool:  # type: ignore
                try:
                    me = member.guild.me  # type: ignore
                    if me is None:
                        return False
                    perms = ch.permissions_for(me)  # type: ignore
                    return bool(perms.view_channel and perms.send_messages)
                except Exception:
                    return False

            # Require an explicitly configured channel that exists and is sendable.
            target = channel if channel and can_send(channel) else None
            if target is None:
                # Auto-disable welcome until owner/second owner sets a valid channel again.
                gkey = str(member.guild.id)
                try:
                    conf['enabled'] = False
                    self.config[gkey] = conf
                    self.save_config(self.config)
                except Exception:
                    pass
                return

            # Build message content (pre-embed message)
            pre_message = self.format_template(conf.get('message', ''), member)

            # Check if we should send both message and embed
            send_both = conf.get('send_both', False)
            
            if not conf.get('use_embed', True):
                # Message-only
                content = pre_message or f"Welcome {member.mention} to {member.guild.name}!"
                await target.send(content)
                return

            # Build embed like Mimu-style
            title = self.format_template(conf.get('title', 'Welcome!'), member)
            description = self.format_template(conf.get('description', ''), member)
            color_val = conf.get('color', 0xFFFFFF)
            try:
                color = discord.Color(color_val)
            except Exception:
                color = discord.Color.from_rgb(255, 255, 255)

            embed = discord.Embed(title=title, description=description, color=color)

            # Thumbnail: user's avatar
            try:
                embed.set_thumbnail(url=member.display_avatar.url)
            except Exception:
                pass

            # Image: configured banner URL or user's banner if available
            banner_url = conf.get('banner_url')
            used_banner = False
            if banner_url:
                try:
                    embed.set_image(url=banner_url)
                    used_banner = True
                except Exception:
                    used_banner = False
            if not used_banner:
                try:
                    fetched = await member.fetch()
                    if getattr(fetched, 'banner', None):
                        embed.set_image(url=fetched.banner.url)
                except Exception:
                    pass

            # Footer: show joined user's avatar when enabled (embed only)
            if conf.get('footer_enabled', False) and conf.get('use_embed', True):
                try:
                    embed.set_footer(text='\u200b', icon_url=member.display_avatar.url)
                except Exception:
                    embed.set_footer(text='\u200b')

            # Create buttons if configured
            view = None
            buttons_created = False
            
            # Check for multiple buttons (button1, button2, button3, button4, button5)
            for i in range(1, 6):
                button_text = conf.get(f'button{i}_text')
                button_url = conf.get(f'button{i}_url')
                if button_text and button_url:
                    try:
                        if view is None:
                            view = View(timeout=None)  # No timeout for persistent views
                        
                        button = Button(
                            label=button_text if len(button_text) <= 80 else button_text[:77] + "...",
                            url=button_url,
                            style=discord.ButtonStyle.link  # Use link style for URL buttons
                        )
                        view.add_item(button)
                        buttons_created = True
                    except Exception as e:
                        print(f"[Welcome] Button{i} creation error: {e}")
            
            # Fallback to old single button format for compatibility
            if not buttons_created:
                button_text = conf.get('button_text')
                button_url = conf.get('button_url')
                if button_text and button_url:
                    try:
                        view = View(timeout=None)
                        button = Button(
                            label=button_text if len(button_text) <= 80 else button_text[:77] + "...",
                            url=button_url,
                            style=discord.ButtonStyle.link
                        )
                        view.add_item(button)
                    except Exception as e:
                        print(f"[Welcome] Single button creation error: {e}")
                        view = None

            # Send based on mode
            if send_both:
                # Send both message and embed
                if pre_message:
                    await target.send(pre_message)
                await target.send(embed=embed, view=view)
            else:
                # Send embed with optional pre-message
                content = pre_message if pre_message else None
                await target.send(content=content, embed=embed, view=view)
        except Exception as e:
            try:
                print(f"[Welcome] on_member_join error: {e}")
            except Exception:
                pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Welcome(bot))


