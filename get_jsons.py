import os
import re
import shutil
import tempfile
from typing import Optional

import discord
from discord.ext import commands

from bot import bot, PENDING_FIXES_CHANNEL, l, COOL_CRAB


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