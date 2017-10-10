import requests
import json
individual_constant = 0x0110000100000000

def convert_text_to_32id(steam_id):
	steam_id = steam_id[6:]
	#print(steam_id)
	steam_id = steam_id.split(":")
	instance = int(steam_id[1])
	account_number = int(steam_id[2]) * 2 + instance + individual_constant
	return account_number - 76561197960265728

def get_account_info(id_32):
	api = "https://api.opendota.com/api/players/"
	headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
	request = requests.get(api + str(id_32), headers = headers)
	if request.status_code != 200:
		print("bad call to api")
	else:
		JSON = json.loads(request.content.decode("utf-8"))
		return JSON["solo_competitive_rank"], JSON["mmr_estimate"]

if __name__ == '__main__':
	steam_id = "STEAM_0:1:51900704"
	steam_32 = convert_text_to_32id(steam_id)
	get_account_info(steam_32)
