import os
import traceback
from typing import Optional

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


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MaxConcurrencyReached):
        await ctx.channel.send('Bot is busy! Try again later.')
        return


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


async def hell_counter(channel_id) -> list[discord.Message]:
    BLUE_ID = 144019275210817536
    message_counter = 0
    last_message: Optional[discord.Message] = None
    batch_size = 1000
    messages: list[discord.Message] = []

    channel = bot.get_channel(channel_id)
    while True:
        if last_message is None:
            l.debug(f"getting {batch_size} messages...")
            message_batch: list[discord.Message] = await channel.history(limit=batch_size).flatten()
        else:
            l.debug(f"getting {batch_size} messages from {last_message.jump_url} ...")
            message_batch: list[discord.Message] = await channel.history(limit=batch_size, before=last_message).flatten()
        if len(message_batch) == 0:
            l.warn(f"no messages found, weird.")
            return messages
        last_message = message_batch[-1]
        messages.extend(message_batch)

        l.debug("processing messages...")
        for msg in message_batch:
            message_counter += 1
            reactions = msg.reactions
            if len(reactions) > 0:
                l.debug(f"analyzing reactions for msg {msg.id} - message {message_counter}...")
            for reaction in reactions:
                if reaction.emoji != "🛠️":
                    continue
                l.debug(f"found hammer, getting reactions users for msg {msg.id} and reaction {reaction}...")
                users: list[discord.User] = await reaction.users().flatten()
                for user in users:
                    if user.id == BLUE_ID:
                        return messages[:message_counter]


@bot.command(name="hell", hidden=True)
@commands.has_role("Administrator")
@commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
async def hell(ctx: discord.ext.commands.Context, channel_alias: str):
    """Counts how many discord messages are remaining to be processed by Blue, measured by looking for Blue's hammer reaction."""
    if channel_alias == "flash":
        channel_id = FLASH_GAMES_CHANNEL
    elif channel_alias == "other":
        channel_id = OTHER_GAMES_CHANNEL
    elif channel_alias == "animation":
        channel_id = ANIMATIONS_CHANNEL
    else:
        await ctx.channel.send("invalid channel")
        return

    await ctx.channel.send(f"Measuring the length of Blue's curation journey through hell. "
                           f"Sit back and relax, this will take a while <:cool_crab:587188729362513930>.")

    messages = await hell_counter(channel_id)
    if len(messages) > 0:
        await ctx.channel.send(f"Blue's curation journey in `{channel_alias}` channel is `{len(messages)}` messages long.\n"
                               f"🔗 {messages[-1].jump_url}")
    else:
        await ctx.channel.send(f"Blue has earned his freedom... for now.")


l.info(f"starting the bot...")
bot.run(TOKEN)
