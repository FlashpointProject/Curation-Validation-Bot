import datetime
import re
import sqlite3
from sqlite3 import Error, Connection
from typing import Optional, Union

import discord
from discord import Forbidden, HTTPException, NotFound
from discord.ext import commands, tasks

from pygicord import Paginator

from bot import TIMEOUT_ID
from logger import getLogger
from util import TimeDeltaConverter

db_path = 'data/moderation_log.db'
l = getLogger("main")


async def ban(member: discord.Member, reason: str, dry_run=False):
    log_user_event("Ban", member, member.guild, reason)
    if not dry_run:
        await try_dm(member, "You have been permanently banned from the flashpoint discord server.\n"
                             f"Reason: {reason}")
        await member.ban(reason=reason)


async def kick(member: discord.Member, reason: str, dry_run=False):
    log_user_event("Kick", member, member.guild, reason)
    if not dry_run:
        await try_dm(member, "You have been kicked from the flashpoint discord server.\n"
                             f"Reason: {reason}")
        await member.kick(reason=reason)


async def warn(member: discord.Member, reason: str, dry_run=False):
    log_user_event("Warn", member, member.guild, reason)
    if not dry_run:
        await try_dm(member, "You have been formally warned by the moderators of the Flashpoint discord server."
                             "Another infraction will have steeper consequences.\n"
                             f"Reason: {reason}")


async def timeout(member: discord.Member, duration: datetime.timedelta, reason: str, dry_run=False):
    timeout_role = member.guild.get_role(TIMEOUT_ID)
    log_tempban("Timeout", member, duration, reason)
    if not dry_run:
        await try_dm(member, f"You have been put in timeout from the Flashpoint discord server for {duration}."
                             f"You will not be able to interact any channels. Leaving and rejoining to avoid this will"
                             f"result in a ban.\n"
                             f"Reason: {reason}")
        await member.add_roles(timeout_role)


async def tempban(member: discord.Member, duration: datetime.timedelta, reason: str, dry_run=False):
    # The type checker doesn't understand how converters work, so I suppressed the warning here.
    # noinspection PyTypeChecker
    log_tempban("Ban", member, duration, reason)
    if not dry_run:
        await try_dm(member, f"You have been banned from the Flashpoint discord server for {duration}.\n"
                             f"Reason: {reason}")
        await member.ban(reason=reason)


async def unban(user: Union[discord.User, discord.Member], guild: discord.Guild, reason: str, dry_run=False):
    log_user_event("Unban", user, guild, reason)
    log_unban(user.id, guild)
    if not dry_run:
        await try_dm(user, "You have been unbanned from the Flashpoint discord server.\n"
                           f"Reason: {reason}")
        await guild.unban(user, reason=reason)


async def untimeout(member: discord.Member, reason: str, dry_run=False):
    timeout_role = member.guild.get_role(TIMEOUT_ID)
    log_user_event("Untimeout", member, member.guild, reason)
    if not dry_run:
        await try_dm(member, f"Your timeout is over, you can now interact with all channels freely.\n"
                             f"Reason: {reason}")
        await member.remove_roles(timeout_role)


class Moderation(commands.Cog, description="Moderation tools."):

    def __init__(self, bot):
        self.bot: discord.ext.commands.Bot = bot
        self.do_temp_unbans.start()

    @commands.command(name="ban", brief="Ban a user.", description="Ban a user, and optionally give a reason.")
    @commands.has_role("Moderator")
    async def ban_command(self, ctx: discord.ext.commands.Context, member: discord.Member, *, reason: Optional[str]):
        l.debug(f"ban command issued by {ctx.author.id} on user {member.id}")
        await ban(member, reason)
        await ctx.send(f"{member.display_name} was banned.")

    @commands.command(name="kick", brief="Kick a user.", description="Kick a user, and optionally give a reason.")
    @commands.has_role("Moderator")
    async def kick_command(self, ctx: discord.ext.commands.Context, member: discord.Member, *, reason: Optional[str]):
        l.debug(f"kick command issued by {ctx.author.id} on user {member.id}")
        await kick(member, reason)
        await ctx.send(f"{member.display_name} was kicked.")

    @commands.command(name="warn", brief="Warn a user.",
                      description="Warn a user and give a reason, "
                                  "kicks if user has already been warned once "
                                  "and bans if they've been warned twice.")
    @commands.has_role("Moderator")
    async def warn_command(self, ctx: discord.ext.commands.Context, member: discord.Member, *, reason: Optional[str]):
        l.debug(f"warn command issued by {ctx.author.id} on user {member.id}")
        await warn(member, reason)
        await ctx.send(f"{member.display_name} was formally warned.")

    @commands.command(name="tempban", brief="Tempban a user.",
                      description="Temporarily ban a user, and optionally give a reason. "
                                  "Dates should be formatted as [minutes]m[hours]h[days]d[weeks]w, "
                                  "for example 1m3h or 3h1m for an hour and 3 minutes.")
    @commands.has_role("Moderator")
    async def tempban_command(self, ctx: discord.ext.commands.Context, member: discord.Member,
                              duration: TimeDeltaConverter, *, reason: Optional[str]):
        l.debug(f"tempban command issued by {ctx.author.id} on user {member.id}")
        # The type checker can't understand converters, so we have to do this.
        # noinspection PyTypeChecker
        await tempban(member, duration, reason)
        await ctx.send(f"{member.display_name} was banned for {duration}.")

    @commands.command(name="timeout", brief="Timeout a user.",
                      description="Timeout a user, and optionally give a reason. "
                                  "Dates should be formatted as [minutes]m[hours]h[days]d[weeks]w, "
                                  "for example 1m3h or 3h1m for an hour and 3 minutes.")
    @commands.has_role("Moderator")
    async def timeout_command(self, ctx: discord.ext.commands.Context, member: discord.Member,
                              duration: TimeDeltaConverter, *, reason: Optional[str]):
        l.debug(f"timeout command issued by {ctx.author.id} on user {member.id}")
        # The type checker can't understand converters, so we have to do this.
        # noinspection PyTypeChecker
        await timeout(member, duration, reason)
        await ctx.send(f"{member.display_name} was given the timeout role for {duration}.")

    @commands.command(name="untimeout", aliases=["remove-timeout", "undo-timeout"], brief="Unban a user.",
                      description="Unban a user, and optionally give a reason.")
    @commands.has_role("Moderator")
    async def untimeout_command(self, ctx: discord.ext.commands.Context, member: discord.Member, *,
                                reason: Optional[str]):
        l.debug(f"untimeout command issued by {ctx.author.id} on user {member.id}")
        await untimeout(member, reason)
        await ctx.send(f"{member.display_name} had their timeout removed.")

    @commands.command(name="unban", brief="Unban a user.", description="Unban a user, and optionally give a reason.")
    @commands.has_role("Moderator")
    async def unban_command(self, ctx: discord.ext.commands.Context, member: Union[discord.User, discord.Member], *,
                            reason: Optional[str]):
        l.debug(f"unban command issued by {ctx.author.id} on user {member.id}")
        await unban(member, member.guild, reason)
        await ctx.send(f"{member.display_name} was unbanned.")

    @commands.command(name="log", brief="Gives a log of all moderator actions done to a user.",
                      description="Gives a log of all moderator actions done."
                                  "May need full username/mention.")
    @commands.has_role("Moderator")
    async def log(self, ctx: discord.ext.commands.Context, user: Union[discord.User, discord.Member]):
        l.debug(f"log command issued by {ctx.author.id} on user {user.id}")
        # We're parsing timestamps, so we need the detect-types part
        connection = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        c = connection.cursor()
        try:
            c.execute("SELECT action, reason, action_date FROM log WHERE user_id = ? AND guild_id = ?",
                      (user.id, ctx.guild.id))
            events: list[tuple[str, str, datetime]] = c.fetchall()
            c.close()
        finally:
            connection.close()

        if any(x[0] == "Ban" for x in events):
            embed_color = discord.Color.red()
        elif any(x[0] == "Kick" for x in events):
            embed_color = discord.Color.orange()
        elif any(x[0] == "Warn" for x in events):
            embed_color = discord.Color.gold()
        elif any(x[0] == "Timeout" for x in events):
            embed_color = discord.Color.blue()
        else:
            embed_color = discord.Color.green()
        pages: list[discord.Embed]

        pages = []
        embed = discord.Embed(color=embed_color)
        embed.set_author(name=user.name, icon_url=user.avatar_url)
        for event in events:
            if len(embed.fields) >= 25:
                pages.append(embed)
                embed = discord.Embed(color=embed_color)
                embed.set_author(name=user.name, icon_url=user.avatar_url)
            time_str = event[2].strftime("%Y-%m-%d %H:%M:%S")
            embed.add_field(name=event[0],
                            value=f"Date: {time_str}\n"
                                  f"Reason: {event[1]}",
                            inline=False)
            # embed.add_field(name="Action", value=event[0])
            # embed.add_field(name="Reason", value=event[1])
            # embed.add_field(name="Date", value=event[2].strftime("%Y-%m-%d %H:%M:%S"))

        pages.append(embed)
        paginator = Paginator(pages=pages)
        await paginator.start(ctx)

    # for each tempban in the database, if it's before now, unban by id.
    @tasks.loop(seconds=30.0)
    async def do_temp_unbans(self):
        l.debug("checking for unbans")
        connection = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        c = connection.cursor()
        try:
            c.execute(
                "SELECT user_id, guild_id, action "
                "FROM log "
                "WHERE undone = '0' "
                "AND unban_date < datetime('now')")
            expired_tempbans: list[tuple[int, int, str]] = c.fetchall()
            for expired_tempban in expired_tempbans:
                guild: discord.Guild = self.bot.get_guild(expired_tempban[1])
                action = expired_tempban[2]
                user_id = expired_tempban[0]
                if action == "Ban":
                    try:
                        user: discord.User = await self.bot.fetch_user(user_id)
                        await unban(user, guild, "Tempban expired")
                    except NotFound:
                        log_unban(user_id, guild)
                    except HTTPException:
                        pass
                elif action == "Timeout":
                    member: discord.Member = guild.get_member(user_id)
                    if member is not None:
                        await untimeout(member, "Timeout expired")
                    else:
                        log_unban(user_id, guild)

        finally:
            c.close()
            connection.close()

    @do_temp_unbans.before_loop
    async def before_start_unbans(self):
        await self.bot.wait_until_ready()


def log_tempban(action: str, member: discord.Member, duration: datetime.timedelta, reason: str):
    connection = sqlite3.connect(db_path)
    c = connection.cursor()
    try:
        utc_now: datetime.datetime = datetime.datetime.now(tz=datetime.timezone.utc)
        c.execute(
            "INSERT INTO log (user_id, guild_id, action, reason, action_date, unban_date, undone) "
            "VALUES (?, ?, ?, ?, ?, ? , 0)",
            (member.id, member.guild.id, action, reason, utc_now, utc_now + duration))
        connection.commit()
    finally:
        c.close()
        connection.close()


def log_user_event(action: str, user: Union[discord.User, discord.Member], guild: discord.Guild, reason: str):
    connection = sqlite3.connect(db_path)
    c = connection.cursor()
    try:
        utc_now: datetime.datetime = datetime.datetime.now(tz=datetime.timezone.utc)
        c.execute("INSERT INTO log (user_id, guild_id, action, reason, action_date)"
                  "VALUES (?, ?, ?, ?, ?)",
                  (user.id, guild.id, action, reason, utc_now))
        connection.commit()
    finally:
        c.close()
        connection.close()


# In theory this has a problem in that it undoes all the actions on a person, but the only actions that
# can be undone are timeout and unban, and they're mutually exclusive. It'd be pretty easy to change if
# this is ever not the case though.
def log_unban(user_id: int, guild: discord.Guild):
    connection = sqlite3.connect(db_path)
    c = connection.cursor()
    try:
        c.execute("UPDATE log "
                  "SET undone = 1 "
                  "WHERE undone = 0 "
                  "AND user_id = ? "
                  "AND guild_id = ?",
                  (user_id, guild.id))
        connection.commit()
    finally:
        c.close()
        connection.close()


def create_moderation_log() -> None:
    connection = sqlite3.connect(db_path)
    c = connection.cursor()
    try:
        c.execute("CREATE TABLE IF NOT EXISTS log ("
                  "user_id integer NOT NULL,"
                  "guild_id integer NOT NULL,"
                  "action text NOT NULL,"
                  "reason text,"
                  "action_date timestamp NOT NULL,"
                  "unban_date timestamp,"
                  "undone integer);")
    finally:
        c.close()
        connection.close()
    return


async def try_dm(user: Union[discord.User, discord.Member], message):
    try:
        await user.send(message)
    except Forbidden:
        l.debug(f"Not allowed to send message to {user.id}")
    except HTTPException:
        l.debug(f"Failed to send message to {user.id}")


def setup(bot: commands.Bot):
    try:
        create_moderation_log()
    except Exception as e:
        l.error(f"Error {e} when trying to set up moderation, will not be initialized.")
    bot.add_cog(Moderation(bot))
