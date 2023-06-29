import datetime
import re
from typing import Optional

import discord
from discord.ext import commands
import humanize

from bot import AUDITION_CHAT_CHANNEL
from logger import getLogger

l = getLogger("main")


class Moderation(commands.Cog, description="Moderation tools."):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="trial", aliases=["make-trial", "make-trial-curator", "make-curator", "add-trial"],
                      brief="Make a user a trial curator (Staff).",
                      description="Make a user a trial curator (Staff only).")
    @commands.has_any_role("Mechanic", "Developer", "Curator", "Archivist", "Hacker", "Hunter", "Administrator")
    async def make_trial(self, ctx: discord.ext.commands.Context, *, member: discord.Member):
        l.debug(f"make trial curator command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        trial_curator_role = discord.utils.get(ctx.guild.roles, name="Trial Curator")
        await member.add_roles(trial_curator_role)
        audition_chat_channel = self.bot.get_channel(AUDITION_CHAT_CHANNEL)
        await audition_chat_channel.send(f"Congratulations {member.mention}, you are now a Trial Curator!"
                       f" Please log out and log back in of the submission site to update your permissions.")

    @commands.command(name="untrial", aliases=["unmake-trial", "unmake-trial-curator", "unmake-curator", "remove-trial"],
                      brief="Remove the trial curator role from a user (Staff).",
                      description="Remove the trial curator role from a user (Staff only).")
    @commands.has_any_role("Mechanic", "Developer", "Curator", "Archivist", "Hacker", "Hunter", "Administrator")
    async def unmake_trial(self, ctx: discord.ext.commands.Context, *, member: discord.Member):
        l.debug(f"unmake trial curator command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        trial_curator_role = discord.utils.get(ctx.guild.roles, name="Trial Curator")
        await member.remove_roles(trial_curator_role)
        await ctx.send("Done!")

    @commands.command(name="make-donator", aliases=["make-don", "add-donator", "add-don"],
                      brief="Give a user the donator role(Staff).",
                      description="Give the donator role to a user (Staff only).")
    @commands.has_any_role("Mechanic", "Developer", "Curator", "Archivist", "Hacker", "Hunter", "Administrator")
    async def make_donator(self, ctx: discord.ext.commands.Context, *, member: discord.Member):
        l.debug(f"make donator command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        donator_role = discord.utils.get(ctx.guild.roles, name="Donator")
        await member.add_roles(donator_role)
        await ctx.send("Done!")

    @commands.command(name="remove-donator", aliases=["unmake-don", "unmake-donator", "remove-don"],
                      brief="Remove the donator role from a user (Staff).",
                      description="Remove the donator role from a user (Staff only).")
    @commands.has_any_role("Mechanic", "Developer", "Curator", "Archivist", "Hacker", "Hunter", "Administrator")
    async def unmake_donator(self, ctx: discord.ext.commands.Context, *, member: discord.Member):
        l.debug(f"unmake donator command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        donator_role = discord.utils.get(ctx.guild.roles, name="Donator")
        await member.remove_roles(donator_role)
        await ctx.send("Done!")

    @commands.command(name="sban", brief="Softban a user and send account recovery message (Staff).",
                      description="Softban a user and send an account recovery message (Staff only).",
                      aliases=["softban", "sb", "kick-delete", "spammer", "spamkick", "spam-kick", "spam-ban", "spamban"])
    @commands.has_role("Moderator")
    async def softban(self, ctx: discord.ext.commands.Context, *, user: discord.Member):
        l.debug(f"softban command invoked from {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        await user.send("Hello there, you might be unaware, but your account recently sent a message on the "
                        "BlueMaxima's Flashpoint server soliciting free Nitro gifts. Our bot blocked the message, "
                        "but your account may still be hacked. As a safety precaution, we have also kicked you from "
                        "the sever to prevent your account from being able to send messages to other people. Here's "
                        "what you can do to protect yourself:\n"
                        "1) Remove any suspicious Authorized Apps. Go into your User Settings, and under Authorized "
                        "Apps, there is a list of bots that you invited to have "
                        "access to your account. Sometimes they will be disguised as legit websites such as Twitch "
                        "offering fake things for free.\n"
                        "2) Do a full reinstall of Discord. Most scripts used by "
                        "these scams will sit in your installation, and a simple reinstall won't get rid of them. To "
                        "do a full reinstall, follow the directions from Discord "
                        "Support:\n<https://support.discord.com/hc/en-us/articles/115004307527--Windows-Corrupt"
                        "-Installation>\n"
                        "3) Change your password. If a bot had access to an account to post on your "
                        "behalf, it likely has an authorization token of your account, which is the same as having "
                        "your username and password. Changing your password will also change the token.\nAs a "
                        "side-note: To increase security, you can enable Two-Factor Authentication. You can do this "
                        "under User Settings > My Account > Enable Two-Factor Auth.\n4) If you'd like to rejoin the "
                        "server, you're more than welcome to! Just be careful next time not to click any random links "
                        "promising free gifts. You can find the invite link on our website "
                        "at:\n<https://bluemaxima.org/flashpoint/>")
        await user.ban(reason="Compromised account", delete_message_days=1)
        await user.unban()
        await ctx.send("Done!")


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
