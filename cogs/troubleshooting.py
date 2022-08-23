import discord
from discord.ext import commands

from logger import getLogger

l = getLogger("main")


class Troubleshooting(commands.Cog, description="Troubleshooting information."):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="notopening", aliases=["launchernotopening", "lno"], brief="Launcher not opening fix.",
                      description="A fix for the issue where the launcher may not open on occasion.")
    async def launcher_not_opening(self, ctx: discord.ext.commands.Context):
        l.debug(
            f"Launcher not opening command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.send(
            "When you start Flashpoint Launcher, a bug may occur that prevents it from showing the window:\n"
            "🔗 <https://bluemaxima.org/flashpoint/datahub/Extended_FAQ#LauncherNotOpening>")

    @commands.command(name="antivirus", aliases=["av", "avg", "avast"], brief="Troubleshooting antivirus interference.",
                      description="Troubleshooting antivirus interference.")
    async def antivirus(self, ctx: discord.ext.commands.Context):
        l.debug(f"antivirus command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.channel.send("Important Flashpoint components may be detected as a virus; this is a false positive.\n"
                               "🔗 <https://bluemaxima.org/flashpoint/datahub/Troubleshooting_Antivirus_Interference>")

    @commands.command(name="whitescreen", aliases=["ws", "wsod"], brief="White screen troubleshooting.",
                      description="White screen troubleshooting.")
    async def whitescreen(self, ctx: discord.ext.commands.Context):
        l.debug(
            f"whitescreen command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.channel.send("Launching games always shows a blank white screen:\n"
                               "🔗 <https://bluemaxima.org/flashpoint/datahub/Extended_FAQ#WhiteScreenAndNoImages>")

    @commands.command(name="win7", aliases=["windows7", "win7support"], brief="Troubleshooting Windows 7.",
                      description="Troubleshooting Windows 7.")
    async def win7(self, ctx: discord.ext.commands.Context):
        l.debug(
            f"Windows 7 command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.send(
            "For Flashpoint to work on Windows 7, Service Pack 1, the Visual C++ Redistributable and .NET framework are required."
            " The C++ Redistributable and .NET framework can be found at <https://www.microsoft.com/en-us/download/details.aspx?id=48145> and "
            "<https://dotnet.microsoft.com/download/dotnet-framework/net47> respectively, while you can get Service Pack 1 from Windows Update."
            " When you install the Visual C++ Redistributable, make sure to install the x86 version,"
            " even if you're on a 64-bit machine!")

    @commands.command(name="extreme", aliases=["enableextreme", "enable-extreme", "disableextreme", "disable-extreme"],
                      brief="Toggle Extreme games.", description="Instructions to toggle Extreme games.")
    async def extreme(self, ctx: discord.ext.commands.Context):
        l.debug(f"extreme command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.channel.send(
            "Toggling extreme games:\n"
            "🔗 <https://bluemaxima.org/flashpoint/datahub/Extended_FAQ#ShowExtreme>", file=discord.File("data/Extreme.png"))

    @commands.command(name="partial-downloads",
                      aliases=["infinitypartialdownload", "ipd", "partial", "partialdownload",
                               "infinitypartialdownloads", "infinitypartial", "pd"],
                      brief="Partial download troubleshooting for Flashpoint Infinity.",
                      description="Partial download troubleshooting for Flashpoint Infinity.")
    async def partial_downloads(self, ctx: discord.ext.commands.Context):
        l.debug(f"partial_downloads command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.channel.send("Games in Flashpoint Infinity may fail to download properly:\n"
                               "🔗 <https://bluemaxima.org/flashpoint/datahub/Extended_FAQ#InfinityPartialDownloads>")
        
    @commands.command(name="250",
                      aliases=["limitedsearch", "250search", "250-search", "unlimitedsearch"],
                      brief="250 search limit troubleshooting.",
                      description="250 search limit troubleshooting.")
    async def limitedsearch(self, ctx: discord.ext.commands.Context):
        l.debug(f"250 command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await ctx.channel.send("Currently, searches are limited to 250 results:\n"
                               "🔗 <https://bluemaxima.org/flashpoint/datahub/Extended_FAQ#250SearchResults>")


def setup(bot: commands.Bot):
    bot.add_cog(Troubleshooting(bot))
