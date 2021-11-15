import datetime
import re
from typing import Optional

import discord
from discord.ext import commands
import humanize

from logger import getLogger

l = getLogger("main")

time_regex = re.compile(r"(\d{1,5}(?:[.,]?\d{1,5})?)([smhdw])")
time_dict = {"h": 3600, "s": 1, "m": 60, "d": 86400, "w": 604800}


class TimeConverter(commands.Converter):
    async def convert(self, ctx, argument):
        matches = time_regex.findall(argument.lower())
        time = 0
        for v, k in matches:
            try:
                time += time_dict[k] * float(v)
            except KeyError:
                raise commands.BadArgument("{} is an invalid time-key! h/m/s/d are valid!".format(k))
            except ValueError:
                raise commands.BadArgument("{} is not a number!".format(v))
        return datetime.timedelta(seconds=time)


class Moderation(commands.Cog, description="Moderation tools."):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="make-curator", brief="Make a user a trial curator (Staff).",
                      description="Make a user a trial curator (Staff only).")
    @commands.has_any_role("Mechanic", "Developer", "Curator", "Archivist", "Hacker", "Hunter", "Administrator")
    async def make_trial(self, ctx: discord.ext.commands.Context, member: discord.Member):
        l.debug(
            f"make trial curator command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await member.add_roles("Trial Curator")
        await ctx.send("Done!")

    @commands.command(name="unmake-curator", brief="Remove the trial curator role from a user (Staff).",
                      description="Remove the trial curator role from a user (Staff only).")
    @commands.has_any_role("Mechanic", "Developer", "Curator", "Archivist", "Hacker", "Hunter", "Administrator")
    async def unmake_trial(self, ctx: discord.ext.commands.Context, member: discord.Member):
        l.debug(
            f"untrial curator command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await member.remove_roles("Trial Curator")
        await ctx.send("Done!")

    @commands.command(name="timeout", brief="Give timeout role, with an optional time to undo (Staff).",
                      description="Add the timeout role to a user with the option of a time to untimeout, formatted as "
                                  "[seconds]s[minutes]m[hours]h[days]d[weeks]w, for example 25m30s for a "
                                  "25 minute 30 second timeout (Staff only).")
    @commands.has_any_role("Mechanic", "Developer", "Curator", "Archivist", "Hacker", "Hunter", "Administrator",
                           "Moderator [cs]", "Moderator [ar]", "Moderator [fr]", "Moderator [de]", "Moderator [es]",
                           "Moderator [ru]", "Moderator [it]", "Moderator [pt]", "Moderator [nl]", "Moderator [pl]",
                           "Moderator [tr]", "Moderator [zh]", "Moderator [ja]", "Moderator [ko]", "Moderator [da]",
                           "Moderator [th]", "Moderator [vi]", "Moderator [id]", "Moderator [he]", "Moderator [fa]",
                           "Moderator [hi]", "Moderator [no]", "Moderator [sv]", "Moderator [fi]", "Moderator"
                           )
    async def timeout(self, ctx: discord.ext.commands.Context, member: discord.Member, time: Optional[TimeConverter]):
        l.debug(f"timeout command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await member.add_roles("Timeout")
        if time:
            await ctx.send(f"Gave timeout rule to {member.display_name} for {humanize.naturaldelta(time)}")
            await discord.utils.sleep_until(datetime.datetime.now() + time)
            await member.remove_roles("Timeout")
        else:
            await ctx.send("Done!")

    @commands.command(name="untimeout", brief="Remove timeout role (Staff).",
                      description="Remove the timeout role from a user (Staff only).")
    @commands.has_any_role("Mechanic", "Developer", "Curator", "Archivist", "Hacker", "Hunter", "Administrator",
                           "Moderator [cs]", "Moderator [ar]", "Moderator [fr]", "Moderator [de]", "Moderator [es]",
                           "Moderator [ru]", "Moderator [it]", "Moderator [pt]", "Moderator [nl]", "Moderator [pl]",
                           "Moderator [tr]", "Moderator [zh]", "Moderator [ja]", "Moderator [ko]", "Moderator [da]",
                           "Moderator [th]", "Moderator [vi]", "Moderator [id]", "Moderator [he]", "Moderator [fa]",
                           "Moderator [hi]", "Moderator [no]", "Moderator [sv]", "Moderator [fi]", "Moderator"
                           )
    async def untimeout(self, ctx: discord.ext.commands.Context, member: discord.Member):
        l.debug(f"untimeout command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await member.remove_roles("Timeout")
        await ctx.send("Done!")

    # @commands.command(name="ban", brief="Ban a user, with an optional time to undo (Staff).",
    #                   description="Ban a user with the option of a time to untimeout, formatted as "
    #                               "[seconds]s[minutes]m[hours]h[days]d[weeks]w, for example 25m30s for a "
    #                               "25 minute 30 second timeout (Staff only).")
    # @commands.has_any_role("Moderator")
    # async def ban(self, ctx: discord.ext.commands.Context, member: discord.Member, time: Optional[TimeConverter]):
    #     l.debug(f"ban command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
    #     await member.ban(reason=f"Banned by {ctx.author.display_name}")
    #     if time:
    #         await ctx.send(f"Banned {member.display_name} for {humanize.naturaldelta(time)}")
    #         await discord.utils.sleep_until(datetime.datetime.now() + time)
    #         await member.unban(reason="Unbanned after designated time")


def setup(bot: commands.Bot):
    bot.add_cog(Moderation(bot))
