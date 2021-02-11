import os
import shutil
from typing import List

import py7zr
import discord
import ruamel.yaml as yaml
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL = os.getenv('CHANNEL')

client = discord.Client()


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    text_channel_list = []
    for guild in client.guilds:
        for channel in guild.text_channels:
            text_channel_list.append(channel)
    print(text_channel_list)


@client.event
async def on_message(message: discord.Message):
    reply: str = ""
    try:
        attachment = message.attachments[0]
        filename: str = attachment.filename
        if filename.endswith('7z'):
            await attachment.save(filename)
            archive = py7zr.SevenZipFile(filename, mode='r')
            names = archive.getnames()
            archive.extractall()
            archive.close()
            meta = [match for match in names if "meta" in match]
            logo = [match for match in names if "logo" in match]
            ss = [match for match in names if "ss" in match]
            if not logo:
                reply += "No logo!\n"
            if not ss:
                reply += "No screenshot!\n"
            try:
                with open(meta[0]) as stream:
                    try:
                        props: dict = yaml.safe_load(stream)
                    except yaml.YAMLError:
                        # text file handling goes here
                        pass
                    print(props)
                    title: tuple[str, bool] = ("Title", none_checker(props["Title"]))
                    # developer: tuple[str, bool] = ("Developer", none_checker(props["Developer"]))
                    # release_date_format: tuple[str, bool] = ("Release Date", none_checker(props["Release Date"]))
                    languages: tuple[str, bool] = ("Languages", none_checker(props["Languages"]))
                    tag: tuple[str, bool] = ("Tags", none_checker(props["Tags"]))
                    source: tuple[str, bool] = ("Source", none_checker(props["Source"]))
                    status: tuple[str, bool] = ("Status", none_checker(props["Status"]))
                    launch_command: tuple[str, bool] = ("Launch Command", none_checker(props["Launch Command"]))
                    application_path: tuple[str, bool] = ("Application Path", none_checker(props["Application Path"]))
                    description: tuple[str, bool] = ("Description", none_checker(props["Original Description"]))
                    if description[1] is False and (
                            none_checker(props["Curation Notes"]) or none_checker(props["Game Notes"])):
                        reply += "Make sure you didn't put your description in the notes section.\n"
                    if "https" in props["Launch Command"]:
                        reply += "https in launch command. All launch commands must use http instead of https.\n"
                    mandatory_props: list[tuple[str, bool]] = [title, languages, source, launch_command, tag, status]
                    # optional_props: list[tuple[str, bool]] = [developer, release_date, tag, description]
                    tags: List[str] = props["Tags"].split(";")
                    tags: List[str] = [x.strip(' ') for x in tags]
                    with open('tags.txt') as file:
                        contents = file.read()
                        for x in tags:
                            if x not in contents:
                                reply += x + " is not a valid tag.\n"
                    if not all(mandatory_props[1]):
                        for x in mandatory_props:
                            if x[1] is False:
                                reply += x[0] + " is missing.\n"
                    # if not all(optional_props[1]):
                    #     for x in optional_props:
                    #         if x[1] is False:
                    #             reply += x[0] + " is missing, but not necessary. Add it if you can find it, but it's okay if you can't.\n"
            except IndexError:
                reply += "Missing meta file! Are you curating using Flashpoint Core?\n"
            os.remove(filename)
            for x in names:
                shutil.rmtree(x, True)
            for x in names:
                try:
                    os.remove(x)
                except OSError:
                    pass
            if reply:
                author: discord.Member = message.author
                reply = author.mention + " Your curation has the following problems:\n" + reply
                # channel = client.get_channel(curator_lounge)
                # channel.send(reply)
    except IndexError:
        pass


def none_checker(prop: str):
    """

    :rtype: bool
    """
    if prop is None:
        not_none = False
    else:
        not_none = True
    return not_none


client.run(TOKEN)
