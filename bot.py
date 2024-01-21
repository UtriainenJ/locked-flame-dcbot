"""
Copyright © Krypton 2019-2023 - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized discord bot in Python programming language.

Version: 6.1.0
"""

import json
import logging
import os
import platform
import random
import sys
from datetime import datetime

import requests
from requests.auth import HTTPBasicAuth
import aiosqlite
import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context
from dotenv import load_dotenv

#from database import DatabaseManager

load_dotenv()

# If LOCAL send desktop / play music
show_notification = lambda *args: None
play_sound = lambda *args: None
if os.getenv("LOCAL") == "LOCAL":
    import pygame # Play sound mp3
    from plyer import notification # Send desktop notification
    # Local sound
    def play_sound():
        pygame.mixer.init()
        pygame.mixer.music.load("alert_sound_short.mp3")
        pygame.mixer.music.play(loops=3)

    # Local notification
    def show_notification(title, message):
        notification.notify(
            title=title,
            message=message,
            app_icon=None,
            timeout=10,  # seconds
        )

CHANNEL_ID_BOT_STATUS_LOCAL = 1187859524376342598
CHANNEL_ID_BOT_STATUS_HOSTED = 1187902358299091004
CHANNEL_ID_BOT_STATUS_HOSTED2 = 1188091059323019284

CHANNEL_ID_BOT_PING_ME = 1187859369493266432
SERVER_ID = 1187848575435157685

import time
count = 0
START_TIME = time.time()  # Record the start time

if not os.path.isfile(f"{os.path.realpath(os.path.dirname(__file__))}/config.json"):
    sys.exit("'config.json' not found! Please add it and try again.")
else:
    with open(f"{os.path.realpath(os.path.dirname(__file__))}/config.json") as file:
        config = json.load(file)

"""	
Setup bot intents (events restrictions)
For more information about intents, please go to the following websites:
https://discordpy.readthedocs.io/en/latest/intents.html
https://discordpy.readthedocs.io/en/latest/intents.html#privileged-intents


Default Intents:
intents.bans = True
intents.dm_messages = True
intents.dm_reactions = True
intents.dm_typing = True
intents.emojis = True
intents.emojis_and_stickers = True
intents.guild_messages = True
intents.guild_reactions = True
intents.guild_scheduled_events = True
intents.guild_typing = True
intents.guilds = True
intents.integrations = True
intents.invites = True
intents.messages = True # `message_content` is required to get the content of the messages
intents.reactions = True
intents.typing = True
intents.voice_states = True
intents.webhooks = True

Privileged Intents (Needs to be enabled on developer portal of Discord), please use them only if you need them:
intents.members = True
intents.message_content = True
intents.presences = True
"""

intents = discord.Intents.default()

"""
Uncomment this if you want to use prefix (normal) commands.
It is recommended to use slash commands and therefore not use prefix commands.

If you want to use prefix commands, make sure to also enable the intent below in the Discord developer portal.
"""
# intents.message_content = True

# Setup both of the loggers


class LoggingFormatter(logging.Formatter):
    # Colors
    black = "\x1b[30m"
    red = "\x1b[31m"
    green = "\x1b[32m"
    yellow = "\x1b[33m"
    blue = "\x1b[34m"
    gray = "\x1b[38m"
    # Styles
    reset = "\x1b[0m"
    bold = "\x1b[1m"

    COLORS = {
        logging.DEBUG: gray + bold,
        logging.INFO: blue + bold,
        logging.WARNING: yellow + bold,
        logging.ERROR: red,
        logging.CRITICAL: red + bold,
    }

    def format(self, record):
        log_color = self.COLORS[record.levelno]
        format = "(black){asctime}(reset) (levelcolor){levelname:<8}(reset) (green){name}(reset) {message}"
        format = format.replace("(black)", self.black + self.bold)
        format = format.replace("(reset)", self.reset)
        format = format.replace("(levelcolor)", log_color)
        format = format.replace("(green)", self.green + self.bold)
        formatter = logging.Formatter(format, "%Y-%m-%d %H:%M:%S", style="{")
        return formatter.format(record)


logger = logging.getLogger("discord_bot")
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(LoggingFormatter())
# File handler
file_handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
file_handler_formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}: {message}", "%Y-%m-%d %H:%M:%S", style="{"
)
file_handler.setFormatter(file_handler_formatter)

# Add the handlers
logger.addHandler(console_handler)
logger.addHandler(file_handler)

def format_elapsed_time(elapsed_time):
    days, remainder = divmod(elapsed_time, 86400)  # 1 day = 24 * 60 * 60 seconds
    hours, remainder = divmod(remainder, 3600)  # 1 hour = 60 * 60 seconds
    minutes, seconds = divmod(remainder, 60)

    return f"{int(days)} days, {int(hours)} hours, {int(minutes)} minutes, {int(seconds)} seconds"


class DiscordBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned_or(config["prefix"]),
            intents=intents,
            help_command=None,
        )
        """
        This creates custom bot variables so that we can access these variables in cogs more easily.

        For example, The config is available using the following code:
        - self.config # In this class
        - bot.config # In this file
        - self.bot.config # In cogs
        """
        self.logger = logger
        self.config = config
        self.database = None
        self.token = None
        self.expiry_timestamp = None

    async def init_db(self) -> None:
        async with aiosqlite.connect(
            f"{os.path.realpath(os.path.dirname(__file__))}/database/database.db"
        ) as db:
            with open(
                f"{os.path.realpath(os.path.dirname(__file__))}/database/schema.sql"
            ) as file:
                await db.executescript(file.read())
            await db.commit()

    async def load_cogs(self) -> None:
        """
        The code in this function is executed whenever the bot will start.
        """
        for file in os.listdir(f"{os.path.realpath(os.path.dirname(__file__))}/cogs"):
            if file.endswith(".py"):
                extension = file[:-3]
                try:
                    await self.load_extension(f"cogs.{extension}")
                    self.logger.info(f"Loaded extension '{extension}'")
                except Exception as e:
                    exception = f"{type(e).__name__}: {e}"
                    self.logger.error(
                        f"Failed to load extension {extension}\n{exception}"
                    )

    # this should be moved to a /cog folder
    @tasks.loop(seconds=10)
    async def check_status_living_flame_task(self) -> None:

        CLIENT_ID = os.getenv("CLIENT_ID")
        CLIENT_SECRET = os.getenv("CLIENT_SECRET")

        # Check if Access Token is about to expire
        global count
        count = count + 1

        # Check if we're due for a refresh
        if self.expiry_timestamp is not None and (count%60 == 1):
            current_timestamp = int(datetime.utcnow().timestamp())
            # Set the threshold for refreshing (e.g., 1 hour before expiry)
            refresh_threshold_seconds = 1 * 60 * 60
            # Calculate the difference between expiry and current timestamp
            time_difference = self.expiry_timestamp - current_timestamp
            # Check if the difference is less than the threshold
            if time_difference < refresh_threshold_seconds:
                self.logger.info("The token is about to expire. Refreshing now.")
                self.token = None

        # Get Access Token
        if self.token is None:
            try:
                response = requests.post(
                    "https://eu.battle.net/oauth/token",
                    auth=HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET),
                    data={"grant_type": "client_credentials"}
                )

                # Check if the request was successful (status code 200)
                if response.status_code == 200:
                    self.logger.info(response.json())
                    self.token = response.json().get("access_token")
                    self.logger.info(f"Loaded access token")
                    current_timestamp = int(datetime.utcnow().timestamp())
                    self.expiry_timestamp = current_timestamp + response.json().get("expires_in")
                else:
                    self.logger.error(f"Error getting access token: {response.status_code} - {response.text}")
                    return
            except requests.ConnectionError as e:
                self.logger.error(f"Connection error: {e}")
                return

        # Get population type
        try:
            # 5827 Living Flame; 5828 Crusader Strike
            response = requests.get("https://eu.api.blizzard.com/data/wow/connected-realm/5827",
                params={"access_token": self.token,
                        "namespace": "dynamic-classic1x-eu",
                        "locale": "en_GB",
                        "region": "eu"
                })
            if response.status_code == 200:
                response = response.json()
            else:
                self.logger.error(f"Error: {response.status_code} - {response.text}")
                return
        except requests.ConnectionError as e:
            self.logger.error(f"Connection error: {e}")
            return

        # Parse result
        try:
            type = response['population']['type']
        except (TypeError, KeyError) as e:
            self.logger.error(f"TypeError or KeyError: {e}\n:{type}")
            return
        # Queue response['has_queue'] True/False

        # Update channel message
        GUILD = bot.get_guild(SERVER_ID)

        # Hosted and Local to different channels
        ENV_LOCAL = os.getenv("LOCAL")
        if ENV_LOCAL == "LOCAL":
            CHANNEL_BOT_STATUS = GUILD.get_channel(CHANNEL_ID_BOT_STATUS_LOCAL)
        elif ENV_LOCAL == "HOSTED2":
            CHANNEL_BOT_STATUS = GUILD.get_channel(CHANNEL_ID_BOT_STATUS_HOSTED2)
        else:
            CHANNEL_BOT_STATUS = GUILD.get_channel(CHANNEL_ID_BOT_STATUS_HOSTED)

        elapsed_time_in_seconds = time.time() - START_TIME
        formatted_time = format_elapsed_time(elapsed_time_in_seconds)
        message = (f"🔥Living Flame🔥 Status: **{type}** elapsed_time: {formatted_time}; requests: {count:,}")

        if count%60 == 1:
            self.logger.info(message)

        if count%6  == 1: # Reduce spam
            try:
                try:
                    await CHANNEL_BOT_STATUS.purge()
                except discord.errors.NotFound as e:
                    self.logger.error(f"Error NotFound: {e}")
                await CHANNEL_BOT_STATUS.send(message)
            except discord.errors.HTTPException as e:
                self.logger.error(f"Error HTTPException: {e}")

        if type != "LOCKED" and type != "OFFLINE":
            CHANNEL_BOT_PING_ME = GUILD.get_channel(CHANNEL_ID_BOT_PING_ME)
            await CHANNEL_BOT_PING_ME.send(f"@everyone 🔥Living Flame🔥 Status: **{type}**")
            if os.getenv("LOCAL") == "LOCAL":
                play_sound()
                show_notification("🔥Living Flame🔥", "Realm is not LOCKED!")


    @check_status_living_flame_task.before_loop
    async def before_check_status_living_flame_task(self) -> None:
        """
        Before starting the task, we make sure the bot is ready
        """
        await self.wait_until_ready()

    @tasks.loop(minutes=1.0)
    async def status_task(self) -> None:
        """
        Setup the game status task of the bot.
        """
        statuses = ["with you!", "with Krypton!", "with humans!"]
        await self.change_presence(activity=discord.Game(random.choice(statuses)))

    @status_task.before_loop
    async def before_status_task(self) -> None:
        """
        Before starting the status changing task, we make sure the bot is ready
        """
        await self.wait_until_ready()

    async def setup_hook(self) -> None:
        """
        This will just be executed when the bot starts the first time.
        """
        self.logger.info(f"Logged in as {self.user.name}")
        self.logger.info(f"discord.py API version: {discord.__version__}")
        self.logger.info(f"Python version: {platform.python_version()}")
        self.logger.info(
            f"Running on: {platform.system()} {platform.release()} ({os.name})"
        )
        self.logger.info("-------------------")
        #await self.init_db()
        # No need to load cogs
        #await self.load_cogs()
        #self.status_task.start()
        #self.database = DatabaseManager(
        #    connection=await aiosqlite.connect(
        #        f"{os.path.realpath(os.path.dirname(__file__))}/database/database.db"
        #    )
        #)
        self.check_status_living_flame_task.start()

    async def on_message(self, message: discord.Message) -> None:
        """
        The code in this event is executed every time someone sends a message, with or without the prefix

        :param message: The message that was sent.
        """
        if message.author == self.user or message.author.bot:
            return
        await self.process_commands(message)

    async def on_command_completion(self, context: Context) -> None:
        """
        The code in this event is executed every time a normal command has been *successfully* executed.

        :param context: The context of the command that has been executed.
        """
        full_command_name = context.command.qualified_name
        split = full_command_name.split(" ")
        executed_command = str(split[0])
        if context.guild is not None:
            self.logger.info(
                f"Executed {executed_command} command in {context.guild.name} (ID: {context.guild.id}) by {context.author} (ID: {context.author.id})"
            )
        else:
            self.logger.info(
                f"Executed {executed_command} command by {context.author} (ID: {context.author.id}) in DMs"
            )

    async def on_command_error(self, context: Context, error) -> None:
        """
        The code in this event is executed every time a normal valid command catches an error.

        :param context: The context of the normal command that failed executing.
        :param error: The error that has been faced.
        """
        if isinstance(error, commands.CommandOnCooldown):
            minutes, seconds = divmod(error.retry_after, 60)
            hours, minutes = divmod(minutes, 60)
            hours = hours % 24
            embed = discord.Embed(
                description=f"**Please slow down** - You can use this command again in {f'{round(hours)} hours' if round(hours) > 0 else ''} {f'{round(minutes)} minutes' if round(minutes) > 0 else ''} {f'{round(seconds)} seconds' if round(seconds) > 0 else ''}.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.NotOwner):
            embed = discord.Embed(
                description="You are not the owner of the bot!", color=0xE02B2B
            )
            await context.send(embed=embed)
            if context.guild:
                self.logger.warning(
                    f"{context.author} (ID: {context.author.id}) tried to execute an owner only command in the guild {context.guild.name} (ID: {context.guild.id}), but the user is not an owner of the bot."
                )
            else:
                self.logger.warning(
                    f"{context.author} (ID: {context.author.id}) tried to execute an owner only command in the bot's DMs, but the user is not an owner of the bot."
                )
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                description="You are missing the permission(s) `"
                + ", ".join(error.missing_permissions)
                + "` to execute this command!",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                description="I am missing the permission(s) `"
                + ", ".join(error.missing_permissions)
                + "` to fully perform this command!",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="Error!",
                # We need to capitalize because the command arguments have no capital letter in the code and they are the first word in the error message.
                description=str(error).capitalize(),
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        else:
            raise error



bot = DiscordBot()
bot.run(os.getenv("TOKEN"))
