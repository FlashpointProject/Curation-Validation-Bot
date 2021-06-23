import datetime
import sqlite3
from sqlite3 import Error, Connection
from typing import Optional

import discord
from discord.ext import commands

from logger import getLogger

l = getLogger("main")


class Moderation(commands.Cog, description="Moderation tools."):

    def __init__(self, bot):
        self.bot: discord.ext.commands.Bot = bot

    @commands.command(name="ban", brief="Ban a user.", description="Ban a user, and optionally give a reason.")
    @commands.has_role("Moderator")
    async def ban(self, ctx: discord.ext.commands.Context, member: discord.Member, reason: Optional[str]):
        l.debug(f"ban command issued by {ctx.author.id} on user {member.id}")
        self.log_event("ban", member, reason)
        await member.send("You have been banned from the flashpoint discord server.\n"
                          f"Reason: {reason}")
        await member.ban(reason=reason)
        await ctx.send(f"{member.nick} was banned.")

    @commands.command(name="kick", brief="Kick a user.", description="Kick a user, and optionally give a reason.")
    @commands.has_role("Moderator")
    async def kick(self, ctx: discord.ext.commands.Context, member: discord.Member, reason: Optional[str]):
        l.debug(f"kick command issued by {ctx.author.id} on user {member.id}")
        self.log_event("kick", member, reason)
        await member.send("You have been kicked from the flashpoint discord server.\n"
                          f"Reason: {reason}")
        await member.kick(reason=reason)
        await ctx.send(f"{member.nick} was kicked.")


    @commands.command(name="kick", brief="Warn a user.", description="Warn a user and give a reason.")
    @commands.has_role("Moderator")
    async def warn(self, ctx: discord.ext.commands.Context, member: discord.Member, reason: Optional[str]):
        l.debug(f"kick command issued by {ctx.author.id} on user {member.id}")
        self.log_event("kick", member, reason)
        await member.send("You have been formally warned from the flashpoint discord server."
                          "Another infraction will have steeper consequences.\n"
                          f"Reason: {reason}")
        await member.kick(reason=reason)
        await ctx.send(f"{member.nick} was formally warned.")

    def log_event(self, action: str, member: discord.Member, reason: str):
        connection = sqlite3.connect('data/moderation_log.db')

        try:
            c = connection.cursor()
            utc_now: datetime.datetime = datetime.datetime.now(tz=datetime.timezone.utc)
            c.execute("INSERT INTO log (id, name, action, reason, date) VALUES (?, ?, ?, ?, ?)",
                      (member.id, member.nick, action, reason, utc_now))
            c.close()
        finally:
            connection.close()


def create_moderation_log() -> None:
    connection = sqlite3.connect('data/moderation_log.db')
    try:
        c = connection.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS log ("
                  "id integer PRIMARY KEY,"
                  "name text NOT NULL,"
                  "action text NOT NULL,"
                  "reason text,"
                  "date timestamp NOT NULL,"
                  "unban_date timestamp,"
                  "unbanned integer);")
        c.close()
    finally:
        connection.close()
    return


def setup(bot: commands.Bot):
    try:
        create_moderation_log()
    except Exception as e:
        l.error(f"Error {e} when trying to set up moderation, will not be initialized.")
    bot.add_cog(Moderation(bot))
