"""Steam + OpenDota API Interaction."""
from urllib.error import HTTPError

import aiohttp
import requests

import hero_data

# Mapping of hero information based on hero id
hero_info = hero_data.HeroData()
# Magic number :O
INDIVIDUAL_CONSTANT = 0x0110000100000000


def convert_text_to_32id(steam_id):
    steam_id = steam_id[6:]
    # print(steam_id)
    steam_id = steam_id.split(":")
    instance = int(steam_id[1])
    account_number = int(steam_id[2]) * 2 + instance + INDIVIDUAL_CONSTANT
    return account_number - 76561197960265728


def get_account_info_sync(id_32):
    """
    Synchronously get account details with requests.

    Parameters
    ----------
    id_32: int
        The Steam32 ID of a player

    Returns
    -------
    player_resp: dict
        Dict containing player information

    """
    api = "https://api.opendota.com/api/players/" + str(id_32)
    req = requests.get(api)
    if req.status_code != 200:
        raise HTTPError(url=api, code=req.status_code, hdrs=[], fp=None,
                        msg="bad call to api in get_account_info_sync")
    else:
        return req.json()


async def get_account_info_async(session, id_32):
    """
    Asynchronously get account details with aiohttp.

    Parameters
    ----------
    session: aiohttp.ClientSession
        Client session to manage outgoing requests

    id_32: int
        The Steam32 ID of a player

    Returns
    -------
    player_resp: dict
        Dict containing player information

    """
    api = "https://api.opendota.com/api/players/" + str(id_32)
    async with session.get(api) as req:
        if req.status != 200:
            raise HTTPError(url=api, code=req.status, hdrs=[], fp=None,
                            msg="bad call to api in get_account_info_async")
        else:
            return await req.json()


def get_account_heroes_sync(id_32, matches_limit=100, num_heroes=5,
                            min_games=0, lobby_only=False):
    """
    Synchronously get the most played heroes for this player with requests.

    For more information about the API endpoint used here, see the docs at:
    https://docs.opendota.com/#tag/players%2Fpaths%2F~1players~1%7Baccount_id%7D~1heroes%2Fget

    Additionally, we add the following key-value pairs to the dictionary:
        loc_name, containing the hero's English name
        winrate, containing the player's winrate with the hero

    Parameters
    ----------
    id_32: int
        The Steam32 ID of a player

    matches_limit: int (default 100)
        The number of recent matches to consider for this player.

    num_heroes: int (default 5)
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
    api = "https://api.opendota.com/api/players/" + str(id_32) + "/heroes"
    api_params = dict(limit=matches_limit)
    if lobby_only:
        api_params['lobby_type'] = 1
    req = requests.get(api, params=api_params)
    if req.status_code != 200:
        raise HTTPError(url=api, code=req.status_code, hdrs=[], fp=None,
                        msg="bad call to api in get_account_heroes_sync")
    else:
        return get_account_heroes(req.json(), num_heroes, min_games)


async def get_account_heroes_async(session: aiohttp.ClientSession, id_32,
                                   matches_limit=100, num_heroes=5,
                                   min_games=0, lobby_only=False):
    """
    Asynchronously get the most played heroes for this player with aiohttp.

    For more information about the API endpoint used here, see the docs at:
    https://docs.opendota.com/#tag/players%2Fpaths%2F~1players~1%7Baccount_id%7D~1heroes%2Fget

    Additionally, we add the following key-value pairs to the dictionary:
        loc_name, containing the hero's English name
        winrate, containing the player's winrate with the hero

    Parameters
    ----------
    session: aiohttp.ClientSession
        Client session to manage outgoing requests

    id_32: int
        The Steam32 ID of a player

    matches_limit: int (default 100)
        The number of recent matches to consider for this player.

    num_heroes: int (default 5)
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
    api = "https://api.opendota.com/api/players/" + str(id_32) + "/heroes"
    api_params = dict(limit=matches_limit)
    if lobby_only:
        api_params['lobby_type'] = 1
    async with session.get(api, params=api_params) as req:
        if req.status != 200:
            raise HTTPError(url=api, code=req.status, hdrs=[], fp=None,
                            msg="bad call to api in get_account_heroes_async")
        else:
            return get_account_heroes(await req.json(), num_heroes, min_games)


def get_account_heroes(json, num_heroes=5, min_games=0):
    """
        Process the account's most played heroes from OpenDota.

        For more information about the API endpoint used here, see the docs at:
        https://docs.opendota.com/#tag/players%2Fpaths%2F~1players~1%7Baccount_id%7D~1heroes%2Fget

        Additionally, we add the following key-value pairs to the dictionary:
            loc_name, containing the hero's English name
            winrate, containing the player's winrate with the hero

        Parameters
        ----------
        json: dict
            JSON dict response from OpenDota API endpoint.

        num_heroes: int (default 5)
            The maximum number of most played heroes to display.

        min_games: int (default 0)
            The minimum number of games on a hero to display.

        Returns
        -------
        played_heroes: list of dicts
            The list of num_heroes heroes that the player has played the most.

        """
    for hero_dict in json:
        hero_dict['loc_name'] = hero_info[hero_dict['hero_id']]['loc_name']
        try:
            hero_dict['winrate'] = hero_dict['win'] / hero_dict['games']
        except ZeroDivisionError:
            # This will definitely happen for unplayed heroes
            hero_dict['winrate'] = 0.0
    return sorted([item for item in json if item['games'] >= min_games],
                  key=lambda item: item['games'],
                  reverse=True)[:num_heroes]


if __name__ == '__main__':
    steam_id = "STEAM_0:1:51900704"
    steam_32 = convert_text_to_32id(steam_id)
    print(steam_32)
    account_info = get_account_info_sync(steam_32)
    account_matches = get_account_heroes_sync(steam_32)
    print(account_info)
    print(account_matches)
