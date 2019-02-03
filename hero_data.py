"""Dota hero information lookup."""

import os

import requests

HERO_DATA_ENDPOINT = "http://api.steampowered.com/IEconDOTA2_570/GetHeroes/v1"


def create_hero_dicts(api_hero_resp):
    """
    Create hero dictionaries based on API response to get heroes.

    The following mappings are created:
    Hero ID -> Hero Information
    Hero ID -> Sequential ID
    Sequential ID -> Hero ID

    Where sequential ID is our own, monotonically increasing counter for
    hero IDs, which valve assigns (rather randomly, it seems)

    Parameters
    ----------
    api_hero_resp: dict: str -> list
        A dict with a single item, in the format the API returns.

    """
    hero_info = {}
    hero_seq = {}
    seq_hero = []
    seq_count = 0
    for hero in api_hero_resp['heroes']:
        hero_id = hero['id']
        hero_info[hero_id] = {'name': hero['name'], 'id': hero_id,
                              'loc_name': hero['localized_name']}
        hero_seq[hero_id] = seq_count
        seq_hero.append(hero_id)
        seq_count += 1
    return hero_info, hero_seq, seq_hero


class HeroData:
    """
    Mappings from hero ID to other information.

    The mappings are generated using Valve's REST API, which we query to get
    some of the fancy information, i.e. name.

    See https://wiki.teamfortress.com/wiki/WebAPI/GetHeroes for more info.

    Attributes
    ----------
    hero_info: dict, hero_id -> dict
        Contains hero information based on hero id.
        The following information is stored in the mapping:
        name: dota 2 internal name (npc_dota_hero_...)
        id: hero id; the key used to obtain this information
        loc_name: localized name

    """

    def __init__(self, lang="en"):
        """
        Construct HeroData with names in the given language.

        Parameters
        ----------
        lang: str, default "en"
            The language to retrieve the data in.

        """
        # Steam key from environment vars. Get one or ask Bo Qu :)
        self._api_key = os.environ.get("STEAM_KEY")
        self._api_key = "5702A306A57CDC3AC6716D0963514C70"
        req = requests.get(HERO_DATA_ENDPOINT,
                           params=dict(key=self._api_key, language=lang))
        self.hero_info, _, _ = create_hero_dicts(req.json()['result'])

    def __getitem__(self, item):
        """Get hero information from hero id."""
        try:
            return self.hero_info[item]
        except KeyError:
            # For some reason OpenDota API returns hero ID as str???
            return self.hero_info[int(item)]
