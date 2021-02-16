import os
import traceback

import discord
from discord.ext import commands

from dotenv import load_dotenv
from logger import getLogger, set_global_logging_level
from curation_validator import archive_cleanup, validate_curation

set_global_logging_level('DEBUG')
l = getLogger("main")

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
FLASH_GAMES_CHANNEL = int(os.getenv('FLASH_GAMES_CHANNEL'))
OTHER_GAMES_CHANNEL = int(os.getenv('OTHER_GAMES_CHANNEL'))
ANIMATIONS_CHANNEL = int(os.getenv('ANIMATIONS_CHANNEL'))
AUDITIONS_CHANNEL = int(os.getenv('AUDITIONS_CHANNEL'))
CURATOR_LOUNGE_CHANNEL = int(os.getenv('CURATOR_LOUNGE_CHANNEL'))
AUDITION_CHAT_CHANNEL = int(os.getenv('AUDITION_CHAT_CHANNEL'))
NSFW_LOUNGE_CHANNEL = int(os.getenv('NSFW_LOUNGE_CHANNEL'))
EXCEPTION_CHANNEL = int(os.getenv('EXCEPTION_CHANNEL'))
BOT_ALERTS_CHANNEL = int(os.getenv('BOT_ALERTS_CHANNEL'))
GOD_USER = int(os.getenv('GOD_USER'))

bot = commands.Bot(command_prefix="~")


@bot.event
async def on_ready():
    l.info(f"{bot.user} connected")


@bot.event
async def on_message(message: discord.Message):
    await bot.process_commands(message)
    await check_curations(message)


async def check_curations(message: discord.Message):
    if len(message.attachments) != 1:
        return

    is_flash_game = message.channel.id == FLASH_GAMES_CHANNEL
    is_other_game = message.channel.id == OTHER_GAMES_CHANNEL
    is_animation = message.channel.id == ANIMATIONS_CHANNEL
    is_audition = message.channel.id == AUDITIONS_CHANNEL

    # TODO disable
    # is_curator_lounge = message.channel.id == CURATOR_LOUNGE_CHANNEL

    if not (is_flash_game or is_other_game or is_animation or is_audition):  # or is_curator_lounge):
        return

    attachment = message.attachments[0]
    archive_filename: str = attachment.filename
    if not (archive_filename.endswith('.7z') or archive_filename.endswith('.zip')):
        return

    l.debug(
        f"detected message '{message.id}' from user '{message.author}' in channel '{message.channel}' with attachment '{archive_filename}'")
    l.debug(f"downloading attachment '{attachment.id}' - '{archive_filename}'...")
    await attachment.save(archive_filename)

    try:
        curation_errors, curation_warnings, is_extreme = validate_curation(archive_filename)
    except Exception as e:
        l.exception(e)
        l.debug(f"removing archive {archive_filename}...")
        os.remove(archive_filename)
        await message.add_reaction('💥')
        reply_channel: discord.TextChannel = bot.get_channel(EXCEPTION_CHANNEL)
        await reply_channel.send(f"<@{GOD_USER}> the curation validator has thrown an exception:\n```{traceback.format_exc()}```")
        return

    # archive cleanup
    l.debug(f"removing archive {archive_filename}...")
    os.remove(archive_filename)

    # format reply
    final_reply: str = ""
    if len(curation_errors) > 0 or len(curation_warnings) > 0:
        author: discord.Member = message.author
        final_reply += author.mention + f" Your curation has some problems:\n" \
                                        f"🤖 (This bot is currently in the testing phase, so it may not work correctly.)\n" \
                                        f"🔗 {message.jump_url}\n"
    if len(curation_errors) > 0:
        await message.add_reaction('🚫')
        for curation_error in curation_errors:
            final_reply += f"🚫 {curation_error}\n"

    if len(curation_warnings) > 0:
        await message.add_reaction('ℹ️')
        for curation_warning in curation_warnings:
            final_reply += f"ℹ️ {curation_warning}\n"

    if len(final_reply) > 0:
        reply_channel: discord.TextChannel = bot.get_channel(BOT_ALERTS_CHANNEL)
        if is_extreme:
            reply_channel = bot.get_channel(NSFW_LOUNGE_CHANNEL)
        elif is_flash_game or is_other_game or is_animation:
            reply_channel = bot.get_channel(BOT_ALERTS_CHANNEL)
        elif is_audition:
            reply_channel = bot.get_channel(AUDITION_CHAT_CHANNEL)
        l.info(f"sending reply to message '{message.id}' : '" + final_reply.replace('\n', ' ') + "'")
        await reply_channel.send(final_reply)
    else:
        await message.add_reaction('🤖')


@bot.command(hidden=True)
@commands.has_role("Administrator")
async def ping(ctx: discord.ext.commands.Context):
    l.debug(f"received ping from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
    await ctx.channel.send("pong")


l.info(f"starting the bot...")
bot.run(TOKEN)
