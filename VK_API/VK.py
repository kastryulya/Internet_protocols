import configparser

import requests

domain = ''
access_token = ''
version = 0
METHOD_NAMES = {'info': 'account.getInfo',
                'profileInfo': 'account.getProfileInfo',
                'banned': 'account.getBanned'}
all_info = {}


def get_info_from_config():
    global access_token
    global domain
    global version

    config = configparser.ConfigParser()
    config.read('config.ini')
    access_token = config['Settings']['access_token']
    domain = config['Settings']['domain']
    version = config['Settings']['version']


def make_query(method_name):
    try:
        query = f"{domain}/{method_name}?&access_token={access_token}&v={version}"
        response = requests.get(query)
    except requests.exceptions:
        return None
    else:
        return response.json()


def get_profile_info():
    try:
        profile_info = make_query(METHOD_NAMES['profileInfo'])

        all_info['home_town'] = profile_info['response']['home_town']
        all_info['first_name'] = profile_info['response']['first_name']
        all_info['last_name'] = profile_info['response']['last_name']
        all_info['bdate'] = profile_info['response']['bdate']
        all_info['phone'] = profile_info['response']['phone']
        all_info['screen_name'] = profile_info['response']['screen_name']

        sex = {1: 'Женский',
               2: 'Мужской'}
        all_info['sex'] = sex[profile_info['response']['sex']]
    except KeyError:
        return None


def get_banned():
    banned_info = make_query(METHOD_NAMES['banned'])
    banned_str = ''

    for people in banned_info['response']['profiles']:
        name = f"{people['last_name']} {people['first_name']}, "
        banned_str += name

    banned_str = banned_str[:-2]
    all_info['banned'] = banned_str


if __name__ == '__main__':
    get_info_from_config()
    get_profile_info()
    get_banned()

    print(f'''
    Имя: {all_info['first_name']}
    Фамилия: {all_info['last_name']}
    Родной город: {all_info['home_town']}
    Дата рождения: {all_info['bdate']}
    Телефон: {all_info['phone']}
    Ник нэйм: {all_info['screen_name']}
    Пол: {all_info['sex']}
    Пользователи в черном списке: {all_info['banned']}
    ''')
