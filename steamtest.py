import json

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


def get_account_info(id_32):
    api = "https://api.opendota.com/api/players/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    request = requests.get(api + str(id_32), headers=headers)
    if request.status_code != 200:
        print("bad call to api")
    else:
        JSON = json.loads(request.content.decode("utf-8"))
        return JSON["solo_competitive_rank"], JSON["mmr_estimate"], JSON[
            "rank_tier"], JSON["leaderboard_rank"]


def get_account_heroes(id_32, matches_limit=100, num_heroes=5):
    """
    Get the most played heroes for this player.

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
        The number of most played heroes to display.

    Returns
    -------
    played_heroes: list of dicts
        The list of num_heroes heroes that the player has played the most.

    """
    api = "https://api.opendota.com/api/players/" + str(id_32) + "/heroes"
    req = requests.get(api, params=dict(limit=matches_limit))
    if req.status_code != 200:
        print("bad call to api")
    else:
        ret = req.json()
        for hero_dict in ret:
            hero_dict['loc_name'] = hero_info[hero_dict['hero_id']]['loc_name']
            try:
                hero_dict['winrate'] = hero_dict['win'] / hero_dict['games']
            except ZeroDivisionError:
                hero_dict['winrate'] = 0.0
        return sorted(ret,
                      key=lambda item: item['games'],
                      reverse=True)[:num_heroes]


if __name__ == '__main__':
    steam_id = "STEAM_0:1:51900704"
    steam_32 = convert_text_to_32id(steam_id)
    account_info = get_account_info(steam_32)
    print(account_info)
