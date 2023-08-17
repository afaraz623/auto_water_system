import json

with open('personal.json', 'r') as json_file:
    data = json.load(json_file)

print(data['bot_token'])