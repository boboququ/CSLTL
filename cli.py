"""
Command Line Interface for team lookups.

Commands are invoked in CLI in the classic $ python3 cli.py etc.

Supported Subcommands
---------------------
lookup ([--last] | <team_number>)
    Look up a team based on CSL team number, or redo the previous lookup.
    Team Number can optionally also be a URL.

    This command gives a short summary of the players in the team,
    and also stores them so a call with --last will work also.

profile ([--last] | [user_1, user_2, ...]) [--num_games (100)]
        [--max_heroes (5)] [--min_games (5)] [--tourney_only]
    Generates a more detailed profile for the listed players.
    If the last option is specified, profiles are created for all
    players that were in the command; user_i will be considered an error.
    Otherwise, user_i is a steam 32 ID, and multiple can be specified.

    The num_games parameter is the max number of games they've recently
    played to look back at. The default is 100.

    The min_games parameter is the minimum number of games on a hero
    required to be returned.
    The max_heroes parameter is the max number of most played heroes to
    be returned.

    The tourney only flag limits the results to tournament lobbies only.

stalk [user_1, user_2, ...]
    Reports the current session variables for given users.
    If no usernames are given, return those of the caller.

"""

import argparse
import asyncio
import io

import aiohttp

from backend import TangyBotBackend


class ArgumentParserError(Exception):
    """Basic Argument Parsing Error to differentiate from other Exceptions."""
    pass


class BufferThrowingArgParser(argparse.ArgumentParser):
    """
    ArgParser implementation that throws and prints to buffer.

    We need this throwing behavior here, because we are definitely NOT going
    to be printing any feedback to sys.stderr since only Bo can see that,
    and only if he really wants to.

    By throwing an error, we can catch it in TangyBot, and instead of calling
    exit and printing to stderr, we can instead print to an internal buffer,
    which we can access from external sources such as discord.

    Attributes
    ----------
    buffer: StringIO
        Contains the printed output from an invocation of argument parsing

    """

    def __init__(self, **kwargs):
        super(BufferThrowingArgParser, self).__init__(**kwargs)
        self.buffer = io.StringIO()

    def parse_args(self, args=None, namespace=None):
        # Need to reset buffer on every invocation
        # self.buffer = io.StringIO()
        # For now, it appears that the subparsers do not get this called...
        # So, we need to reset at the call site
        # Then delegate parse args to base class
        return super(BufferThrowingArgParser, self).parse_args(args, namespace)

    def get_buffer_val(self):
        """Return the string currently in this parsers' buffer."""
        return self.buffer.getvalue()

    def get_buffer_val_reset(self):
        """Return the string currently in this parser's buffer and reset it."""
        res = self.buffer.getvalue()
        self.buffer = io.StringIO()
        return res

    # We're revisionists, so we need to override a whole lot of stuff here...

    def print_usage(self, file=None):
        if file is None:
            file = self.buffer
        self._print_message(self.format_usage(), file)

    def print_help(self, file=None):
        if file is None:
            file = self.buffer
        self._print_message(self.format_help(), file)

    def _print_message(self, message, file=None):
        if message:
            if file is None:
                file = self.buffer
            file.write(message)

    def exit(self, status=0, message=None):
        if message:
            self._print_message(message, self.buffer)
        raise ArgumentParserError(message)

    def error(self, message):
        self.print_usage(self.buffer)
        raise ArgumentParserError(message)


class TangyBotArgParse:
    """Argument Parsing Implementation for TangyBot."""

    def __init__(self):
        self.arg_parser = BufferThrowingArgParser(prog="TangyBot",
                                                  description="CSL Team "
                                                              "Lookup")
        self.subparsers = self.arg_parser.add_subparsers()

        self.lookup_parser = self.subparsers.add_parser("lookup",
                                                        help="Look up a team")
        self.lookup_parser.set_defaults(command='lookup')
        self.lookup_group = self.lookup_parser.add_mutually_exclusive_group(
            required=True)

        self.lookup_group.add_argument('team_number', nargs="?", default="",
                                       help="The CSL team number or url to "
                                            "look up")
        self.lookup_group.add_argument("-l", "--last", action="store_true",
                                       help="Use the last team that was "
                                            "looked up by you")

        self.profile_parser = self.subparsers.add_parser("profile",
                                                         help="Get detailed "
                                                              "profiles")
        self.profile_parser.set_defaults(command='profile')

        # Whether to use --last or a list of profiles
        self.profile_group = self.profile_parser.add_mutually_exclusive_group(
            required=True)
        self.profile_group.add_argument("-l", "--last", action="store_true",
                                        help="Use the last players that were "
                                             "looked up by you")
        self.profile_group.add_argument("profiles", nargs="*", default=[],
                                        type=int,
                                        help="List of Steam32IDs of players")

        # Filtering options
        self.profile_filter = self.profile_parser.add_argument_group(
            'filtering',
            'Game '
            'filtering options')

        self.profile_filter.add_argument("-m", "--max_heroes", type=int,
                                         default=5,
                                         help="Report at most the top n "
                                              "heroes played")
        self.profile_filter.add_argument("-g", "--min_games", type=int,
                                         default=5,
                                         help="Report all heroes with at "
                                              "least this many games played.")

        self.profile_filter.add_argument("-n", "--num_games", type=int,
                                         default=100,
                                         help="The previous number of games "
                                              "to consider.")

        # Lobby only
        self.profile_parser.add_argument("-t", "--tourney_only",
                                         action='store_true',
                                         help="Set if only lobby games are "
                                              "desired")

        # Session information
        self.stalk_parser = self.subparsers.add_parser("stalk",
                                                       help="Access "
                                                            "session "
                                                            "information")
        self.stalk_parser.set_defaults(command="stalk")

        self.stalk_parser.add_argument("users", nargs="*",
                                       help="User names to get session "
                                            "information of")

        self.parser_list = [self.arg_parser, self.lookup_parser,
                            self.profile_parser, self.stalk_parser]

    def parse_args(self, args=None, namespace=None):
        """Parse arguments using argparse."""
        # Rest buffers first
        self.reset_buffers()
        return self.arg_parser.parse_args(args, namespace)

    def get_strings(self):
        """Get the strings from the argparsers."""
        return "".join(parser.get_buffer_val() for parser in self.parser_list)

    def get_strings_reset(self):
        """Get the strings from the argparsers and reset the buffers."""
        return "".join(
            parser.get_buffer_val_reset() for parser in self.parser_list)

    def reset_buffers(self):
        """Reset the buffers of all argparsers."""
        for parser in self.parser_list:
            parser.buffer = io.StringIO()


arg_parse = TangyBotArgParse()


async def main(args):
    """Main CLI for testing."""
    async with aiohttp.ClientSession() as session:
        the_tangy = TangyBotBackend(session=session)
        return await the_tangy.dispatch(args)


# Debugging main; enter your args however you want :^)
if __name__ == "__main__":
    try:
        res = arg_parse.parse_args()
        print(res)
        print(res.command)
        loop = asyncio.get_event_loop()
        tangy_res = loop.run_until_complete(main(res))
        print(tangy_res)
    except ArgumentParserError:
        print("oops")
    print("BUFFER IS")
    print(arg_parse.arg_parser.get_buffer_val())
    print("LOOKUP BUFFER IS")
    print(arg_parse.lookup_parser.get_buffer_val())
    print("PROFILE BUFFER IS")
    print(arg_parse.profile_parser.get_buffer_val())
    print("END")
