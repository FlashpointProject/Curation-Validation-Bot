from typing import Optional

import discord
from discord.ext import commands

from bot import bot, l, FLASH_GAMES_CHANNEL, OTHER_GAMES_CHANNEL, ANIMATIONS_CHANNEL, COOL_CRAB, \
    check_curation_in_message


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