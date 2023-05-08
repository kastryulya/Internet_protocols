#!/usr/bin/env python3
import binascii
import hashlib
import pickle
import socket
import time
import sys

cache = {}
TTL = 300


# сохранение кэша
def save_cache():
    with open('cache', 'wb') as cache_file:
        pickle.dump(cache, cache_file)


# загрузка кэша из файла
def load_cache():
    global cache
    try:
        with open('cache', 'rb+') as cache_file:
            cache = pickle.load(cache_file)
            cache_update()
    except FileNotFoundError:
        pass


# получаем словарь со значениями всех флагов\полей в заголовке
def parse_header(header):
    header_dict = {'ID': int.from_bytes(header[:2], byteorder='big')}

    third_byte = bin(header[2])[2:]
    if len(third_byte) < 8:
        third_byte = "{num:08}".format(num=int(third_byte))

    header_dict['QR'] = third_byte[0]
    header_dict['AA'] = third_byte[5]
    header_dict['RD'] = third_byte[7]

    forth_byte = bin(header[3])[2:]
    if len(forth_byte) < 8:
        forth_byte = "{num:08}".format(num=int(forth_byte))
    header_dict['RA'] = forth_byte[0]
    header_dict['RCODE'] = forth_byte[4:]
    header_dict['QDCOUNT'] = int.from_bytes(header[5:6], byteorder='big')
    header_dict['ANCOUNT'] = int.from_bytes(header[7:8], byteorder='big')
    header_dict['NSCOUNT'] = int.from_bytes(header[9:10], byteorder='big')
    header_dict['ARCOUNT'] = int.from_bytes(header[11:12], byteorder='big')

    return header_dict


# удаление старых записей
def cache_update():
    global cache
    to_delete = []

    for key in cache:
        if time.time() - cache[key]['time_of_saving'] > TTL:
            to_delete.append(key)

    for name in to_delete:
        del cache[name]


# парсинг DNS ответа
def parse_dns_response(data):
    response = {}
    header_dict = parse_header(data[:12])

    response['QDCOUNT'] = header_dict['QDCOUNT']
    response['ANCOUNT'] = header_dict['ANCOUNT']
    response['NSCOUNT'] = header_dict['NSCOUNT']
    response['ARCOUNT'] = header_dict['ARCOUNT']

    name = get_name_of_query(data)
    len_of_name = get_len_name_of_query(data)

    data_without_header_and_question = data[12 + len_of_name + 5:]

    # ответы
    offset = 0
    answers = []
    for i in range(response['ANCOUNT']):
        answer = {}
        offset += 2  # тут 2 потому что используется указатель
        answer['name'] = name
        answer['type'] = data_without_header_and_question[offset:offset + 2].hex()
        answer['class'] = data_without_header_and_question[offset + 2:offset + 4].hex()
        answer['ttl'] = int.from_bytes(data_without_header_and_question[offset + 4:offset + 8], byteorder='big')
        answer['data_length'] = int.from_bytes(data_without_header_and_question[offset + 8:offset + 10],
                                               byteorder='big')
        answer['data'] = data_without_header_and_question[offset + 10:offset + 10 + answer['data_length']].hex()
        answers.append(answer)
        offset += 10 + answer['data_length']
    response['answers'] = answers

    # авторитетные записи
    authorities = []
    for i in range(response['NSCOUNT']):
        authority = {}
        offset += 2
        authority['type'] = data_without_header_and_question[offset:offset + 2].hex()
        authority['class'] = data_without_header_and_question[offset + 2:offset + 4].hex()
        authority['ttl'] = int.from_bytes(data_without_header_and_question[offset + 4:offset + 8], byteorder='big')
        authority['data_length'] = int.from_bytes(data_without_header_and_question[offset + 8:offset + 10],
                                                  byteorder='big')
        authority['data'] = data_without_header_and_question[offset + 10:offset + 10 + authority['data_length']].hex()
        authorities.append(authority)
        offset += 10 + authority['data_length']
    response['authorities'] = authorities

    # дополнительные записи
    additions = []
    for i in range(response['ARCOUNT']):
        additional = {}
        offset += 2
        additional['type'] = data_without_header_and_question[offset:offset + 2].hex()
        additional['class'] = data_without_header_and_question[offset + 2:offset + 4].hex()
        additional['ttl'] = int.from_bytes(data_without_header_and_question[offset + 4:offset + 8], byteorder='big')
        additional['data_length'] = int.from_bytes(data_without_header_and_question[offset + 8:offset + 10],
                                                   byteorder='big')
        additional['data'] = data_without_header_and_question[offset + 10:offset + 10 + additional['data_length']].hex()
        authorities.append(additional)
        offset += 10 + additional['data_length']
    response['additions'] = additions

    return response


# составление DNS запроса
def make_dns_query(name, type):
    request = b''

    # заголовок
    request += bytes.fromhex('8989')  # ID
    request += bytes.fromhex('0000')  # флаги
    request += bytes.fromhex('0001')  # количество вопросов
    request += bytes.fromhex('0000')  # количество ответов
    request += bytes.fromhex('0000')  # количество автор.записей
    request += bytes.fromhex('0000')  # количество доп.записей

    # вопрос
    request += name
    request += bytes.fromhex(type)
    request += bytes.fromhex('0001')
    return request


# обращение к корневоу серверу, TLD и авторитетному серверу
# name передается в бинарном виде
def get_ip_from_senior_server(name):
    hash_name = hashlib.sha1(name).hexdigest()
    cache[hash_name] = {'time_of_saving': time.time()}

    # запрашиваем у одного из корневых серверов информацию(запись типа NS) по нужному адресу
    query = make_dns_query(name, '0002')
    resolver = ('199.7.83.42', 53)
    resolver_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    resolver_sock.sendto(query, resolver)
    response, _ = resolver_sock.recvfrom(1024)
    parsed = parse_dns_response(response)

    top_level_domains = []
    for record in parsed['authorities']:
        if record['type'] == '0001':
            top_level_domains.append(get_dec_adr_from_hex(record['data']))

    # запрашиваем у TLD информацию(запись типа NS) об авторитетных серверах
    authoritative_servers = []
    j = 0
    while True:
        query = make_dns_query(name, '0002')
        resolver = (top_level_domains[j], 53)
        resolver_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        resolver_sock.sendto(query, resolver)
        response, _ = resolver_sock.recvfrom(1024)
        parsed2 = parse_dns_response(response)

        for record in parsed2['authorities']:
            if record['type'] == '0001':
                authoritative_servers.append(get_dec_adr_from_hex(record['data']))
        cache[hash_name]['NS'] = {}
        cache[hash_name]['NS'] = authoritative_servers

        if not authoritative_servers:
            j += 1
            continue
        break

    # запрашиваем у авторитетных серверов информацию(запись типа А) об адресе
    ip_adrresses = []
    i = 0
    while True:
        try:
            query = make_dns_query(name, '0001')
            resolver = (authoritative_servers[i], 53)
            resolver_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            resolver_sock.sendto(query, resolver)
            response, _ = resolver_sock.recvfrom(1024)
            parsed3 = parse_dns_response(response)

            for record in parsed3['answers']:
                ip_adrresses.append(get_dec_adr_from_hex(record['data']))
            cache[hash_name]['A'] = {}
            cache[hash_name]['A'] = ip_adrresses

            if not ip_adrresses:
                i += 1
                continue
            break
        except:
            i += 1

    return cache[hash_name]['A']


def get_dec_adr_from_hex(adr):
    return '.'.join(str(int(i, 16)) for i in [adr[i:i + 2] for i in range(0, len(adr), 2)])


def get_len_name_of_query(data):
    without_header = data[12:]
    offset = 1
    len_temp_label = without_header[0]
    length = len_temp_label
    while len_temp_label != 0:
        offset += len_temp_label + 1
        len_temp_label = without_header[offset - 1]
        length += len_temp_label + 1
    return length


def get_name_of_query(data):
    # data - это весь запрос

    without_header = data[12:]
    offset = 1
    len_temp_label = without_header[0]
    name = []
    while len_temp_label != 0:
        temp_label = ''
        for i in range(len_temp_label):
            temp_label += chr(without_header[i + offset])
        offset += len_temp_label + 1
        len_temp_label = without_header[offset - 1]
        name.append(temp_label)
    return '.'.join(name)


def get_bin_name_of_query(data):
    # data - это весь запрос

    len_of_name = get_len_name_of_query(data)
    return data[12:12 + len_of_name + 1]


def get_ip(data):
    name = get_bin_name_of_query(data)
    hash_name = hashlib.sha1(name).hexdigest()

    if cache and hash_name in cache:
        print("Record from cache:")
        return cache[hash_name]['A']
    else:
        print("Record from server:")
        return get_ip_from_senior_server(name)
    pass


def server():
    global cache
    load_cache()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('localhost', 1025))

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            print(get_ip(data))
        except KeyboardInterrupt:
            save_cache()
            exit(0)


if __name__ == '__main__':
    server()
