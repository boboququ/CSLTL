"""Discord bindings for TangyBot."""
import os

import discord

from teamlookup import *

CLIENT_ID = ""
client = discord.Client()


async def write_to_discord(client, channel, message_contents):
    # client.send_message(message.channel, "Looking up team " + str(team_id))
    await client.send_message(channel, str(message_contents))


async def handle_lookup_message(client, channel, team_id):
    if "http" in team_id:
        team_id = team_id[team_id.rfind("/") + 1:]
        print(team_id)

    await client.send_message(channel, "Looking up team " + str(team_id))
    return_messages = look_up_team(team_id)

    for return_message in return_messages:
        if return_message == "":
            return_message = "404 error"

        await write_to_discord(client, channel, return_message)


async def handle_help_message(self, channel):
    message = "How to Use: @tangy_bot lookup<space><team_url or team id> \n"
    write_to_discord(client, channel, message)


@client.event
async def on_ready():
    print("Tangy Bot Start")
    await client.change_presence(game=discord.Game(name="Secret Strats"))


@client.event
async def on_message(message):
    print(message.content)
    if message.author == client.user:
        return
    if message.content == "TangyBot":
        await client.send_message(message.channel, "Present")
    elif message.content == "BoBot":
        await client.send_message(message.channel, "NANI")
    if message.content.startswith("<@" + CLIENT_ID):
        print("tagged")
        start_location = message.content.find('>')
        read_message = message.content[start_location + 2:]
        read_command = read_message.split(" ")
        print(read_command)

        if read_command[0] == "lookup":
            team_id = read_command[1]
            await handle_lookup_message(client, message.channel, team_id)


# token from environment variables


if __name__ == '__main__':
    discord_token = os.environ.get("DISCORD_TOKEN")
    discord_client_id = os.environ.get("DISCORD_CLIENT_ID")
    print(discord_token)
    print(discord_client_id)
    CLIENT_ID = discord_client_id
    client.run(discord_token)
