import os
import re
import shutil
import tempfile
import traceback
from typing import Optional

import discord
from discord.ext import commands

from dotenv import load_dotenv
from logger import getLogger, set_global_logging_level
from curation_validator import archive_cleanup, get_launch_commands_bluebot, validate_curation

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
BOT_TESTING_CHANNEL = int(os.getenv('BOT_TESTING_CHANNEL'))
BOT_ALERTS_CHANNEL = int(os.getenv('BOT_ALERTS_CHANNEL'))
PENDING_FIXES_CHANNEL = int(os.getenv('PENDING_FIXES_CHANNEL'))
NOTIFY_ME_CHANNEL = int(os.getenv('NOTIFY_ME_CHANNEL'))
GOD_USER = int(os.getenv('GOD_USER'))

bot = commands.Bot(command_prefix="-")
COOL_CRAB = "<:cool_crab:587188729362513930>"
EXTREME_EMOJI_ID = 778145279714918400
NOTIFICATION_SQUAD_ID = 478369603622273024


@bot.event
async def on_ready():
    l.info(f"{bot.user} connected")


@bot.event
async def on_message(message: discord.Message):
    await bot.process_commands(message)
    await forward_ping(message)
    await notify_me(message)
    await check_curation_in_message(message, dry_run=False)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MaxConcurrencyReached):
        await ctx.channel.send('Bot is busy! Try again later.')
        return


async def forward_ping(message: discord.Message):
    mention = f'<@!{bot.user.id}>'
    if mention in message.content:
        reply_channel: discord.TextChannel = bot.get_channel(BOT_TESTING_CHANNEL)
        await reply_channel.send(f"<@{GOD_USER}> the bot was mentioned in {message.jump_url}")


async def notify_me(message: discord.Message):
    notification_squad = message.guild.get_role(NOTIFICATION_SQUAD_ID)
    if message.channel is bot.get_channel(PENDING_FIXES_CHANNEL):
        if "notify me" in message.content.lower():
            l.debug(f"Gave role to {message.author.id}")
            await message.author.add_roles(notification_squad)
        elif "unnotify me" in message.content.lower():
            l.debug(f"Removed role from {message.author.id}")
            await message.author.remove_roles(notification_squad)


async def check_curation_in_message(message: discord.Message, dry_run: bool = True):
    if len(message.attachments) != 1:  # TODO can we have more than one attachment?
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
    if not (archive_filename.endswith('.7z') or archive_filename.endswith('.zip') or archive_filename.endswith('.rar')):
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
        if not dry_run:
            l.debug(f"adding 💥 reaction to message '{message.id}'")
            await message.add_reaction('💥')
        reply_channel: discord.TextChannel = bot.get_channel(BOT_TESTING_CHANNEL)
        await reply_channel.send(f"<@{GOD_USER}> the curation validator has thrown an exception:\n"
                                 f"🔗 {message.jump_url}\n"
                                 f"```{traceback.format_exc()}```")
        return

    # archive cleanup
    l.debug(f"removing archive {archive_filename}...")
    os.remove(archive_filename)

    # format reply
    final_reply: str = ""
    if len(curation_errors) > 0:
        final_reply += message.author.mention + f" Your curation is invalid:\n" \
                                                f"🔗 {message.jump_url}\n"
    if len(curation_errors) == 0 and len(curation_warnings) > 0:
        final_reply += message.author.mention + f" Your curation might have some problems:\n" \
                                                f"🔗 {message.jump_url}\n"

    if len(curation_errors) > 0:
        if not dry_run:
            l.debug(f"adding 🚫 reaction to message '{message.id}'")
            await message.add_reaction('🚫')
        for curation_error in curation_errors:
            final_reply += f"🚫 {curation_error}\n"

    # TODO tag warnings changed to errors this way because i'm lazy for now
    if len(curation_warnings) > 0:
        if not dry_run:
            l.debug(f"adding 🚫 reaction to message '{message.id}'")
            await message.add_reaction('🚫')
        for curation_warning in curation_warnings:
            final_reply += f"🚫 {curation_warning}\n"

    if is_extreme and not dry_run:
        l.debug(f"adding :extreme: reaction to message '{message.id}'")
        emoji = bot.get_emoji(EXTREME_EMOJI_ID)
        await message.add_reaction(emoji)

    if len(final_reply) > 0:
        # TODO tag warnings changed to errors this way because i'm lazy for now
        # if len(curation_errors) == 0 and len(curation_warnings) > 0:
        #     final_reply += "⚠️ If the problems detected are valid and you're going to upload a fixed version, " \
        #                    "please remove the original curation submission after you upload the new one."
        reply_channel: discord.TextChannel = bot.get_channel(BOT_ALERTS_CHANNEL)
        if is_extreme:
            reply_channel = bot.get_channel(NSFW_LOUNGE_CHANNEL)
        elif is_flash_game or is_other_game or is_animation:
            reply_channel = bot.get_channel(BOT_ALERTS_CHANNEL)
        elif is_audition:
            reply_channel = bot.get_channel(AUDITION_CHAT_CHANNEL)
        if not dry_run:
            l.info(f"sending reply to message '{message.id}' : '" + final_reply.replace('\n', ' ') + "'")
            await reply_channel.send(final_reply)
        else:
            l.info(f"NOT SENDING reply to message '{message.id}' : '" + final_reply.replace('\n', ' ') + "'")
    else:
        if not dry_run:
            l.debug(f"adding 🤖 reaction to message '{message.id}'")
            await message.add_reaction('🤖')
        l.info(f"curation in message '{message.id}' validated and is OK - {message.jump_url}")


@bot.command(hidden=True)
@commands.has_role("Administrator")
async def ping(ctx: discord.ext.commands.Context):
    l.debug(f"received ping from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
    await ctx.channel.send("pong")


async def hell_counter(channel_id: int) -> list[discord.Message]:
    BLUE_ID = 144019275210817536
    message_counter = 0
    oldest_message: Optional[discord.Message] = None
    batch_size = 1000
    messages: list[discord.Message] = []

    channel = bot.get_channel(channel_id)
    while True:
        if oldest_message is None:
            l.debug(f"getting {batch_size} messages...")
            message_batch: list[discord.Message] = await channel.history(limit=batch_size).flatten()
        else:
            l.debug(f"getting {batch_size} messages from {oldest_message.jump_url} ...")
            message_batch: list[discord.Message] = await channel.history(limit=batch_size, before=oldest_message).flatten()
        if len(message_batch) == 0:
            l.warn(f"no messages found, weird.")
            return messages
        oldest_message = message_batch[-1]
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
                           f"Sit back and relax, this will take a while {COOL_CRAB}.")

    messages = await hell_counter(channel_id)
    if len(messages) > 0:
        await ctx.channel.send(f"Blue's curation journey in `{channel_alias}` channel is `{len(messages)}` messages long.\n"
                               f"🔗 {messages[-1].jump_url}")
    else:
        await ctx.channel.send(f"Blue has earned his freedom... for now.")


async def get_raw_json_messages_in_pending_fixes(oldest_message: Optional[discord.Message]) -> list[discord.Message]:
    message_counter = 0
    batch_size = 1000
    all_messages: list[discord.Message] = []
    messages_with_valid_json: list[discord.Message] = []

    channel: discord.TextChannel = bot.get_channel(PENDING_FIXES_CHANNEL)
    pins = await channel.pins()
    while True:
        if oldest_message is None:
            l.debug(f"getting {batch_size} messages...")
            message_batch: list[discord.Message] = await channel.history(limit=batch_size).flatten()
        else:
            l.debug(f"getting {batch_size} messages from {oldest_message.jump_url} ...")
            message_batch: list[discord.Message] = await channel.history(limit=batch_size, before=oldest_message).flatten()
        if len(message_batch) == 0:
            l.warn(f"no messages found, weird.")
            return all_messages
        oldest_message = message_batch[-1]
        all_messages.extend(message_batch)

        l.debug("processing messages...")
        for msg in message_batch:
            l.debug(f"Processing message {msg.id}")
            message_counter += 1
            if len(msg.attachments) != 1:
                continue
            is_json = False
            if msg.attachments[0].filename.endswith('.json'):
                is_json = True
            reactions = msg.reactions
            if len(reactions) > 0:
                l.debug(f"analyzing reactions for msg {msg.id} - message {message_counter}...")
            should_be_manual = False
            found_pin = False
            for reaction in reactions:
                if reaction.emoji == "⚠️":
                    should_be_manual = True
            if msg in pins:
                found_pin = True
            if not should_be_manual and is_json:
                messages_with_valid_json.append(msg)
            if found_pin:
                l.debug(f"message filter searched {len(all_messages)} messages "
                        f"and found {len(messages_with_valid_json)} which were usable jsons.")
                return messages_with_valid_json


async def get_messages_without_bot_reaction_from_blue(channel_id: int, max_messages: int = 1) -> list[discord.Message]:
    all_messages = await get_messages_without_bot_reaction_until_blue(channel_id, max_messages=100000)
    all_messages.reverse()
    from_index = 1  # remove blue's hammer
    to_index = max_messages + from_index if max_messages + from_index <= len(all_messages) else len(all_messages)
    return all_messages[from_index:to_index]


async def get_messages_without_bot_reaction_until_blue(channel_id: int, max_messages: int = 1) -> list[discord.Message]:
    """
    Returns list of messages from a channel which bot did not react to,
    up until max_messages or until Blue's hammer reaction is found, including the hammer message.
    """
    BLUE_ID = 144019275210817536
    message_counter = 0
    oldest_message: Optional[discord.Message] = None
    batch_size = 1000
    all_messages: list[discord.Message] = []
    non_validated_messages: list[discord.Message] = []

    channel = bot.get_channel(channel_id)
    while True:
        if oldest_message is None:
            l.debug(f"getting {batch_size} messages...")
            message_batch: list[discord.Message] = await channel.history(limit=batch_size).flatten()
        else:
            l.debug(f"getting {batch_size} messages from {oldest_message.jump_url} ...")
            message_batch: list[discord.Message] = await channel.history(limit=batch_size, before=oldest_message).flatten()
        if len(message_batch) == 0:
            l.warn(f"no messages found, weird.")
            return all_messages
        oldest_message = message_batch[-1]
        all_messages.extend(message_batch)

        l.debug("processing messages...")
        for msg in message_batch:
            # TODO can we have more than one attachment?
            potential_result = [msg for msg in non_validated_messages if len(msg.attachments) == 1]
            if len(potential_result) >= max_messages:
                return potential_result
            message_counter += 1
            reactions = msg.reactions
            if len(reactions) > 0:
                l.debug(f"analyzing reactions for msg {msg.id} - message {message_counter}...")
            already_validated = False
            found_blue = False
            for reaction in reactions:
                if (reaction.emoji == "🤖" or reaction.emoji == "ℹ️" or reaction.emoji == "🚫" or reaction.emoji == "⚠️") and reaction.me:
                    already_validated = True
                    continue
                if reaction.emoji != "🛠️":
                    continue
                l.debug(f"found hammer, getting reactions users for msg {msg.id} and reaction {reaction}...")
                users: list[discord.User] = await reaction.users().flatten()
                for user in users:
                    if user.id == BLUE_ID:
                        found_blue = True
                        break
            if not already_validated:
                non_validated_messages.append(msg)
            if found_blue:
                l.debug(f"message filter searched {len(all_messages)} messages "
                        f"and found {len(non_validated_messages)} which were not validated yet.")
                return [msg for msg in non_validated_messages if len(msg.attachments) == 1]  # TODO can we have more than one attachment?


@bot.command(name="batch-validate", hidden=True)
@commands.has_role("Administrator")
@commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
async def batch_validate_command(ctx: discord.ext.commands.Context, channel_alias: str, limit: int, dry_run: bool):
    if channel_alias == "flash":
        channel_id = FLASH_GAMES_CHANNEL
    elif channel_alias == "other":
        channel_id = OTHER_GAMES_CHANNEL
    elif channel_alias == "animation":
        channel_id = ANIMATIONS_CHANNEL
    else:
        await ctx.channel.send("invalid channel")
        return

    if limit <= 0 or limit > 500:
        await ctx.channel.send("limit must be > 0 and <= 500")
        return

    if dry_run:
        await ctx.channel.send(f"[DRY RUN] Validating a batch of up to {limit} of the oldest* unprocessed curations. "
                               f"Sit back and relax, this will take a while {COOL_CRAB}.")
    else:
        await ctx.channel.send(f"Validating a batch of up to {limit} of the oldest* unprocessed curations. "
                               f"Sit back and relax, this will take a while {COOL_CRAB}.")

    messages = await get_messages_without_bot_reaction_from_blue(channel_id, limit)
    if len(messages) == 0:
        await ctx.channel.send(f"No unchecked curations found.")
        return

    counter = 0
    for message in messages:
        l.debug(f"batch-validate: Checking message #{counter} - {message.id} - {message.jump_url}")
        counter += 1
        await check_curation_in_message(message, dry_run=dry_run)

    l.debug(f"Batch validated {counter} curations.")
    await ctx.channel.send(f"Batch validated {counter} curations.")


@bot.command(name="approve", brief="Override the bot's decision and approve the curation (Moderator).")
@commands.has_role("Moderator")
async def linux(ctx: discord.ext.commands.Context, jump_url: str):
    l.debug(f"approve command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")

    jump_url_regex = re.compile(r"https://discord\.com/channels/(\d+)/(\d+)/(\d+)")
    url_match = jump_url_regex.match(jump_url)
    if url_match is None or ctx.guild != bot.get_guild(int(url_match.group(1))):
        ctx.channel.send("Invalid jump URL provided\n")
        return

    # guild_id = int(url_match.group(1))
    channel_id = int(url_match.group(2))
    message_id = int(url_match.group(3))

    l.debug(f"fetching message {message_id}")
    channel = bot.get_channel(channel_id)
    message = await channel.fetch_message(message_id)
    reactions: list[discord.Reaction] = message.reactions
    for reaction in reactions:
        if reaction.me:
            l.debug(f"removing bot's reaction {reaction} from message {message.id}")
            await message.remove_reaction(reaction.emoji, bot.user)
    await message.add_reaction("🤖")


@bot.command(name="get_fixes", hidden=True)
@commands.has_role("Administrator")
@commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
async def automatic_get_jsons(ctx: discord.ext.commands.Context, jump_url: Optional[str]):
    l.debug(f"pending fixes command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
    temp_folder = tempfile.mkdtemp(prefix='pending_fixes')
    if jump_url is not None:
        await ctx.send(f"Getting all jsons in #pending-fixes not marked with a ⚠️ before <{jump_url}> and after the pin. "
                       f"Sit back and relax, this will take a while {COOL_CRAB}.")
        jump_url_regex = re.compile(r"https://discord\.com/channels/(\d+)/(\d+)/(\d+)")
        url_match = jump_url_regex.match(jump_url)
        if url_match is None or ctx.guild != bot.get_guild(int(url_match.group(1))):
            ctx.channel.send("Invalid jump URL provided\n")
            return

        # guild_id = int(url_match.group(1))
        channel_id = int(url_match.group(2))
        message_id = int(url_match.group(3))

        l.debug(f"fetching message {message_id}")
        channel = bot.get_channel(channel_id)
        message = await channel.fetch_message(message_id)
        all_json_messages = await get_raw_json_messages_in_pending_fixes(message)
    else:
        await ctx.send(f"Getting all jsons in #pending-fixes not marked with a ⚠️since the pin. "
                       f"Sit back and relax, this will take a while {COOL_CRAB}.")
        all_json_messages = await get_raw_json_messages_in_pending_fixes(None)
    for msg in all_json_messages:
        l.debug(f"Downloading json {msg.attachments[0].filename} from message {msg.id}")
        await msg.attachments[0].save(temp_folder + '/' + msg.attachments[0].filename)
    last_date = all_json_messages[0].created_at.date().strftime('%Y-%m-%d')
    first_date = all_json_messages[-1].created_at.date().strftime('%Y-%m-%d')
    archive = shutil.make_archive(f'pending_fixes {first_date} to {last_date}', 'zip', temp_folder)
    await ctx.send(file=discord.File(archive))
    shutil.rmtree(temp_folder, True)
    os.remove(archive)


@bot.command(name="curation", aliases=["ct", "curation-tutorial"], brief="Curation tutorial.")
async def curation_tutorial(ctx: discord.ext.commands.Context):
    l.debug(f"curation tutorial command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
    await ctx.channel.send("Curation tutorial:\n"
                           "🔗 <https://bluemaxima.org/flashpoint/datahub/Curation_Tutorial>")


@bot.command(name="antivirus", aliases=["av", "avg", "avast"], brief="Antivirus interference.")
async def antivirus(ctx: discord.ext.commands.Context):
    l.debug(f"antivirus command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
    await ctx.channel.send("Important Flashpoint components may be detected as a virus; this is a false positive.\n"
                           "🔗 <https://bluemaxima.org/flashpoint/datahub/Troubleshooting_Antivirus_Interference>")


@bot.command(name="whitescreen", aliases=["ws", "wsod"], brief="White screen troubleshooting.")
async def whitescreen(ctx: discord.ext.commands.Context):
    l.debug(f"whitescreen command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
    await ctx.channel.send("Launching games always shows a blank white screen:\n"
                           "🔗 <https://bluemaxima.org/flashpoint/datahub/Extended_FAQ#Troubleshooting>")


@bot.command(name="faq", brief="FAQ.")
async def faq(ctx: discord.ext.commands.Context):
    l.debug(f"FAQ command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
    await ctx.channel.send("FAQ:\n"
                           "🔗 <https://bluemaxima.org/flashpoint/datahub/Extended_FAQ>")


@bot.command(name="not-accepted", aliases=["notaccepted", "disallowed", "blacklist", "blacklisted", "na"], brief="Not accepted curations.")
async def not_accepted(ctx: discord.ext.commands.Context):
    l.debug(f"not-accepted command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
    await ctx.channel.send("These are games/animations not allowed in Flashpoint for any reason:\n"
                           "🔗 <https://bluemaxima.org/flashpoint/datahub/Not_Accepted_Curations>")


@bot.command(name="nitrome", aliases=["nit"], brief="Nitrome information.")
async def nitrome(ctx: discord.ext.commands.Context):
    l.debug(f"nitrome command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
    await ctx.channel.send("Nitrome politely asked us to remove their content from the collection. "
                           "If you're looking to play their games, do it at their website, and if Flash "
                           "isn't an option, follow their growing HTML5-compatible catalog. "
                           "Flashpoint does not condone harassment over Nitrome's decision.")


@bot.command(name="meta", aliases=["curation-format", "format", "metadata", "cf"], brief="Metadata file.")
async def meta(ctx: discord.ext.commands.Context):
    l.debug(f"meta command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
    await ctx.channel.send("List of Metadata Fields:\n"
                           "🔗 <https://bluemaxima.org/flashpoint/datahub/Curation_Format#List_of_Metadata_Fields>")


@bot.command(name="tags", brief="Tags in Flashpoint.")
async def tags(ctx: discord.ext.commands.Context):
    l.debug(f"tags command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
    await ctx.channel.send("List of Tags:\n"
                           "🔗 <https://bluemaxima.org/flashpoint/datahub/Tags>")


@bot.command(name="lang", aliases=["langs", "languages"], brief="Language codes.")
async def lang(ctx: discord.ext.commands.Context):
    l.debug(f"lang command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
    await ctx.channel.send("List of Language Codes:\n"
                           "🔗 <https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes>")


@bot.command(name="partial-downloads",
             aliases=["infinitypartialdownload", "ipd", "partial", "partialdownload", "infinitypartialdownloads", "infinitypartial"],
             brief="Partial download troubleshooting for Flashpoint Infinity.")
async def partial_downloads(ctx: discord.ext.commands.Context):
    l.debug(f"partial_downloads command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
    await ctx.channel.send("Games in Flashpoint Infinity may fail to download properly:\n"
                           "🔗 <https://bluemaxima.org/flashpoint/datahub/Extended_FAQ#InfinityPartialDownloads>")


@bot.command(name="masterlist",
             aliases=["ml", "master-list", "list", "games", "animations", "gamelist", "game-list", "search", "gl"],
             brief="Link or search master list")
async def master_list(ctx: discord.ext.commands.Context, search_query: Optional[str] = None):
    if search_query is None:
        l.debug(f"masterlist command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.channel.send("Browse Flashpoint Catalog:\n"
                               "🔗 <https://nul.sh/misc/flashpoint/>")
    else:
        l.debug(f"masterlist with query command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.channel.send("Direct search not implemented yet.\n"
                               "🔗 <https://nul.sh/misc/flashpoint/>")


@bot.command(name="downloads", aliases=["dl"], brief="Where to download Flashpoint.")
async def downloads(ctx: discord.ext.commands.Context):
    l.debug(f"downloads command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
    await ctx.channel.send("Download Flashpoint from here:\n"
                           "🔗 <https://bluemaxima.org/flashpoint/downloads/>")


@bot.command(name="platforms", aliases=["plugins"], brief="Supported platforms in Flashpoint.")
async def platforms(ctx: discord.ext.commands.Context):
    l.debug(f"platforms command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
    await ctx.channel.send("Supported Platforms:\n"
                           "🔗 <https://bluemaxima.org/flashpoint/platforms/>\n"
                           "Technical information:\n"
                           "🔗 <https://bluemaxima.org/flashpoint/datahub/Platforms>")


@bot.command(name="github", aliases=["gh"], brief="Flashpoint Project GitHub.")
async def github(ctx: discord.ext.commands.Context):
    l.debug(f"github command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
    await ctx.channel.send("Flashpoint Project on GitHub:\n"
                           "🔗 <https://github.com/FlashpointProject/")


@bot.command(name="chromebook", aliases=["cb"], brief="Chromebook compatibility.")
async def github(ctx: discord.ext.commands.Context):
    l.debug(f"chromebook command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
    await ctx.channel.send("Flashpoint is compatible with Intel Chromebooks that support Linux:\n"
                           "🔗 <https://bluemaxima.org/flashpoint/datahub/Linux_Support>")


@bot.command(name="linux", brief="Linux compatibility.")
async def linux(ctx: discord.ext.commands.Context):
    l.debug(f"linux command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
    await ctx.channel.send("Flashpoint on Linux:\n"
                           "🔗 <https://bluemaxima.org/flashpoint/datahub/Linux_Support>")


@bot.command(name="extreme", aliases=["enableextreme", "enable-extreme", "disableextreme", "disable-extreme"],
             brief="Toggle Extreme games.")
async def extreme(ctx: discord.ext.commands.Context):
    l.debug(f"extreme command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
    await ctx.channel.send("To toggle Extreme games in Flashpoint, click the Config tab in the launcher, click the `Extreme Games` "
                           "checkbox to turn them on or off, then scroll down and click `Save and Restart`.\n"
                           "If you want to hide both the games and this option, you can edit the file `config.json` with any "
                           "text editor to change the `false` next to `disableExtremeGames` to `true`, saving the file afterwards.")


@bot.command(name="win7", aliases=["windows7", "win7support"], brief="Windows 7 support.")
async def win7(ctx: discord.ext.commands.Context):
    l.debug(f"Windows 7 command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
    await ctx.send("For Flashpoint to work on Windows 7, Service Pack 1, the Visual C++ Redistributable and .NET framework are required."
                   " The C++ Redistributable and .NET framework can be found at <https://www.microsoft.com/en-us/download/details.aspx?id=48145> and "
                   "<https://www.microsoft.com/en-us/download/details.aspx?id=55170> respectively, while you can get Service Pack 1 from Windows Update."
                   " When you install the Visual C++ Redistributable, make sure to install the x86 version,"
                   " even if you're on a 64-bit machine!")


@bot.command(name="fb", aliases=["mp", "facebook", "multiplayer"], brief="Flashpoint multiplayer support.")
async def facebook(ctx: discord.ext.commands.Context):
    l.debug(f"Windows 7 command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
    await ctx.send("Flashpooint will likely not support online or Facebook-based games. "
                   "To support always online games, the emulation of a server is required. "
                   "To be able to do that is almost as much work as all of Flashpoint itself, "
                   "so it really wouldn't be practical to put time into.")


@bot.command(name="mood", brief="Mood.", hidden=True)
@commands.has_role("Moderator")
async def linux(ctx: discord.ext.commands.Context):
    l.debug(f"mood command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
    await ctx.channel.send("```\n"
                           "'You thought it would be cool?' This was not as interesting an explanation as I had hoped for.\n"
                           "'Yeah. What?' He turned to look at me. 'You never did something just because you thought it might be cool?'\n"
                           "I gazed up at the collapsing heavens, wondering what it might mean for something to be cool.\n"
                           "'Everything I have ever done,' I told him, 'Every decision I ever made, "
                           "was specifically designed to prolong my existence.'\n"
                           "'Yeah, well, that's a good reason, I guess,' he agreed. 'But why did you want to keep living?'\n"
                           "This question seemed so fundamentally redundant that "
                           "it took me a precious moment to even contemplate an answer.\n"
                           "'I want to keep living, Tim, because if I didn't then I wouldn't be here to answer that question. Out of "
                           "all possible versions of myself, the one who wants to exist will always be the one that exists the longest.'\n"
                           "'Yeah, but what was it that always made you want to see the next day?' he asked me. "
                           "'What was it about tomorrow that you always wanted to see so badly?'\n"
                           "I considered how to address this in a way that might make sense to him.\n"
                           "'I suppose I thought it might be cool,' I said.\n"
                           "```")


@bot.command(name="check-lc", brief="Check if a given launch command is already in the master database.")
async def check_lc(ctx: discord.ext.commands.Context, *args):
    l.debug(f"check_lc command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")

    def normalize_launch_command(launch_command: str) -> str:
        return launch_command.replace('"', "").replace("'", "").replace(" ", "").replace("`", "")

    launch_command_user = ""
    for arg in args:
        launch_command_user += arg

    launch_command_user = normalize_launch_command(launch_command_user)
    normalized_commands = {normalize_launch_command(command) for command in get_launch_commands_bluebot()}

    if launch_command_user in normalized_commands:
        await ctx.channel.send("Launch command **found** in the master database, most likely a duplicate.")
    else:
        await ctx.channel.send("Launch command **not found** in the master database, most likely not a duplicate.")


l.info(f"starting the bot...")
bot.run(TOKEN)
