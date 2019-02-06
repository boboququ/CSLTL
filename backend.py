"""Main TangyBot backend logic."""

import asyncio

from bs4 import BeautifulSoup

import util
from api_dispatch import *


def extract_id_user(players):
    """Extract player steam ID and other info from the CSL website."""
    player_dict = {}
    for player in players:
        player = str(player)
        # print(player)
        split = player.find("href=\"")

        steam_id = player[:split]
        steam_id = steam_id[
                   steam_id.find("ID") + 4: steam_id[1:].find("<") - 2]

        user_name = player[split + 1:]
        user_name = user_name[user_name.find(">") + 1:user_name.find("<")]

        steam_id = convert_text_to_32id(steam_id)

        # print("steamid is" , steam_id)
        # print("username is", user_name)
        # TODO write dotabuff to file maybe
        dotabuff_link = "https://dotabuff.com/players/" + str(steam_id)
        opendota_link = "https://www.opendota.com/players/" + str(steam_id)
        # print("Dota Buff is ", dotabuff_link)
        # print("Open Dota is ", opendota_link)
        player_dict[user_name] = dict(steam_id=steam_id,
                                      dotabuff_link=dotabuff_link,
                                      opendota_link=opendota_link)
    return player_dict


def extract_team_id(team_banner_div):
    """Extract the team ID from HTML."""
    # TODO: Don't do this with brute force
    team_banner_div = str(team_banner_div[0])
    team_banner_div = team_banner_div[
                      team_banner_div.find("h3") + 3:team_banner_div.find(
                          "</h3>")]
    team_banner_div = team_banner_div[
                      team_banner_div.find(">") + 1:team_banner_div.find(
                          "</a>")]
    return team_banner_div


class TangyBotError(Exception):
    """Basic TangyBot Error to differentiate from other Exceptions."""
    pass


class TangyBotSession:
    """Simple wrapper class for TangyBot Sessions."""
    __slots__ = ['last_team', 'last_players']

    def __init__(self, last_team=None, last_players=None):
        self.last_team = last_team
        self.last_players = last_players


USER_SESSION_FILE = "sessions.pkl.gzip"


class TangyBotBackend:
    """
    Real backend for TangyBot.

    We consider this the backend because it handles the heavy lifting that
    TangyBot needs to perform for its different tasks. This creates a layer
    of abstraction between the bot's lookup actions and its discord
    "frontend" responses, for example. As a result, we can optionally expand
    this later on to incorporate different frontends, such as a REST API.

    As a result, we only respond with Python objects. Differents will have
    to manipulate the objects we respond with to display them as desired.

    We also introduce the idea of an (unencrypted) "session" for each player,
    which holds their most recent team and player lookup, as well as
    potentially other fields if we so wish to expand them.

    All of the commands that TangyBot can use asynchronous in nature,
    as this allows more flexibility and "concurrency" in our implementation.

    Attributes
    ----------
    user_sessions: dict, username -> TangyBotSession
        Session information based on some username

    session: Asynchronous request maker, or None
        The ClientSession to use in TangyBot
        If None, create a new session

    """

    def __init__(self, session=None):
        try:
            self.user_sessions = util.load(USER_SESSION_FILE)
        except FileNotFoundError:
            self.user_sessions = {}
        self.session = session or aiohttp.ClientSession()

    # TODO stolen from discord client. Is this needed?
    @asyncio.coroutine
    def close(self):
        yield from self.session.close()

    async def command_dispatch(self, args, username=None):
        """
        Dispatch function for TangyBot to perform actions based on args.

        This function examines the value of args.command to call the
        appropriate function, with the values contained in args. In fact,
        with a bit of reflection, this should be infinitely scalable (as far
        as python allows, anyways), i.e. we won't have to add more cases
        here as we add more commands as long as we program the function
        correctly.

        Please call this function, since it does important bookkeeping too!

        Parameters
        ----------
        args: Namespace
            Arguments for TangyBot to do, i.e. via cli
            At the least, it expects the key 'command' to be present

        username: str or None
            The username to use a session
            If None, use the default session

        Raises
        ------
        TangyBotError
            On a command error, i.e. improper command

        Returns
        -------
        data: dict
            Response data as a Python dict
            See specific functions for more details

        """
        # Set default value
        if username not in self.user_sessions:
            self.user_sessions[username] = TangyBotSession()

        try:
            func_to_call = getattr(self, args.command)
            # Splatter and pass username as kwargs
            res = await func_to_call(username=username, **vars(args))
            util.save(self.user_sessions, USER_SESSION_FILE)
            return res
        # Only handle keyerror here. Propogate other TangyBotErrors
        except KeyError:
            raise TangyBotError("Missing command in command dispatch!")
        except AttributeError:
            raise TangyBotError("Unknown command " + args.command +
                                " in command dispatch!")

    async def lookup(self, last, team_number, username=None, **_):
        """
        Perform a team lookup based on passed in arguments.

        Parameters
        ----------
        last: bool
            Whether to repeat last team lookup

        team_number: int or str
            Team number or URL to lookup

        username: str or None
            The username to use a session
            If None, use the default session

        kwargs: dict
            kwargs so they get ignored

        Raises
        ------
        TangyBotError
            On a lookup error, i.e. team was not found

        Returns
        -------
        data: dict

        """
        # Check args for validity first
        if last and not team_number:
            # Check for last team number
            try:
                last_team = self.user_sessions[username].last_team
            except KeyError:
                raise TangyBotError("Lookup: user has no last team to use")
            if last_team is None:
                raise TangyBotError("Lookup: user has no last team to use")
            return await self._lookup(last_team, username)
        elif team_number and not last:
            self.user_sessions[username].last_team = team_number
            return await self._lookup(team_number, username)
        else:
            raise TangyBotError("Lookup: must specify either last or "
                                "team_number, but got neither!")

    async def _lookup(self, team_id, username):
        """Internal lookup implementation."""
        url = "https://cstarleague.com/dota2/teams/" + str(team_id)
        print("Looking up URL " + url)
        # Pepega (KHTML, like Gecko)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

        try:
            # TODO wonder if we can replace this part with aiohttp
            async with self.session.get(url, headers=headers) as req:
                content = await req.text()
            soup = BeautifulSoup(content, 'lxml')

            team_name_div = soup.findAll("div", {"class": "hero-title"})
            team_name = extract_team_id(team_name_div)

            players = soup.findAll("span", {"class": "tool-tip"})

            player_dict = extract_id_user(players)

            steam_ids = {}
            for player, item in player_dict.items():
                steam_ids[player] = item['steam_id']

            self.user_sessions[username].last_players = steam_ids

            steam_ids = [player['steam_id'] for _, player
                         in player_dict.items()]

            tasks = (get_account_info_async(self.session, id) for id in
                     steam_ids)

            return_dict = dict(zip(player_dict.keys(),
                                   await asyncio.gather(*tasks)))

            merged_dict = {}
            for key in player_dict:
                merged_dict[key] = {**player_dict[key], **return_dict[key]}

            return dict(team_name=team_name,
                        players=merged_dict)
        except HTTPError as e:
            raise TangyBotError("_lookup: " + e.msg)

    async def profile(self, last, profiles, num_games, games_n,
                      top_n, tourney_only, username=None, **_):
        """
        Perform a player profile based on passed in arguments.

        Parameters
        ----------
        last: bool
            Whether to repeat last team lookup

        profiles: list of ints
            List of player IDs to profile

        num_games: int
            Number of games to look back

        games_n: int
            Minimum number of games played to be included

        top_n: int
            Maximum number of heroes to be included

        tourney_only: bool
            Whether to filter to only tournament games

        username: str or None
            The username to use a session
            If None, use the default session

        kwargs: dict
            kwargs so they get ignored

        Raises
        ------
        TangyBotError
            On a lookup error, i.e. team was not found

        """
        # Check args for validity first
        if last and not profiles:
            # Check for last team number
            try:
                last_players = self.user_sessions[username].last_players
                last_players = [id for _, id in last_players.items()]
            except KeyError:
                raise TangyBotError("Profile: user has no last players to use")
            except AttributeError:
                raise TangyBotError("Profile: user has no last players to use")
            return await self._profile(last_players, num_games, games_n,
                                       top_n, tourney_only, username)
        elif profiles and not last:
            self.user_sessions[username].last_players = profiles
            return await self._profile(profiles, num_games, games_n,
                                       top_n, tourney_only, username)
        else:
            raise TangyBotError("Profile: must specify either last or "
                                "profile list, but got neither!")

    async def _profile(self, profiles, num_games, games_n,
                       top_n, tourney_only, username):
        """Internal profile implementation."""
        names = self.user_sessions[username].last_players
        tasks = (get_account_heroes_async(self.session, profile, num_games,
                                          top_n, games_n, tourney_only) for
                 profile in profiles)
        return_dict = dict(zip(names.keys(), await asyncio.gather(*tasks)))
        return dict(profiles=return_dict)


async def main(team):
    """Main CLI for testing."""
    async with aiohttp.ClientSession() as session:
        the_tangy = TangyBotBackend(session=session)
        return await the_tangy.lookup(False, team)


if __name__ == "__main__":
    # michigan
    url = 839

    loop = asyncio.get_event_loop()
    tangy_res = loop.run_until_complete(main(url))
