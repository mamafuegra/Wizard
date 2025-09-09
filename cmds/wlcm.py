import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import os
from typing import Dict, Optional


CONFIG_FILE = 'welcome_config.json'


def load_config() -> Dict[str, Dict]:
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_config(config: Dict[str, Dict]) -> None:
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass


def is_second_owner(guild_id: int, user_id: int) -> bool:
    try:
        with open('second_owners.json', 'r') as f:
            data = json.load(f)
        return str(user_id) == data.get(str(guild_id))
    except Exception:
        return False


class WelcomeConfig(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.config = load_config()

    def is_admin_owner_or_sso(self, ctx: commands.Context) -> bool:
        if ctx.guild is None:
            return False
        if ctx.author.id == ctx.guild.owner_id:
            return True
        if ctx.author.guild_permissions.administrator:
            return True
        if is_second_owner(ctx.guild.id, ctx.author.id):
            return True
        # welcome mod role
        conf = self.config.get(str(ctx.guild.id)) or {}
        mod_role_id = conf.get('welcome_mod')
        if mod_role_id:
            role = ctx.guild.get_role(int(mod_role_id))
            if role and role in ctx.author.roles:
                return True
        return False

    @commands.group(name='welcome', aliases=['wl', 'wlcm'], invoke_without_command=True)
    @commands.guild_only()
    async def welcome_group(self, ctx: commands.Context):
        await ctx.send("Welcome help documentation is available on our website.")

    @welcome_group.command(name='set')
    async def welcome_set(self, ctx: commands.Context, channel: discord.TextChannel, state: Optional[str] = None):
        if not self.is_admin_owner_or_sso(ctx):
            await ctx.send("Only Admins, Guild Owner, or Second Owner can use this.")
            return
        g = str(ctx.guild.id)
        self.config.setdefault(g, {})
        self.config[g]['channel_id'] = channel.id
        if state is not None:
            self.config[g]['enabled'] = state.lower() in ('on', 'true', 'enable', 'enabled', 'yes', 'y', '1')
        else:
            self.config[g]['enabled'] = True
        # defaults
        self.config[g].setdefault('use_embed', True)
        self.config[g].setdefault('send_both', False)
        self.config[g].setdefault('message', '')
        self.config[g].setdefault('title', 'Welcome!')
        self.config[g].setdefault('description', 'Glad to have you here, {user.mention}!')
        self.config[g].setdefault('footer_enabled', True)
        self.config[g].setdefault('banner_url', None)
        self.config[g].setdefault('color', 0x5865F2)
        self.config[g].setdefault('button_text', None)
        self.config[g].setdefault('button_url', None)
        save_config(self.config)
        await ctx.send(f"Welcome enabled in {channel.mention}")

    @welcome_group.command(name='mode')
    async def welcome_mode(self, ctx: commands.Context, mode: str):
        if not self.is_admin_owner_or_sso(ctx):
            return
        g = str(ctx.guild.id)
        if g not in self.config:
            await ctx.send("Run welcome set first.")
            return
        
        mode_lower = mode.lower()
        if mode_lower in ('embed', 'e'):
            self.config[g]['use_embed'] = True
            self.config[g]['send_both'] = False
            mode_name = "Embed only"
        elif mode_lower in ('message', 'msg', 'm'):
            self.config[g]['use_embed'] = False
            self.config[g]['send_both'] = False
            mode_name = "Message only"
        elif mode_lower in ('both', 'b', 'hybrid'):
            self.config[g]['use_embed'] = True
            self.config[g]['send_both'] = True
            mode_name = "Both message and embed"
        else:
            await ctx.send("Invalid mode. Use: `embed`, `message`, or `both`")
            return
            
        save_config(self.config)
        await ctx.send(f"Welcome mode set to: **{mode_name}**")

    @welcome_group.command(name='remove')
    async def welcome_remove(self, ctx: commands.Context):
        """Disable welcome and clear all settings for this server."""
        if not self.is_admin_owner_or_sso(ctx):
            await ctx.send("Only Admins, Guild Owner, or Second Owner can use this.")
            return
        g = str(ctx.guild.id)
        if g in self.config:
            del self.config[g]
            save_config(self.config)
            await ctx.send("Welcome configuration removed. Set it again with your prefix commands when ready.")
        else:
            await ctx.send("No welcome configuration found for this server.")

    @welcome_group.command(name='message')
    async def welcome_message(self, ctx: commands.Context, *, text: str):
        if not self.is_admin_owner_or_sso(ctx):
            return
        g = str(ctx.guild.id)
        if g not in self.config:
            await ctx.send("Run welcome set first.")
            return
        self.config[g]['message'] = text
        save_config(self.config)
        await ctx.message.add_reaction('✅')

    @welcome_group.command(name='title')
    async def welcome_title(self, ctx: commands.Context, *, text: str):
        if not self.is_admin_owner_or_sso(ctx):
            return
        g = str(ctx.guild.id)
        if g not in self.config:
            await ctx.send("Run welcome set first.")
            return
        self.config[g]['title'] = text
        save_config(self.config)
        await ctx.message.add_reaction('✅')

    @welcome_group.command(name='description', aliases=['desc'])
    async def welcome_description(self, ctx: commands.Context, *, text: str):
        if not self.is_admin_owner_or_sso(ctx):
            return
        g = str(ctx.guild.id)
        if g not in self.config:
            await ctx.send("Run welcome set first.")
            return
        self.config[g]['description'] = text
        save_config(self.config)
        await ctx.message.add_reaction('✅')

    @welcome_group.command(name='footer')
    async def welcome_footer(self, ctx: commands.Context, toggle: Optional[str] = None):
        if not self.is_admin_owner_or_sso(ctx):
            return
        g = str(ctx.guild.id)
        if g not in self.config:
            await ctx.send("Run welcome set first.")
            return
        if toggle is not None:
            self.config[g]['footer_enabled'] = toggle.lower() in ('on', 'true', 'enable', 'enabled', 'yes', 'y', '1')
        save_config(self.config)
        await ctx.message.add_reaction('✅')

    @welcome_group.command(name='banner')
    async def welcome_banner(self, ctx: commands.Context, *, url_or_off: str):
        if not self.is_admin_owner_or_sso(ctx):
            return
        g = str(ctx.guild.id)
        if g not in self.config:
            await ctx.send("Run welcome set first.")
            return
        val = url_or_off.strip()
        if val.lower() in ('off', 'none', 'disable', 'disabled'):
            self.config[g]['banner_url'] = None
        else:
            self.config[g]['banner_url'] = val
        save_config(self.config)
        await ctx.message.add_reaction('✅')

    @welcome_group.command(name='color')
    async def welcome_color(self, ctx: commands.Context, *, hex_or_int: str):
        if not self.is_admin_owner_or_sso(ctx):
            return
        g = str(ctx.guild.id)
        if g not in self.config:
            await ctx.send("Run welcome set first.")
            return
        raw = hex_or_int.strip().lstrip('#')
        try:
            color = int(raw, 16)
        except Exception:
            try:
                color = int(raw)
            except Exception:
                await ctx.send("Provide a valid color (hex like #5865F2).")
                return
        self.config[g]['color'] = color
        save_config(self.config)
        await ctx.message.add_reaction('✅')

    @welcome_group.command(name='status')
    async def welcome_status(self, ctx: commands.Context):
        g = str(ctx.guild.id)
        conf = self.config.get(g)
        if not conf:
            await ctx.send("Welcome is not configured.")
            return
        ch = ctx.guild.get_channel(conf.get('channel_id')) if conf.get('channel_id') else None
        try:
            from utils.formatting import quote
        except Exception:
            def quote(t: str) -> str:
                return t
        embed = discord.Embed(title="Welcome Status", color=0xFFFFFF)
        # Auto-disable if the configured channel no longer exists
        if ch is None and conf.get('enabled'):
            conf['enabled'] = False
            save_config(self.config)
            embed.add_field(name="Enabled", value=quote("No (channel missing; please run welcome set again)"), inline=False)
            await ctx.send(embed=embed)
            return
        embed.add_field(name="Enabled", value=quote("Yes" if conf.get('enabled') else "No"), inline=False)
        embed.add_field(name="Channel", value=(ch.mention if ch else 'Not set'), inline=True)
        # Determine mode display
        use_embed = conf.get('use_embed', True)
        send_both = conf.get('send_both', False)
        if send_both:
            mode_display = "Both (Message + Embed)"
        elif use_embed:
            mode_display = "Embed only"
        else:
            mode_display = "Message only"
        
        embed.add_field(name="Mode", value=mode_display, inline=True)
        msg_preview = (conf.get('message') or '').strip()
        if len(msg_preview) > 100:
            msg_preview = msg_preview[:97] + '...'
        embed.add_field(name="Message", value=quote(msg_preview or 'None'), inline=False)
        embed.add_field(name="Title", value=conf.get('title', 'None'), inline=True)
        desc_preview = (conf.get('description') or '').strip()
        if len(desc_preview) > 100:
            desc_preview = desc_preview[:97] + '...'
        embed.add_field(name="Description", value=quote(desc_preview or 'None'), inline=False)
        embed.add_field(name="Footer Avatar", value=("On" if conf.get('footer_enabled') else "Off"), inline=True)
        embed.add_field(name="Banner URL", value=(conf.get('banner_url') or 'None'), inline=False)
        embed.add_field(name="Color", value=str(conf.get('color', 0xFFFFFF)), inline=True)
        
        # Button info
        buttons_info = []
        
        # Check for multiple buttons (button1, button2, button3, button4, button5)
        for i in range(1, 6):
            button_text = conf.get(f'button{i}_text')
            button_url = conf.get(f'button{i}_url')
            if button_text and button_url:
                buttons_info.append(f"Button{i}: {button_text} → {button_url}")
        
        # Fallback to old single button format for compatibility
        if not buttons_info:
            button_text = conf.get('button_text')
            button_url = conf.get('button_url')
            if button_text and button_url:
                buttons_info.append(f"Button: {button_text} → {button_url}")
        
        if buttons_info:
            embed.add_field(name="Buttons", value="\n".join(buttons_info), inline=False)
        else:
            embed.add_field(name="Buttons", value="None", inline=True)
        mod_role_id = conf.get('welcome_mod')
        mod_role = ctx.guild.get_role(mod_role_id) if mod_role_id else None
        embed.add_field(name="Welcome Mod", value=(mod_role.mention if mod_role else 'None'), inline=True)
        await ctx.send(embed=embed)

    @welcome_group.command(name='mod')
    async def welcome_mod(self, ctx: commands.Context, role: discord.Role):
        if not self.is_admin_owner_or_sso(ctx):
            return
        g = str(ctx.guild.id)
        self.config.setdefault(g, {})
        self.config[g]['welcome_mod'] = role.id
        save_config(self.config)
        await ctx.send(f"Welcome moderator set to {role.mention}")

    @welcome_group.command(name='button')
    async def welcome_button(self, ctx: commands.Context, text_or_emoji: str, url: str = None):
        if not self.is_admin_owner_or_sso(ctx):
            return
        g = str(ctx.guild.id)
        if g not in self.config:
            await ctx.send("Run welcome set first.")
            return
        
        if text_or_emoji.lower() == 'remove':
            self.config[g]['button_text'] = None
            self.config[g]['button_url'] = None
            save_config(self.config)
            await ctx.send("Welcome button removed.")
            return
        
        if not url:
            await ctx.send("Provide both button text/emoji and URL. Use 'welcome button remove' to remove button.")
            return
        
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            await ctx.send("Please provide a valid URL starting with http:// or https://")
            return
        
        self.config[g]['button_text'] = text_or_emoji
        self.config[g]['button_url'] = url
        save_config(self.config)
        await ctx.send(f"Welcome button set: {text_or_emoji} → {url}")

    @welcome_group.command(name='button1')
    async def welcome_button1(self, ctx: commands.Context, text_or_emoji: str, url: str = None):
        if not self.is_admin_owner_or_sso(ctx):
            return
        g = str(ctx.guild.id)
        if g not in self.config:
            await ctx.send("Run welcome set first.")
            return
        
        if text_or_emoji.lower() == 'remove':
            self.config[g]['button1_text'] = None
            self.config[g]['button1_url'] = None
            save_config(self.config)
            await ctx.send("Welcome button1 removed.")
            return
        
        if not url:
            await ctx.send("Provide both button text/emoji and URL. Use 'welcome button1 remove' to remove button.")
            return
        
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            await ctx.send("Please provide a valid URL starting with http:// or https://")
            return
        
        self.config[g]['button1_text'] = text_or_emoji
        self.config[g]['button1_url'] = url
        save_config(self.config)
        await ctx.send(f"Welcome button1 set: {text_or_emoji} → {url}")

    @welcome_group.command(name='button2')
    async def welcome_button2(self, ctx: commands.Context, text_or_emoji: str, url: str = None):
        if not self.is_admin_owner_or_sso(ctx):
            return
        g = str(ctx.guild.id)
        if g not in self.config:
            await ctx.send("Run welcome set first.")
            return
        
        if text_or_emoji.lower() == 'remove':
            self.config[g]['button2_text'] = None
            self.config[g]['button2_url'] = None
            save_config(self.config)
            await ctx.send("Welcome button2 removed.")
            return
        
        if not url:
            await ctx.send("Provide both button text/emoji and URL. Use 'welcome button2 remove' to remove button.")
            return
        
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            await ctx.send("Please provide a valid URL starting with http:// or https://")
            return
        
        self.config[g]['button2_text'] = text_or_emoji
        self.config[g]['button2_url'] = url
        save_config(self.config)
        await ctx.send(f"Welcome button2 set: {text_or_emoji} → {url}")

    @welcome_group.command(name='button3')
    async def welcome_button3(self, ctx: commands.Context, text_or_emoji: str, url: str = None):
        if not self.is_admin_owner_or_sso(ctx):
            return
        g = str(ctx.guild.id)
        if g not in self.config:
            await ctx.send("Run welcome set first.")
            return
        
        if text_or_emoji.lower() == 'remove':
            self.config[g]['button3_text'] = None
            self.config[g]['button3_url'] = None
            save_config(self.config)
            await ctx.send("Welcome button3 removed.")
            return
        
        if not url:
            await ctx.send("Provide both button text/emoji and URL. Use 'welcome button3 remove' to remove button.")
            return
        
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            await ctx.send("Please provide a valid URL starting with http:// or https://")
            return
        
        self.config[g]['button3_text'] = text_or_emoji
        self.config[g]['button3_url'] = url
        save_config(self.config)
        await ctx.send(f"Welcome button3 set: {text_or_emoji} → {url}")

    @welcome_group.command(name='button4')
    async def welcome_button4(self, ctx: commands.Context, text_or_emoji: str, url: str = None):
        if not self.is_admin_owner_or_sso(ctx):
            return
        g = str(ctx.guild.id)
        if g not in self.config:
            await ctx.send("Run welcome set first.")
            return
        
        if text_or_emoji.lower() == 'remove':
            self.config[g]['button4_text'] = None
            self.config[g]['button4_url'] = None
            save_config(self.config)
            await ctx.send("Welcome button4 removed.")
            return
        
        if not url:
            await ctx.send("Provide both button text/emoji and URL. Use 'welcome button4 remove' to remove button.")
            return
        
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            await ctx.send("Please provide a valid URL starting with http:// or https://")
            return
        
        self.config[g]['button4_text'] = text_or_emoji
        self.config[g]['button4_url'] = url
        save_config(self.config)
        await ctx.send(f"Welcome button4 set: {text_or_emoji} → {url}")

    @welcome_group.command(name='button5')
    async def welcome_button5(self, ctx: commands.Context, text_or_emoji: str, url: str = None):
        if not self.is_admin_owner_or_sso(ctx):
            return
        g = str(ctx.guild.id)
        if g not in self.config:
            await ctx.send("Run welcome set first.")
            return
        
        if text_or_emoji.lower() == 'remove':
            self.config[g]['button5_text'] = None
            self.config[g]['button5_url'] = None
            save_config(self.config)
            await ctx.send("Welcome button5 removed.")
            return
        
        if not url:
            await ctx.send("Provide both button text/emoji and URL. Use 'welcome button5 remove' to remove button.")
            return
        
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            await ctx.send("Please provide a valid URL starting with http:// or https://")
            return
        
        self.config[g]['button5_text'] = text_or_emoji
        self.config[g]['button5_url'] = url
        save_config(self.config)
        await ctx.send(f"Welcome button5 set: {text_or_emoji} → {url}")

    @welcome_group.command(name='preview')
    async def welcome_preview(self, ctx: commands.Context):
        if not self.is_admin_owner_or_sso(ctx):
            await ctx.send("Only Admins, Guild Owner, or Second Owner can use this.")
            return
        
        g = str(ctx.guild.id)
        if g not in self.config:
            await ctx.send("Run welcome set first.")
            return
        
        conf = self.config[g]
        if not conf.get('enabled'):
            await ctx.send("Welcome is not enabled. Run welcome set first.")
            return
        
        # Create a preview member (the command author)
        preview_member = ctx.author
        
        # Format the message template
        try:
            from welcome import WelcomeCog
            welcome_cog = WelcomeCog(self.bot)
            pre_message = welcome_cog.format_template(conf.get('message', ''), preview_member)
        except:
            # Fallback formatting if welcome cog not available
            pre_message = conf.get('message', '').replace('{user.mention}', preview_member.mention).replace('{user.name}', preview_member.name).replace('{guild.name}', ctx.guild.name).replace('{member_count}', str(ctx.guild.member_count))
        
        # Check mode
        send_both = conf.get('send_both', False)
        use_embed = conf.get('use_embed', True)
        
        if not use_embed:
            # Message-only preview
            content = pre_message or f"Welcome {preview_member.mention} to {ctx.guild.name}!"
            await ctx.send("**Welcome Preview (Message Mode):**")
            await ctx.send(content)
            return
        
        # Build embed preview
        title = conf.get('title', 'Welcome!').replace('{user.mention}', preview_member.mention).replace('{user.name}', preview_member.name).replace('{guild.name}', ctx.guild.name).replace('{member_count}', str(ctx.guild.member_count))
        description = conf.get('description', '').replace('{user.mention}', preview_member.mention).replace('{user.name}', preview_member.name).replace('{guild.name}', ctx.guild.name).replace('{member_count}', str(ctx.guild.member_count))
        color_val = conf.get('color', 0xFFFFFF)
        
        try:
            color = discord.Color(color_val)
        except Exception:
            color = discord.Color.from_rgb(255, 255, 255)
        
        embed = discord.Embed(title=title, description=description, color=color)
        
        # Thumbnail: user's avatar
        try:
            embed.set_thumbnail(url=preview_member.display_avatar.url)
        except Exception:
            pass
        
        # Image: configured banner URL
        banner_url = conf.get('banner_url')
        if banner_url:
            try:
                embed.set_image(url=banner_url)
            except Exception:
                pass
        
        # Footer: show user's avatar when enabled
        if conf.get('footer_enabled', False):
            try:
                embed.set_footer(text='\u200b', icon_url=preview_member.display_avatar.url)
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
                    print(f"Button{i} creation error: {e}")
        
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
                    print(f"Single button creation error: {e}")
                    view = None
        
        # Send preview based on mode
        if send_both:
            await ctx.send("**Welcome Preview (Both Mode):**")
            if pre_message:
                await ctx.send(pre_message)
            await ctx.send(embed=embed, view=view)
        else:
            await ctx.send("**Welcome Preview (Embed Mode):**")
            content = pre_message if pre_message else None
            await ctx.send(content=content, embed=embed, view=view)

    @commands.command(name='setwelcome')
    @commands.guild_only()
    async def setwelcome(self, ctx: commands.Context, channel: discord.TextChannel, *, message: Optional[str] = None):
        if not self.is_admin_owner_or_sso(ctx):
            await ctx.send("Only Admins, Guild Owner, or Second Owner can use this.")
            return
        g = str(ctx.guild.id)
        self.config.setdefault(g, {})
        self.config[g]['channel_id'] = channel.id
        self.config[g]['enabled'] = True
        self.config[g]['use_embed'] = False
        self.config[g]['send_both'] = False
        self.config[g]['message'] = message or '{user.mention} welcome to {guild.name}!'
        self.config[g]['button_text'] = None
        self.config[g]['button_url'] = None
        save_config(self.config)
        await ctx.send(f"Message-only welcome set in {channel.mention}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WelcomeConfig(bot))



