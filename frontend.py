"""Basic frontend string parsing tasks."""


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
            results[-1] += string + "\n"
            current_len += len(string) + 1
    return results


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
        return_strings = [team_name + "\n"]
        for username, player in players.items():
            return_string = "-" * 100 + "\n"
            return_string += "CSL USERNAME:   " + str(username or "?") + "\n"
            return_string += "STEAM USERNAME: "
            return_string += player["profile"]["personaname"] + "\n"

            return_string += "SOLO MMR: " + str(
                player["solo_competitive_rank"] or "?") + "\n"
            return_string += "MMR ESTIMATE: " + str(
                player["mmr_estimate"]["estimate"] or "?") + "\n"
            return_string += "RANK TIER: " + rank_string(player) + "\n"

            return_string += "<" + str(player["dotabuff_link"] or "") + ">\n"
            return_string += "<" + str(player["opendota_link"] or "") + ">\n"

            return_strings.append(return_string)
        return_strings.append("-" * 100)
        return return_strings

    def profile(self, profiles):
        """Format profile string."""
        return_strings = []
        for username, heroes in profiles.items():
            return_string = username + ":\n```"

            for hero in heroes:
                return_string += "{:20s}".format(hero['loc_name'])
                return_string += f"{hero['games']:3d} games @ "
                return_string += f"{100 * hero['winrate']:.2f}" + "% winrate\n"
            if not heroes:
                return_string += "No heroes!\n"

            return_string += "```"
            return_strings.append(return_string)
        return return_strings
