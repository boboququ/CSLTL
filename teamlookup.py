from bs4 import BeautifulSoup
import urllib
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
		
		#print("steamid is" , steam_id)
		#print("username is", user_name)
		#TODO write dotabuff to file maybe
		dotabuff_link = "dotabuff.com/players/" + str(convert_text_to_32id(steam_id))
		opendota_link = "https://www.opendota.com/players/" + str(convert_text_to_32id(steam_id))
		#print("Dota Buff is ", dotabuff_link)
		#print("Open Dota is ", opendota_link)
		player_dict[user_name] = {}
		player_dict[user_name]["steam_id"] = steam_id
		player_dict[user_name]["dotabuff_link"] = dotabuff_link
		player_dict[user_name]["opendota_link"] = opendota_link

	return player_dict

def query_opendota_api(player_dict):
	for username in player_dict:
		player = player_dict[username]
		steam_32id = convert_text_to_32id(player["steam_id"])
		solommr, mmr_estimate = get_account_info(steam_32id)
		player["solommr"] = solommr
		player["mmr_estimate"] = mmr_estimate
		player_dict[username] = player

	return player_dict

def print_player_info(player_dict):
	for username in player_dict:
		player = player_dict[username]

		print("CSL USERNAME IS: ", username)
		print("SOLO MMR: ", player["solommr"], " MMR ESTIMATE: ", player["mmr_estimate"])
		print(player["dotabuff_link"])
		print(player["opendota_link"])
		print()

	return 

def player_info_to_string(player_dict):
	return_string = ""
	for username in player_dict:
		player = player_dict[username]
		return_string = return_string + "CSL USERNAME IS: " +  str(username or "") + "\n"
		return_string = return_string + "SOLO MMR: " + str(player["solommr"] or "") + " MMR ESTIMATE: " +  str(player["mmr_estimate"] or "") + "\n"
		return_string = return_string + str(player["dotabuff_link"] or "") + "\n"
		return_string = return_string + str(player["opendota_link"] or "") + "\n"
		return_string = return_string + "\n"
	return return_string

def look_up_team(team_id):
	url = "https://cstarleague.com/dota2/teams/"
	url = url + str(team_id)
	print("Looking up URL" + url)
	headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
	
	try:
		request = Request(url, headers = headers)
		content = urlopen(request).read()
		soup = BeautifulSoup(content, 'lxml')
		
		players = soup.findAll("span", {"class" : "tool-tip"})

		player_dict = extract_id_user(players)
		
		player_dict = query_opendota_api(player_dict)

		#print_player_info(player_dict)
		return player_info_to_string(player_dict)
	except urllib.error.HTTPError as e:
		print("404 error")
		return ""
if __name__ == "__main__":
	#michigan
	url = 839
	#purdue
	purdue = 2496
	#simon fraser
	url = 4982
	#Trine Thunder
	trine = 4621
	trine = 1360

	print(look_up_team(trine))


