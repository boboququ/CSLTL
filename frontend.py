"""Basic frontend string parsing tasks."""

# Divider string to break up sections, if needed
DIVIDER_STR = "`" + "-" * 98 + "`"

# URL headers for dota stats sites
DOTABUFF_HEAD = "https://dotabuff.com/players/"
OPENDOTA_HEAD = "https://www.opendota.com/players/"


def rank_string(player_resp):
    """Create rank string from player dictionary."""
    """Get rank (+ number) string from player dictionary."""
    rank_number = player_resp["rank_tier"]
    leaderboard_rank = player_resp["leaderboard_rank"]
    if rank_number is None:
        return "Unranked"
    elif leaderboard_rank is not None:
        return "Immortal #" + str(leaderboard_rank)
    badges = ["Herald", "Guardian", "Crusader", "Archon", "Legend",
              "Ancient", "Divine", "Immortal"]
    trailing = " " + str(rank_number % 10) if rank_number < 80 else ""
    return badges[(rank_number // 10) - 1] + trailing


def buffer_strings(strings, length_limit=2000):
    """Buffer strings by writing up to the limit."""
    # Need to bootstrap first string
    results = [strings[0]]
    current_len = len(strings[0])
    for string in strings[1:]:
        if current_len + len(string) + 1 >= length_limit:
            # We'd go over, so restart
            results.append(string)
            current_len = len(string)
        else:
            # We can append here
            results[-1] += "\n" + string
            current_len += len(string) + 1
    return results


def create_ascii_bar(perc, num_bars=20, midpoint=True):
    """Create an ascii bar representing the given percentage."""
    return_string = "|"
    rounded_bars = round(num_bars * perc)
    winrate_bar = "-" * rounded_bars + " " * (num_bars - rounded_bars)
    if midpoint:
        mid_ind = num_bars//2
        return_string += winrate_bar[:mid_ind] + "|" + winrate_bar[mid_ind:]
    else:
        return_string += winrate_bar
    return_string += "|"
    return return_string


class FrontendFormatter:
    """
    Frontend string formatting for backend responses.

    Attributes
    ----------
    buffer: bool
        Whether to buffer the output up to discord's message length limits
    """

    def __init__(self, buffer=True):
        self.buffer = buffer

    def dispatch(self, command, api_response):
        """
        Dispatch to help format the API response for a given command.

        Please call this function instead of calling them directly.

        Parameters
        ----------
        command: str
            The command to use

        api_response: dict
            API response to format

        Returns
        -------
        strings: list of str
            The list of strings that the formatting created

        """
        # If we get a keyerror, oh well
        func_to_call = getattr(self, command)
        # Splatter and pass username as kwargs
        res = func_to_call(**api_response)
        if self.buffer:
            res = buffer_strings(res)
        return res

    def lookup(self, team_name, players):
        """Format lookup string."""
        return_strings = ["CSL Team: " + team_name]
        for steam_id, player in players.items():
            return_string = DIVIDER_STR + "\n"
            return_string += "CSL USERNAME:   " + player['csl_name'] + "\n"
            return_string += "STEAM USERNAME: " + player['steam_name'] + "\n"

            return_string += "SOLO MMR: " + str(
                player["solo_competitive_rank"] or "?") + "\n"

            return_string += "MMR ESTIMATE: "
            try:
                return_string += str(player["mmr_estimate"]["estimate"])
            except KeyError:
                return_string += "?"
            return_string += "\n"

            return_string += "RANK TIER: " + rank_string(player) + "\n"

            return_string += "<" + DOTABUFF_HEAD + str(steam_id) + ">\n"
            return_string += "<" + OPENDOTA_HEAD + str(steam_id) + ">\n"

            return_strings.append(return_string)
        return_strings.append(DIVIDER_STR)
        return return_strings

    def profile(self, players):
        """Format profile string."""
        return_strings = ["Profiling results"]
        for steam_id, player in players.items():
            user_string = "Unknown player " + str(steam_id) + " (yell at Bo)"
            try:
                user_string = player['csl_name']
            except KeyError:
                try:
                    user_string = player['steam_name'] + " (steam name)"
                except KeyError:
                    pass

            return_string = user_string + ":\n```\n"

            for hero in player['heroes']:
                return_string += "{:20s}".format(hero['loc_name'])
                return_string += f"{hero['games']:3d} games "

                # Winrate bar
                return_string += create_ascii_bar(hero['winrate']) + " ("

                return_string += f"{100 * hero['winrate']:6.2f}" + "%)\n"
            if not player['heroes']:
                return_string += "No heroes!\n"

            return_string += "```"
            return_strings.append(return_string)
        return return_strings
