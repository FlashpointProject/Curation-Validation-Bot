from typing import Optional

import discord
from discord.ext import commands

from logger import getLogger

l = getLogger("main")


class Info(commands.Cog, description="General information about Flashpoint."):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="masterlist",
                      aliases=["ml", "master-list", "list", "games", "animations", "gamelist", "game-list", "search", "gl"],
                      brief="Link or search master list", description="Search the master list for a title, "
                                                                      "or link to a place to search if none is provided.")
    async def master_list(self, ctx: discord.ext.commands.Context, search_query: Optional[str] = None):
        if search_query is None:
            l.debug(
                f"masterlist command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
            await ctx.channel.send("Browse Flashpoint Catalog:\n"
                                   "🔗 <https://nul.sh/misc/flashpoint/>")
        else:
            l.debug(
                f"masterlist with query command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
            await ctx.channel.send("Direct search not implemented yet.\n"
                                   "🔗 <https://nul.sh/misc/flashpoint/>")

    @commands.command(name="downloads", aliases=["dl"], brief="Where to download Flashpoint.",
                      description="A link to the place to to download Flashpoint.")
    async def downloads(self, ctx: discord.ext.commands.Context):
        l.debug(f"downloads command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.channel.send("Download Flashpoint from here:\n"
                               "🔗 <https://bluemaxima.org/flashpoint/downloads/>")

    @commands.command(name="platforms", aliases=["plugins"], brief="Supported platforms in Flashpoint.",
                      description="Supported platforms in Flashpoint.")
    async def platforms(self, ctx: discord.ext.commands.Context):
        l.debug(f"platforms command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.channel.send("Supported Platforms:\n"
                               "🔗 <https://bluemaxima.org/flashpoint/platforms/>\n"
                               "Technical information:\n"
                               "🔗 <https://bluemaxima.org/flashpoint/datahub/Platforms>")

    @commands.command(name="github", aliases=["gh"], brief="Flashpoint Project GitHub.",
                      description="A link to the Flashpoint Project GitHub.")
    async def github(self, ctx: discord.ext.commands.Context):
        l.debug(f"github command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.channel.send("Flashpoint Project on GitHub:\n"
                               "🔗 <https://github.com/FlashpointProject/>")

    @commands.command(name="chromebook", aliases=["cb"], brief="Chromebook compatibility.",
                      desription="Flashpoint's chromebook compatibility.")
    async def chromebook(self, ctx: discord.ext.commands.Context):
        l.debug(f"chromebook command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.channel.send("Flashpoint is compatible with Intel Chromebooks that support Linux:\n"
                               "🔗 <https://bluemaxima.org/flashpoint/datahub/Linux_Support>")

    @commands.command(name="linux", brief="Linux compatibility.", description="Linux compatibility.")
    async def linux(self, ctx: discord.ext.commands.Context):
        l.debug(f"linux command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.channel.send("Flashpoint on Linux:\n"
                               "🔗 <https://bluemaxima.org/flashpoint/datahub/Linux_Support>")

    @commands.command(name="mac", brief="Mac compatibility.", description="Mac compatibility.")
    async def mac(self, ctx: discord.ext.commands.Context):
        l.debug(f"mac command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.channel.send("Flashpoint on Mac:\n"
                               "🔗 <https://bluemaxima.org/flashpoint/datahub/Mac_Support>")

    @commands.command(name="multiplayer", aliases=["fb", "mp", "facebook"], brief="Flashpoint multiplayer support.",
                      description="A description of Flashpoint's multiplayer support.")
    async def facebook(self, ctx: discord.ext.commands.Context):
        l.debug(f"Facebook command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.send("Flashpoint will likely not support online or Facebook-based games. "
                       "To support always online games, the emulation of a server is required. "
                       "To be able to do that is almost as much work as all of Flashpoint itself, "
                       "so it really wouldn't be practical to put time into.")

    @commands.command(name="nitrome", aliases=["nit"], brief="Nitrome information.", description="Nitrome information.")
    async def nitrome(self, ctx: discord.ext.commands.Context):
        l.debug(f"nitrome command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.channel.send("Nitrome politely asked us to remove their content from the collection. "
                               "If you're looking to play their games, do it at their website, and if Flash "
                               "isn't an option, follow their growing HTML5-compatible catalog. "
                               "Flashpoint does not condone harassment over Nitrome's decision.")

    @commands.command(name="faq", brief="FAQ.", description="A link to the FAQ page.")
    async def faq(self, ctx: discord.ext.commands.Context):
        l.debug(f"FAQ command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.channel.send("FAQ:\n 🔗 <https://bluemaxima.org/flashpoint/datahub/Extended_FAQ>")
        
    @commands.command(name="fullscreen", aliases=["fs", "full-screen"], brief="Fullscreening games.", description="How to fullscreen games.")
    async def fullscreen(self, ctx: discord.ext.commands.Context):
        l.debug(f"fullscreen command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.channel.send("There are multiple ways to fullscreen games:\n 🔗 "
                               "<https://bluemaxima.org/flashpoint/datahub/Extended_FAQ#Fullscreen>")

    @commands.command(name="flashfreeze", aliases=["ff", "archived-websites"], brief="Flashfreeze info.",
                      description="How to find what flashpoint has archived.")
    async def flashfreeze(self, ctx: discord.ext.commands.Context):
        l.debug(f"flashfreeze command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.channel.send("How to see what we've archived:\n 🔗 "
                               "<https://bluemaxima.org/flashpoint/datahub/Extended_FAQ#ArchivedWebsites>")

    @commands.command(name="update", aliases=["updates"], brief="Updating Flashpoint.",
                      description="Information about updating Flashpoint.")
    async def update(self, ctx: discord.ext.commands.Context):
        l.debug(f"update command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.channel.send("Updating Flashpoint:\n 🔗 "
                               "<https://bluemaxima.org/flashpoint/datahub/Extended_FAQ#UpdateFlashpoint>")


def setup(bot: commands.Bot):
    bot.add_cog(Info(bot))
