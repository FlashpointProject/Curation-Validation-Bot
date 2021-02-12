import os
import shutil
import json
import re
from typing import List

import py7zr
import discord
import yaml
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
            props: dict = {}
            if not logo:
                reply += "No logo!\n"
            if not ss:
                reply += "No screenshot!\n"
            try:
                with open(meta[0]) as stream:
                    try:
                        props: dict = yaml.safe_load(stream)
                    except yaml.YAMLError:  # If this is being called, it's a meta .txt
                        break_index: int = 0
                        while break_index != -1:
                            props, break_index = parse_lines_until_multiline(stream.readlines(), props,
                                                                             break_index)
                            props, break_index = parse_multiline(stream.readlines(), props, break_index)
                    print(props)
                    title: tuple[str, bool] = ("Title", none_checker(props["Title"]))
                    # developer: tuple[str, bool] = ("Developer", none_checker(props["Developer"]))
                    release_date: tuple[str, bool] = ("Release Date", none_checker(props["Release Date"]))
                    if release_date[1]:
                        date_string = props["Release Date"]
                        regex = re.compile("[A-Za-z]")
                        if regex.match(date_string):
                            reply += "Release date contains letters. Release dates should always be in YYYY-MM-DD " \
                                     "format.\n"
                    language_properties: tuple[str, bool] = ("Languages", none_checker(props["Languages"]))
                    if language_properties[1]:
                        with open("language-codes.json") as f:
                            list_of_language_codes: list[dict] = json.load(f)
                            print(type(list_of_language_codes[0]))
                            language_str: str = props["Languages"]
                            languages = language_str.split(";")
                            languages = [x.strip(' ') for x in languages]
                            language_codes = []
                            for x in list_of_language_codes:
                                language_codes.append(x["alpha2"])
                            for language in languages:
                                if language not in language_codes:
                                    if language is "sp":
                                        reply += "The correct ISO 639-1 language code for Spanish is es, not sp.\n"
                                    elif language is "ge":
                                        reply += "The correct ISO 639-1 language code for German is de, not ge.\n"
                                    elif language is "jp":
                                        reply += "The correct ISO 639-1 language code for Japanese is ja, not jp.\n"
                                    elif language is "kr":
                                        reply += "The correct ISO 639-1 language code for Korean is ko, not kr.\n"
                                    elif language is "ch":
                                        reply += "The correct ISO 639-1 language code for Chinese is zh, not ch.\n"
                                    elif language is "iw":
                                        reply += "The correct ISO 639-1 language code for Hebrew is he, not iw.\n"
                                    elif language is "cz":
                                        reply += "The correct ISO 639-1 language code for Czech is cs, not cz.\n"
                                    elif language is "pe":
                                        reply += "The correct ISO 639-1 language code for Farsi is fa, not pe.\n"
                                    else:
                                        reply += language + " is not a valid ISO 639-1 language code.\n"
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
                    mandatory_props: list[tuple[str, bool]] = [title, language_properties, source, launch_command, tag,
                                                               status,
                                                               application_path]
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
                # reply_channel = client.get_channel(curator_lounge)
                # reply_channel.send(reply)
    except IndexError:
        pass


def parse_lines_until_multiline(lines: List[str], d: dict, starting_number: int):
    break_number: int = -1
    for idx, line in enumerate(lines[starting_number:]):
        if '|' not in line:
            split: List[str] = line.split(":")
            split: List[str] = [x.strip(' ') for x in split]
            d.update({split[0]: split[1]})
        else:
            break_number = idx
            break
    return d, break_number


def parse_multiline(lines: List[str], d: dict, starting_number: int):
    break_number = -1
    key: str = ""
    val: str = ""
    for idx, line in enumerate(lines[starting_number:]):
        if idx is starting_number:
            split = line.split(':')
            split = [x.strip(' ') for x in split]
            key = split[0]
        else:
            if line.startswith('\t'):
                line = line.strip(" \t")
                val += line
            else:
                break_number = idx
                break
    d.update({key: val})
    return d, break_number


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
