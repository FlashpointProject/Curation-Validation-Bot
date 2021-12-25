import datetime
import re
from typing import Optional

import discord
from discord.ext import commands
import humanize

from logger import getLogger

l = getLogger("main")


class Moderation(commands.Cog, description="Moderation tools."):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="trial", aliases=["make-trial", "make-trial-curator", "make-curator", "add-trial"],
                      brief="Make a user a trial curator (Staff).",
                      description="Make a user a trial curator (Staff only).")
    @commands.has_any_role("Mechanic", "Developer", "Curator", "Archivist", "Hacker", "Hunter", "Administrator")
    async def make_trial(self, ctx: discord.ext.commands.Context, member: discord.Member):
        l.debug(f"make trial curator command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        trial_curator_role = discord.utils.get(ctx.guild.roles, name="Trial Curator")
        await member.add_roles(trial_curator_role)
        await ctx.send("Done!")

    @commands.command(name="untrial", aliases=["unmake-trial", "unmake-trial-curator", "unmake-curator", "remove-trial"],
                      brief="Remove the trial curator role from a user (Staff).",
                      description="Remove the trial curator role from a user (Staff only).")
    @commands.has_any_role("Mechanic", "Developer", "Curator", "Archivist", "Hacker", "Hunter", "Administrator")
    async def unmake_trial(self, ctx: discord.ext.commands.Context, member: discord.Member):
        l.debug(f"unmake trial curator command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        trial_curator_role = discord.utils.get(ctx.guild.roles, name="Trial Curator")
        await member.remove_roles(trial_curator_role)
        await ctx.send("Done!")


def setup(bot: commands.Bot):
    bot.add_cog(Moderation(bot))
