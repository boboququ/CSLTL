"""Steam + OpenDota API Interaction."""
from urllib.error import HTTPError

import aiohttp
import requests

# Magic number (from steam) :O
INDIVIDUAL_CONSTANT = 0x0110000100000000

# Conversion factor between steam32 ID and account number
CONVERSION_FACTOR = 76561197960265728


def convert_text_to_32id(steam_id):
    """Convert steam ID text to steam 32 ID."""
    steam_id = steam_id[6:]
    # print(steam_id)
    steam_id = steam_id.split(":")
    instance = int(steam_id[1])
    account_number = int(steam_id[2]) * 2 + instance + INDIVIDUAL_CONSTANT
    return account_number - CONVERSION_FACTOR


def convert_32id_to_account(steam_id):
    """Convert steam 32 ID to account number."""
    return steam_id + CONVERSION_FACTOR


def get_account_info_sync(id_32):
    """
    Get account details synchronously with requests.

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
    Get account details asynchronously with aiohttp.

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


def get_account_heroes_sync(id_32, matches_limit=100, lobby_only=False):
    """
    Get the most played heroes for this player synchronously with requests.

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
        return req.json()


async def get_account_heroes_async(session: aiohttp.ClientSession, id_32,
                                   matches_limit=100, lobby_only=False):
    """
    Get the most played heroes for this player asynchronously with aiohttp.

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
            return await req.json()


if __name__ == '__main__':
    steam_id = "STEAM_0:1:51900704"
    steam_32 = convert_text_to_32id(steam_id)
    print(steam_32)
    account_info = get_account_info_sync(steam_32)
    account_matches = get_account_heroes_sync(steam_32)
    print(account_info)
    print(account_matches)
