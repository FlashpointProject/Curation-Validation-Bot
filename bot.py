import os
import re
import traceback
from typing import Optional

import discord
from discord.ext import commands
from pretty_help import PrettyHelp

from dotenv import load_dotenv

from get_all_curations_in_zip import get_all_curations_in_zip
from logger import getLogger, set_global_logging_level
from curation_validator import get_launch_commands_bluebot, validate_curation, CurationType

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

bot = commands.Bot(command_prefix="-", help_command=PrettyHelp(color=discord.Color.red()))
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

    is_in_flash_game_channel = message.channel.id == FLASH_GAMES_CHANNEL
    is_in_other_game_channel = message.channel.id == OTHER_GAMES_CHANNEL
    is_in_animation_channel = message.channel.id == ANIMATIONS_CHANNEL
    is_audition = message.channel.id == AUDITIONS_CHANNEL
    # TODO disable
    # is_curator_lounge = message.channel.id == CURATOR_LOUNGE_CHANNEL

    if not (is_in_flash_game_channel or is_in_other_game_channel or is_in_animation_channel or is_audition):  # or is_curator_lounge):
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
        _, archives = get_all_curations_in_zip(archive_filename)
        for archive in archives:
            curation_errors, curation_warnings, is_extreme, curation_type, title = validate_curation(archive)
            if message.content == "":
                curation_errors.append("Discord upload must include title of game.")
            if not is_audition:
                mentioned_channel: discord.TextChannel
                if curation_type == CurationType.FLASH_GAME and not is_in_flash_game_channel:
                    mentioned_channel = bot.get_channel(FLASH_GAMES_CHANNEL)
                    curation_errors.append(f"Curation is a flash game, please submit to {mentioned_channel.mention}")
                if curation_type == CurationType.OTHER_GAME and not is_in_other_game_channel:
                    mentioned_channel = bot.get_channel(OTHER_GAMES_CHANNEL)
                    curation_errors.append(f"Curation is an other game, please submit to {mentioned_channel.mention}")
                if curation_type == CurationType.ANIMATION and not is_in_animation_channel:
                    mentioned_channel = bot.get_channel(ANIMATIONS_CHANNEL)
                    curation_errors.append(f"Curation is an animation, please submit to {mentioned_channel.mention}")

            # format reply
            final_reply: str = ""
            if title is not None:
                if len(curation_errors) > 0:
                    final_reply += message.author.mention + f" Your curation `{title}` is invalid:\n" \
                                                            f"🔗 {message.jump_url}\n"
                if len(curation_errors) == 0 and len(curation_warnings) > 0:
                    final_reply += message.author.mention + f" Your curation `{title}` might have some problems:\n" \
                                                            f"🔗 {message.jump_url}\n"
            else:
                if len(curation_errors) > 0:
                    final_reply += message.author.mention + f" Your curation is invalid:\n" \
                                                            f"🔗 {message.jump_url}\n"
                if len(curation_errors) == 0 and len(curation_warnings) > 0:
                    final_reply += message.author.mention + f" Your curation might have some problems:\n" \
                                                            f"🔗 {message.jump_url}\n"

            has_errors = len(curation_errors) > 0
            if has_errors:
                if not dry_run:
                    l.debug(f"adding 🚫 reaction to message '{message.id}'")
                    await message.add_reaction('🚫')
                for curation_error in curation_errors:
                    final_reply += f"🚫 {curation_error}\n"

            # TODO tag warnings changed to errors this way because i'm lazy for now
            has_warnings = len(curation_warnings) > 0
            if has_warnings:
                if not dry_run:
                    l.debug(f"adding 🚫 reaction to message '{message.id}'")
                    await message.add_reaction('🚫')
                for curation_warning in curation_warnings:
                    final_reply += f"🚫 {curation_warning}\n"

            is_audition_with_mistakes = is_audition and (has_warnings or has_errors)
            if is_audition_with_mistakes and "duplicate" not in final_reply:
                final_reply += "Please fix these errors and resubmit."
            elif is_audition_with_mistakes:
                final_reply += "Feel free to curate another game instead."

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
                elif is_in_flash_game_channel or is_in_other_game_channel or is_in_animation_channel:
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
        # archive cleanup
        l.debug(f"removing archive {archive_filename}...")
        os.remove(archive_filename)
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


@bot.command(name="mood", brief="Mood.", hidden=True)
@commands.has_role("Moderator")
async def mood(ctx: discord.ext.commands.Context):
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


bot.load_extension('troubleshooting')
bot.load_extension('curation')
bot.load_extension('info')
bot.load_extension('utilities')
l.info(f"starting the bot...")
bot.run(TOKEN)
