import datetime
import re
import sqlite3
from sqlite3 import Error, Connection
from typing import Optional

import discord
from discord.ext import commands
from discord.ext.commands import BadArgument, Greedy

from logger import getLogger
from util import TimeDeltaConverter

l = getLogger("main")


class Moderation(commands.Cog, description="Moderation tools."):

    def __init__(self, bot):
        self.bot: discord.ext.commands.Bot = bot

    @commands.command(name="ban", brief="Ban a user.", description="Ban a user, and optionally give a reason.")
    @commands.has_role("Moderator")
    async def ban(self, ctx: discord.ext.commands.Context, member: discord.Member, *, reason: Optional[str]):
        l.debug(f"ban command issued by {ctx.author.id} on user {member.id}")
        log_event("ban", member, reason)
        await member.send("You have been permanently banned from the flashpoint discord server.\n"
                          f"Reason: {reason}")
        await member.ban(reason=reason)
        await ctx.send(f"{member.display_name} was banned.")

    @commands.command(name="kick", brief="Kick a user.", description="Kick a user, and optionally give a reason.")
    @commands.has_role("Moderator")
    async def kick(self, ctx: discord.ext.commands.Context, member: discord.Member, *, reason: Optional[str]):
        l.debug(f"kick command issued by {ctx.author.id} on user {member.id}")
        log_event("kick", member, reason)
        await member.send("You have been kicked from the flashpoint discord server.\n"
                          f"Reason: {reason}")
        await member.kick(reason=reason)
        await ctx.send(f"{member.display_name} was kicked.")

    @commands.command(name="warn", brief="Warn a user.",
                      description="Warn a user and give a reason, "
                                  "kicks if user has already been warned once "
                                  "and bans if they've been warned twice.")
    @commands.has_role("Moderator")
    async def warn(self, ctx: discord.ext.commands.Context, member: discord.Member, *, reason: Optional[str]):
        l.debug(f"warn command issued by {ctx.author.id} on user {member.id}")
        log_event("warn", member, reason)
        await member.send("You have been formally warned from the Flashpoint discord server."
                          "Another infraction will have steeper consequences.\n"
                          f"Reason: {reason}")
        await ctx.send(f"{member.display_name} was formally warned.")

    @commands.command(name="tempban", brief="Tempban a user.",
                      description="Temporarily ban a user, and optionally give a reason. "
                                  "Dates should be formatted as [minutes]m[hours]h[days]d[weeks]w, "
                                  "for example 1m3h or 3h1m for an hour and 3 minutes.")
    @commands.has_role("Moderator")
    async def tempban(self, ctx: discord.ext.commands.Context, member: discord.Member, duration: TimeDeltaConverter, *, reason: Optional[str]):
        l.debug(f"tempban command issued by {ctx.author.id} on user {member.id}")
        log_unban("tempban", member, duration, reason)
        await member.send(f"You have been banned from the Flashpoint discord server for {duration}.\n"
                          f"Reason: {reason}")
        await member.ban()
        await ctx.send(f"{member.display_name} was banned for {duration}.")

    @commands.has_role("Moderator")
    async def log(self, ctx: discord.ext.commands.Context, user: discord.User):
        connection = sqlite3.connect('data/moderation_log.db')
        try:
            c = connection.cursor()
            c.execute("SELECT (action, reason, date) FROM log WHERE id = '?'", user.id)
            things: list[tuple[str, str, datetime]] = c.fetchall()
            c.close()
            connection.commit()
        finally:
            connection.close()
        embed = discord.Embed()
        if any(x[0] == "ban" for x in things):
            embed = discord.Embed(color=discord.Color.red())
        elif any(x[0] == "kick" for x in things):
            embed = discord.Embed(color=discord.Color.orange())
        elif any(x[0] == "warn" for x in things):
            embed = discord.Embed(color=discord.Color.gold())
        else:
            embed = discord.Embed(color=discord.Color.green())
        embed.set_author(name=user.name, )



def log_unban(action: str, member: discord.Member, duration: datetime.timedelta, reason: str):
    connection = sqlite3.connect('data/moderation_log.db')
    try:
        c = connection.cursor()
        utc_now: datetime.datetime = datetime.datetime.now(tz=datetime.timezone.utc)
        c.execute("INSERT INTO log (id, action, reason, date, unban_date, unbanned) VALUES (?, ?, ?, ?, ? , 0)",
                  (member.id, action, reason, utc_now, utc_now + duration))
        c.close()
        connection.commit()
    finally:
        connection.close()


def log_event(action: str, member: discord.Member, reason: str):
    connection = sqlite3.connect('data/moderation_log.db')
    try:
        c = connection.cursor()
        utc_now: datetime.datetime = datetime.datetime.now(tz=datetime.timezone.utc)
        c.execute("INSERT INTO log (id, action, reason, date) VALUES (?, ?, ?, ?)",
                  (member.id, action, reason, utc_now))
        c.close()
        connection.commit()
    finally:
        connection.close()


def create_moderation_log() -> None:
    connection = sqlite3.connect('data/moderation_log.db')
    try:
        c = connection.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS log ("
                  "id integer NOT NULL,"
                  "action text NOT NULL,"
                  "reason text,"
                  "date timestamp NOT NULL,"
                  "unban_date timestamp,"
                  "unbanned integer);")
        c.close()
        connection.commit()
    finally:
        connection.close()
    return


def setup(bot: commands.Bot):
    try:
        create_moderation_log()
    except Exception as e:
        l.error(f"Error {e} when trying to set up moderation, will not be initialized.")
    bot.add_cog(Moderation(bot))
