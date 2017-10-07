from bs4 import BeautifulSoup
from urllib.request import urlopen, Request
from steamtest import *

def extract_id_user(players):
	player_dict = {}
	for player in players:
		player = str(player)
		#print(player)
		split = player.find("href=\"")
		
		steam_id = player[:split]
		steam_id = steam_id[steam_id.find("ID") + 4: steam_id[1:].find("<")-2]
		
		user_name = player[split + 1:]
		user_name = user_name[user_name.find(">") + 1:user_name.find("<")]
		
		print("steamid is" , steam_id)
		print("username is", user_name)
		player_dict[user_name] = steam_id

	return player_dict

def query_opendota_api(player_list):
	for username in player_list:
		steamid = player_list[username]
		print("STEAM ID IS ", steamid)
		steam_32id = convert_text_to_32id(steamid)
		acc_info = get_account_info(steam_32id)
		print(acc_info)

if __name__ == "__main__":
	url = "https://cstarleague.com/dota2/teams/839"
	headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
	request = Request(url, headers = headers)
	content = urlopen(request).read()
	soup = BeautifulSoup(content, 'lxml')
	
	players= soup.findAll("span", {"class" : "tool-tip"})

	player_list = extract_id_user(players)
	
	query_opendota_api(player_list)

