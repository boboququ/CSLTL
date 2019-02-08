"""Main TangyBot backend logic."""

import asyncio

import boto3
from bs4 import BeautifulSoup

import hero_data
import util
from api_dispatch import *


def extract_id_user(players):
    """Extract player steam ID and other info from the CSL website."""
    player_dict = {}
    for player in players:
        player = str(player)
        split = player.find("href=\"")

        steam_id = player[:split]
        steam_id = steam_id[steam_id.find("ID") + 4:steam_id[1:].find("<") - 2]

        user_name = player[split + 1:]
        user_name = user_name[user_name.find(">") + 1:user_name.find("<")]

        steam_id = convert_text_to_32id(steam_id)

        player_dict[steam_id] = dict(csl_name=user_name)
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


# Mapping of resource to primary key values on aws
RESOURCE_KEY_NAMES = dict(session="username", profile="steamid")


class PersistentData:
    """
    Persistent information for TangyBot that must survive restarts.

    This information includes session data and player profile information.

    The backend chosen for storing the persistent information can be
    configured; the following backends are currently supported:
        "file"  gzipped pickled file
        "aws"   aws dynamodb + boto3 wrapper

    Attributes
    ----------
    backend: str
        The backend to use for storing the data

    session_data: dict
        The data for user sessions, at least until it overruns memory

    profile_data: dict
        The data for player profiles, at least until it overruns memory

    AWS Exclusive Attributes
    ------------------------
    dynamodb: DynamoDB resource
        The dynamoDB instance
        Only exists if backend is set to aws

    session_table: DynamoDB Table
        The dynamodb table holding user session information

    profile_table: DynamoDB Table
        The dynamodb table holding user profile information

    """

    def __init__(self, backend="file"):
        self.backend = backend
        if backend == "aws":
            self.dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
            self.session_table = self.dynamodb.Table("TangyBot_Session")
            self.profile_table = self.dynamodb.Table("TangyBot_Profile")
        elif backend == "file":
            pass
        else:
            raise ValueError("Backend must be either aws or file")
        self.profile_data = self._load('profile')
        self.session_data = self._load('session')

    def _load(self, resource):
        """
        Load the requested resource from source.

        Valid resources are:
            "profile"   player profiles
            "session"   user sessions

        Parameters
        ----------
        resource: str
            The resource requested to be loaded

        """
        if self.backend == "aws":
            table = getattr(self, resource + "_table")
            return_dict = {}
            for item in table.scan()['Items']:
                # Even though numeric keys have the weird type Decimal('123')
                # they still compare fine when we try to access their values
                key = item.pop(RESOURCE_KEY_NAMES[resource])
                return_dict[key] = item
            return return_dict
        elif self.backend == "file":
            try:
                return util.load(resource + '.pkl.gzip')
            except FileNotFoundError:
                return {}
        else:
            raise ValueError("Backend must be either aws or file")

    def update(self, resource, resource_key, dict_key, new_val):
        """
        Update the key-value pair of resource.

        Valid resources are:
            "profile"   player profiles
            "session"   user sessions

        Parameters
        ----------
        resource: str
            The resource requested to be loaded

        resource_key: any
            The key to the resource dict

        dict_key: any
            The key to the item in the dict

        new_val: any
            The new value to associate it with

        """
        target = getattr(self, resource + "_data")
        if resource_key not in target:
            target[resource_key] = {}
        target[resource_key][dict_key] = new_val

        # Update persistent storage
        if self.backend == "aws":
            # AWS wants the data in this format lol
            aws_dict = target[resource_key].copy()
            aws_dict[RESOURCE_KEY_NAMES[resource]] = resource_key

            table = getattr(self, resource + "_table")
            table.put_item(Item=aws_dict)
        elif self.backend == "file":
            util.save(target, resource + '.pkl.gzip')
        else:
            raise ValueError("Backend must be either aws or file")


class TangyBotBackend:
    """
    Real backend for TangyBot.

    We consider this the backend because it handles the heavy lifting that
    TangyBot needs to perform for its different tasks. This creates a layer
    of abstraction between the bot's lookup actions and its discord
    "frontend" responses, for example. As a result, we can optionally expand
    this later on to incorporate different frontends, such as a REST API.

    As a result, we only respond with Python objects. Different frontends will
    have to manipulate the objects we respond with to display them as desired.

    We also introduce the idea of an (unencrypted) "session" for each player,
    which holds their most recent team and player lookup, as well as
    potentially other fields if we so wish to expand them.

    All of the commands that TangyBot can use asynchronous in nature,
    as this allows more flexibility and "concurrency" in our implementation.
    The returned values are still returned synchronously, though, so there's
    only speedup if the APIs we are querying are slow (i.e. OpenDota with
    more specific parameters), so an asynchronous querying is more akin to
    multiple synchronous threads querying the endpoint concurrently.

    Attributes
    ----------
    persist: PersistentData
        The persistent data storage to use

    session: Asynchronous request maker, or None
        The ClientSession to use in TangyBot
        If None, uses our own session, but please close it when needed

    hero_info: HeroData
        The hero information store (i.e. localized name)

    """

    def __init__(self, backend="file", session=None):
        """
        Construct TangyBot's backend

        Parameters
        ----------
        backend: str
            The backend to use for persistent storage

        session: Asynchronous request maker, or None
            The ClientSession to use in TangyBot
            If None, create a new session, but please close it when needed

        """
        self.persist = PersistentData(backend)
        self.session = session or aiohttp.ClientSession()
        self.hero_info = hero_data.HeroData()

    # TODO stolen from discord client. Is this needed?
    async def close(self):
        """Close the session on cleanup."""
        if not self.session.closed:
            await self.session.close()

    async def dispatch(self, args, username="user"):
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
        if username not in self.persist.session_data:
            self.persist.session_data[username] = dict(last_team=None,
                                                       last_players=None)

        try:
            func_to_call = getattr(self, args.command)
        except AttributeError:
            raise TangyBotError("Unknown command " + args.command +
                                " in command dispatch!")
        # Splatter and pass username as kwargs
        # Looks like the call site will have to have their own
        # **_ kwargs declaration to eat up the unused kwargs...
        res = await func_to_call(username=username, **vars(args))
        return res

    async def lookup(self, last, team_number, username="user", **_):
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
            Dictionary with lookup results. The specific format is:

            team_name: str, the university's name

            players: dict, steam 32 id -> dict of values
                The dict of values is mostly in the OpenDota API response
                format, but also includes steam_name and csl_name if they exist

        """
        # Check args for validity first
        if last and not team_number:
            # Check for last team number
            try:
                last_team = self.persist.session_data[username]['last_team']
            except KeyError:
                raise TangyBotError("Lookup: " + username + " has no last "
                                                            "team to use")
            if last_team is None:
                raise TangyBotError("Lookup: " + username + " has no last "
                                                            "team to use")
            return await self._lookup(last_team, username)
        elif team_number and not last:
            self.persist.update('session', username, 'last_team',
                                team_number)
            return await self._lookup(team_number, username)
        else:
            raise TangyBotError("Lookup: must specify either last or "
                                "team_number, but got neither!")

    async def _lookup(self, team_id, username):
        """Internal lookup implementation."""
        url = "https://cstarleague.com/dota2/teams/" + str(team_id)
        print("Looking up URL " + url)
        # Pepega
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/39.0.2171.95 Safari/537.36'
        }

        try:
            async with self.session.get(url, headers=headers) as req:
                content = await req.text()
            soup = BeautifulSoup(content, 'lxml')

            team_name_div = soup.findAll("div", {"class": "hero-title"})
            team_name = extract_team_id(team_name_div)

            players = soup.findAll("span", {"class": "tool-tip"})

            # Maps steam 32 id to names
            player_dict = extract_id_user(players)

            steam_ids = list(player_dict.keys())

            self.persist.update('session', username, 'last_players',
                                steam_ids)

            # Update CSL names
            for steam_id, data in player_dict.items():
                self.persist.update('profile', steam_id,
                                    'csl_name', data['csl_name'])

            tasks = (get_account_info_async(self.session, id) for id in
                     steam_ids)

            return_dict = dict(zip(steam_ids,
                                   await asyncio.gather(*tasks)))

            # Update steam names
            for prof, res in return_dict.items():
                try:
                    self.persist.update('profile', prof, 'steam_name',
                                        res['profile']['personaname'])
                except KeyError:
                    self.persist.update('profile', prof, 'steam_name',
                                        'INVALID?')

            # Merge in known profile information
            merged_dict = {}
            for key in player_dict:
                merged_dict[key] = {**self.persist.profile_data[key],
                                    **return_dict[key]}

            return dict(team_name=team_name,
                        players=merged_dict)
        except HTTPError as err:
            raise TangyBotError("_lookup: " + err.msg)

    async def profile(self, last, profiles, num_games, max_heroes,
                      min_games, tourney_only, username="user", **_):
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

        Returns
        -------
        data: dict
            Dictionary with profile results. The specific format is:

            players: dict, steam 32 id -> dict of values
                Each dict contains csl_name and steam_name, as well as a
                list of heroes in the OpenDota API heroes response format

        """
        # Check args for validity first
        if last and not profiles:
            # Check for last team number
            try:
                last_players = self.persist.session_data[username][
                    'last_players']
            except KeyError:
                raise TangyBotError("Profile: user has no last players to use")
            except AttributeError:
                raise TangyBotError("Profile: user has no last players to use")
            return await self._profile(last_players, num_games, max_heroes,
                                       min_games, tourney_only)
        elif profiles and not last:
            self.persist.update('session', username, 'last_players',
                                profiles)
            return await self._profile(profiles, num_games, max_heroes,
                                       min_games, tourney_only)
        else:
            raise TangyBotError("Profile: must specify either last or "
                                "profile list, but got neither!")

    async def _profile(self, profiles, num_games, max_heroes,
                       min_games, tourney_only):
        """Internal profile implementation."""
        # Fill missing dict items if needed
        await self._fill_missing_accounts([prof for prof in profiles if prof
                                           not in self.persist.profile_data])

        # Resume normal tasks
        tasks = (self._get_account_heroes(profile, num_games, max_heroes,
                                          min_games, tourney_only) for
                 profile in profiles)
        return_dict = dict(zip(profiles, await asyncio.gather(*tasks)))

        # Merge in known profile information
        merged_dict = {}
        for key in return_dict:
            merged_dict[key] = {**self.persist.profile_data[key],
                                'heroes': return_dict[key]}

        return dict(players=merged_dict)

    async def _fill_missing_accounts(self, missing_profiles):
        """Fill in account information about missing profiles."""
        tasks = (get_account_info_async(self.session, id) for
                 id in missing_profiles)
        results = await asyncio.gather(*tasks)

        for prof, res in zip(missing_profiles, results):
            try:
                self.persist.update('profile', prof, 'steam_name',
                                    res['profile']['personaname'])
            except KeyError:
                self.persist.update('profile', prof, 'steam_name', 'INVALID??')

    async def _get_account_heroes(self, id_32, num_games, max_heroes=5,
                                  min_games=0, tourney_only=False):
        """
        Process the account's most played heroes from OpenDota.

        For more information about the API endpoint used here, see the docs at:
        https://docs.opendota.com/#tag/players%2Fpaths%2F~1players~1%7Baccount_id%7D~1heroes%2Fget

        Additionally, we add the following key-value pairs to the dictionary:
            loc_name, containing the hero's English name
            winrate, containing the player's winrate with the hero

        Parameters
        ----------
        id_32: int
        The Steam32 ID of a player

        num_games: int (default 100)
            The number of recent matches to consider for this player.

        max_heroes: int (default 5)
            The maximum number of most played heroes to display.

        min_games: int (default 0)
            The minimum number of games on a hero to display.

        lobby_only: bool (default False)
            Limit match results to lobby matches only?

        Returns
        -------
        played_heroes: list of dicts
            The list of num_heroes heroes that the player has played the most.

        """
        resp = await get_account_heroes_async(self.session, id_32,
                                              num_games, tourney_only)
        for hero_dict in resp:
            hero_dict['loc_name'] = self.hero_info[hero_dict['hero_id']][
                'loc_name']
            try:
                hero_dict['winrate'] = hero_dict['win'] / hero_dict['games']
            except ZeroDivisionError:
                # This will definitely happen for unplayed heroes
                hero_dict['winrate'] = 0.0
        return sorted([item for item in resp if item['games'] >= min_games],
                      key=lambda item: item['games'],
                      reverse=True)[:max_heroes]

    async def stalk(self, users, username="user", **_):
        """
        Get the session information for the following users.

        Parameters
        ----------
        users: list
            List of all usernames to get information about
            If empty, get information about username

        username: str or None
            The username to use a session
            If None, use the default session

        Raises
        ------
        TangyBotError
            On a lookup error, i.e. user was not found

        Returns
        -------
        data: dict
            Dictionary with session results. Specifically, the format is:

            users: dict, username -> dict of values
                Each dict contains last_team and last_players, or None if
                no applicable previous query is on record

        """
        # Blank check
        try:
            if users:
                return_dict = {}
                for username in users:
                    return_dict[username] = self.persist.session_data[username]
                return dict(users=return_dict)
            else:
                return dict(users={username: self.persist.session_data[
                                           username]})
        except KeyError as err:
            raise TangyBotError("Session data not found for user " +
                                str(err.args[0]))


async def main(team):
    """Main CLI for testing."""
    async with aiohttp.ClientSession() as session:
        the_tangy = TangyBotBackend(session=session)
        return await the_tangy.lookup(False, team)


if __name__ == "__main__":
    # michigan
    mich_url = 839

    loop = asyncio.get_event_loop()
    tangy_res = loop.run_until_complete(main(mich_url))
    print(tangy_res)
