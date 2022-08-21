from typing import Optional

import discord
from discord import HTTPException
from discord.ext import commands

import json


from logger import getLogger
l = getLogger("main")


class ReactionRoles(commands.Cog, description="Reaction Roles"):
    def __init__(self, bot):
        self.bot = bot
    @commands.command(name="rolereactionmessage", hidden=True)
    @commands.has_role("Administrator")
    async def rolereactionmessage(self, ctx: discor d.ext.commands.Context):
        l.debug(f"Role reaction message created by {ctx.author.id} in channel {ctx.channel.id} - {ctx.message.jump_url}")
        with open('data/rolereaction.json', 'r+', encoding='utf8') as f:
            rolereaction = json.load(f)
        embed=discord.Embed(title=rolereaction['messageTitle'], color=discord.Color.red(), description="")
        for emoji in rolereaction['emojiRoleMap'].keys():
            embed.description += emoji + " " + rolereaction['emojiRoleMap'][emoji][1] + "\n"
        msg = await self.bot.get_channel(rolereaction['channelId']).send(embed=embed)
        for emoji in rolereaction['emojiRoleMap'].keys():
            await msg.add_reaction(emoji)
        rolereaction['messageId'] = msg.id
        with open('data/rolereaction.json', 'w', encoding='utf8') as f:
            json.dump(rolereaction, f, indent=4)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        f = open('data/rolereaction.json', 'r', encoding='utf8') 
        rolereaction = json.load(f)
        reactionmessage = rolereaction['messageId']
        if reaction.message.id != reactionmessage:
            l.debug(f"Message id is {reaction.message.id}, needed message id is {reactionmessage}; role not added")
            f.close()
            return
        l.debug(f"Role reaction messages reacted to by {user.id} with {reaction.emoji}")
        if reaction.emoji in rolereaction['emojiRoleMap'].keys():
            roleid = rolereaction['emojiRoleMap'][reaction.emoji][0]
            role = reaction.message.guild.get_role(roleid)
            await user.add_roles(role)
        f.close()
    
    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        f = open('data/rolereaction.json', 'rb', encoding='utf8') 
        rolereaction = json.load(f)
        reactionmessage = rolereaction['messageId']
        if reaction.message.id != reactionmessage:
            l.debug(f"Message id is {reaction.message.id}, needed message id is {reactionmessage}; role not removed")
            f.close()
            return
        l.debug(f"Role reaction removed by {user.id} with {reaction.emoji}")
        if reaction.emoji in rolereaction['emojiRoleMap'].keys():
            roleid = rolereaction['emojiRoleMap'][reaction.emoji][0]
            role = reaction.message.guild.get_role(roleid)
            await user.remove_roles(role)
        f.close()

def setup(bot: commands.Bot):
    bot.add_cog(ReactionRoles(bot))
