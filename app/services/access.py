import json

def get_access_levels() -> list:
    with open('access_levels.json', 'r') as f:
        data_as_dict = json.load(f)
    return data_as_dict


def access_level_lookup() -> dict:
    with open('access_levels.json', 'r') as f:
        data_dict = json.load(f)

    access_level_dict = {}
    for item in data_dict:
        access_level_dict[(item['codename'])] = item['access_level']

    return access_level_dict