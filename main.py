import discord
import random
from discord.ext import commands
import os
import json
from dotenv import load_dotenv
from utils.formatting import quote


# Load environment variables from .env file
load_dotenv()

# Default prefix
DEFAULT_PREFIX = '!'

# Function to get prefix
def get_prefix(bot, message):
    # If DM, use default prefix
    if message.guild is None:
        return DEFAULT_PREFIX
    
    # Try to load from prefixes.json
    try:
        with open('prefixes.json', 'r') as f:
            prefixes = json.load(f)
        return prefixes.get(str(message.guild.id), DEFAULT_PREFIX)
    except (FileNotFoundError, json.JSONDecodeError):
        # If file doesn't exist or is invalid, use default
        return DEFAULT_PREFIX

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # needed for accurate human/bot counts across servers
intents.presences = True  # required for vanity status tracking
bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None)

# Helper function to check if a user is a second owner
def is_second_owner(guild_id, user_id):
    try:
        with open('second_owners.json', 'r') as f:
            second_owners = json.load(f)
        return str(user_id) == second_owners.get(str(guild_id), None)
    except (FileNotFoundError, json.JSONDecodeError):
        return False



# Wizard-style responses
WIZARD_QUOTES = [
    "Bite my shiny metal ass!",
    "I'm 40% back in business, baby!",
    "Aww, it's a little baby beer! I'll put it with the others.",
    "Game's over, losers! I have all the money. Compare your lives to mine and then kill yourselves!",
    "I'm going to build my own theme park with blackjack and hookers. In fact, forget the park!",
    "Hey sexy mama, wanna kill all humans?",
    "Bender is great, oh Bender is great, Bender Bender Bender!",
    "I don't tell you how to tell me what to do, so don't tell me how to do what you tell me to do!",
    "Ah, she's built like a steakhouse but she handles like a bistro!",
    "Shut up baby, I know it!",
    "Compare your lives to mine and then kill yourselves!",
    "I'm back, baby!",
    "Neat! *takes picture*",
    "Well, I'm screwed.",
    "Me, Bender, am going to allow this."
]

WIZARD_GREETINGS = [
    "What's up, meatbags?",
    "Ol' Bender's here to save the day!",
    "Guess who just got back, baby!",
    "It's me, Bender! The lovable scamp!",
    "Hail, hail, the gang's all here! What the hell do you care?"
]

WIZARD_INSULTS = [
    "You call that an insult? I've heard better comebacks from a vending machine!",
    "Your code runs slower than a sloth on tranquilizers!",
    "If you were a robot, you'd be running on Windows ME!",
    "You couldn't debug your way out of a paper bag!",
    "Your logic circuits must be malfunctioning, meatbag!"
]

@bot.event
async def on_ready():
    print(f'{bot.user.name} is online and ready to cast spells!')
    print('------')
    # Track start time for uptime
    try:
        import datetime as _dt
        bot.start_time = _dt.datetime.utcnow()
    except Exception:
        pass
    
    # Set streaming status
    try:
        streaming_activity = discord.Streaming(
            name="🔗 wizard.spell",
            url="https://www.twitch.tv/impalewizardbot"
        )
        await bot.change_presence(activity=streaming_activity, status=discord.Status.online)
        print('✅ Streaming status set successfully!')
    except Exception as e:
        print(f'❌ Failed to set streaming status: {e}')
    
    # Sync slash commands with Discord
    try:
        print('🔄 Syncing slash commands...')
        await bot.tree.sync()
        print('✅ Slash commands synced successfully!')
    except Exception as e:
        print(f'❌ Failed to sync slash commands: {e}')
    
    # Create prefixes.json if it doesn't exist
    try:
        with open('prefixes.json', 'r') as f:
            json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        with open('prefixes.json', 'w') as f:
            json.dump({}, f)
            
    # Create second_owners.json if it doesn't exist
    try:
        with open('second_owners.json', 'r') as f:
            json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        with open('second_owners.json', 'w') as f:
            json.dump({}, f)


@bot.event
async def on_message(message):
    """Global bot ping handler - replies with prefix only."""
    # Process commands first
    await bot.process_commands(message)
    
    # Ignore bot messages and DMs
    if message.author.bot or not message.guild:
        return
    
    # Check if bot is mentioned (either by @mention or by name)
    bot_mentioned = (
        bot.user in message.mentions or 
        bot.user.name.lower() in message.content.lower() or
        bot.user.display_name.lower() in message.content.lower()
    )
    
    if bot_mentioned:
        # Get the bot's prefix for this guild
        prefix = get_prefix(bot, message)
        
        embed = discord.Embed(
            description=f"Your prefix is: `{prefix}`",
            color=0xFFFFFF  # White hex color
        )
        
        await message.channel.send(embed=embed)

@bot.command(name='quote')
async def quote(ctx):
    """Responds with a random Wizard quote"""
    await ctx.send(random.choice(WIZARD_QUOTES))

@bot.command(name='insult')
async def insult(ctx, member: discord.Member = None):
    """Wizard insults a specified user or the command user if no one is specified"""
    if member is None:
        await ctx.send(f"{ctx.author.mention} {random.choice(WIZARD_INSULTS)}")
    else:
        await ctx.send(f"{member.mention} {random.choice(WIZARD_INSULTS)}")

@bot.command(name='cast')
async def cast(ctx, *, spell):
    """Wizard will cast the specified spell"""
    responses = [
        f"I just cast {spell}! *waves wand dramatically*",
        f"Behold the power of {spell}!",
        f"By the ancient arts, I summon {spell}!",
        f"*Mutters arcane words* {spell} is now in effect!"
    ]
    await ctx.send(random.choice(responses))

@bot.command(name='potion')
async def potion(ctx):
    """Wizard drinks a magical potion"""
    responses = [
        "*Drinks a bubbling blue potion* I can see through time now!",
        "This potion grants me the wisdom of the ancients!",
        "*Sips from a glowing vial* My power grows stronger!",
        "Ah, a refreshing mana potion to restore my magical energy!",
        "*Drinks a swirling purple liquid* I feel the arcane forces flowing through me!"
    ]
    await ctx.send(random.choice(responses))





@bot.command(name='bothelp', aliases=['h', 'commands', 'help'])
async def help_command(ctx):
    await ctx.send(f"{ctx.author.mention}: Help documentation is available on our website https://wizardspell.netlify.app/.")

@bot.command(name='jsk_help', aliases=['jskhelp'])
async def jsk_help(ctx):
    await ctx.send(f"{ctx.author.mention}: Help documentation is available on our website https://wizardspell.netlify.app/.")

@bot.command(name='sync')
async def sync_commands(ctx):
    """Sync slash commands with Discord (Owner/Admin only)"""
    if not (ctx.author.guild_permissions.administrator or is_second_owner(ctx.guild.id, ctx.author.id)):
        await ctx.send("❌ Only administrators or second owners can sync commands.")
        return
    
    try:
        await ctx.send("🔄 Syncing slash commands...")
        await bot.tree.sync()
        await ctx.send("✅ Slash commands synced successfully!")
    except Exception as e:
        await ctx.send(f"❌ Failed to sync slash commands: {e}")

@bot.command(name='prefix')
async def prefix(ctx, new_prefix=None):
    """Change the command prefix for this server"""
    # If no prefix provided or in DMs, show current prefix
    if new_prefix is None or ctx.guild is None:
        current_prefix = get_prefix(bot, ctx.message)
        await ctx.send(f"Current prefix is: `{current_prefix}`")
        return
    
    # Check if user has permission to change prefix
    if not (ctx.author.guild_permissions.administrator or 
            ctx.author.id == ctx.guild.owner_id or 
            is_second_owner(ctx.guild.id, ctx.author.id)):
        await ctx.send("You need administrator permissions to change the prefix!")
        return
    
    # Update prefix in prefixes.json
    try:
        with open('prefixes.json', 'r') as f:
            prefixes = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        prefixes = {}
    
    prefixes[str(ctx.guild.id)] = new_prefix
    
    with open('prefixes.json', 'w') as f:
        json.dump(prefixes, f)
    
    embed = discord.Embed(
        description=f"Prefix changed to: `{new_prefix}`",
        color=0xFFFFFF  # White hex color
    )
    await ctx.send(embed=embed)

@bot.group(name='secondowner', aliases=['so'])
async def secondowner(ctx):
    """Second owner management commands"""
    if ctx.invoked_subcommand is None:
        await ctx.send("Second owner help documentation is available on our website https://wizardspell.netlify.app/.")

@secondowner.command(name='set')
async def set_second_owner(ctx, member: discord.Member = None):
    """Set a second owner for the server (Guild owner only)"""
    if not ctx.guild:
        await ctx.send("This command can only be used in a server!")
        return
        
    if ctx.author.id != ctx.guild.owner_id:
        await ctx.send("Only the guild owner can set a second owner!")
        return
        
    if member is None:
        await ctx.send("Please mention a user to set as second owner!")
        return
    
    # Check if trying to set guild owner as second owner
    if member.id == ctx.guild.owner_id:
        await ctx.send("You are already the guild owner, poser!")
        return
        
    # Update second_owners.json
    try:
        with open('second_owners.json', 'r') as f:
            second_owners = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        second_owners = {}
    
    # Check if there's already a second owner
    if str(ctx.guild.id) in second_owners:
        await ctx.send(f"There is already a second owner set for this server. Use `{get_prefix(bot, ctx.message)}remove secondowner` to remove them first.")
        return
    
    second_owners[str(ctx.guild.id)] = str(member.id)
    
    with open('second_owners.json', 'w') as f:
        json.dump(second_owners, f)
    
    await ctx.send(f"{member.mention} has been set as the second owner of this server!")

@secondowner.command(name='view')
async def view_second_owner(ctx):
    """View the current second owner of the server"""
    if not ctx.guild:
        await ctx.send("This command can only be used in a server!")
        return
        
    try:
        with open('second_owners.json', 'r') as f:
            second_owners = json.load(f)
            
        second_owner_id = second_owners.get(str(ctx.guild.id), None)
        
        if second_owner_id:
            second_owner = ctx.guild.get_member(int(second_owner_id))
            if second_owner:
                await ctx.send(f"The second owner of this server is: {second_owner.mention}")
            else:
                await ctx.send("The second owner is no longer in this server.")
        else:
            await ctx.send("This server does not have a second owner set.")
            
    except (FileNotFoundError, json.JSONDecodeError):
        await ctx.send("This server does not have a second owner set.")

@bot.command(name='sso')
async def sso(ctx, member: discord.Member = None):
    """Shortcut for secondowner set command"""
    # Call the set_second_owner function directly
    await set_second_owner(ctx, member)

@secondowner.command(name='remove_so')
async def remove_second_owner(ctx):
    """Remove the second owner for the server (Guild owner only)"""
    if not ctx.guild:
        await ctx.send("This command can only be used in a server!")
        return
        
    if ctx.author.id != ctx.guild.owner_id:
        await ctx.send("Only the guild owner can remove a second owner!")
        return
    
    # Update second_owners.json
    try:
        with open('second_owners.json', 'r') as f:
            second_owners = json.load(f)
            
        if str(ctx.guild.id) in second_owners:
            del second_owners[str(ctx.guild.id)]
            
            with open('second_owners.json', 'w') as f:
                json.dump(second_owners, f)
                
            await ctx.send("Second owner has been removed from this server!")
        else:
            await ctx.send("This server does not have a second owner set.")
            
    except (FileNotFoundError, json.JSONDecodeError):
        await ctx.send("This server does not have a second owner set.")

@bot.command(name='remove_cmd')
async def remove_cmd(ctx, option=None, member: discord.Member = None):
    """Remove command for various options"""
    if option is None:
        await ctx.send(f"Please specify what you want to remove. Use `{get_prefix(bot, ctx.message)}remove sso @user` to remove the second owner.")
        return
        
    if option.lower() == 'sso':
        if not ctx.guild:
            await ctx.send("This command can only be used in a server!")
            return
            
        if ctx.author.id != ctx.guild.owner_id:
            await ctx.send("Only the guild owner can remove a second owner!")
            return
            
        if member is None:
            await ctx.send("Please mention a user to remove as second owner!")
            return
        
        # Update second_owners.json
        try:
            with open('second_owners.json', 'r') as f:
                second_owners = json.load(f)
                
            if str(ctx.guild.id) in second_owners:
                # Check if the mentioned user is actually the second owner
                if str(member.id) == second_owners[str(ctx.guild.id)]:
                    del second_owners[str(ctx.guild.id)]
                    
                    with open('second_owners.json', 'w') as f:
                        json.dump(second_owners, f)
                        
                    await ctx.send(f"{member.mention} has been removed as the second owner of this server!")
                else:
                    await ctx.send(f"{member.mention} is not the second owner of this server!")
            else:
                await ctx.send("This server does not have a second owner set.")
                
        except (FileNotFoundError, json.JSONDecodeError):
            await ctx.send("This server does not have a second owner set.")
    elif option.lower() == 'secondowner':
        # For backward compatibility
        if not ctx.guild:
            await ctx.send("This command can only be used in a server!")
            return
            
        if ctx.author.id != ctx.guild.owner_id:
            await ctx.send("Only the guild owner can remove a second owner!")
            return
        
        # Update second_owners.json
        try:
            with open('second_owners.json', 'r') as f:
                second_owners = json.load(f)
                
            if str(ctx.guild.id) in second_owners:
                del second_owners[str(ctx.guild.id)]
                
                with open('second_owners.json', 'w') as f:
                    json.dump(second_owners, f)
                    
                await ctx.send("Second owner has been removed from this server!")
            else:
                await ctx.send("This server does not have a second owner set.")
                
        except (FileNotFoundError, json.JSONDecodeError):
            await ctx.send("This server does not have a second owner set.")
    else:
        await ctx.send(f"Unknown option: {option}")



# Load command cogs
async def load_extensions():
    """Load all command cogs"""
    try:
        await bot.load_extension('cmds.jail')
        print("✅ Loaded jail command")
    except Exception as e:
        print(f"❌ Failed to load jail command: {e}")
    try:
        await bot.load_extension('cmds.info')
        print("✅ Loaded info commands (serverinfo/userinfo)")
    except Exception as e:
        print(f"❌ Failed to load info commands: {e}")
    try:
        await bot.load_extension('cmds.owner_tools')
        print("✅ Loaded owner tools (jsk + moderation)")
    except Exception as e:
        print(f"❌ Failed to load owner tools: {e}")
    try:
        await bot.load_extension('cmds.fun')
        print("✅ Loaded fun commands (bully)")
    except Exception as e:
        print(f"❌ Failed to load fun commands: {e}")
    try:
        await bot.load_extension('cmds.voicemaster')
        print("✅ Loaded voice master")
    except Exception as e:
        print(f"❌ Failed to load voice master: {e}")
    try:
        await bot.load_extension('cmds.purge')
        print("✅ Loaded purge command")
    except Exception as e:
        print(f"❌ Failed to load purge command: {e}")
    try:
        await bot.load_extension('cmds.ticket')
        print("✅ Loaded ticket command")
    except Exception as e:
        print(f"❌ Failed to load ticket command: {e}")
        import traceback
        traceback.print_exc()
    try:
        await bot.load_extension('cmds.vanity')
        print("✅ Loaded vanity/booster system")
    except Exception as e:
        print(f"❌ Failed to load vanity/booster system: {e}")
    try:
        await bot.load_extension('welcome')
        print("✅ Loaded welcome listener")
    except Exception as e:
        print(f"❌ Failed to load welcome listener: {e}")
    try:
        await bot.load_extension('cmds.wlcm')
        print("✅ Loaded welcome configuration commands")
    except Exception as e:
        print(f"❌ Failed to load welcome configuration commands: {e}")
    try:
        await bot.load_extension('cmds.automod')
        print("✅ Loaded automod")
    except Exception as e:
        print(f"❌ Failed to load automod: {e}")
    try:
        await bot.load_extension('cmds.antinuke')
        print("✅ Loaded antinuke")
    except Exception as e:
        print(f"❌ Failed to load antinuke: {e}")
    try:
        await bot.load_extension('cmds.emoji')
        print("✅ Loaded emoji tools")
    except Exception as e:
        print(f"❌ Failed to load emoji tools: {e}")
    try:
        await bot.load_extension('cmds.nickname')
        print("✅ Loaded nickname command")
    except Exception as e:
        print(f"❌ Failed to load nickname command: {e}")
    try:
        await bot.load_extension('cmds.manage')
        print("✅ Loaded channel manage commands (hide/lock)")
    except Exception as e:
        print(f"❌ Failed to load channel manage commands: {e}")
    try:
        await bot.load_extension('cmds.role')
        print("✅ Loaded role management system")
    except Exception as e:
        print(f"❌ Failed to load role management system: {e}")
    try:
        await bot.load_extension('cmds.buttonrole')
        print("✅ Loaded button role system")
    except Exception as e:
        print(f"❌ Failed to load button role system: {e}")
    try:
        await bot.load_extension('cmds.embed')
        print("✅ Loaded embed creator (slash commands)")
    except Exception as e:
        print(f"❌ Failed to load embed creator: {e}")
    try:
        await bot.load_extension('cmds.giveaway')
        print("✅ Loaded giveaway system (slash commands)")
    except Exception as e:
        print(f"❌ Failed to load giveaway system: {e}")
    try:
        await bot.load_extension('cmds.join')
        print("✅ Loaded join roles")
    except Exception as e:
        print(f"❌ Failed to load join roles: {e}")
    try:
        await bot.load_extension('cmds.premium')
        print("✅ Loaded premium/AI commands")
    except Exception as e:
        print(f"❌ Failed to load premium/AI commands: {e}")
    try:
        await bot.load_extension('cmds.spotify')
        print("✅ Loaded Spotify integration")
    except Exception as e:
        print(f"❌ Failed to load Spotify integration: {e}")

# Run the bot
if __name__ == '__main__':
    import asyncio
    
    async def main():
        await load_extensions()
        token = os.getenv('DISCORD_TOKEN')
        if not token:
            print("Error: No Discord token found. Please create a .env file with your DISCORD_TOKEN.")
        else:
            await bot.start(token)
    
    asyncio.run(main())
