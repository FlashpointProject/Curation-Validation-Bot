import discord
from discord.ext import commands

from logger import getLogger

l = getLogger("main")


class Curation(commands.Cog, description="Information about curating games for Flashpoint."):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="curation", aliases=["ct", "curation-tutorial"], brief="Curation tutorial.")
    async def curation_tutorial(self, ctx: discord.ext.commands.Context):
        l.debug(
            f"curation tutorial command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.channel.send("Curation tutorial:\n"
                               "🔗 <https://bluemaxima.org/flashpoint/datahub/Curation_Tutorial>")

    @commands.command(name="not-accepted", aliases=["notaccepted", "disallowed", "blacklist", "blacklisted", "na"],
                 brief="Not accepted curations.")
    async def not_accepted(self, ctx: discord.ext.commands.Context):
        l.debug(
            f"not-accepted command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.channel.send("These are games/animations not allowed in Flashpoint for any reason:\n"
                               "🔗 <https://bluemaxima.org/flashpoint/datahub/Not_Accepted_Curations>")

    @commands.command(name="meta", aliases=["curation-format", "format", "metadata", "cf"], brief="Metadata file.")
    async def meta(self, ctx: discord.ext.commands.Context):
        l.debug(f"meta command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.channel.send("List of Metadata Fields:\n"
                               "🔗 <https://bluemaxima.org/flashpoint/datahub/Curation_Format#List_of_Metadata_Fields>")

    @commands.command(name="tags", brief="Tags in Flashpoint.")
    async def tags(self, ctx: discord.ext.commands.Context):
        l.debug(f"tags command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.channel.send("List of Tags:\n"
                               "🔗 <https://bluemaxima.org/flashpoint/datahub/Tags>")

    @commands.command(name="lang", aliases=["langs", "languages"], brief="Language codes.")
    async def lang(self, ctx: discord.ext.commands.Context):
        l.debug(f"lang command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.channel.send("List of Language Codes:\n"
                               "🔗 <https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes>")


def setup(bot: commands.Bot):
    bot.add_cog(Curation(bot))
