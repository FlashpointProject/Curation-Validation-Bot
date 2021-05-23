import os
import re
import shutil
import tempfile
from typing import Optional

import discord
from discord.ext import commands

from bot import COOL_CRAB, PENDING_FIXES_CHANNEL, bot, FLASH_GAMES_CHANNEL, OTHER_GAMES_CHANNEL, ANIMATIONS_CHANNEL, \
    is_bot_guy
from curation_validator import get_launch_commands_bluebot
from logger import getLogger

l = getLogger("main")


class Utilities(commands.Cog, description="Utilities, primarily for moderators."):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="check-lc", brief="Check if a given launch command is already in the master database.",
                      description="Check if a given launch command is already in the master database.")
    async def check_lc(self, ctx: discord.ext.commands.Context, *launch_command):
        l.debug(f"check_lc command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")

        def normalize_launch_command(launch_command: str) -> str:
            return launch_command.replace('"', "").replace("'", "").replace(" ", "").replace("`", "")

        launch_command_user = ""
        for arg in launch_command:
            launch_command_user += arg

        launch_command_user = normalize_launch_command(launch_command_user)
        normalized_commands = {normalize_launch_command(command) for command in get_launch_commands_bluebot()}

        if launch_command_user in normalized_commands:
            await ctx.channel.send("Launch command **found** in the master database, most likely a duplicate.")
        else:
            await ctx.channel.send("Launch command **not found** in the master database, most likely not a duplicate.")

    @commands.command(hidden=True)
    @commands.has_role("Administrator")
    async def ping(self, ctx: discord.ext.commands.Context):
        l.debug(f"received ping from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.channel.send("pong")

    @commands.command(name="approve", brief="Override the bot's decision and approve the curation (Moderator).",
                      description="Override the bot's decision and approve the curation (Moderator only).")
    @commands.check_any(commands.has_role("Moderator"), is_bot_guy())
    async def approve(self, ctx: discord.ext.commands.Context, jump_url: str):
        l.debug(f"approve command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")

        jump_url_regex = re.compile(r"https://discord\.com/channels/(\d+)/(\d+)/(\d+)")
        url_match = jump_url_regex.match(jump_url)
        if url_match is None or ctx.guild != self.bot.get_guild(int(url_match.group(1))):
            ctx.channel.send("Invalid jump URL provided\n")
            return

        # guild_id = int(url_match.group(1))
        channel_id = int(url_match.group(2))
        message_id = int(url_match.group(3))

        l.debug(f"fetching message {message_id}")
        channel = self.bot.get_channel(channel_id)
        message = await channel.fetch_message(message_id)
        reactions: list[discord.Reaction] = message.reactions
        for reaction in reactions:
            if reaction.me:
                l.debug(f"removing bot's reaction {reaction} from message {message.id}")
                await message.remove_reaction(reaction.emoji, self.bot.user)
        await message.add_reaction("🤖")

    @commands.command(name="get-fixes", hidden=True)
    @commands.has_role("Administrator")
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def automatic_get_jsons(self, ctx: discord.ext.commands.Context, last_message_url: Optional[str]):
        l.debug(
            f"pending fixes command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        temp_folder = tempfile.mkdtemp(prefix='pending_fixes')
        if last_message_url is not None:
            await ctx.send(
                f"Getting all jsons in #pending-fixes not marked with a ⚠️ before <{last_message_url}> and after the pin. "
                f"Sit back and relax, this will take a while {COOL_CRAB}.")
            jump_url_regex = re.compile(r"https://discord\.com/channels/(\d+)/(\d+)/(\d+)")
            url_match = jump_url_regex.match(last_message_url)
            if url_match is None or ctx.guild != self.bot.get_guild(int(url_match.group(1))):
                ctx.channel.send("Invalid jump URL provided\n")
                return

            # guild_id = int(url_match.group(1))
            channel_id = int(url_match.group(2))
            message_id = int(url_match.group(3))

            l.debug(f"fetching message {message_id}")
            channel = self.bot.get_channel(channel_id)
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

    @commands.command(name="hell", hidden=True)
    @commands.has_role("Administrator")
    @commands.max_concurrency(1, per=commands.BucketType.default, wait=False)
    async def hell(self, ctx: discord.ext.commands.Context, channel_alias: str):
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
            await ctx.channel.send(
                f"Blue's curation journey in `{channel_alias}` channel is `{len(messages)}` messages long.\n"
                f"🔗 {messages[-1].jump_url}")
        else:
            await ctx.channel.send(f"Blue has earned his freedom... for now.")

    @commands.command(name="mood", brief="Mood.", hidden=True)
    @commands.has_role("Moderator")
    async def mood(self, ctx: discord.ext.commands.Context):
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


async def get_raw_json_messages_in_pending_fixes(oldest_message: Optional[discord.Message]) -> list[
    discord.Message]:
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
            message_batch: list[discord.Message] = await channel.history(limit=batch_size,
                                                                         before=oldest_message).flatten()
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


def setup(bot: commands.Bot):
    bot.add_cog(Utilities(bot))
