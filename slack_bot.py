"""Slack bindings for TangyBot (rip)."""
import os
import time

from slackclient import SlackClient


class CSL_Lookup_Bot(object):
    def __init__(self, bot_token):
        self.slack_client = SlackClient(bot_token)
        self.app_name = "tangy_bot"

    def slack_connect(self):
        success = self.slack_client.rtm_connect()
        print("Connection status:", success)
        return

    def slack_read_rtm(self):
        return self.slack_client.rtm_read()

    def parse_slack_input(self, input, botID):
        if input == []:
            return None
        bot_at_ID = "<@" + botID + ">"
        if input and len(input) > 0:
            input = input[0]
            if 'text' in input:
                if bot_at_ID in input['text']:
                    print("bot was tagged in message")
                    user = input['user']
                    message = input['text'].split(bot_at_ID)[1].strip(" ")
                    channel = input["channel"]
                    print("user:", user, "Message:", message, "channel:",
                          channel)
                    print("MESSAGE WAS GOT:", str(message), "ON ",
                          str(channel))
                    return [str(user), str(message), str(channel)]
        else:
            return None

    def get_bot_id(self, botname):
        # call slack api
        api_call = self.slack_client.api_call("users.list")
        users = api_call["members"]
        for user in users:
            if "name" in user and botname in user.get('name') and not user.get(
                    "deleted"):
                return user.get("id")

    def write_to_slack(self, channel, message):
        print("Writing to slack")
        return self.slack_client.api_call("chat.postMessage", channel=channel,
                                          text=message, as_user=True)

    def decide_to_take_action(self, message):
        print("Deciding Whether To Take Action")
        message = message.lower()
        if "help" in message:
            return 1
        if "lookup" in message:
            return 2

        return 0

    def handle_help_message(self, channel):
        message = "How to Use: @tangy_bot lookup <team_url or team id> \n"
        self.write_to_slack(channel, message)

    def handle_lookup_message(self, message, channel):
        message = message.split(" ")
        team_id = message[1]
        team_id = team_id.strip(">")
        if "http" in team_id:
            team_id = team_id[team_id.rfind("/") + 1:]
        print(team_id)
        return_messages = look_up_team(team_id)
        for return_message in return_messages:
            if return_message == "":
                return_message = "404 error"
            self.write_to_slack(channel, return_message)

    def run(self):
        self.slack_connect()
        my_name = self.app_name
        my_id = self.get_bot_id(my_name)
        print("My id is", my_id)
        while True:
            result = self.parse_slack_input(self.slack_read_rtm(), my_id)

            if result is not None:
                user = result[0]
                message = result[1]
                channel = result[2]
                print(user, message, channel)
                proceed = self.decide_to_take_action(message)
                if proceed > 0:
                    if proceed == 1:
                        self.handle_help_message(channel)

                    if proceed == 2:
                        self.handle_lookup_message(message, channel)

            time.sleep(1)


if __name__ == "__main__":
    # create instance of bot
    # run bot
    bot_token = os.environ.get("BOT_TOKEN")
    print(bot_token)
    bot_instance = CSL_Lookup_Bot(bot_token)
    bot_instance.run()
