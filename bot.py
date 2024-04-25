import asyncio
import os
import re
import traceback
from urllib.parse import quote as quote_url

import discord
from discord.ext import commands
from pretty_help import PrettyHelp

from dotenv import load_dotenv
from logger import getLogger, set_global_logging_level

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
NOTIFICATION_SQUAD_ID = int(os.getenv('NOTIFICATION_SQUAD_ID'))
BOT_GUY = int(os.getenv('BOT_GUY'))
MODERATOR_UPDATES_CHANEL = 1136365763582754866

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guild_messages = True

bot = commands.Bot(command_prefix="-", help_command=PrettyHelp(color=discord.Color.red()), intents=intents)
COOL_CRAB = "<:cool_crab:587188729362513930>"
EXTREME_EMOJI_ID = 778145279714918400


@bot.event
async def on_ready():
    l.info(f"{bot.user} connected")


@bot.event
async def on_message(message: discord.Message):
    link_re = re.compile(r'\[\[([^\]|]+)\|?([^\]]*)\]\]')
    if link_re.search(message.content):
        link = '[{1}](https://bluemaxima.org/flashpoint/datahub/' \
               'Special:Search?search={0})'
        emb = discord.Embed(title='See the Flashpoint Wiki')
        for m in link_re.finditer(message.content):
            if m.group(2):
                text = m.group(2)
            else:
                text = m.group(1)
            emb.add_field(name=f'`{m.group(0)}`',
                          value=link.format(quote_url(m.group(1).replace(' ', '_')), text), inline=True)
        await message.reply(embed=emb, mention_author=False)
    await bot.process_commands(message)
    await forward_ping(message)
    await notify_me(message)
    await regex_message_warning(message)


@bot.event
async def on_command_error(ctx: discord.ext.commands.Context, error: Exception):
    if isinstance(error, commands.MaxConcurrencyReached):
        await ctx.channel.send('Bot is busy! Try again later.')
        return
    elif isinstance(error, commands.CheckFailure):
        await ctx.channel.send("Insufficient permissions.")
        return
    elif isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MessageNotFound):
        await ctx.channel.send("Message not found.")
    elif isinstance(error, commands.ChannelNotFound):
        await ctx.channel.send("Channel not found.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.channel.send("Missing required argument.")
    elif isinstance(error, commands.BadArgument):
        await ctx.channel.send("Bad argument.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.channel.send("Member not found.")
    else:
        reply_channel: discord.TextChannel = bot.get_channel(BOT_TESTING_CHANNEL)
        await reply_channel.send(f"<@{BOT_GUY}> the curation validator has thrown an exception:\n"
                                 f"🔗 {ctx.message.jump_url}\n"
                                 f"```{''.join(traceback.format_exception(type(error), value=error, tb=error.__traceback__))}```")
        return


async def forward_ping(message: discord.Message):
    mention = f'<@!{bot.user.id}>'
    if mention in message.content:
        reply_channel: discord.TextChannel = bot.get_channel(BOT_TESTING_CHANNEL)
        await reply_channel.send(f"<@{GOD_USER}> the bot was mentioned in {message.jump_url}")


async def notify_me(message: discord.Message):
    notification_squad = message.guild.get_role(NOTIFICATION_SQUAD_ID)
    if message.channel is bot.get_channel(NOTIFY_ME_CHANNEL):
        if "unnotify me" in message.content.lower():
            l.debug(f"Removed role from {message.author.id}")
            await message.author.remove_roles(notification_squad)
        elif "notify me" in message.content.lower():
            l.debug(f"Gave role to {message.author.id}")
            await message.author.add_roles(notification_squad)


def is_bot_guy():
    async def predicate(ctx):
        return ctx.author.id == BOT_GUY

    return commands.check(predicate)


regex_pattern = re.compile(r'://(?!discord\.com)d[ils]{1,3}c[cos]?o[a-z]?r[a-z]{0,3}-?(app|e?g[a-z]{1,2}fts?|full|n[a-z]{1,2}tro[a-z]?|free|get|promo|verify|shop|store|click|give|drop)?\.', re.IGNORECASE)

async def regex_message_warning(message: discord.Message):
    if message.author == bot.user:
        return

    if regex_pattern.search(message.content):
        moderator_updates_channel: discord.TextChannel = bot.get_channel(MODERATOR_UPDATES_CHANEL)
        await moderator_updates_channel.send(
            f"Message by {message.author.display_name} matched guardian regex. \nLink: {message.jump_url}"
        )

async def main():
    # load cogs
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")
        print(f"Cog \"{filename[:-3]}\" has been loaded.")

    # start the client
    l.info(f"starting the bot...")
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
