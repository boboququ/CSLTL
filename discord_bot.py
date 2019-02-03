import os

import discord

from teamlookup import *

CLIENT_ID = ""
client = discord.Client()


async def Write_To_Discord(client, channel, message_contents):
    # client.send_message(message.channel, "Looking up team " + str(team_id))
    await client.send_message(channel, "Found " + str(message_contents))


async def Handle_Lookup_Message(client, channel, team_id):
    if "http" in team_id:
        team_id = team_id[team_id.rfind("/") + 1:]
        print(team_id)

    await client.send_message(channel, "Looking up team " + str(team_id))
    return_message = look_up_team(team_id)

    if return_message == "":
        return_message = "404 error"

    await Write_To_Discord(client, channel, return_message)


async def Handle_Help_Message(self, channel):
    message = "How to Use: @tangy_bot lookup<space><team_url or team id> \n"
    Write_To_Discord(client, channel, message)


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
    if message.content.startswith("<@" + CLIENT_ID):
        print("tagged")
        start_location = message.content.find('>')
        read_message = message.content[start_location + 2:]
        read_command = read_message.split(" ")
        print(read_command)

        if read_command[0] == "lookup":
            team_id = read_command[1]
            await Handle_Lookup_Message(client, message.channel, team_id)


# token from environment variables


if __name__ == '__main__':
    discord_token = os.environ.get("DISCORD_TOKEN")
    discord_client_id = os.environ.get("DISCORD_CLIENT_ID")
    print(discord_token)
    print(discord_client_id)
    CLIENT_ID = discord_client_id
    client.run(discord_token)
