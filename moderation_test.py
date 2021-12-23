import discord.ext.commands
import pytest
import discord.ext.test as dpytest
from discord.ext import commands
from pretty_help import PrettyHelp


@pytest.fixture
def bot(event_loop):
    intents = discord.Intents.default()
    intents.members = True
    bot = commands.Bot(command_prefix="-",
                       help_command=PrettyHelp(color=discord.Color.red()),
                       case_insensitive=False,
                       intents=intents, loop=event_loop)
    bot.load_extension('cogs.batch_validate')
    bot.load_extension('cogs.troubleshooting')
    bot.load_extension('cogs.curation')
    bot.load_extension('cogs.info')
    bot.load_extension('cogs.utilities')
    bot.load_extension('cogs.moderation')
    bot.load_extension('cogs.admin')
    dpytest.configure(bot)
    return bot


@pytest.mark.asyncio
async def test_timeout(bot):
    guild = bot.guilds[0]
    member1 = guild.members[0]
    await dpytest.message(f"-timeout {member1.id}")


@pytest.mark.asyncio
async def test_foo(bot):
    await dpytest.message("!hello")
    assert dpytest.verify().message().content("Hello World!")