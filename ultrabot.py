import logging
from colorama import Fore, Style
import discord
from discord.ext import commands
import asyncio
import random
import os
import re
from datetime import datetime
import queue
import threading
import aiohttp
import sys
import requests

# made by jinn
# Clear screen and prompt for token
TOKEN = ""
PREFIX = "."
logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.presences = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, self_bot=True)

# Global variables
deleted_messages = {}
edited_messages = {}
auto_reply_target_id = None
auto_reply_message = None
autoreact_enabled = False
autoreact_targets = set() 
autoreact_emoji = "👍"
autoreact_emoji_list = ["👍", "❤️", "😂", "😮", "😢", "😡"]
autoreact_emoji_rotation = False
autoreact_emoji_index = 0
superreact_enabled = False
superreact_targets = set()
superreact_emoji_list = ["👍", "❤️", "😂", "😮", "😢", "😡", "🔥", "💯", "⭐", "🎉"]
superreact_emoji_rotation = False
superreact_emoji_index = 0
chatpack_running = False
chatpack_task = None
chatpack_messages = []
chatpack_paused = False  # New: Pause chatpack for AFK responses
afk_response_pending = False  # New: Track if AFK response is happening
spam_running = False
spam_task = None
user_note = ""
custom_status = None  
antiafk_enabled = True  
antiafk_secure_mode = True  # SECURE: Only respond when mentioned/pinged 
killgc_running = False
killgc_task = None
killgc_names = []
antigc_enabled = False
antigc_message = "nah im good"


# Command queue for thread communication
command_queue = queue.Queue()
command_responses = {}

# ========== PAGE SYSTEM HEADERS ==========
HEADERS = {
    "page1": """\u001b[2;31m
╔═════════════════════════════╗
║     REACTION COMMANDS       ║
╚═════════════════════════════╝\u001b[0m""",

    "page2": """\u001b[2;32m
╔═════════════════════════════╗
║     STATUS & PRESENCE       ║
╚═════════════════════════════╝\u001b[0m""",

    "page3": """\u001b[2;34m
╔═════════════════════════════╗
║    AUTOMATION & SPAM        ║
╚═════════════════════════════╝\u001b[0m""",

    "page4": """\u001b[2;35m
╔═════════════════════════════╗
║     UTILITY & TOOLS         ║
╚═════════════════════════════╝\u001b[0m""",

    "page5": """\u001b[2;36m
╔═════════════════════════════╗
║    INFORMATION COMMANDS     ║
╚═════════════════════════════╝\u001b[0m""",

    "page6": """\u001b[2;33m
╔═════════════════════════════╗
║    FUN & ENTERTAINMENT      ║
╚═════════════════════════════╝\u001b[0m""",

    "page7": """\u001b[2;91m
╔═════════════════════════════╗
║   DESTRUCTIVE & WEBHOOKS    ║
╚═════════════════════════════╝\u001b[0m""",

}

PAGES = {
    "page1": f"""{HEADERS['page1']}
\u001b[2;31m`.autoreact [@user] <emoji>`\u001b[0m – Auto-react to messages  
\u001b[2;31m`.addreact @user <emoji>`\u001b[0m – Add user to targets  
\u001b[2;31m`.removereact @user`\u001b[0m – Remove user from targets  
\u001b[2;31m`.stopreact`\u001b[0m – Stop auto-reacting  
\u001b[2;31m`.reactlist`\u001b[0m – Show current targets  
\u001b[2;31m`.reactrotate [on/off]`\u001b[0m – Toggle emoji rotation  
\u001b[2;31m`.reactemojis <emojis>`\u001b[0m – Set custom emoji list  
\u001b[2;31m`.superreact [@user]`\u001b[0m – Enable super-react (Nitro)  
\u001b[2;31m`.superreactlist`\u001b[0m – Show super-react targets  
\u001b[2;31m`.reactstatus`\u001b[0m – Show both systems status  
""",

    "page2": f"""{HEADERS['page2']}
\u001b[2;32m`.stream on/off <content>`\u001b[0m – Set streaming status  
\u001b[2;32m`.playing <text>`\u001b[0m – Set "Playing..." status  
\u001b[2;32m`.watching <text>`\u001b[0m – Set "Watching..." status  
\u001b[2;32m`.listening <text>`\u001b[0m – Set "Listening to..." status  
\u001b[2;32m`.customstatus <emoji> <text>`\u001b[0m – Set custom status  
\u001b[2;32m`.fakegame <text>`\u001b[0m – Set fake game status  
\u001b[2;32m`.clearstatus`\u001b[0m – Clear all status  
\u001b[2;32m`.statuscycle`\u001b[0m – Start status cycling from status.txt  
\u001b[2;32m`.statusstop`\u001b[0m – Stop status cycling  
""",

    "page3": f"""{HEADERS['page3']}
\u001b[2;34m`.ar @user <msg>`\u001b[0m – Auto-reply to user  
\u001b[2;34m`.arstop`\u001b[0m – Stop auto-replying  
\u001b[2;34m`.stam <msg>`\u001b[0m – Spam messages with counter  
\u001b[2;34m`.stamstop`\u001b[0m – Stop spamming  
\u001b[2;34m`.kill [channel_id]`\u001b[0m – Start chatpack  
\u001b[2;34m`.turbo [channel_id]`\u001b[0m – Ultra fast chatpack  
\u001b[2;34m`.stopkill [channel_id]`\u001b[0m – Stop chatpack  
\u001b[2;34m`.killgc [channel_id]`\u001b[0m – Group chat name changing  
\u001b[2;34m`.antiafk on/off`\u001b[0m – Toggle anti-AFK system  
\u001b[2;34m`.antigc <message>`\u001b[0m – Enable anti-GC  
""",

    "page4": f"""{HEADERS['page4']}
\u001b[2;35m`.snipe`\u001b[0m – Show last deleted message  
\u001b[2;35m`.editsnipe`\u001b[0m – Show last edited message  
\u001b[2;35m`.purge <amount>`\u001b[0m – Delete your messages  
\u001b[2;35m`.remind <sec> <msg>`\u001b[0m – Set a reminder  
\u001b[2;35m`.note <text>`\u001b[0m – Save a note  
\u001b[2;35m`.getnote`\u001b[0m – Get your saved note  
\u001b[2;35m`.prefix <new>`\u001b[0m – Change command prefix  
""",

    "page5": f"""{HEADERS['page5']}
\u001b[2;36m`.pfp <@user/user_id>`\u001b[0m – Show user's avatar  
\u001b[2;36m`.userinfo [@user]`\u001b[0m – Show user information  
\u001b[2;36m`.serverinfo`\u001b[0m – Show server info  
\u001b[2;36m`.ping`\u001b[0m – Show bot latency  
""",

    "page6": f"""{HEADERS['page6']}
\u001b[2;33m`.gayrate @user`\u001b[0m – Rate gayness (0-100%)  
\u001b[2;33m`.ppsize @user`\u001b[0m – Check pp size  
\u001b[2;33m`.simp @user`\u001b[0m – Check simp level  
""",

    "page7": f"""{HEADERS['page7']}
\u001b[2;91m`.nuke`\u001b[0m – Nuke entire server (DANGEROUS)  
\u001b[2;91m`.spamchannels <name>`\u001b[0m – Spam create channels  
\u001b[2;91m`.spamroles <name>`\u001b[0m – Spam create roles  
\u001b[2;91m`.deleteroles`\u001b[0m – Delete all server roles  
\u001b[2;91m`.deletechannels`\u001b[0m – Delete all channels  
\u001b[2;91m`.deletemojis`\u001b[0m – Delete all server emojis  
\u001b[2;91m`.deletewebhooks`\u001b[0m – Delete all webhooks  
\u001b[2;91m`.massban`\u001b[0m – Ban all server members  
\u001b[2;91m`.masskick`\u001b[0m – Kick all server members  
\u001b[2;91m`.dmall <msg>`\u001b[0m – DM all server members  
\u001b[2;91m`.whspam <url> <msg>`\u001b[0m – Spam webhook 20 times  
\u001b[2;91m`.whnuke <url> <msg>`\u001b[0m – Nuke webhook 50 times  
\u001b[2;91m`.whflood <url>`\u001b[0m – Flood webhook infinitely  
\u001b[2;91m`.whdelete <url>`\u001b[0m – Delete a webhook  
\u001b[2;91m`.whhook <name> <msg>`\u001b[0m – Send styled webhook message  
""",

}


bot.remove_command('help')

async def process_command_queue():
    global chatpack_running, chatpack_task, chatpack_messages
    global killgc_running, killgc_task, killgc_names
    
    while True:
        try:
            if not command_queue.empty():
                cmd_data = command_queue.get_nowait()
                cmd_type = cmd_data['type']
                cmd_id = cmd_data['id']
                
                try:
                    if cmd_type == 'start_chatpack':
                        channel_id = cmd_data['channel_id']
                        filename = cmd_data['filename']
                        mode = cmd_data['mode']
                        
                        # Get channel
                        target_channel = bot.get_channel(channel_id)
                        if not target_channel:
                            command_responses[cmd_id] = f"❌ Channel {channel_id} not found!"
                            continue
                        
                        # Load messages
                        with open(filename, 'r', encoding='utf-8') as f:
                            chatpack_messages = [line.strip() for line in f.readlines() if line.strip()]
                        
                        # Start chatpack
                        chatpack_running = True
                        chatpack_task = asyncio.create_task(chatpack_loop(target_channel, mode))
                        command_responses[cmd_id] = f"🔥 Chatpack started in {target_channel.name if hasattr(target_channel, 'name') else 'Unknown'}"
                        
                    elif cmd_type == 'start_killgc':
                        channel_id = cmd_data['channel_id']
                        filename = cmd_data['filename']
                        
                        # Get channel
                        target_channel = bot.get_channel(channel_id)
                        if not target_channel:
                            command_responses[cmd_id] = f"❌ Channel {channel_id} not found!"
                            continue
                        
                        # Check if it's a group chat
                        if not (hasattr(target_channel, 'type') and str(target_channel.type) == 'group'):
                            command_responses[cmd_id] = f"❌ Channel {channel_id} is not a group chat!"
                            continue
                        
                        # Load names
                        with open(filename, 'r', encoding='utf-8') as f:
                            killgc_names = [line.strip() for line in f.readlines() if line.strip()]
                        
                        # Start kill GC
                        killgc_running = True
                        killgc_task = asyncio.create_task(killgc_loop(target_channel))
                        command_responses[cmd_id] = f"💀 Kill GC started in group chat (ID: {channel_id})"
                        
                except Exception as e:
                    command_responses[cmd_id] = f"❌ Error: {e}"
            
            await asyncio.sleep(0.1)  # Small delay
            
        except Exception as e:
            print(f"Error in command queue processor: {e}")
            await asyncio.sleep(1)


@bot.event
async def on_ready():
    print('='*50)
    print(f"{Fore.MAGENTA}[+]Selfbot successfully logged in as {Style.RESET_ALL} {bot.user}")
    print(f"{Fore.MAGENTA}[+]Guilds: {Style.RESET_ALL} {[g.name for g in bot.guilds]}")
    print(f'{Fore.MAGENTA}[+]User ID: {Style.RESET_ALL} {bot.user.id}')
    print(f'{Fore.MAGENTA}[+]Bot Status: {Style.RESET_ALL} Online')
    print(f'{Fore.MAGENTA}[+]Command Prefix: {Style.RESET_ALL} {bot.command_prefix}')
    print('='*50)
    
    # Start command queue processor
    asyncio.create_task(process_command_queue())
    
    # ...existing code...

@bot.event
async def on_group_join(channel, user):
    global antigc_enabled, antigc_message
    
    # Only process if the user joining is the bot itself
    if user.id != bot.user.id:
        return
    
    print(f"🔔 Group join detected! Channel: {channel.name if hasattr(channel, 'name') else 'Unnamed Group'} (ID: {channel.id})")
    print(f"📊 Anti-GC status: {antigc_enabled}")
    
    if antigc_enabled:
        try:
            print(f"📤 Sending anti-GC message: '{antigc_message}'")
            # Send the anti-GC message in the group chat
            await channel.send(antigc_message)
            await asyncio.sleep(1.0)  # Slightly longer delay to ensure message sends
            
            # Leave the group chat immediately
            print("🚪 Leaving group chat...")
            await channel.leave()
            print(f"✅ Successfully left group chat: {channel.name if hasattr(channel, 'name') else 'Unnamed Group'} (ID: {channel.id})")
            
        except Exception as e:
            print(f"❌ Error in anti-GC: {e}")
            try:
                print("🔄 Attempting to leave without message...")
                await channel.leave()
                print("✅ Left group chat (message failed)")
            except Exception as e2:
                print(f"❌ Failed to leave group chat: {e2}")

# Alternative event handler for channel updates (backup method)
@bot.event
async def on_private_channel_create(channel):
    global antigc_enabled, antigc_message
    
    # Check if it's a group channel (more than 2 recipients)
    if hasattr(channel, 'recipients') and len(channel.recipients) > 1:
        print(f"🔔 Private group channel detected! Recipients: {len(channel.recipients)} (ID: {channel.id})")
        print(f"📊 Anti-GC status: {antigc_enabled}")
        
        if antigc_enabled:
            # Small delay to ensure channel is fully ready
            await asyncio.sleep(0.5)
            try:
                print(f"📤 Sending anti-GC message: '{antigc_message}'")
                await channel.send(antigc_message)
                await asyncio.sleep(1.0)
                
                print("🚪 Leaving group chat...")
                await channel.leave()
                print(f"✅ Successfully left private group chat (ID: {channel.id})")
                
            except Exception as e:
                print(f"❌ Error in private channel anti-GC: {e}")
                try:
                    await channel.leave()
                    print("✅ Left private group chat (message failed)")
                except Exception as e2:
                    print(f"❌ Failed to leave private group chat: {e2}")

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    
    channel_id = message.channel.id
    deleted_messages[channel_id] = {
        'content': message.content,
        'author': message.author,
        'timestamp': datetime.now(),
        'attachments': [att.url for att in message.attachments] if message.attachments else []
    }

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content:
        return
    
    channel_id = before.channel.id
    edited_messages[channel_id] = {
        'before': before.content,
        'after': after.content,
        'author': before.author,
        'timestamp': datetime.now()
    }

@bot.event
async def on_message(message):
    # For selfbots, we need to process our own messages for commands
    # Only skip if it's another bot (not ourselves)
    if message.author.bot and message.author != bot.user:
        return
    
    # Debug: Print message info for troubleshooting
    if message.content.startswith(PREFIX) and message.author == bot.user:
        print(f"Command detected: {message.content} in {type(message.channel).__name__} (Guild: {message.guild.name if message.guild else 'DM'})")
        
        # Add delay for server commands to avoid rate limiting
        if message.guild:
            await asyncio.sleep(0.5)
    
    # Auto-react functionality - react to targeted users in any channel
    if autoreact_enabled and autoreact_targets and message.author.id in autoreact_targets:
        try:
            emoji_to_use = autoreact_emoji
            
            # Use emoji rotation if enabled
            if autoreact_emoji_rotation:
                global autoreact_emoji_index
                emoji_to_use = autoreact_emoji_list[autoreact_emoji_index]
                autoreact_emoji_index = (autoreact_emoji_index + 1) % len(autoreact_emoji_list)
            
            # Handle custom server emojis and unicode emojis
            if emoji_to_use.startswith('<') and emoji_to_use.endswith('>'):
                # Custom emoji format: <:name:id> or <a:name:id>
                emoji_id = emoji_to_use.split(':')[-1][:-1]  # Extract ID
                emoji_obj = discord.utils.get(bot.emojis, id=int(emoji_id))
                if emoji_obj:
                    await message.add_reaction(emoji_obj)
                else:
                    # Try using the raw emoji string
                    await message.add_reaction(emoji_to_use)
            else:
                # Unicode emoji or emoji name
                await message.add_reaction(emoji_to_use)
        except Exception as e:
            # Silently fail if emoji not found or no permission
            pass
    
    # Super-react functionality - react with burst effect for targeted users
    if superreact_enabled and superreact_targets and message.author.id in superreact_targets:
        try:
            emoji_to_use = superreact_emoji_list[0]  # Default emoji
            
            # Use emoji rotation if enabled
            if superreact_emoji_rotation:
                global superreact_emoji_index
                emoji_to_use = superreact_emoji_list[superreact_emoji_index]
                superreact_emoji_index = (superreact_emoji_index + 1) % len(superreact_emoji_list)
            
            # Try to add super reaction with burst effect first (requires Nitro)
            try:
                if emoji_to_use.startswith('<') and emoji_to_use.endswith('>'):
                    # Custom emoji format: <:name:id> or <a:name:id>
                    emoji_id = emoji_to_use.split(':')[-1][:-1]  # Extract ID
                    emoji_obj = discord.utils.get(bot.emojis, id=int(emoji_id))
                    if emoji_obj:
                        await message.add_reaction(emoji_obj, burst=True)
                    else:
                        # Try using the raw emoji string with burst
                        await message.add_reaction(emoji_to_use, burst=True)
                else:
                    # Unicode emoji with burst effect
                    await message.add_reaction(emoji_to_use, burst=True)
            except (TypeError, AttributeError):
                # burst parameter not supported in this discord.py version, use normal reaction
                if emoji_to_use.startswith('<') and emoji_to_use.endswith('>'):
                    emoji_id = emoji_to_use.split(':')[-1][:-1]
                    emoji_obj = discord.utils.get(bot.emojis, id=int(emoji_id))
                    if emoji_obj:
                        await message.add_reaction(emoji_obj)
                    else:
                        await message.add_reaction(emoji_to_use)
                else:
                    await message.add_reaction(emoji_to_use)
            except discord.HTTPException as e:
                # Likely means account doesn't have Nitro or burst not available, fallback to normal reaction
                if emoji_to_use.startswith('<') and emoji_to_use.endswith('>'):
                    emoji_id = emoji_to_use.split(':')[-1][:-1]
                    emoji_obj = discord.utils.get(bot.emojis, id=int(emoji_id))
                    if emoji_obj:
                        await message.add_reaction(emoji_obj)
                    else:
                        await message.add_reaction(emoji_to_use)
                else:
                    await message.add_reaction(emoji_to_use)
        except Exception as e:
            # Silently fail if emoji not found or no permission
            pass
    
    # Auto-reply functionality
    await handle_auto_reply(message)
    
    # Anti-AFK
    if antiafk_enabled:
        content = message.content.lower()
        original_content = message.content
        response_message = None

        # Prevent anti-AFK from responding to our own AFK check commands
        if message.author == bot.user and re.search(r'\bafk\s*check\b', content, re.IGNORECASE):
            print(f"🚫 Skipping anti-AFK for own AFK check command: '{original_content}'")
            return

        # 🔍 DEBUG: Log potential AFK checks for analysis
        has_afk_pattern = re.search(r'\b(afk|check|type|say|respond|here|active|awake|alive|present)\b', content, re.IGNORECASE)
        if has_afk_pattern:
            print(f"🔍 DEBUG: Message with AFK keywords from {message.author}: '{original_content}'")
            print(f"   Channel: {message.channel} | Guild: {message.guild}")
            print(f"   Secure mode: {antiafk_secure_mode} | Mentioned: {bot.user in message.mentions}")
            print(f"   Contains @!: {'@!' in original_content}")
            print(f"   Content mentions us: {f'<@{bot.user.id}>' in original_content or f'<@!{bot.user.id}>' in original_content}")
            print(f"   AFK keywords found: {has_afk_pattern.group()}")
        
        # 🔍 DEBUG: Also log mentions without AFK keywords to show filtering
        elif (bot.user in message.mentions or f'<@{bot.user.id}>' in message.content or f'<@!{bot.user.id}>' in message.content):
            print(f"🔕 DEBUG: Mention without AFK keywords (IGNORED): '{original_content}' from {message.author}")

        # SECURITY: Check if we should use secure mode  
        if antiafk_secure_mode and message.author != bot.user:
            # Only respond if we're mentioned or it's a direct message AND contains AFK keywords
            is_mentioned = bot.user in message.mentions
            is_dm = isinstance(message.channel, discord.DMChannel)

            # Additional check for @! or @here patterns that might target us
            content_mentions_us = (f'<@{bot.user.id}>' in message.content or 
                                 f'<@!{bot.user.id}>' in message.content or
                                 '@!' in message.content.lower() or
                                 re.search(r'@!\s*$', message.content.strip()))

            # FIXED: Must be mentioned/DM AND contain AFK-related keywords
            has_afk_keywords = re.search(r'\b(afk|check|type|say|respond|here|active|awake|alive|present)\b', content, re.IGNORECASE)

            if not ((is_mentioned or is_dm or content_mentions_us) and has_afk_keywords):
                # Check if the message contains AFK patterns (for logging)
                if re.search(r'\bafk\s+check\b', content):
                    print(f"🔒 Anti-AFK: BLOCKED potential trigger from {message.author} (secure mode enabled, not mentioned or no AFK keywords)")
                return  # Ignore messages that don't target us OR don't contain AFK keywords
        
        # 🧠 ULTIMATE PATTERN DETECTION - COVERS EVERYTHING
        patterns = [
            # Standard patterns (with optional mentions at start and end) - CASE INSENSITIVE
            (r'(?:<@!?\d+>\s+)?afk\s+check\s+say\s+\[(.+?)\](?:\s*<@!?\d*>?)?', lambda m: m.group(1).strip().upper()),
            (r'(?:<@!?\d+>\s+)?afk\s+check\s+say\s+([a-zA-Z0-9\s\'\"]+?)(?:\s*<@!?\d*>?|\s*@!|\s*$)', lambda m: m.group(1).strip().upper()),
            (r'(?:<@!?\d+>\s+)?afk\s+check\s+type\s+(.+?)(?:\s*<@!?\d*>?|\s*@!|\s*$)', lambda m: m.group(1).strip()),
            (r'(?:<@!?\d+>\s+)?afk\s+check\s+respond\s+(.+?)(?:\s*<@!?\d*>?|\s*@!|\s*$)', lambda m: m.group(1).strip()),
            
            # Advanced patterns (more specific)
            (r'(?:are\s+you\s+|u\s+)?(?:still\s+)?(?:here|active|awake|alive|present)\s*\?', lambda m: random.choice(["yes", "here", "yep", "yeah", "yup", "present"])),
            (r'(?:type|say|send|write)\s+(.+?)\s+(?:if\s+)?(?:you\'?re\s+|ur\s+)?(?:here|active|awake|not\s+afk)', lambda m: m.group(1).strip()),
            (r'respond\s+with\s+(.+?)(?:\s*$|\s+if)', lambda m: m.group(1).strip()),
            
            # Sneaky patterns (require AFK context)
            (r'if\s+(?:you\'?re\s+|ur\s+)?(?:not\s+)?(?:afk|here|active|awake),?\s+(?:type|say|send)\s+(.+?)(?:\s*$)', lambda m: m.group(1).strip()),
            (r'(?:prove|show)\s+(?:you\'?re\s+|ur\s+)?(?:not\s+)?(?:afk|here|active|awake)(?:\s+(?:by\s+)?(?:typing|saying|sending)\s+(.+?))?(?:\s*$)', lambda m: m.group(1).strip() if m.group(1) else random.choice(["HERE", "DORK ASS LOSER IM HERE LMFAO", "YES IM HERE NOW WHAT DORK", "YES IM HERE SLUT"])),
            
            # Simple AFK check patterns (with optional mentions at start OR end)
            (r'(?:(?:<@!?\d+>\s+)?\bafk\s+check\b(?!\s+(?:say|type|respond))(?:\s*<@!?\d*>?|\s*@!)?)', lambda m: random.choice([
                "IM HERE SON NOW WHAT", "HERE LMFAOAOAOAOOAO", "SLUT DO U THINK IM AFK", "here", 
                "DORK ASS LOSER IM HERE LMFAO", "IM HERE FUCKTARD", "UGLY PIECE OF SHIT STARTED TO DO RANDOM CHECKS ITS BAD", "LMFAOAOAO DW NIGGA IM HERE U FAILED TO AFK CHECK ME MISERABLY", "SUP DORK IM HERE", "IM HERE DORK"
            ])),
            
            # AFK-specific questions only (not random questions)
            (r'(?:are\s+you\s+|u\s+)(?:still\s+)?(?:afk|away)\s*\?', lambda m: random.choice(["no", "nah", "not afk", "here"])),
        ]
        
        # 🔍 SMART PATTERN MATCHING - CASE INSENSITIVE
        for pattern, response_func in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    response_message = response_func(match)
                    
                    # 🛡️ ANTI-BYPASS SECURITY: Block suspicious responses
                    suspicious_words = ["owner", "slave", "owns me", "my owner", "vanish", "daddy", "master", 
                                      "property", "belongs to", "owned by", "possession", "bitch", "whore", "didnt hoe me", "hoed me", "runs me",
                                      "im your", "i'm your", "i am your", "ur slave", "you own me", "you own me", "u own me"]
                    
                    # Block if contains suspicious words OR is too long (spam prevention)
                    if (any(word in response_message.lower() for word in suspicious_words) or 
                        len(response_message) > 100):
                        
                        bypass_type = "LONG MESSAGE" if len(response_message) > 100 else "SUSPICIOUS CONTENT"
                        print(f"🚫 BLOCKED BYPASS ATTEMPT ({bypass_type}): '{response_message[:50]}...' from {message.author}")
                        
                        response_message = random.choice([
                            "IM HERE SON NOW WHAT", "HERE LMFAOAOAOAOOAO", "SLUT DO U THINK IM AFK", 
                            "DORK ASS LOSER IM HERE LMFAO", "IM HERE FUCKTARD", "SUP DORK IM HERE",
                            "nice try loser", "NICE TRY DORK", "lol failed bypass attempt"
                        ])
                    
                    pattern_type = "ULTIMATE" if "afk" in pattern else "SMART"
                    print(f"🔥 {pattern_type} Anti-AFK: Detected pattern '{pattern[:30]}...' from {message.author} → '{response_message}'")
                    break
                except:
                    continue
        
        # 🎭 HUMAN-LIKE RESPONSE SYSTEM
        if response_message:
            # Clean and enhance response
            response_message = response_message.strip()
            
            # 🎲 Random response variations for realism
            variations = {
                "yes": ["yes", "yeah", "yep", "yup", "ye", "ye"],
                "here": ["here", "im here", "im here son", "here lol"],
                "not afk": ["not afk", "im not afk", "nah im here", "not afk lol"],
                "what": ["what", "huh", "wym", "?", "hm?"]
            }
            
            for key, options in variations.items():
                if response_message.lower() == key:
                    response_message = random.choice(options)
                    break
            
            # 🛑 PAUSE CHATPACK FOR AFK RESPONSE
            global chatpack_paused, afk_response_pending
            
            # Signal chatpack to pause if it's running
            if chatpack_running:
                chatpack_paused = True
                afk_response_pending = True
                print("⏸️ PAUSING chatpack for AFK response...")
            
            # Wait exactly 2 seconds to look less suspicious/botty
            await asyncio.sleep(2.0)
            
            # 🎯 SEND RESPONSE
            await message.channel.send(response_message)
            print(f"✅ ULTIMATE Anti-AFK: Sent '{response_message}' in {message.channel.id} after 2.0s delay")
            
            # 🔄 RESUME CHATPACK AFTER RESPONSE
            if chatpack_running and chatpack_paused:
                # Small delay to ensure response is sent
                await asyncio.sleep(0.5)
                chatpack_paused = False
                afk_response_pending = False
                print("▶️ RESUMING chatpack after AFK response!")
    
    # Anti-GC backup method - REMOVED to prevent false triggers on existing group chats
    # The main anti-GC functionality is handled by the on_group_join and on_private_channel_create events
    # This message-based detection was causing issues where it would trigger on existing group chats
    # when someone mentioned the user, which is not the intended behavior
    
    # Process commands - Critical for selfbot functionality
    try:
        # Add extra delay for server commands to avoid Discord detection
        if message.guild and message.content.startswith(PREFIX) and message.author == bot.user:
            await asyncio.sleep(1.0)  # 1 second delay for server commands
            
        await bot.process_commands(message)
        
        # Log successful command processing
        if message.content.startswith(PREFIX) and message.author == bot.user:
            location = f"Server: {message.guild.name}" if message.guild else "DM"
            print(f"✅ Command processed successfully in {location}")
            
    except Exception as e:
        if message.content.startswith(PREFIX) and message.author == bot.user:
            print(f"❌ Command processing failed: {e}")
            print(f"Message: {message.content}")
            print(f"Channel: {type(message.channel).__name__}")
            print(f"Guild: {message.guild.name if message.guild else 'DM'}")

# utility commands

@bot.command()
async def snipe(ctx):
    if ctx.channel.id in deleted_messages:
        msg_data = deleted_messages[ctx.channel.id]
        content = msg_data['content']
        author = msg_data['author']
        await ctx.send(f"```Last deleted message:```\n{author}: {content}")
    else:
        await ctx.send("```No deleted messages to snipe```")
    await ctx.message.delete()

@bot.command()
async def editsnipe(ctx):
    if ctx.channel.id in edited_messages:
        msg_data = edited_messages[ctx.channel.id]
        old_content = msg_data['before']
        new_content = msg_data['after']
        author = msg_data['author']
        await ctx.send(f"```Last edited message:```\n{author}:\nBefore: {old_content}\nAfter: {new_content}")
    else:
        await ctx.send("```No edited messages to snipe.```")
    await ctx.message.delete()

# reaction commands

@bot.command()
async def autoreact(ctx, user: discord.User = None, *, emoji="👍"):
    global autoreact_enabled, autoreact_emoji, autoreact_targets
    
    # If no user specified, target yourself
    if user is None:
        user = ctx.author
    
    # Handle custom server emojis
    if emoji.startswith('<') and emoji.endswith('>'):
        # Custom emoji format: <:name:id> or <a:name:id>
        autoreact_emoji = emoji
    else:
        # Regular unicode emoji or emoji name
        autoreact_emoji = emoji
    
    # Add user to autoreact targets
    autoreact_targets.add(user.id)
    autoreact_enabled = True
    
    if user.id == ctx.author.id:
        await ctx.send(f"Auto-react enabled for your messages with {emoji} in all channels", delete_after=5)
    else:
        await ctx.send(f"Auto-react enabled for {user.display_name}'s messages with {emoji} in all channels", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def addreact(ctx, user: discord.User, *, emoji="👍"):
    """Add another user to auto-react targets"""
    global autoreact_targets, autoreact_emoji
    
    # Update emoji if provided
    if emoji != "👍":
        autoreact_emoji = emoji
    
    autoreact_targets.add(user.id)
    await ctx.send(f"Added {user.display_name} to auto-react targets with {emoji}", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def removereact(ctx, user: discord.User):
    """Remove user from auto-react targets"""
    global autoreact_targets
    
    if user.id in autoreact_targets:
        autoreact_targets.remove(user.id)
        await ctx.send(f"Removed {user.display_name} from auto-react targets", delete_after=5)
    else:
        await ctx.send(f"{user.display_name} is not in auto-react targets", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def stopreact(ctx):
    """Stop auto-react completely"""
    global autoreact_enabled, autoreact_targets
    autoreact_enabled = False
    autoreact_targets.clear()
    await ctx.send("Auto-react disabled and all targets cleared", delete_after=5)
    await ctx.message.delete()

# destructive commands
@bot.command()
async def nuke(ctx):
    await ctx.send("vanish is now nuking this server...")
    try:
        for ch in ctx.guild.channels:
            try:
                await ch.delete()
                await asyncio.sleep(0.3)
            except: pass
        for r in ctx.guild.roles:
            try:
                await r.delete()
                await asyncio.sleep(0.3)
            except: pass
        for i in range(10):
            await ctx.guild.create_text_channel(f"fucked-by-vanish-{random.randint(100,999)}")
        await ctx.send("vanish nuke finished.")
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command()
async def spamchannels(ctx, *, name="fucked-by-vanish"):
    await ctx.send(f"vanish is now spamming channels with name: `{name}`")
    try:
        for _ in range(20):
            await ctx.guild.create_text_channel(name)
            await asyncio.sleep(0.2)
        await ctx.send("done twin")
    except Exception as e:
        await ctx.send(f" Error: {e}")

@bot.command()
async def spamroles(ctx, *, name="vanish runs u"):
    await ctx.send(f"spamming all roles: `{name}`")
    try:
        for _ in range(20):
            await ctx.guild.create_role(name=name)
            await asyncio.sleep(0.2)
        await ctx.send("Roles created.")
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command()
async def deleteroles(ctx):
    await ctx.send("Deleting all roles...")
    try:
        for role in ctx.guild.roles:
            if role != ctx.guild.default_role:
                try:
                    await role.delete()
                    await asyncio.sleep(0.2)
                except: pass
        await ctx.send("Roles wiped.")
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command()
async def deletechannels(ctx):
    await ctx.send("Deleting all channels...")
    try:
        for ch in ctx.guild.channels:
            try:
                await ch.delete()
                await asyncio.sleep(0.2)
            except: pass
        await ctx.send("Channels deleted.")
    except Exception as e:
        await ctx.send(f" Error: {e}")

@bot.command()
async def deletemojis(ctx):
    await ctx.send("Deleting all emojis...")
    try:
        for emoji in ctx.guild.emojis:
            try:
                await emoji.delete()
                await asyncio.sleep(0.2)
            except: pass
        await ctx.send(" Emojis wiped.")
    except Exception as e:
        await ctx.send(f" Error: {e}")

@bot.command()
async def deletewebhooks(ctx):
    await ctx.send(" Deleting all webhooks...")
    try:
        for channel in ctx.guild.text_channels:
            try:
                hooks = await channel.webhooks()
                for hook in hooks:
                    await hook.delete()
                    await asyncio.sleep(0.1)
            except: pass
        await ctx.send(" webhook(s) gone.")
    except Exception as e:
        await ctx.send(f" Error: {e}")

@bot.command()
async def massban(ctx):
    await ctx.send(" banning all users...")
    try:
        for member in ctx.guild.members:
            try:
                await member.ban(reason="your ass")
                await asyncio.sleep(0.3)
            except: pass
        await ctx.send("mass ban finished.")
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command()
async def masskick(ctx):
    await ctx.send("kicking everyone")
    try:
        for member in ctx.guild.members:
            try:
                await member.kick(reason="no mercy")
                await asyncio.sleep(0.3)
            except: pass
        await ctx.send("everyone kicked.")
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command()
async def dmall(ctx, *, msg):
    await ctx.send("vanish is now dming everyone in the server WARNING: THIS CAN GET YOUR ACCOUNT LOCKED")
    try:
        for member in ctx.guild.members:
            if not member.bot:
                try:
                    await member.send(msg)
                    await asyncio.sleep(1)
                except: pass
        await ctx.send("DMs sent.")
    except Exception as e:
        await ctx.send(f" Error: {e}")

# webhook commands

@bot.command()
async def whspam(ctx, url, *, msg):
    await ctx.send(f"vanish is now spamming the webhook with: `{msg}`")
    try:
        for _ in range(20):
            async with aiohttp.ClientSession() as session:
                await session.post(url, json={"content": msg})
            await asyncio.sleep(0.3)
        await ctx.send("vanish webhook spam done xd.")
    except Exception as e:
        await ctx.send(f"error please contact sxundwav3: {e}")

@bot.command()
async def whdelete(ctx, url):
    try:
        async with aiohttp.ClientSession() as session:
            await session.delete(url)
        await ctx.send("webhook deleted.")
    except Exception as e:
        await ctx.send(f"error please contact vanish: {e}")

@bot.command()
async def whnuke(ctx, url, *, msg):
    await ctx.send(f"vanish is now nuking the webhook with `{msg}`shoutout sxundwav3 heh...")
    try:
        for _ in range(50):
            async with aiohttp.ClientSession() as session:
                await session.post(url, json={"content": msg})
            await asyncio.sleep(0.1)
        await ctx.send("vanish webhook nuked.")
    except Exception as e:
        await ctx.send(f"error please contact sxundwav3: {e}")

@bot.command()
async def whflood(ctx, url):
    await ctx.send("vanish webhook flooding is now started.")
    try:
        while True:
            async with aiohttp.ClientSession() as session:
                await session.post(url, json={"content": "vanish runs me!! 💦"})
            await asyncio.sleep(0.1)
    except:
        pass

@bot.command()
async def whhook(ctx, name, *, msg):
    embed = discord.Embed(title=name, description=msg, color=0x00ffcc)
    async with aiohttp.ClientSession() as session:
        await session.post("YOUR_WEBHOOK_HERE", json={
            "username": name,
            "embeds": [embed.to_dict()]
        })

# fun commands

@bot.command()
async def gayrate(ctx, user: discord.User):
    """Rate how gay someone is (0-100%)"""
    percent = random.randint(0, 100)
    await ctx.send(f"vanish {user.mention} is **{percent}%** gay.")

@bot.command()
async def ppsize(ctx, user: discord.User):
    """Check someone's pp size"""
    length = random.randint(0, 15)
    bar = "8" + "=" * length + "D"
    await ctx.send(f"{user.mention}'s PP size:\n`{bar}`")

@bot.command()
async def simp(ctx, user: discord.User):
    """Check someone's simp level (0-100%)"""
    percent = random.randint(0, 100)
    await ctx.send(f"vanish {user.mention} is **{percent}%** simp.")


@bot.command()
async def reactlist(ctx):
    """Show current auto-react targets"""
    global autoreact_targets, autoreact_enabled, autoreact_emoji
    
    if not autoreact_enabled:
        await ctx.send("Auto-react is disabled", delete_after=5)
        await ctx.message.delete()
        return
    
    if not autoreact_targets:
        await ctx.send("No auto-react targets set", delete_after=5)
        await ctx.message.delete()
        return
    
    target_names = []
    for user_id in autoreact_targets:
        user = bot.get_user(user_id)
        if user:
            target_names.append(user.display_name)
        else:
            target_names.append(f"Unknown User ({user_id})")
    
    embed = discord.Embed(
        title="Auto-React Status",
        color=0x00ff00,
        description=f"**Emoji:** {autoreact_emoji}\n**Targets:** {', '.join(target_names)}"
    )
    
    await ctx.send(embed=embed, delete_after=15)
    await ctx.message.delete()

@bot.command()
async def reactrotate(ctx, action="toggle"):
    """Enable/disable emoji rotation for autoreact (toggle/on/off)"""
    global autoreact_emoji_rotation
    
    if action.lower() == "on":
        autoreact_emoji_rotation = True
    elif action.lower() == "off":
        autoreact_emoji_rotation = False
    else:  # toggle
        autoreact_emoji_rotation = not autoreact_emoji_rotation
    
    status = "enabled" if autoreact_emoji_rotation else "disabled"
    await ctx.send(f"Auto-react emoji rotation {status}", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def reactemojis(ctx, *emojis):
    """Set custom emoji list for autoreact rotation (e.g., .reactemojis 👍 ❤️ 😂 🔥)"""
    global autoreact_emoji_list
    
    if not emojis:
        current_emojis = " ".join(autoreact_emoji_list)
        await ctx.send(f"Current auto-react emojis: {current_emojis}", delete_after=10)
        await ctx.message.delete()
        return
    
    autoreact_emoji_list = list(emojis)
    emoji_display = " ".join(autoreact_emoji_list)
    await ctx.send(f"Auto-react emoji list updated: {emoji_display}", delete_after=5)
    await ctx.message.delete()

# ========== SUPER-REACT COMMANDS (NITRO REQUIRED) ==========

@bot.command()
async def superreact(ctx, user: discord.User = None):
    """Enable super-react (burst effect) to specific user - requires Nitro"""
    global superreact_enabled, superreact_targets
    
    # If no user specified, target yourself
    if user is None:
        user = ctx.author
    
    # Add user to superreact targets
    superreact_targets.add(user.id)
    superreact_enabled = True
    
    if user.id == ctx.author.id:
        await ctx.send(f"Super-react enabled for your messages with burst effect (requires Nitro, falls back to normal react)", delete_after=7)
    else:
        await ctx.send(f"Super-react enabled for {user.display_name}'s messages with burst effect (requires Nitro, falls back to normal react)", delete_after=7)
    await ctx.message.delete()

@bot.command()
async def addsuperreact(ctx, user: discord.User):
    """Add another user to super-react targets"""
    global superreact_targets
    
    superreact_targets.add(user.id)
    await ctx.send(f"Added {user.display_name} to super-react targets", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def removesuperreact(ctx, user: discord.User):
    """Remove user from super-react targets"""
    global superreact_targets
    
    if user.id in superreact_targets:
        superreact_targets.remove(user.id)
        await ctx.send(f"Removed {user.display_name} from super-react targets", delete_after=5)
    else:
        await ctx.send(f"{user.display_name} is not in super-react targets", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def stopsuperreact(ctx):
    """Stop super-react completely"""
    global superreact_enabled, superreact_targets
    superreact_enabled = False
    superreact_targets.clear()
    await ctx.send("Super-react disabled and all targets cleared", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def superreactrotate(ctx, action="toggle"):
    """Enable/disable emoji rotation for super-react (toggle/on/off)"""
    global superreact_emoji_rotation
    
    if action.lower() == "on":
        superreact_emoji_rotation = True
    elif action.lower() == "off":
        superreact_emoji_rotation = False
    else:  # toggle
        superreact_emoji_rotation = not superreact_emoji_rotation
    
    status = "enabled" if superreact_emoji_rotation else "disabled"
    await ctx.send(f"Super-react emoji rotation {status}", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def superreactemojis(ctx, *emojis):
    """Set custom emoji list for super-react rotation (e.g., .superreactemojis 👍 ❤️ 😂 🔥 💯 ⭐)"""
    global superreact_emoji_list
    
    if not emojis:
        current_emojis = " ".join(superreact_emoji_list)
        await ctx.send(f"Current super-react emojis: {current_emojis}", delete_after=10)
        await ctx.message.delete()
        return
    
    superreact_emoji_list = list(emojis)
    emoji_display = " ".join(superreact_emoji_list)
    await ctx.send(f"Super-react emoji list updated: {emoji_display}", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def superreactlist(ctx):
    """Show current super-react targets"""
    global superreact_targets, superreact_enabled, superreact_emoji_list, superreact_emoji_rotation
    
    if not superreact_enabled:
        await ctx.send("Super-react is disabled", delete_after=5)
        await ctx.message.delete()
        return
    
    if not superreact_targets:
        await ctx.send("No super-react targets set", delete_after=5)
        await ctx.message.delete()
        return
    
    target_names = []
    for user_id in superreact_targets:
        user = bot.get_user(user_id)
        if user:
            target_names.append(user.display_name)
        else:
            target_names.append(f"Unknown User ({user_id})")
    
    rotation_status = "On" if superreact_emoji_rotation else "Off"
    emoji_display = " ".join(superreact_emoji_list[:5])  # Show first 5 emojis
    
    embed = discord.Embed(
        title="Super-React Status",
        color=0xff6600,
        description=f"**Emojis:** {emoji_display}\n**Rotation:** {rotation_status}\n**Targets:** {', '.join(target_names)}"
    )
    
    await ctx.send(embed=embed, delete_after=15)
    await ctx.message.delete()

@bot.command()
async def reactstatus(ctx):
    """Show status for both autoreact and superreact"""
    global autoreact_enabled, autoreact_targets, autoreact_emoji_rotation
    global superreact_enabled, superreact_targets, superreact_emoji_rotation
    
    # Auto-react status
    autoreact_status = "✅ Enabled" if autoreact_enabled else "❌ Disabled"
    autoreact_rotation = "✅ On" if autoreact_emoji_rotation else "❌ Off"
    autoreact_target_count = len(autoreact_targets)
    
    # Super-react status
    superreact_status = "✅ Enabled" if superreact_enabled else "❌ Disabled"
    superreact_rotation = "✅ On" if superreact_emoji_rotation else "❌ Off"
    superreact_target_count = len(superreact_targets)
    
    embed = discord.Embed(
        title="React System Status",
        color=0x00ffff,
        description=f"""
        **Auto-React:**
        Status: {autoreact_status}
        Targets: {autoreact_target_count}
        Rotation: {autoreact_rotation}
        
        **Super-React:**
        Status: {superreact_status}
        Targets: {superreact_target_count}
        Rotation: {superreact_rotation}
        """
    )
    
    await ctx.send(embed=embed, delete_after=15)
    await ctx.message.delete()

# Auto-reply Functions
async def handle_auto_reply(message):
    global auto_reply_target_id, auto_reply_message
    if auto_reply_target_id and message.author.id == auto_reply_target_id:
        await message.reply(auto_reply_message)

# auto reply
@bot.command()
async def ar(ctx, user: discord.User, *, message: str):
    """Set auto-reply message for a specific user"""
    global auto_reply_target_id, auto_reply_message
    auto_reply_target_id = user.id
    auto_reply_message = message
    await ctx.send(f"Auto-reply set for {user.mention}.", delete_after=3)
    await ctx.message.delete()

@bot.command()
async def arstop(ctx):
    """Stop auto-replying"""
    global auto_reply_target_id, auto_reply_message
    auto_reply_target_id = None
    auto_reply_message = None
    await ctx.send("Auto-reply stopped.", delete_after=3)
    await ctx.message.delete()

@bot.command()
async def afksecurity(ctx, mode: str = None):
    """Toggle AFK security mode - secure (mention only) or open (any message)"""
    global antiafk_secure_mode, antiafk_enabled
    
    if mode is None:
        # Show current status
        status = "SECURE" if antiafk_secure_mode else "OPEN"
        enabled_status = "ENABLED" if antiafk_enabled else "DISABLED"
        
        embed = discord.Embed(
            title="AFK Security Status", 
            color=0x00ff00 if antiafk_secure_mode else 0xff6600,
            description=f"**AFK System:** {enabled_status}\n**Security Mode:** {status}\n\n"
                       f"**Secure Mode:** Only responds when mentioned/DMed (safer)\n"
                       f"**Open Mode:** Responds to any AFK check (vulnerable)\n\n"
                       f"Use `.afksecurity secure` or `.afksecurity open`"
        )
        await ctx.send(embed=embed, delete_after=15)
    
    elif mode.lower() == "secure":
        antiafk_secure_mode = True
        await ctx.send("🔒 AFK security set to SECURE mode (mention/DM only)", delete_after=5)
    
    elif mode.lower() == "open":
        antiafk_secure_mode = False
        await ctx.send("AFK security set to OPEN mode (responds to any AFK check)", delete_after=5)
    
    else:
        await ctx.send("Invalid mode. Use 'secure' or 'open'", delete_after=5)
    
    await ctx.message.delete()

# automation
@bot.command()
async def kill(ctx, target=None, filename="vanishwl.txt", mode="fast"):
    """Start bitching f tier dorks - now with optimized speed"""
    global chatpack_running, chatpack_task, chatpack_messages
    
    if chatpack_running:
        await ctx.send("already hoeing this nigga use .stopkill to stop it first", delete_after=5)
        await ctx.message.delete()
        return
    
    # Determine target channel
    target_channel = None
    if target is None:
        # Use current channel if no target specified
        target_channel = ctx.channel
    else:
        try:
            # Try to get channel by ID
            if target.isdigit():
                target_channel = bot.get_channel(int(target))
                if not target_channel:
                    await ctx.send(f"Channel with ID {target} not found!", delete_after=5)
                    await ctx.message.delete()
                    return
            else:
                # If target is not a digit, treat it as filename
                filename = target
                target_channel = ctx.channel
        except:
            # If conversion fails, treat as filename
            filename = target
            target_channel = ctx.channel
    
    # Check if file exists
    if not os.path.exists(filename):
        await ctx.send(f"File '{filename}' not found", delete_after=5)
        await ctx.message.delete()
        return
    
    # Load messages from file
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            chatpack_messages = [line.strip() for line in f.readlines() if line.strip()]
    except Exception as e:
        await ctx.send(f"Error reading file: {e}", delete_after=5)
        await ctx.message.delete()
        return
    
    if not chatpack_messages:
        await ctx.send("No messages found in the file", delete_after=5)
        await ctx.message.delete()
        return
    
    chatpack_running = True
    chatpack_task = asyncio.create_task(chatpack_loop(target_channel, mode))
    await ctx.send(f"Chatpack started in {target_channel.name if hasattr(target_channel, 'name') else 'DM'} with {len(chatpack_messages)} messages (Mode: {mode})", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def turbo(ctx, target=None, filename="vanishwl.txt"):
    """Ultra fast mode kill - maximum speed (higher rate limit risk)"""
    # Call kill with turbo mode
    await kill(ctx, target, filename, "turbo")

@bot.command()
async def stopkill(ctx, target=None):
    """Stop slamming this dork"""
    global chatpack_running, chatpack_task
    
    if not chatpack_running:
        await ctx.send("Killing is not running", delete_after=5)
        await ctx.message.delete()
        return
    
    chatpack_running = False
    if chatpack_task:
        chatpack_task.cancel()
    
    await ctx.send("stopped hoeing this low tier faggot", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def unpause(ctx):
    """Unpause chatpack if it's stuck"""
    global chatpack_paused, afk_response_pending, chatpack_running
    
    if not chatpack_running:
        await ctx.send("Chatpack is not running", delete_after=5)
        await ctx.message.delete()
        return
    
    if chatpack_paused:
        chatpack_paused = False
        afk_response_pending = False
        await ctx.send("✅ Chatpack unpaused and resumed", delete_after=5)
        print("🔄 Manually unpaused chatpack")
    else:
        await ctx.send("Chatpack is not paused", delete_after=5)
    
    await ctx.message.delete()

@bot.command()
async def killstatus(ctx):
    """Check chatpack status"""
    global chatpack_running, chatpack_paused, afk_response_pending, chatpack_messages
    
    if not chatpack_running:
        await ctx.send("❌ Chatpack is not running", delete_after=10)
        await ctx.message.delete()
        return
    
    status = "🔄 Running"
    if chatpack_paused:
        status = "⏸️ PAUSED (AFK response pending)" if afk_response_pending else "⏸️ PAUSED"
    
    message_count = len(chatpack_messages) if chatpack_messages else 0
    
    embed = discord.Embed(
        title="Chatpack Status",
        color=0x00ff00 if not chatpack_paused else 0xffaa00,
        description=f"**Status:** {status}\n**Messages loaded:** {message_count}\n**Anti-AFK enabled:** {'✅' if antiafk_enabled else '❌'}"
    )
    
    if chatpack_paused:
        embed.add_field(name="Tip", value="Use `.unpause` to manually resume", inline=False)
    
    await ctx.send(embed=embed, delete_after=15)
    await ctx.message.delete()

async def chatpack_loop(channel, mode="fast"):
    """hoe some nigga while also outlasting as long as u want"""
    global chatpack_running, chatpack_messages, chatpack_paused, afk_response_pending
    
    # Dynamic speed control based on mode
    if mode.lower() == "turbo":
        base_delay = 0.3  # Ultra fast mode
    elif mode.lower() == "safe":
        base_delay = 1.2  # Conservative mode
    else:
        base_delay = 0.6  # Default fast mode
    current_delay = base_delay
    consecutive_successes = 0
    rate_limit_hits = 0
    
    while chatpack_running and chatpack_messages:
        # 🛑 PAUSE SYSTEM: Wait if AFK response is happening
        while chatpack_paused and afk_response_pending:
            print("⏸️ Chatpack paused for AFK response...")
            await asyncio.sleep(0.1)  # Short sleep while paused
            
        # Exit if stopped during pause
        if not chatpack_running:
            break
            
        try:
            message = random.choice(chatpack_messages)
            await channel.send(message)
            
            # Success! Track it and potentially speed up
            consecutive_successes += 1
            
            # Speed up if we've had many successes
            if consecutive_successes >= 5:
                current_delay = max(0.4, current_delay * 0.95)  # Gradually get faster
                consecutive_successes = 0
            
            # Reset rate limit counter on success
            if rate_limit_hits > 0:
                rate_limit_hits -= 1
            
            # Use current delay with small randomization
            await asyncio.sleep(current_delay + random.uniform(0.1, 0.3))
            
        except discord.errors.HTTPException as e:
            consecutive_successes = 0  # Reset success counter
            
            if e.status == 429:  # Rate limited
                rate_limit_hits += 1
                print(f"Rate limited! Hits: {rate_limit_hits}")
                
                # Use Discord's recommended retry_after if available
                retry_after = getattr(e, 'retry_after', None)
                if retry_after:
                    await asyncio.sleep(retry_after + random.uniform(0.2, 0.8))
                else:
                    # Exponential backoff based on consecutive rate limits
                    backoff_time = min(30, 2 ** rate_limit_hits + random.uniform(1, 3))
                    await asyncio.sleep(backoff_time)
                
                # Increase delay for next messages based on rate limit frequency
                current_delay = min(3.0, base_delay * (1.5 ** rate_limit_hits))
                
            else:
                print(f"Error sending message: {e}")
                await asyncio.sleep(random.uniform(1, 2))
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Unexpected error in killing: {e}")
            await asyncio.sleep(3)

# Group Chat Name Killing Commands  
@bot.command()
async def killgc(ctx, target=None, filename="killgc.txt"):
    """Start group chat name changing from specified txt file"""
    global killgc_running, killgc_task, killgc_names
    
    if killgc_running:
        await ctx.send("Kill GC is already running! Use .stopkillgc to stop it first.", delete_after=5)
        await ctx.message.delete()
        return
    
    # Determine target channel (group chat or current channel)
    target_channel = None
    if target is None:
        # Use current channel
        target_channel = ctx.channel
        # Check if it's actually a group chat
        if not (hasattr(ctx.channel, 'type') and str(ctx.channel.type) == 'group'):
            await ctx.send("❌ Current channel is not a group chat! Use this command in a group chat or specify a channel ID.", delete_after=5)
            await ctx.message.delete()
            return
    else:
        try:
            # Try to get channel by ID
            if target.isdigit():
                target_channel = bot.get_channel(int(target))
                if not target_channel:
                    await ctx.send(f"❌ Channel with ID {target} not found!", delete_after=5)
                    await ctx.message.delete()
                    return
                # Check if it's a group chat
                if not (hasattr(target_channel, 'type') and str(target_channel.type) == 'group'):
                    await ctx.send(f"❌ Channel {target} is not a group chat!", delete_after=5)
                    await ctx.message.delete()
                    return
            else:
                # If target is not a digit, treat it as filename
                filename = target
                target_channel = ctx.channel
                # Check if current channel is a group chat
                if not (hasattr(ctx.channel, 'type') and str(ctx.channel.type) == 'group'):
                    await ctx.send("❌ Current channel is not a group chat! Use this command in a group chat.", delete_after=5)
                    await ctx.message.delete()
                    return
        except:
            # If conversion fails, treat as filename
            filename = target
            target_channel = ctx.channel
            if not (hasattr(ctx.channel, 'type') and str(ctx.channel.type) == 'group'):
                await ctx.send("❌ Current channel is not a group chat! Use this command in a group chat.", delete_after=5)
                await ctx.message.delete()
                return
    
    # Check if file exists
    if not os.path.exists(filename):
        await ctx.send(f"File '{filename}' not found!", delete_after=5)
        await ctx.message.delete()
        return
    
    # Load names from file
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            killgc_names = [line.strip() for line in f.readlines() if line.strip()]
    except Exception as e:
        await ctx.send(f"Error reading file: {e}", delete_after=5)
        await ctx.message.delete()
        return
    
    if not killgc_names:
        await ctx.send("No names found in the file!", delete_after=5)
        await ctx.message.delete()
        return
    
    killgc_running = True
    killgc_task = asyncio.create_task(killgc_loop(target_channel))
    await ctx.send(f"✅ Kill GC started in group chat (ID: {target_channel.id}) with {len(killgc_names)} names", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def stopkillgc(ctx, target=None):
    """Stop the group chat name changing"""
    global killgc_running, killgc_task
    
    if not killgc_running:
        await ctx.send("Kill GC is not running!", delete_after=5)
        await ctx.message.delete()
        return
    
    killgc_running = False
    if killgc_task:
        killgc_task.cancel()
    
    await ctx.send("Kill GC stopped", delete_after=5)
    await ctx.message.delete()

async def killgc_loop(channel):
    """Loop through changing group chat names rapidly"""
    global killgc_running, killgc_names
    
    print(f"🚀 Starting killgc loop for channel ID: {channel.id}")
    
    while killgc_running and killgc_names:
        try:
            new_name = random.choice(killgc_names)
            print(f"🔄 Attempting to change group chat name to: '{new_name}'")
            
            # Change group chat name
            await channel.edit(name=new_name)
            print(f"✅ Successfully changed group chat name to: '{new_name}'")
            
            # Fast name changes with some randomization
            await asyncio.sleep(random.uniform(0.3, 0.8))
            
        except discord.errors.HTTPException as e:
            if e.status == 429:  # Rate limited by Discord
                print(f"⚠️ Rate limited! Status: {e.status}")
                retry_after = getattr(e, 'retry_after', None)
                if retry_after:
                    print(f"⏳ Waiting {retry_after} seconds...")
                    await asyncio.sleep(retry_after + random.uniform(0.1, 0.5))
                else:
                    await asyncio.sleep(random.uniform(3, 6))
            elif e.status == 403:  # No permission
                print("❌ No permission to change group chat name")
                break
            elif e.status == 400:  # Bad request (invalid name, etc.)
                print(f"❌ Invalid name format: '{new_name}' - skipping")
                await asyncio.sleep(0.5)
            else:
                print(f"❌ HTTP Error {e.status}: {e}")
                await asyncio.sleep(random.uniform(1, 3))
        except discord.errors.NotFound:
            print("❌ Group chat not found or no longer accessible")
            break
        except asyncio.CancelledError:
            print("🛑 killgc loop cancelled")
            break
        except Exception as e:
            print(f"❌ Unexpected error in killgc: {e}")
            await asyncio.sleep(random.uniform(1, 3))



# info commands
@bot.command(name='pfp', aliases=['avatar'])
async def avatarUrl(ctx, user_info):
    if ctx.message.mentions:
        user = ctx.message.mentions[0]
    else:
        try:
            user_id = int(user_info)
            user = await bot.fetch_user(user_id)
        except ValueError:
            await ctx.send("Please mention a user or provide a valid user ID.")
            return
        except discord.NotFound:
            await ctx.send("User not found. Please provide a valid user ID.")
            return

    if user:
        url = user.avatar_url_as(format='png', size=1024)
        await ctx.send(url)
    else:
        await ctx.send("User not found. Please provide a valid user or user ID.")
    
    await ctx.message.delete()

# status commands
@bot.command()
async def stream(ctx, action: str = None, *, stream_content: str = None):
    """Set streaming status on/off"""
    try:
        if action == 'off':
            await bot.change_presence(activity=None)
            await ctx.send("```Vanish turned off the stream.```", delete_after=10)
        elif action == 'on' and stream_content:
            await bot.change_presence(activity=discord.Streaming(name=stream_content, url='https://twitch.tv/vanish'))
            await ctx.send(f"```Vanish set the streaming status to: {stream_content}```", delete_after=10)
        else:
            await ctx.send("```Invalid command. Use `.stream on <content>` or `.stream off`.```", delete_after=10)
    except Exception as e:
        await ctx.send(f"```An error occurred: {e}```", delete_after=10)
    finally:
        await ctx.message.delete()

@bot.command()
async def playing(ctx, *, text):
    await bot.change_presence(activity=discord.Game(name=text))
    await ctx.send(f"vanish set status to playing heh **{text}**")

@bot.command()
async def watching(ctx, *, text):
    activity = discord.Activity(type=discord.ActivityType.watching, name=text)
    await bot.change_presence(activity=activity)
    await ctx.send(f"vanish status set to: watching **{text}**")

@bot.command()
async def listening(ctx, *, text):
    activity = discord.Activity(type=discord.ActivityType.listening, name=text)
    await bot.change_presence(activity=activity)
    await ctx.send(f"vanish status set to: listening to **{text}**")

@bot.command()
async def clearstatus(ctx):
    await bot.change_presence(activity=None)
    await ctx.send("vanish presence cleared.")

@bot.command()
async def statuscycle(ctx):
    global status_task
    if status_task:
        await ctx.send("vanish status cycling already running.")
        return

    async def cycle():
        global status_task
        try:
            while True:
                with open("status.txt", "r", encoding="utf-8") as f:
                    for line in f:
                        await bot.change_presence(activity=discord.Game(name=line.strip()))
                        await asyncio.sleep(10)
        except:
            pass

    status_task = bot.loop.create_task(cycle())
    await ctx.send("vanish  status cycling started from `status.txt`.")

@bot.command()
async def statusstop(ctx):
    global status_task
    if status_task:
        status_task.cancel()
        status_task = None
        await ctx.send("vanish SELFBOT status cycling is now off")
    else:
        await ctx.send("vanish SELFBOT no status cycling running.")

@bot.command()
async def customstatus(ctx, emoji, *, text):
    try:
        await bot.change_presence(activity=discord.CustomActivity(name=text, emoji=emoji))
        await ctx.send(f"custom status is set to: {emoji} {text}")
    except Exception as e:
        await ctx.send(f"error please contact vanish:: {e}")

@bot.command()
async def fakegame(ctx, *, text):
    await bot.change_presence(activity=discord.Game(name=text))
    await ctx.send(f"vanish SELFBOT Fake game status set: **{text}**")



# User Info Command
@bot.command()
async def userinfo(ctx, user: discord.User = None):
    """Get detailed user information"""
    if user is None:
        user = ctx.author
    
    # Handle display name and avatar safely
    try:
        display_name = user.display_name
    except AttributeError:
        try:
            display_name = user.name
        except:
            display_name = str(user)
    
    try:
        thumbnail_url = user.display_avatar.url
    except AttributeError:
        try:
            thumbnail_url = user.avatar.url if user.avatar else user.default_avatar.url
        except AttributeError:
            try:
                thumbnail_url = str(user.avatar_url)
            except:
                thumbnail_url = "https://cdn.discordapp.com/embed/avatars/0.png"
    
    embed = discord.Embed(
        title=f"{display_name}'s Information",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=thumbnail_url)
    embed.add_field(name="Username", value=f"{user.name}#{user.discriminator}", inline=True)
    embed.add_field(name="User ID", value=user.id, inline=True)
    embed.add_field(name="Account Created", value=user.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    
    if hasattr(user, 'joined_at') and user.joined_at:
        embed.add_field(name="Joined Server", value=user.joined_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    
    await ctx.send(embed=embed, delete_after=30)
    await ctx.message.delete()

# Server Info Command
@bot.command()
async def serverinfo(ctx):
    """Get server information"""
    guild = ctx.guild
    if not guild:
        await ctx.send("This command can only be used in servers nigga", delete_after=5)
        await ctx.message.delete()
        return
    
    embed = discord.Embed(
        title=f"{guild.name} Information",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    embed.add_field(name="Server ID", value=guild.id, inline=True)
    embed.add_field(name="Owner", value=f"<@{guild.owner_id}>", inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    
    await ctx.send(embed=embed, delete_after=30)
    await ctx.message.delete()

# Ping Command
@bot.command()
async def ping(ctx):
    """Ping command with debugging info"""
    try:
        latency = round(bot.latency * 1000)
        channel_type = "Server" if ctx.guild else "DM"
        guild_name = ctx.guild.name if ctx.guild else "Direct Message"
        
        await ctx.send(f"```🏓 Pong! {latency}ms\n📍 {channel_type}: {guild_name}\n✅ Commands working!```", delete_after=10)
        await ctx.message.delete()
        print(f"✅ Ping successful in {channel_type} ({guild_name}) - {latency}ms")
    except Exception as e:
        print(f"❌ Ping failed: {e}")
        print(f"Context: {type(ctx.channel).__name__} in {ctx.guild.name if ctx.guild else 'DM'}")

# ========== AUTOMATION & SPAM COMMANDS ==========
@bot.command()
async def stam(ctx, *, message: str):
    """Spam a message with counter"""
    global spam_running, spam_task
    
    if spam_running:
        await ctx.send("Spam is already running! Use !stamstop to stop it first.", delete_after=5)
        await ctx.message.delete()
        return
    
    spam_running = True
    spam_task = asyncio.create_task(spam_loop(ctx.channel, message))
    await ctx.send(f"Spam started with message: {message}", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def stamstop(ctx):
    """Stop spamming"""
    global spam_running, spam_task
    
    if not spam_running:
        await ctx.send("Spam is not running!", delete_after=5)
        await ctx.message.delete()
        return
    
    spam_running = False
    if spam_task:
        spam_task.cancel()
    
    await ctx.send("Spam stopped", delete_after=5)
    await ctx.message.delete()

async def spam_loop(channel, message):
    """Loop spam messages with counter"""
    global spam_running
    counter = 1
    
    while spam_running:
        try:
            await channel.send(f"{message} [{counter}]")
            counter += 1
            await asyncio.sleep(random.uniform(1.5, 3.0))
        except discord.errors.HTTPException as e:
            if e.status == 429:
                retry_after = getattr(e, 'retry_after', None)
                if retry_after:
                    await asyncio.sleep(retry_after + 2)
                else:
                    await asyncio.sleep(10)
            else:
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in spam loop: {e}")
            await asyncio.sleep(3)

# utility
@bot.command()
async def purge(ctx, amount: int):
    """Delete your own messages"""
    if amount <= 0:
        await ctx.send("Please provide a valid number!", delete_after=5)
        await ctx.message.delete()
        return
    
    deleted = 0
    async for message in ctx.channel.history(limit=amount * 2):
        if message.author == bot.user and deleted < amount:
            try:
                await message.delete()
                deleted += 1
                await asyncio.sleep(0.5)  # Rate limit protection
            except:
                pass
    
    temp_msg = await ctx.send(f"Deleted {deleted} of your messages", delete_after=3)
    await ctx.message.delete()

# Reminder Command
@bot.command()
async def remind(ctx, seconds: int, *, message: str):
    """Set a reminder"""
    if seconds <= 0:
        await ctx.send("Please provide a valid number of seconds!", delete_after=5)
        await ctx.message.delete()
        return
    
    await ctx.send(f"Reminder set for {seconds} seconds: {message}", delete_after=5)
    await ctx.message.delete()
    
    await asyncio.sleep(seconds)
    embed = discord.Embed(
        title="⏰ Reminder",
        description=message,
        color=0xffff00,
        timestamp=datetime.now()
    )
    await ctx.send(embed=embed)

# Note Commands
@bot.command()
async def note(ctx, *, text: str):
    """Save a note"""
    global user_note
    user_note = text
    await ctx.send(f"Note saved: {text}", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def getnote(ctx):
    """Get your saved note"""
    global user_note
    if not user_note:
        await ctx.send("No note saved!", delete_after=5)
    else:
        embed = discord.Embed(
            title="📝 Your Note",
            description=user_note,
            color=0x00ff00
        )
        await ctx.send(embed=embed, delete_after=20)
    await ctx.message.delete()

# Anti-AFK Toggle Commands
@bot.command()
async def antiafk(ctx, toggle: str = None):
    """Toggle anti-AFK on/off"""
    global antiafk_enabled
    
    if toggle is None:
        status = "enabled" if antiafk_enabled else "disabled"
        await ctx.send(f"Anti-AFK is currently {status}. Use `.antiafk on` or `.antiafk off`", delete_after=5)
        await ctx.message.delete()
        return
    
    toggle = toggle.lower()
    if toggle == "on":
        antiafk_enabled = True
        await ctx.send("✅ Anti-AFK enabled - Will respond to AFK checks", delete_after=5)
    elif toggle == "off":
        antiafk_enabled = False
        await ctx.send("❌ Anti-AFK disabled - Will not respond to AFK checks", delete_after=5)
    else:
        await ctx.send("❓ Use `.antiafk on` or `.antiafk off`", delete_after=5)
    
    await ctx.message.delete()

# Prefix Change Command
@bot.command()
async def prefix(ctx, new_prefix: str = None):
    """Change bot command prefix"""
    if new_prefix is None:
        await ctx.send(f"Current prefix: `{bot.command_prefix}`\nUse `.prefix <new_prefix>` to change it", delete_after=5)
        await ctx.message.delete()
        return
    
    if len(new_prefix) > 3:
        await ctx.send("Prefix must be 3 characters or less!", delete_after=5)
        await ctx.message.delete()
        return
    
    old_prefix = bot.command_prefix
    bot.command_prefix = new_prefix
    await ctx.send(f"Prefix changed from `{old_prefix}` to `{new_prefix}`", delete_after=5)
    await ctx.message.delete()

# Anti-GC Commands
@bot.command()
async def antigc(ctx, *, message: str = "nah im good"):
    """Enable anti-GC with custom message"""
    global antigc_enabled, antigc_message
    
    antigc_enabled = True
    antigc_message = message
    
    # Initialize tracking set for existing group chats to prevent false triggers
    if not hasattr(bot, '_processed_antigc_channels'):
        bot._processed_antigc_channels = set()
    
    # Add all current group chats to the processed set so anti-GC won't trigger on them
    existing_groups = []
    for channel in bot.private_channels:
        if (hasattr(channel, 'type') and str(channel.type) == 'group' and 
            hasattr(channel, 'recipients') and len(channel.recipients) > 1):
            bot._processed_antigc_channels.add(channel.id)
            existing_groups.append(channel.id)
    
    if existing_groups:
        print(f"🔄 Anti-GC enabled: Ignoring {len(existing_groups)} existing group chats")
    
    await ctx.send(f"✅ Anti-GC enabled! Message: '{message}' (Ignoring {len(existing_groups)} existing group chats)", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def stopantigc(ctx):
    """Disable anti-GC"""
    global antigc_enabled
    
    antigc_enabled = False
    await ctx.send("❌ Anti-GC disabled", delete_after=5)
    await ctx.message.delete()

@bot.command()
async def testafk(ctx):
    """Test anti-AFK patterns with examples"""
    global antiafk_enabled
    
    embed = discord.Embed(title="Anti-AFK Test & Info", color=0x00ff00 if antiafk_enabled else 0xff0000)
    
    status = "Enabled" if antiafk_enabled else "Disabled"
    embed.add_field(name="Status", value=status, inline=True)
    
    patterns = "`AFK CHECK SAY BANANA` → BANANA\n`AFK CHECK SAY [APPLE]` → APPLE\n`AFK CHECK` → random response\n`afk check say word` → WORD"
    embed.add_field(name="Supported Patterns", value=patterns, inline=False)
    
    embed.add_field(name="How it works", value="Bot detects AFK checks and responds automatically with the specified word or a random response", inline=False)
    
    if not antiafk_enabled:
        embed.add_field(name="⚠️ Note", value="Anti-AFK is currently disabled. Use `.antiafk on` to enable it.", inline=False)
    
    await ctx.send(embed=embed, delete_after=20)
    await ctx.message.delete()

@bot.command()
async def testantigc(ctx):
    """Test anti-GC status and simulate group chat leave"""
    global antigc_enabled, antigc_message
    
    status = "✅ Enabled" if antigc_enabled else "❌ Disabled"
    
    # Check if current channel is a group
    is_group = False
    if hasattr(ctx.channel, 'type'):
        if str(ctx.channel.type) == 'group':
            is_group = True
    
    embed = discord.Embed(title="Anti-GC Status", color=0x00ff00 if antigc_enabled else 0xff0000)
    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(name="Message", value=f"'{antigc_message}'" if antigc_enabled else "N/A", inline=True)
    embed.add_field(name="Current Channel Type", value=str(ctx.channel.type), inline=True)
    embed.add_field(name="Is Group Chat", value="Yes" if is_group else "No", inline=True)
    
    if hasattr(ctx.channel, 'recipients'):
        embed.add_field(name="Recipients Count", value=str(len(ctx.channel.recipients)), inline=True)
    
    await ctx.send(embed=embed, delete_after=15)
    await ctx.message.delete()

# Help Command (alias for menu)
@bot.command()
async def help(ctx):
    """Show custom command menu"""
    await menu(ctx)

# Custom Menu Command with ASCII Art
@bot.command()
async def menu(ctx):
    """Show custom command menu with ASCII art"""
    try:
        menu_text = """```ansi
 _   _  ___   _   _ _____ _____ _   _        
| | | |/ _ \ | \ | |_   _/  ___| | | |       
| | | / /_\ \|  \| | | | \ `--.| |_| |       
| | | |  _  || . ` | | |  `--. \  _  |       
\ \_/ / | | || |\  |_| |_/\__/ / | | |       
 \___/\_| |_/\_| \_/\___/\____/\_| |_/                                                                                               
 _____ _____ _     ____________  _____ _____ 
/  ___|  ___| |    |  ___| ___ \|  _  |_   _|
\ `--.| |__ | |    | |_  | |_/ /| | | | | |  
 `--. \  __|| |    |  _| | ___ \| | | | | |  
/\__/ / |___| |____| |   | |_/ /\ \_/ / | |  
\____/\____/\_____/\_|   \____/  \___/  \_/  
\u001b[2;31m Page 1 — Reaction Commands
\u001b[2;32m Page 2 — Status & Presence
\u001b[2;33m Page 3 — Chatpacking & Spamming
\u001b[2;34m Page 4 — Utility & Tools
\u001b[2;35m Page 5 — Information Commands
\u001b[2;36m Page 6 — Fun & Entertainment
\u001b[2;91m Page 7 — Destructive & Webhooks
\u001b[2;37mType .page<number> to open a section.
\u001b[2;36mExample: .page1 or .page7
```"""
        
        # Add delay for server commands to avoid rate limiting
        if ctx.guild:
            await asyncio.sleep(1.5)
            
        await ctx.send(menu_text, delete_after=45)
        
        # Stagger message deletion to appear more human-like
        if ctx.guild:
            await asyncio.sleep(0.8)
            
        await ctx.message.delete()
        
    except Exception as e:
        print(f"Error in menu command: {e}")
        # Fallback to simple text message
        try:
            await ctx.send("**Vanish V1 Selfbot Commands**\n\n"
                          "Use `.page1` through `.page13` for command categories\n"
                          "Example: `.page1` for reactions, `.page7` for raid commands", 
                          delete_after=15)
            await ctx.message.delete()
        except:
            pass

# Debug command to test basic functionality
@bot.command()
async def test(ctx):
    """Test basic send functionality"""
    try:
        print(f"✅ TEST COMMAND TRIGGERED")
        print(f"Channel type: {ctx.channel.type}")
        print(f"Channel ID: {ctx.channel.id}")
        print(f"Guild: {ctx.guild.name if ctx.guild else 'DM'}")
        print(f"Author: {ctx.author}")
        print(f"Bot user: {bot.user}")
        print(f"Is selfbot message: {ctx.author == bot.user}")
        
        await ctx.send("✅ Test successful! Selfbot is working in this channel.", delete_after=5)
        await ctx.message.delete()
        print(f"✅ Test message sent and deleted successfully")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print(f"Channel info - Type: {type(ctx.channel)}, ID: {getattr(ctx.channel, 'id', 'Unknown')}")

# Add a debug command specifically for servers
@bot.command()
async def servertest(ctx):
    """Test if commands work in servers"""
    if ctx.guild:
        try:
            print(f"🔄 Attempting server test in {ctx.guild.name}...")
            
            # Add delay to avoid detection
            await asyncio.sleep(2.0)
            
            await ctx.send(f"✅ Server test successful! Guild: {ctx.guild.name}\n🕐 Response delayed for stealth", delete_after=8)
            
            # Stagger deletion
            await asyncio.sleep(1.0)
            await ctx.message.delete()
            
            print(f"✅ Server test successful in {ctx.guild.name}")
        except Exception as e:
            print(f"❌ Server test failed in {ctx.guild.name}: {e}")
    else:
        await ctx.send("❌ This is not a server channel.", delete_after=5)
        await ctx.message.delete()

# Quick stealth test command
@bot.command()
async def stealth(ctx):
    """Stealth test with minimal footprint"""
    try:
        if ctx.guild:
            await asyncio.sleep(3.0)  # Long delay for stealth
            await ctx.send("👻", delete_after=3)
            await asyncio.sleep(1.5)
        else:
            await ctx.send("👻 Stealth test - DM mode", delete_after=3)
            
        await ctx.message.delete()
        location = f"Server: {ctx.guild.name}" if ctx.guild else "DM"
        print(f"👻 Stealth test completed in {location}")
    except Exception as e:
        print(f"❌ Stealth test failed: {e}")

# Simple help command without embeds for testing
@bot.command() 
async def simplehelp(ctx):
    """Basic help without embeds"""
    try:
        channel_info = f"Server: {ctx.guild.name}" if ctx.guild else "DM"
        help_text = f"""**Basic Commands:** ({channel_info})
.test - Test functionality
.servertest - Test server functionality  
.ping - Show latency
.simplehelp - This help message
.menu - Full command menu

**Debug Commands:**
.test - Comprehensive functionality test
.ping - Latency and basic info"""
        
        await ctx.send(help_text, delete_after=15)
        await ctx.message.delete()
        print(f"✅ Simple help sent successfully in {channel_info}")
    except Exception as e:
        print(f"❌ Simple help failed: {e}")
        print(f"Channel: {type(ctx.channel).__name__}, Guild: {ctx.guild.name if ctx.guild else 'DM'}")

@bot.command()
async def allcommands(ctx):
    """Show all commands in multiple messages to avoid character limit"""
    try:
        # Split commands into multiple messages to avoid 2000 character limit
        
        # Part 1: Reaction & Auto-Reply Commands
        part1 = """```Vanish V1 - All Commands (Part 1/4):
.autoreact <emoji>         - Auto-react to your messages
.addreact @user <emoji>    - Add user to auto-react targets
.removereact @user         - Remove user from auto-react targets
.stopreact                 - Stop auto-reacting
.reactlist                 - Show current auto-react targets
.reactrotate [on/off]      - Toggle emoji rotation for autoreact
.reactemojis <emojis>      - Set custom emoji list for autoreact
.superreact [@user]        - Enable super-react (requires Nitro)
.addsuperreact @user       - Add user to super-react targets
.removesuperreact @user    - Remove user from super-react targets
.stopsuperreact            - Stop super-reacting
.superreactlist            - Show current super-react targets
.superreactrotate [on/off] - Toggle emoji rotation for super-react
.superreactemojis <emojis> - Set custom emoji list for super-react
.reactstatus               - Show status of both react systems
.ar @user <msg>           - Auto-reply to a user
.arstop                   - Stop auto-replying```"""

        # Part 2: Spam & Automation Commands
        part2 = """```Vanish V1 - All Commands (Part 2/4):
.stam <msg>                - Spam a message with a counter
.stamstop                  - Stop spamming
.kill [channel_id]         - Start chatpack in channel
.turbo [channel_id]        - Ultra fast chatpack
.stopkill [channel_id]     - Stop chatpack
.killgc [channel_id]       - Start group chat name changing
.createkillgc              - Create default killgc.txt file
.stopkillgc                - Stop GC name changing
.snipe                     - Show last deleted message
.editsnipe                 - Show last edited message```"""

        # Part 3: Raid & Nuke Commands
        part3 = """```Vanish V1 - All Commands (Part 3/4):
.nuke                      - Nuke entire server
.spamchannels [name]       - Spam create channels
.spamroles [name]          - Spam create roles
.deletechannels            - Delete all channels
.deleteroles               - Delete all roles
.deletemojis               - Delete all emojis
.deletewebhooks            - Delete all webhooks
.massban                   - Ban all members
.masskick                  - Kick all members
.dmall <msg>               - DM all members```"""

        # Part 4: Utility & System Commands
        part4 = """```Vanish V1 - All Commands (Part 4/4):
.gayrate @user             - Rate how gay someone is
.ppsize @user              - Check someone's pp size
.simp @user                - Check simp level
.ping                      - Show bot latency
.pfp <@user/user_id>       - Show user's avatar
.userinfo [@user]          - Show user info
.serverinfo                - Show server info
.purge <amount>            - Delete your messages
.remind <sec> <msg>        - Set a reminder
.note <text>               - Save a note
.getnote                   - Get your note
.antiafk on/off            - Toggle anti-AFK system
.afksecurity [secure/open] - Toggle AFK security mode
.testafk                   - Test anti-AFK patterns
.antigc <message>          - Enable anti-GC with message
.stopantigc                - Disable anti-GC
.testantigc                - Test anti-GC status
.restart                   - Restart the selfbot
.prefix <new>              - Change command prefix
.stream on/off <content>   - Set streaming status
.customstatus <status>     - Set custom status
.clearstatus               - Clear custom status```"""

        # Send all parts with small delays
        await ctx.send(part1, delete_after=45)
        await asyncio.sleep(0.5)
        await ctx.send(part2, delete_after=45)
        await asyncio.sleep(0.5)
        await ctx.send(part3, delete_after=45)
        await asyncio.sleep(0.5)
        await ctx.send(part4, delete_after=45)
        
        await ctx.message.delete()
        
    except Exception as e:
        print(f"Error in allcommands: {e}")
        await ctx.send("Command list temporarily unavailable. Use .menu instead.", delete_after=10)
        try:
            await ctx.message.delete()
        except:
            pass

@bot.command()
async def reactions(ctx):
    """Show reaction commands"""
    embed = discord.Embed(
        title="🎭 Reaction Commands",
        color=0x00ff00,
        description="Auto-react and Super-react system commands"
    )
    
    embed.add_field(
        name="🔄 **Auto-React**",
        value="```\n.autoreact <emoji> - Auto-react to your messages\n.addreact @user <emoji> - Add user to targets\n.removereact @user - Remove user from targets\n.stopreact - Stop auto-reacting\n.reactlist - Show current targets\n.reactrotate [on/off] - Toggle emoji rotation\n.reactemojis <emojis> - Set emoji list\n```",
        inline=False
    )
    
    embed.add_field(
        name="💥 **Super-React** (Nitro)",
        value="```\n.superreact [@user] - Enable burst reactions\n.addsuperreact @user - Add user to targets\n.removesuperreact @user - Remove from targets\n.stopsuperreact - Stop super-reacting\n.superreactlist - Show targets\n.superreactrotate [on/off] - Toggle rotation\n.superreactemojis <emojis> - Set emoji list\n```",
        inline=False
    )
    
    embed.add_field(
        name="📊 **Status**",
        value="```\n.reactstatus - Show both systems status\n```",
        inline=False
    )
    
    await ctx.send(embed=embed, delete_after=20)
    await ctx.message.delete()

@bot.command()
async def utility(ctx):
    """Show utility commands"""
    embed = discord.Embed(
        title="🛠️ Utility Commands",
        color=0x0099ff,
        description="General purpose and utility commands"
    )
    
    embed.add_field(
        name="📝 **Messages**",
        value="```\n.snipe - Show last deleted message\n.editsnipe - Show last edited message\n.purge <amount> - Delete your messages\n.ar @user <msg> - Auto-reply to user\n.arstop - Stop auto-replying\n```",
        inline=False
    )
    
    embed.add_field(
        name="⏰ **Tools**",
        value="```\n.remind <sec> <msg> - Set a reminder\n.note <text> - Save a note\n.getnote - Get your saved note\n.ping - Show bot latency\n.prefix <new> - Change command prefix\n```",
        inline=False
    )
    
    embed.add_field(
        name="🎭 **Status**",
        value="```\n.stream on/off <content> - Set streaming status\n.customstatus <status> - Set custom status\n.clearstatus - Clear custom status\n```",
        inline=False
    )
    
    await ctx.send(embed=embed, delete_after=20)
    await ctx.message.delete()

@bot.command()
async def info(ctx):
    """Show information commands"""
    embed = discord.Embed(
        title="ℹ️ Information Commands",
        color=0xffff00,
        description="Get information about users and servers"
    )
    
    embed.add_field(
        name="👤 **User Info**",
        value="```\n.pfp <@user/user_id> - Show user's avatar\n.userinfo [@user] - Show detailed user info\n```",
        inline=False
    )
    
    embed.add_field(
        name="🏠 **Server Info**",
        value="```\n.serverinfo - Show server information\n```",
        inline=False
    )
    
    await ctx.send(embed=embed, delete_after=20)
    await ctx.message.delete()

@bot.command()
async def automation(ctx):
    """Show automation commands"""
    embed = discord.Embed(
        title="🤖 Automation Commands",
        color=0x9932cc,
        description="Automated systems and spam tools"
    )
    
    embed.add_field(
        name="😴 **Anti-AFK System**",
        value="```\n.antiafk on/off - Toggle anti-AFK\n.afksecurity [secure/open] - Security mode\n.testafk - Test anti-AFK patterns\n```",
        inline=False
    )
    
    embed.add_field(
        name="🚫 **Anti-GC System**",
        value="```\n.antigc <message> - Enable anti group-chat\n.stopantigc - Disable anti-GC\n.testantigc - Test anti-GC status\n```",
        inline=False
    )
    
    embed.add_field(
        name="💬 **Chat Systems**",
        value="```\n.stam <msg> - Spam messages with counter\n.stamstop - Stop spamming\n.kill [channel_id] - Start chatpack\n.turbo [channel_id] - Ultra fast chatpack\n.stopkill [channel_id] - Stop chatpack\n```",
        inline=False
    )
    
    embed.add_field(
        name="📱 **Group Chat**",
        value="```\n.killgc [channel_id] - GC name changing\n.createkillgc - Create killgc.txt\n.stopkillgc - Stop GC killing\n```",
        inline=False
    )
    
    await ctx.send(embed=embed, delete_after=20)
    await ctx.message.delete()

@bot.command()
async def fun(ctx):
    """Show fun commands"""
    embed = discord.Embed(
        title="🎉 Fun Commands",
        color=0xff69b4,
        description="Entertainment and joke commands"
    )
    
    embed.add_field(
        name="😂 **Rating System**",
        value="```\n.gayrate @user - Rate how gay someone is\n.ppsize @user - Check someone's pp size\n.simp @user - Check simp level\n```",
        inline=False
    )
    
    await ctx.send(embed=embed, delete_after=20)
    await ctx.message.delete()

@bot.command()
async def raid(ctx):
    """Show raid commands - USE AT YOUR OWN RISK"""
    embed = discord.Embed(
        title="⚠️ Raid Commands ⚠️",
        color=0xff4500,
        description="**WARNING: These commands are destructive!**\n*Use at your own risk and responsibility*"
    )
    
    embed.add_field(
        name="🏗️ **Creation Spam**",
        value="```\n.spamchannels [name] - Spam create channels\n.spamroles [name] - Spam create roles\n```",
        inline=False
    )
    
    embed.add_field(
        name="🗑️ **Deletion**",
        value="```\n.deletechannels - Delete all channels\n.deleteroles - Delete all roles\n.deletemojis - Delete all emojis\n.deletewebhooks - Delete all webhooks\n```",
        inline=False
    )
    
    embed.add_field(
        name="👥 **Member Actions**",
        value="```\n.dmall <msg> - DM all server members\n```",
        inline=False
    )
    
    embed.set_footer(text="⚠️ These commands require appropriate permissions and can get your account banned!")
    
    await ctx.send(embed=embed, delete_after=25)
    await ctx.message.delete()

@bot.command()
async def nukehelp(ctx):
    """Show nuke commands - EXTREME CAUTION"""
    embed = discord.Embed(
        title="💀 NUKE Commands 💀",
        color=0x8b0000,
        description="**🚨 EXTREME DANGER ZONE 🚨**\n*These commands will destroy servers completely!*"
    )
    
    embed.add_field(
        name="💣 **Total Destruction**",
        value="```\n.nuke - Complete server destruction\n.shutdown - Emergency bot shutdown\n```",
        inline=False
    )
    
    embed.add_field(
        name="⚠️ **CRITICAL WARNING**",
        value="• These commands are **IRREVERSIBLE**\n"
              "• Will **PERMANENTLY** destroy server data\n"
              "• Can result in **ACCOUNT TERMINATION**\n"
              "• Use only with **FULL PERMISSION**",
        inline=False
    )
    
    embed.set_footer(text="🚨 PROCEED WITH EXTREME CAUTION - NO UNDO POSSIBLE! 🚨")
    
    await ctx.send(embed=embed, delete_after=30)
    await ctx.message.delete()

@bot.command()
async def mass(ctx):
    """Show mass action commands - HIGH RISK"""
    embed = discord.Embed(
        title="⚡ Mass Action Commands ⚡",
        color=0xff1493,
        description="**⚠️ HIGH RISK COMMANDS ⚠️**\n*Mass actions that affect all server members*"
    )
    
    embed.add_field(
        name="👥 **Mass Member Actions**",
        value="```\n.massban - Ban ALL server members\n.masskick - Kick ALL server members\n```",
        inline=False
    )
    
    embed.add_field(
        name="🚨 **WARNING**",
        value="• These affect **ALL** server members\n"
              "• Actions are **IMMEDIATE** and **IRREVERSIBLE**\n"
              "• Will likely result in **ACCOUNT BAN**\n"
              "• Requires administrator permissions",
        inline=False
    )
    
    embed.set_footer(text="⚠️ Use responsibly - High chance of account termination!")
    
    await ctx.send(embed=embed, delete_after=25)
    await ctx.message.delete()

# ========== PAGE SYSTEM COMMANDS ==========

@bot.command()
async def page1(ctx):
    """Show reaction commands page"""
    try:
        await ctx.send(f"```ansi\n{PAGES['page1']}```")
    except Exception as e:
        await ctx.send(f"Error loading page 1: {e}")

@bot.command()
async def page2(ctx):
    """Show status & presence commands page"""
    try:
        await ctx.send(f"```ansi\n{PAGES['page2']}```")
    except Exception as e:
        await ctx.send(f"Error loading page 2: {e}")

@bot.command()
async def page3(ctx):
    """Show automation & spam commands page"""
    try:
        await ctx.send(f"```ansi\n{PAGES['page3']}```")
    except Exception as e:
        await ctx.send(f"Error loading page 3: {e}")

@bot.command()
async def page4(ctx):
    """Show utility & tools commands page"""
    try:
        await ctx.send(f"```ansi\n{PAGES['page4']}```")
    except Exception as e:
        await ctx.send(f"Error loading page 4: {e}")

@bot.command()
async def page5(ctx):
    """Show information commands page"""
    try:
        await ctx.send(f"```ansi\n{PAGES['page5']}```")
    except Exception as e:
        await ctx.send(f"Error loading page 5: {e}")

@bot.command()
async def page6(ctx):
    """Show fun & entertainment commands page"""
    try:
        await ctx.send(f"```ansi\n{PAGES['page6']}```")
    except Exception as e:
        await ctx.send(f"Error loading page 6: {e}")

@bot.command()
async def page7(ctx):
    """Show destructive & webhook commands page"""
    try:
        await ctx.send(f"```ansi\n{PAGES['page7']}```")
    except Exception as e:
        await ctx.send(f"Error loading page 7: {e}")

# ========== SYSTEM COMMANDS ==========
@bot.command()
async def restart(ctx):
    """Restart the selfbot"""
    await ctx.send("🔄 Restarting selfbot...", delete_after=3)
    await ctx.message.delete()
    os._exit(0)

@bot.command()
async def shutdown(ctx):
    """Emergency shutdown"""
    await ctx.send("💀 Emergency shutdown initiated...", delete_after=2)
    await ctx.message.delete()
    os._exit(0)



# 🖥️ COMMAND PROMPT INTERFACE
import sys

def command_prompt_interface():
    """Run command prompt interface in separate thread"""
    global antiafk_enabled, antiafk_secure_mode, chatpack_running, chatpack_task, chatpack_messages
    global killgc_running, killgc_task, killgc_names, antigc_enabled, autoreact_targets
    global auto_reply_target_id, auto_reply_message, user_note
    
    print("\n" + "="*50)
    print("🖥️  COMMAND PROMPT INTERFACE ACTIVE")
    print("📝 Type 'help' for available commands")
    print("="*50)
    
    while True:
        try:
            cmd = input("\n[SELFBOT]> ").strip().lower()
            
            if cmd == "help":
                print("""
🖥️ COMMAND PROMPT COMMANDS:
├── status                    - Show bot status and info
├── afk on/off                - Toggle anti-AFK system
├── security                  - Toggle AFK security mode
├── kill <channel_id> [file]  - Start chatpack in specific channel
├── turbo <channel_id> [file] - Start turbo chatpack in specific channel
├── kill stop                 - Stop chatpack
├── killgc <channel_id> [file] - Start GC name killing in specific channel
├── killgc stop               - Stop GC name killing
├── antigc on/off             - Toggle anti-GC system  
├── stats                     - Show running statistics
├── restart                   - Restart the selfbot
├── exit                      - Close the selfbot
└── help                      - Show this menu
                """)
                
            elif cmd == "status":
                print(f"""
📊 SELFBOT STATUS:
├── Bot User: {bot.user if bot.user else 'Not logged in'}
├── Anti-AFK: {'✅ Enabled' if antiafk_enabled else '❌ Disabled'}
├── AFK Security: {'🔒 Secure' if antiafk_secure_mode else '⚠️ Open'}
├── Chatpack: {'🔥 Running' if chatpack_running else '💤 Stopped'}
├── Anti-GC: {'✅ Enabled' if antigc_enabled else '❌ Disabled'}
└── Prefix: {bot.command_prefix}
                """)
                
            elif cmd == "afk on":
                antiafk_enabled = True
                print("✅ Anti-AFK enabled via command prompt")
                
            elif cmd == "afk off":
                antiafk_enabled = False
                print("❌ Anti-AFK disabled via command prompt")
                
            elif cmd == "security":
                antiafk_secure_mode = not antiafk_secure_mode
                mode = "🔒 Secure" if antiafk_secure_mode else "⚠️ Open"
                print(f"🔄 AFK security mode: {mode}")
                
            elif cmd.startswith("kill ") and not cmd.endswith("stop"):
                
                parts = cmd.split()
                if len(parts) >= 2:
                    try:
                        channel_id = int(parts[1])
                        filename = parts[2] if len(parts) > 2 else "vanishwl.txt"
                        mode = "turbo" if cmd.startswith("turbo") else "fast"
                        
                        if chatpack_running:
                            print("⚠️ Chatpack already running! Stop it first.")
                            continue
                        
                        # Check if file exists
                        if not os.path.exists(filename):
                            print(f"❌ File '{filename}' not found!")
                            continue
                        
                        # Send command to queue
                        import uuid
                        cmd_id = str(uuid.uuid4())
                        command_queue.put({
                            'type': 'start_chatpack',
                            'id': cmd_id,
                            'channel_id': channel_id,
                            'filename': filename,
                            'mode': mode
                        })
                        
                        # Wait for response
                        import time
                        start_time = time.time()
                        while cmd_id not in command_responses and time.time() - start_time < 5:
                            time.sleep(0.1)
                        
                        if cmd_id in command_responses:
                            response = command_responses.pop(cmd_id)
                            print(response)
                            if "started" in response:
                                print(f"📁 File: {filename} | ⚡ Mode: {mode}")
                        else:
                            print("❌ Timeout waiting for response")
                        
                    except ValueError:
                        print("❌ Invalid channel ID! Use: kill <channel_id> [filename]")
                    except Exception as e:
                        print(f"❌ Error starting chatpack: {e}")
                else:
                    print("❌ Usage: kill <channel_id> [filename]")
            
            elif cmd.startswith("turbo "):
                # Handle turbo mode - same as kill but with turbo flag
                parts = cmd.split()
                if len(parts) >= 2:
                    try:
                        channel_id = int(parts[1])
                        filename = parts[2] if len(parts) > 2 else "vanishwl.txt"
                        
                        if chatpack_running:
                            print("⚠️ Chatpack already running! Stop it first.")
                            continue
                        
                        # Check if file exists
                        if not os.path.exists(filename):
                            print(f"❌ File '{filename}' not found!")
                            continue
                        
                        # Send command to queue
                        import uuid
                        cmd_id = str(uuid.uuid4())
                        command_queue.put({
                            'type': 'start_chatpack',
                            'id': cmd_id,
                            'channel_id': channel_id,
                            'filename': filename,
                            'mode': 'turbo'
                        })
                        
                        # Wait for response
                        import time
                        start_time = time.time()
                        while cmd_id not in command_responses and time.time() - start_time < 5:
                            time.sleep(0.1)
                        
                        if cmd_id in command_responses:
                            response = command_responses.pop(cmd_id)
                            print(f"🚀 TURBO {response}")
                            if "started" in response:
                                print(f"📁 File: {filename} | ⚡ Mode: TURBO")
                        else:
                            print("❌ Timeout waiting for response")
                        
                    except ValueError:
                        print("❌ Invalid channel ID! Use: turbo <channel_id> [filename]")
                    except Exception as e:
                        print(f"❌ Error starting turbo chatpack: {e}")
                else:
                    print("❌ Usage: turbo <channel_id> [filename]")
                    
            elif cmd == "kill stop":
                if chatpack_running:
                    chatpack_running = False
                    if chatpack_task:
                        chatpack_task.cancel()
                    print("🛑 Chatpack stopped via command prompt")
                else:
                    print("💤 Chatpack is not running")
            
            elif cmd.startswith("killgc ") and not cmd.endswith("stop"):
                
                parts = cmd.split()
                if len(parts) >= 2:
                    try:
                        channel_id = int(parts[1])
                        filename = parts[2] if len(parts) > 2 else "killgc.txt"
                        
                        if killgc_running:
                            print("⚠️ Kill GC already running! Stop it first.")
                            continue
                        
                        # Get channel
                        target_channel = bot.get_channel(channel_id)
                        if not target_channel:
                            print(f"❌ Channel {channel_id} not found!")
                            continue
                        
                        # Check if it's a group chat
                        if not (hasattr(target_channel, 'type') and str(target_channel.type) == 'group'):
                            print(f"❌ Channel {channel_id} is not a group chat!")
                            continue
                        
                        # Check if file exists
                        if not os.path.exists(filename):
                            print(f"❌ File '{filename}' not found!")
                            continue
                        
                        # Send command to queue
                        import uuid
                        cmd_id = str(uuid.uuid4())
                        command_queue.put({
                            'type': 'start_killgc',
                            'id': cmd_id,
                            'channel_id': channel_id,
                            'filename': filename
                        })
                        
                        # Wait for response
                        import time
                        start_time = time.time()
                        while cmd_id not in command_responses and time.time() - start_time < 5:
                            time.sleep(0.1)
                        
                        if cmd_id in command_responses:
                            response = command_responses.pop(cmd_id)
                            print(response)
                            if "Kill GC started" in response:
                                print(f"📁 File: {filename}")
                        else:
                            print("❌ Timeout waiting for response")
                        
                    except ValueError:
                        print("❌ Invalid channel ID! Use: killgc <channel_id> [filename]")
                    except Exception as e:
                        print(f"❌ Error starting Kill GC: {e}")
                else:
                    print("❌ Usage: killgc <channel_id> [filename]")
            
            elif cmd == "killgc stop":
                if killgc_running:
                    killgc_running = False
                    if killgc_task:
                        killgc_task.cancel()
                    print("🛑 Kill GC stopped via command prompt")
                else:
                    print("💤 Kill GC is not running")
                    
            elif cmd == "antigc on":
                antigc_enabled = True
                print("✅ Anti-GC enabled via command prompt")
                
            elif cmd == "antigc off":
                antigc_enabled = False
                print("❌ Anti-GC disabled via command prompt")
                
            elif cmd == "stats":
                autoreply_status = f"User ID: {auto_reply_target_id}" if auto_reply_target_id else "None"
                print(f"""
📈 STATISTICS:
├── Autoreact Targets: {len(autoreact_targets)}
├── Autoreply Target: {autoreply_status}
├── Chatpack Messages: {len(chatpack_messages)}
├── Kill GC Names: {len(killgc_names)}
└── Current Note: {user_note if user_note else 'None'}
                """)
                
            elif cmd == "restart":
                print("🔄 Restarting selfbot...")
                import subprocess
                subprocess.Popen([sys.executable, __file__])
                os._exit(0)
                
            elif cmd == "exit":
                print("👋 Shutting down selfbot...")
                os._exit(0)
                
            elif cmd == "":
                continue
                
            else:
                print("❓ Unknown command. Type 'help' for available commands.")
                
        except KeyboardInterrupt:
            print("\n👋 Command prompt closed")
            break
        except Exception as e:
            print(f"❌ Error in command prompt: {e}")

# Run the bot
if __name__ == "__main__":
    try:
    
        
        

        
        # Start command prompt interface in separate thread
        cmd_thread = threading.Thread(target=command_prompt_interface, daemon=True)
        cmd_thread.start()
        
        bot.run("", bot=False)
        
    except discord.LoginFailure:
        print("❌ ERROR: Invalid token! Please check your Discord token.")
        input("Press Enter to exit...")
    except discord.HTTPException as e:
        print(f"❌ HTTP Error: {e}")
        input("Press Enter to exit...")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        input("Press Enter to exit...")
