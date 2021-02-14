import os

import discord

from dotenv import load_dotenv
from logger import getLogger, set_global_logging_level
from curation_validator import validate_curation

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

client = discord.Client()


@client.event
async def on_ready():
    l.info(f"{client.user} connected")


@client.event
async def on_message(message: discord.Message):
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

    curation_errors, curation_warnings, is_extreme = validate_curation(archive_filename)

    # archive cleanup
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
        await message.add_reaction('⚠️')
        for curation_warning in curation_warnings:
            final_reply += f"⚠️ {curation_warning}\n"

    if len(final_reply) > 0:
        reply_channel: discord.TextChannel = client.get_channel(CURATOR_LOUNGE_CHANNEL)
        if is_extreme:
            reply_channel = client.get_channel(NSFW_LOUNGE_CHANNEL)
        elif is_flash_game or is_other_game or is_animation:
            reply_channel = client.get_channel(CURATOR_LOUNGE_CHANNEL)
        elif is_audition:
            reply_channel = client.get_channel(AUDITION_CHAT_CHANNEL)
        l.info(f"sending reply to message '{message.id}' : '" + final_reply.replace('\n', ' ') + "'")
        await reply_channel.send(final_reply)
    else:
        await message.add_reaction('🤖')


l.info(f"starting the bot...")
client.run(TOKEN)
