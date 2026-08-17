import sys
import site
sys.path.insert(0, site.getusersitepackages())

import discord
import discord.opus
import discord.voice_client

try:
    if not discord.opus.is_loaded():
        discord.opus._load_default()
except Exception as e:
    print(f"[OPUS WARN] Could not load opus: {e}")

try:
    import davey
    discord.voice_client.has_dave = True
except Exception as e:
    print(f"[VOICE WARN] Could not import davey: {e}")

from discord.ext import commands
import asyncio
import os
import logging

from config import DISCORD_TOKEN, DEFAULT_PREFIX, BOT_NAME, BOT_VERSION, WEB_PORT, YOUTUBE_STATUS_URL, STATUS_TEXT
from utils.database import init_db
from web.server import run_web_server, set_bot_reference



# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ResonanceApex")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix=DEFAULT_PREFIX, intents=intents, help_command=None)

COGS = [
    "cogs.music",
    "cogs.audio_fx",
    "cogs.dj",
    "cogs.playlists",
    "cogs.soundboard",
    "cogs.lyrics",
    "cogs.chatbot",
    "cogs.help",
]


@bot.command(name="sync")
@commands.has_permissions(administrator=True)
async def sync_cmd(ctx: commands.Context):
    """Force sync slash commands to current server immediately"""
    msg = await ctx.send("🔄 Synchronizing slash commands to this server...")
    try:
        guild = ctx.guild
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        await msg.edit(content=f"✅ Successfully synchronized `{len(synced)}` Slash Commands to **{guild.name}**! They are ready to use with `/` now.")
    except Exception as e:
        await msg.edit(content=f"❌ Failed to sync slash commands: `{e}`")


@bot.event
async def on_ready():
    logger.info(f"==================================================")
    logger.info(f"⚡ {BOT_NAME} ({BOT_VERSION}) IS ONLINE!")
    logger.info(f"🤖 Bot Tag: {bot.user} (ID: {bot.user.id})")
    logger.info(f"🌐 Web Remote Control Active at: http://localhost:{WEB_PORT}")
    logger.info(f"==================================================")

    # Global Sync
    try:
        synced = await bot.tree.sync()
        logger.info(f"✅ Synchronized {len(synced)} Slash Commands globally across all servers!")
    except Exception as e:
        logger.error(f"❌ Failed to sync slash commands: {e}")

    activity = discord.Streaming(
        name=STATUS_TEXT,
        url=YOUTUBE_STATUS_URL
    )
    await bot.change_presence(activity=activity, status=discord.Status.online)




@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You lack the required permissions to run this DJ command.")
    else:
        logger.error(f"Unhandled Command Error: {error}", exc_info=error)
        await ctx.send(f"❌ An audio engine error occurred: `{error}`")


async def main():
    # Initialize SQLite Database
    init_db()

    # Pass bot reference to Flask web controller & launch
    set_bot_reference(bot)
    try:
        run_web_server(WEB_PORT)
    except Exception as e:
        logger.warning(f"Could not start web controller server: {e}")

    # Load Cogs
    async with bot:
        for cog in COGS:
            try:
                await bot.load_extension(cog)
                logger.info(f"  └─ Loaded Cog: {cog}")
            except Exception as e:
                logger.error(f"❌ Failed loading cog {cog}: {e}")

        token = DISCORD_TOKEN
        if not token or token == "YOUR_DISCORD_BOT_TOKEN_HERE":
            logger.error("❌ CRITICAL: DISCORD_TOKEN not found in .env or environment!")
            logger.info("👉 Please edit your .env file and add your DISCORD_TOKEN!")
            return

        await bot.start(token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot shut down safely.")
    except Exception as fatal:
        logger.critical(f"💥 Fatal execution error: {fatal}")
