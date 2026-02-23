import discord
from discord.ext import commands
import asyncio
import time
from datetime import datetime, timezone, timedelta
from collections import deque
import os
import aiohttp
import base64
import re
import random
import timedelta
from tls_client import Session
from datetime import datetime, timedelta
import json

intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(command_prefix=',', self_bot=True, intents=intents)

def load_whitelist():
    try:
        with open(whitelist_file, "r") as f:
            return set(map(int, f.read().splitlines()))
    except FileNotFoundError:
        return set()

def save_whitelist(users):
    with open("agcwl.txt", "w") as f:
        for uid in users:
            f.write(f"{uid}\n")       
            
async def unfriend(user_id):
    async with aiohttp.ClientSession() as session:
        url = f"https://discord.com/api/v9/users/@me/relationships/{user_id}"
        headers = {
            "Authorization": bot.http.token,
            "Content-Type": "application/json",
        }

        async with session.delete(url, headers=headers) as response:
            if response.status == 204:
                print(f"Unfriended user {user_id}")
            else:
                print(f"Failed to unfriend {user_id}: {response.status} - {await response.text()}")               
    
            
async def silent_leave(channel_id, token):
    async with aiohttp.ClientSession() as session:
        url = f"https://discord.com/api/v9/channels/{channel_id}?silent=true"
        headers = {
            "Authorization": token,
            "Content-Type": "application/json",
        }
        async with session.delete(url, headers=headers):
            pass
        
def loadgcwl():
    try:
        with open("agcwl.txt", "r") as f:
            return set(map(int, f.read().splitlines()))
    except FileNotFoundError:
        return set()

def savegcwl(users):
    with open("agcwl.txt", "w") as f:
        for uid in users:
            f.write(f"{uid}\n")

gcwls = loadgcwl()        

@bot.event
async def on_private_channel_create(channel):
    global gc, gcmsg, gclog
    if isinstance(channel, discord.GroupChannel) and gc:
        await asyncio.sleep(1)

        print(f"Joined GC {channel.id}: Checking owner...")
        owner = channel.owner

        if owner.id == bot.user.id or owner.id in gcwls:
            print(f"Owner {owner.name} is whitelisted or bot itself. Staying in GC {channel.id}.")
            return

        print(f"Bot is not the owner. Checking last 10 messages...")
        adder = None

        try:
            async for message in channel.history(limit=10):
                if message.system_content and "added" in message.system_content.lower() and bot.user in message.mentions:
                    print(f"added to gc by {message.author}")
                    adder = message.author
                    break

            if adder is None:
                print("Adder not detected. leaving...")
                await channel.edit(name=gcmsg)
                await silent_leave(channel.id, token)
                return

            if adder.id != bot.user.id and adder.id not in gcwls:
                await unfriend(adder.id)
                await channel.edit(name=gcmsg)

                if gclog:
                    member_list = "\n".join([f"[{idx + 1}] {member.name}" for idx, member in enumerate(channel.recipients)])
                    embed = discord.Embed(title="Group Chat Left", color=discord.Color.blue())
                    embed.add_field(name="Adder", value=f"{adder.name}", inline=False)
                    embed.add_field(name="GC Owner", value=f"{owner.name}", inline=False)
                    embed.add_field(name="GC Members", value=member_list if member_list else "None", inline=False)

                    async with aiohttp.ClientSession() as session:
                        webhook = discord.Webhook.from_url(gclog, adapter=discord.AsyncWebhookAdapter(session))
                        await webhook.send(embed=embed)

                await silent_leave(channel.id, token)
            else:
                print(f"Adder {adder.name} is whitelisted. Staying in GC {channel.id}.")

        except Exception as e:
            print(f"Error processing GC {channel.id}: {e}")
            await silent_leave(channel.id, token)

    else:
        print(f"GC disabled or not a GroupChannel: {channel}")
     
            
reaction_emoji = None
reaction_active = False
react_queue = deque()
rate_limit_lock = asyncio.Lock()
gc = True
ap = False
gcmsg = "u cant trap a god"
gclog = "https://discord.com/api/webhooks/1371439553704890484/gXyYzYRvtqVmc53A4hgXyjJQqzJcuMpMgtJROFm0V1yj3fxhK1zoxSk5BK_s_epa793V"
whitelist_file = "agcwl.txt"
whitelisted_users = load_whitelist()
auto_replies = {}
hush_users = {}
start_time = datetime.now(timezone.utc)
auto_replies1 = {}
group_rename_tasks = {}
token = ""

# Load flood.txt safely
if os.path.exists("flood.txt"):
    try:
        with open("flood.txt", "r") as f:
            auto_replies = json.load(f)
    except json.JSONDecodeError:
        print("Corrupted flood.txt. Resetting.")
        auto_replies = {}
        with open("flood.txt", "w") as f:
            json.dump(auto_replies, f)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


# ------------------ REACT ------------------

@bot.command()
async def r(ctx, emoji: str):
    global reaction_emoji, reaction_active
    await ctx.message.delete()
    reaction_emoji = emoji
    reaction_active = True


@bot.command()
async def sr(ctx):
    global reaction_active
    await ctx.message.delete()
    reaction_active = False


@bot.event
async def on_message(message):
    await bot.process_commands(message)
    
    global afk_check_enabled
    content_lower = message.content.lower()
    channel_id = message.channel.id
    now = datetime.utcnow()

    # Detect AFK check if bot is mentioned and specific keywords are present
    if afk_check_enabled:  # Only process if AFK check is enabled
        if bot.user in message.mentions and any(word in content_lower for word in [
            "afk check", "afkcheck", "say", "afk", "afk chck", "chck", 
            "client check", "autobeef check", "check"
        ]):
            active_checks[channel_id] = now + timedelta(seconds=30)  # Track for 30 seconds
            return

        # Respond to messages in active AFK check channels
        if channel_id in active_checks and now < active_checks[channel_id]:
            # Check if the message is likely an AFK check (e.g., number or short text)
            if re.match(r"^\d+$", message.content.strip()) or len(message.content.strip()) < 10:
                del active_checks[channel_id]  # Stop tracking after responding
                async with message.channel.typing():
                    await asyncio.sleep(random.uniform(0.5, 2))  # Random delay for realism
                    await message.channel.send(random.choice(ANTI_AFK_RESPONSES))    

    # Reacting
    if message.author.id == bot.user.id and reaction_active and reaction_emoji:
        react_queue.append(message)
        asyncio.create_task(handle_reactions())

    # Auto reply
    elif str(message.author.id) in auto_replies:
        reply_msg = auto_replies[str(message.author.id)]
        response = reply_msg
        try:
            await message.reply(response)
        except:
            pass
        
    # Auto reply
    elif str(message.author.id) in auto_replies1:
        reply_msg = auto_replies1[str(message.author.id)]
        response = "A\n" + ("\n" * 100) + reply_msg
        try:
            await message.reply(response)
        except:
            pass
        
    if message.author == bot.user:
        return
        
    if message.author.id in hush_users:
        await message.delete()           



async def handle_reactions():
    while react_queue:
        msg = react_queue.popleft()
        async with rate_limit_lock:
            try:
                await msg.add_reaction(reaction_emoji)
            except:
                pass
            await asyncio.sleep(0.5)
            
async def aptask(ctx, message):
    global ap
    counter = 1
    channel = ctx.channel

    while ap:
        try:
            await channel.send(f"{message} ```{counter}```")
        except discord.Forbidden:
            continue
        except Exception as e:
            print(f"An error occurred: {e}")

        counter += 1
        await asyncio.sleep(3)            


# ------------------ AUTO REPLY ------------------

@bot.command()
async def ar(ctx, user: discord.User, *, reply_msg):
    await ctx.message.delete()
    auto_replies[str(user.id)] = reply_msg
    with open("flood.txt", "w") as f:
        json.dump(auto_replies, f)


@bot.command()
async def sar(ctx, user: discord.User):
    await ctx.message.delete()
    if str(user.id) in auto_replies:
        del auto_replies[str(user.id)]
        with open("flood.txt", "w") as f:
            json.dump(auto_replies, f) 
            
@bot.command()
async def ar1(ctx, user: discord.User, *, reply_msg):
    await ctx.message.delete()
    auto_replies1[str(user.id)] = reply_msg
    with open("flood1.txt", "w") as f:
        json.dump(auto_replies1, f)


@bot.command()
async def sar1(ctx, user: discord.User):
    await ctx.message.delete()
    if str(user.id) in auto_replies1:
        del auto_replies1[str(user.id)]
        with open("flood1.txt", "w") as f:
            json.dump(auto_replies1, f)             

@bot.command()
async def arlist(ctx):
    await ctx.message.delete()  # Wipe the command message
    # Initialize output parts
    ar_output = "**Users with AR:**\n```\n"
    if auto_replies:  # Check if auto_replies has entries
        ar_output += "\n".join(user_id for user_id in auto_replies.keys())
    else:
        ar_output += "None"
    ar_output += "\n```"
    
    ar1_output = "**Users with AR1:**\n```\n"
    if auto_replies1:  # Check if auto_replies1 has entries
        ar1_output += "\n".join(user_id for user_id in auto_replies1.keys())
    else:
        ar1_output += "None"
    ar1_output += "\n```"
    
    # Send combined output
    await ctx.send(f"{ar_output}\n{ar1_output}") 
             
# ------------------ STREAM STATUS ------------------

@bot.command()
async def s(ctx, *, status_text):
    await ctx.message.delete()
    streaming_status = discord.Streaming(name=status_text, url="https://twitch.tv/lament")
    await bot.change_presence(activity=streaming_status)


@bot.command()
async def ss(ctx):
    await ctx.message.delete()
    await bot.change_presence(activity=None)

# ------------------ GROUP CHANNEL RENAME ------------------

@bot.command()
async def gn(ctx, *, name):
    await ctx.message.delete()
    if not isinstance(ctx.channel, discord.GroupChannel):
        return

    if ctx.channel.id in group_rename_tasks:
        return

    counter = 1

    async def rename_loop():
        nonlocal counter
        while True:
            try:
                await ctx.channel.edit(name=f"{name} {counter}")
                counter += 1
                await asyncio.sleep(0.1)
            except:
                break

    task = asyncio.create_task(rename_loop())
    group_rename_tasks[ctx.channel.id] = task


@bot.command()
async def stopgn(ctx):
    await ctx.message.delete()
    task = group_rename_tasks.pop(ctx.channel.id, None)
    if task:
        task.cancel()
        
session = None
sesh = Session(client_identifier="chrome_115", random_tls_extension_order=True)

@bot.command()
async def setpfp(ctx, url: str = None):
    attachment = ctx.message.attachments[0] if ctx.message.attachments else None

    if not url and not attachment:
        return await ctx.send("```Please provide a URL or attach an image.```")

    image_url = url or attachment.url

    headers = {
        "authority": "discord.com",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "authorization": bot.http.token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/channels/@me",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": "en-US",
        "x-super-properties": "eyJvcyI6Ik1hYyBPUyBYIiwiYnJvd3NlciI6IlNhZmFyaSIsImRldmljZSI6IiIsInN5c3RlbV9sb2NhbGUiOiJlbi1VUyIsImJyb3dzZXJfdXNlcl9hZ2VudCI6Ik1vemlsbGEvNS4wIChNYWNpbnRvc2g7IEludGVsIE1hYyBPUyBYIDEwXzE1XzcpIEFwcGxlV2ViS2l0LzYwNS4xLjE1IChLSFRNTCwgbGlrZSBHZWNrbykgVmVyc2lvbi8xNi41IFNhZmFyaS82MDUuMS4xNSIsImJyb3dzZXJfdmVyc2lvbiI6IjE2LjUiLCJvc192ZXJzaW9uIjoiMTAuMTUuNyIsInJlZmVycmVyIjoiIiwicmVmZXJyaW5nX2RvbWFpbiI6IiIsInJlZmVycmVyX2N1cnJlbnQiOiIiLCJyZWZlcnJpbmdfZG9tYWluX2N1cnJlbnQiOiIiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNTA2ODQsImNsaWVudF9ldmVudF9zb3VyY2UiOm51bGx9"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as response:
            if response.status == 200:
                image_data = await response.read()
                image_b64 = base64.b64encode(image_data).decode()

                content_type = response.headers.get('Content-Type', '')
                image_format = 'gif' if 'gif' in content_type else 'png'

                payload = {
                    "avatar": f"data:image/{image_format};base64,{image_b64}"
                }

                response = sesh.patch("https://discord.com/api/v9/users/@me", json=payload, headers=headers)

                if response.status_code == 200:
                    await ctx.send("```Successfully set profile picture```")
                else:
                    await ctx.send(f"```Failed to update profile picture: {response.status_code}```")
            else:
                await ctx.send("```Failed to download image```")

@bot.command()
async def setname(ctx, *, name: str = None):
    if not name:
        await ctx.send("```Please provide a name to set```")
        return

    headers = {
            "authority": "discord.com",
            "method": "PATCH",
            "scheme": "https",
            "accept": "/",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US",
            "authorization": bot.http.token,
            "origin": "https://discord.com/",
            "sec-ch-ua": '"Not/A)Brand";v="99", "Brave";v="115", "Chromium";v="115"',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9020 Chrome/108.0.5359.215 Electron/22.3.26 Safari/537.36",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "X-Debug-Options": "bugReporterEnabled",
            "X-Discord-Locale": "en-US",
            "X-Discord-Timezone": "Asia/Calcutta",
            "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRGlzY29yZCBDbGllbnQiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfdmVyc2lvbiI6IjEuMC45MDIwIiwib3NfdmVyc2lvbiI6IjEwLjAuMTkwNDUiLCJvc19hcmNoIjoieDY0IiwiYXBwX2FyY2giOiJpYTMyIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV09XNjQpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIGRpc2NvcmQvMS4wLjkwMjAgQ2hyb21lLzEwOC4wLjUzNTkuMjE1IEVsZWN0cm9uLzIyLjMuMjYgU2FmYXJpLzUzNy4zNiIsImJyb3dzZXJfdmVyc2lvbiI6IjIyLjMuMjYiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNDAyMzcsIm5hdGl2ZV9idWlsZF9udW1iZXIiOjM4NTE3LCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsLCJkZXNpZ25faWQiOjB9"
        }

    payload = {
        "global_name": name
    }

    response = sesh.patch("https://discord.com/api/v9/users/@me", json=payload, headers=headers)
    
    if response.status_code == 200:
        await ctx.send(f"```Successfully set display name to: {name}```")
    else:
        await ctx.send(f"```Failed to update display name: {response.status_code}```") 
            
            
@bot.command()
async def antigc(ctx, mode: str = None, *, value: str = None):
    global gc, gclog, gcmsg, gcwls

    try:
        await ctx.message.delete()
    except:
        pass

    if mode is None or mode == "status":
        status = "enabled" if gc else "disabled"
        webhook_status = "Has set" if gclog else "Not Set"
        wl_count = len(gcwls)
        await ctx.send(
            f"**Anti-GC Status:** `{status}`\n"
            f"**Webhook:** `{webhook_status}`\n"
            f"**GC Rename Message:** `{gcmsg if gcmsg else 'None'}`\n"
            f"**Whitelisted Users:** `{wl_count}`",
            delete_after=10
        )
        return

    mode = mode.lower()

    if mode == "on":
        gc = True
        await ctx.send("antigc enabled.", delete_after=3)

    elif mode == "off":
        gc = False
        await ctx.send("antigc disabled.", delete_after=3)

    elif mode == "log" and value:
        gclog = value
        await ctx.send("Webhook link set for antigc.", delete_after=3)

    elif mode == "msg" and value:
        gcmsg = value
        await ctx.send(f"Group name edit message set to `{gcmsg}`.", delete_after=3)

    elif mode == "wl" and value:
        user_ids = re.findall(r"\d{15,}", value)
        if user_ids:
            added = []
            already = []
            for uid in user_ids:
                user_id = int(uid)
                if user_id not in gcwls:
                    gcwls.add(user_id)
                    added.append(user_id)
                else:
                    already.append(user_id)
            savegcwl(gcwls)

            response = ""
            if added:
                response += f"Added to whitelist: {' '.join(f'<@{uid}>' for uid in added)}\n"
            if already:
                response += f"Already whitelisted: {' '.join(f'<@{uid}>' for uid in already)}"

            await ctx.send(response.strip(), delete_after=5)
        else:
            await ctx.send("No valid user IDs or mentions found.", delete_after=3)

    elif mode == "unwl" and value:
        user_ids = re.findall(r"\d{15,}", value)
        if user_ids:
            removed = []
            not_found = []
            for uid in user_ids:
                user_id = int(uid)
                if user_id in gcwls:
                    gcwls.remove(user_id)
                    removed.append(user_id)
                else:
                    not_found.append(user_id)
            savegcwl(gcwls)

            response = ""
            if removed:
                response += f"Removed from whitelist: {' '.join(f'<@{uid}>' for uid in removed)}\n"
            if not_found:
                response += f"Not in whitelist: {' '.join(f'<@{uid}>' for uid in not_found)}"

            await ctx.send(response.strip(), delete_after=5)
        else:
            await ctx.send("No valid user IDs or mentions found.", delete_after=3)

    elif mode == "list":
        if not gcwls:
            await ctx.send("Whitelist is empty.", delete_after=5)
            return

        progress_msg = await ctx.send("```Fetching users...```")
        msg = "**Whitelisted Users:**\n```(user id) | username\n"
        fetched = 0
        total = len(gcwls)

        for i, uid in enumerate(gcwls, 1):
            user = bot.get_user(uid)
            if user is None:
                try:
                    user = await bot.fetch_user(uid)
                except:
                    user = None

            username = user.name if user else "Unknown"
            msg += f"{uid} | {username}\n"
            fetched += 1

            if i % 5 == 0 or i == total:
                percent = int((i / total) * 100)
                await progress_msg.edit(content=f"```[{percent}%] Done\nList {fetched}/{total} users...```")
            await asyncio.sleep(0.2)

        msg += "```"
        await progress_msg.delete()
        await ctx.send(msg, delete_after=15)

    else:
        await ctx.send(
            "Invalid usage. Use:\n"
            "`.antigc on/off`\n"
            "`.antigc log <webhook>`\n"
            "`.antigc msg <group name>`\n"
            "`.antigc wl <@user1/userid1> <@user2/userid2> ...>` (whitelist users)\n"
            "`.antigc unwl <@user/userid> ...` (remove users from whitelist)\n"
            "`.antigc list` (show whitelisted users)\n"
            "`.antigc status`",
            delete_after=20
        )
        
@bot.command()
async def ping(ctx):
    def convert_units(value):
        units = ["ps", "ns", "µs", "ms", "s"]
        scales = [1e-12, 1e-9, 1e-6, 1e-3, 1]  
        for i in range(len(scales) - 1, -1, -1):
            if value >= scales[i] or i == 0:
                return f"{value / scales[i]:.2f}{units[i]}"

    start_determinism = time.perf_counter()
    _ = ctx.prefix
    end_determinism = time.perf_counter()
    prefix_determinism_time = end_determinism - start_determinism  

    host = bot.latency
    api = (datetime.now(timezone.utc) - ctx.message.created_at.replace(tzinfo=timezone.utc)).total_seconds()
    now = datetime.now(timezone.utc)
    uptime_duration = now - start_time

    days = uptime_duration.days
    hours, remainder = divmod(uptime_duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    uptime_parts = []
    if days > 0:
        uptime_parts.append(f"{days}d")
    if hours > 0:
        uptime_parts.append(f"{hours}h")
    if minutes > 0:
        uptime_parts.append(f"{minutes}m")
    if seconds > 0 or not uptime_parts:
        uptime_parts.append(f"{seconds}s")

    uptime = " ".join(uptime_parts)

    response = (
        "```\n"
        "~ Bot's Status\n"
        "``````js\n"
        f"Host Latency: <{convert_units(host)}>\n"
        f"Uptime: <{uptime}>\n"
        "```"
    )
    
    await ctx.send(response)
    
# ------------------ AUOT DELETE ------------------    
    
@bot.command()
async def hush(ctx, member: discord.Member):
    if member.id not in hush_users:
        hush_users[member.id] = True
        await ctx.send(f"{member.mention} hush is now on ")
    else:
        await ctx.send(f"{member.mention} user has hush on them")

@bot.command()
async def hushoff(ctx, member: discord.Member):
    if member.id in hush_users:
        del hush_users[member.id]
        await ctx.send(f"{member.mention} hush is now off")
    else:
        await ctx.send(f"{member.mention} user does't has hush on them ") 
        
ANTI_AFK_RESPONSES = [
    "HERE",
]


active_users = {}

global afk_check_enabled
afk_check_enabled = False  # Initialize the variable
active_checks = {}


@bot.command()
async def godafk(ctx):
    global afk_check_enabled
    afk_check_enabled = not afk_check_enabled
    status = "enabled" if afk_check_enabled else "disabled"
    await ctx.send(content=f"Anti afk check is now {status}.")
    

auto_responses = {}
        
@bot.command()
async def purge(ctx, amount: int, channel_id: int = None):
    channel = bot.get_channel(channel_id) if channel_id else ctx.channel
    deleted = 0
    edited = 0
    cutoff = datetime.utcnow() - timedelta(days=14)

    async for message in channel.history(limit=None, oldest_first=False):
        if deleted + edited >= amount:
            break
        if message.author.id != bot.user.id:
            continue

        try:
            if message.created_at >= cutoff:
                await message.delete()
                deleted += 1
            else:
                await message.edit(content=".")
                edited += 1
            await asyncio.sleep(3)
        except Exception:
            continue

    await ctx.send(f"Deleted: {deleted} | Edited: {edited}", delete_after=5)     
    
@bot.command()
async def ap(ctx, *, message: str):
    global ap
    if ap:
        await ctx.message.delete()
        return

    ap = True
    await ctx.message.delete()
    await aptask(ctx, message)

@bot.command(name="ape")
async def ape(ctx):
    global ap
    ap = False
    await ctx.message.delete()    
            
@bot.command()
async def av(ctx, user: discord.User = None):
    try:
        if user is None:  # If no user is provided, get the bot's own avatar
            user = bot.user


        # Check if the user has an avatar
        if user.avatar:
            avatar_url = user.avatar_url
            await ctx.send(f"Avatar URL: {avatar_url}", delete_after=10101010101001010100101111)  # Delete response message after 10101010101001010100101111 seconds
        else:
            await ctx.send(f"{user.name} does not have an avatar.", delete_after=10101010101001010100101111)  # Delete response message after 10101010101001010100101111 seconds


        # Delete the command message itself after 2 seconds
        await asyncio.sleep(2)
        await ctx.message.delete()
    except Exception as e:
        await ctx.send(f"An error occurred: {e}", delete_after=10101010101001010100101111)  # Delete response message after 10101010101001010100101111 seconds


# ------------------ RUN ------------------

bot.run(token, bot=False)