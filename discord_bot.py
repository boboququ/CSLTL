"""Discord bindings for TangyBot."""

import asyncio
import os

import discord

from backend import TangyBotBackend, TangyBotError
from cli import TangyBotArgParse, ArgumentParserError
from frontend import FrontendFormatter

CLIENT_ID = ""


class TangyBotClient(discord.Client):
    """
    Custom client subclass for TangyBot.

    Adds support for argparse, allowing TangyBot to be used like any CLI tool.

    Attributes
    ----------
    the_tangy: TangyBotBackend
        The actual backend for the discord bot

    arg_parse: TangyBotArgParse
        Argument parsing for the bot

    frontend_format: FrontendFormatter
        The formatter to use to make the response pretty

    """

    def __init__(self):
        super(TangyBotClient, self).__init__()
        self.the_tangy = TangyBotBackend(self.http.session)
        self.arg_parse = TangyBotArgParse()
        self.frontend_format = FrontendFormatter()

    async def on_ready(self):
        print("Tangy Bot Start")
        await self.change_presence(game=discord.Game(name="Secret Strats"))

    async def on_message(self, message):
        print(message.content)
        print(message.author)
        if message.author == self.user:
            return
        await self.send_typing(message.channel)
        if message.content == "TangyBot":
            await self.send_message(message.channel, "Present")
        elif message.content == "BoBot":
            await self.send_message(message.channel, "NANI")
        if message.content.startswith("<@" + CLIENT_ID):
            print("tagged")
            start_location = message.content.find('>')
            read_message = message.content[start_location + 2:]
            read_command = read_message.split(" ")
            print(read_command)

            try:
                res = self.arg_parse.parse_args(read_command)
                api_resp = await self.the_tangy.command_dispatch(res,
                                                                 message.author)
                strings = self.frontend_format.dispatch(res.command, api_resp)

                # write_tasks = (self.send_message(message.channel, string)
                #                for string in strings)
                # await asyncio.gather(*write_tasks)

                # Need to be written in order...
                for string in strings:
                    await self.send_message(message.channel, string)

            except ArgumentParserError:
                await self.send_argparse_vals(message.channel)
            except TangyBotError as e:
                await self.send_message(message.channel, "```\n" + str(e) +
                                        "\n```")

    async def send_argparse_vals(self, channel):
        """Send the argparse helper vals to discord."""
        print("Argparse vals are:")
        print(self.arg_parse.get_strings())
        await self.send_message(channel,
                                "```\n" + self.arg_parse.get_strings() +
                                "\n```")


# token from environment variables

client = TangyBotClient()

if __name__ == '__main__':
    discord_token = os.environ.get("DISCORD_TOKEN")
    discord_client_id = os.environ.get("DISCORD_CLIENT_ID")
    print(discord_token)
    print(discord_client_id)
    CLIENT_ID = discord_client_id
    client.run(discord_token)
