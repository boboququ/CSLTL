"""Discord bindings for TangyBot."""

import os
import shlex
import sys

import discord

from backend import TangyBotBackend, TangyBotError
from cli import TangyBotArgParse, ArgumentParserError
from frontend import FrontendFormatter

CLIENT_ID = ""


class TangyBotClient(discord.Client):
    """
    Custom Discord client subclass for TangyBot.

    Adds support for argparse, allowing TangyBot to be used like any CLI tool.

    Then uses its own instance of a TangyBotBackend to perform the actual
    querying, before formatting the strings using the frontend formatter and
    writing the end results to the Discord channel where the query was
    initially received.

    Attributes
    ----------
    the_tangy: TangyBotBackend
        The actual backend for the discord bot

    arg_parse: TangyBotArgParse
        Argument parsing for the bot

    frontend_format: FrontendFormatter
        The formatter to use to make the response pretty

    """

    def __init__(self, backend="file"):
        super(TangyBotClient, self).__init__()
        print("Launching with backend", backend)
        self.the_tangy = TangyBotBackend(backend=backend,
                                         session=self.http.session)
        self.arg_parse = TangyBotArgParse()
        self.frontend_format = FrontendFormatter()

    async def close(self):
        super(TangyBotClient, self).close()
        await self.the_tangy.close()

    async def on_ready(self):
        print("Tangy Bot Start")
        await self.change_presence(game=discord.Game(name="Secret Strats"))

    async def on_message(self, message):
        print(message.content)
        print(message.author)
        if message.author == self.user:
            return

        if message.content == "TangyBot":
            await self.send_message(message.channel, "Present")
        elif message.content == "BoBot":
            await self.send_message(message.channel, "NANI")
        if message.content.startswith("<@!" + CLIENT_ID):
            print("tagged")
            start_location = message.content.find('>')
            read_message = message.content[start_location + 2:]
            read_command = shlex.split(read_message)
            print(read_command)

            await self.send_typing(message.channel)

            try:
                res = self.arg_parse.parse_args(read_command)

                await self.send_message(message.channel, "Received command \""
                                        + res.command + "\" with args " +
                                        str(vars(res)))
                await self.send_typing(message.channel)

                api_resp = await self.the_tangy.dispatch(res,
                                                         str(message.author))
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


if __name__ == '__main__':
    # token from environment variables

    client = TangyBotClient(sys.argv[1] if len(sys.argv) == 2 else "aws")

    discord_token = os.environ.get("DISCORD_TOKEN")
    discord_client_id = os.environ.get("DISCORD_CLIENT_ID")
    print(discord_token)
    print(discord_client_id)

    CLIENT_ID = discord_client_id
    client.run(discord_token)
