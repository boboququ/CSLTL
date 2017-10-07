import requests

individual_constant = 0x0110000100000000

def convert_text_to_32id(steam_id):
	steam_id = steam_id[6:]
	steam_id = steam_id.split(":")
	instance = int(steam_id[1])
	account_number = int(steam_id[2]) * 2 + instance + individual_constant
	return account_number - 76561197960265728

def get_account_info(id_32):
	api = "https://api.opendota.com/api/players/"
	request = requests.get(api + str(id_32),verify = False)
	if requests.status_code != 200:
		print("bad call to api")
	else:
		print(request.content)

if __name__ == '__main__':
	steam_id = "STEAM_0:1:51900704"
	steam_32 = convert_text_to_32id(steam_id)
	get_account_info(steam_32)
