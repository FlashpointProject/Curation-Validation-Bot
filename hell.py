from typing import Optional

import discord
from discord.ext import commands

from bot import bot, l, FLASH_GAMES_CHANNEL, OTHER_GAMES_CHANNEL, ANIMATIONS_CHANNEL, COOL_CRAB


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