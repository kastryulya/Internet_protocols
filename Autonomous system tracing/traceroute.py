import argparse
import re
import subprocess
import requests


def get_router_addresses(address):
    timeout = 5
    i = 1
    while True:
        print(f"Receiving router addresses: {i} iteration...")
        i += 1
        proc = subprocess.Popen(f'traceroute {address}', shell=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            outs, errs = proc.communicate(timeout=timeout)
            if proc.returncode == 0:
                result_str = outs.decode('ascii')
                return result_str
        except subprocess.TimeoutExpired:
            proc.kill()
            outs, errs = proc.communicate()

        result_str = outs.decode('ascii')

        if "* * *" in result_str:
            return result_str
        else:
            timeout *= 2
            continue


def parse_addresses(traceroute_str):
    print("Parsing of addresses...")
    list_str = re.findall(r"\(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}\)", traceroute_str)
    list_ip = []
    for ip in list_str:
        list_ip.append(ip[1:-1])
    return list_ip


def get_information_about_ip(numb, ip):
    print(f'Receiving the information about IP: number {numb}, address {ip}')
    try:
        res = requests.get(f'http://ip-api.com/{ip}?fields=country,isp,org,as')

        text = res.text

        regex1 = r'"country".*'
        regex2 = r'"as".*'
        regex3 = r'"isp".*'

        res1 = re.search(regex1, text)
        country = re.search(r'"[A-Z].*"', str(res1[0]))

        res2 = re.search(regex2, text)
        aut_sys = re.search(r'AS\d+', str(res2[0]))

        res3 = re.search(regex3, text)
        provider = re.search(r'"[A-Z]+.*"', str(res3[0]))

        new_str = f'{numb}\t\t{ip}\t\t{aut_sys[0]}\t\t{country[0][1:-1]}\t\t{provider[0][1:-1]}'

    except TypeError:
        new_str = f'{numb}\t\t{ip}\t\tThe local network'

    return new_str


def get_result_list(list_ip):
    result_list = ""
    i = 1
    for ip in list_ip:
        result_list += get_information_about_ip(i, ip) + "\n"
        i += 1

    return result_list


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Autonomous system tracing')
    parser.add_argument('address', type=str, help='Address for tracing')
    args = parser.parse_args()
    ip = args.address

    traceroute_list = get_router_addresses(ip)
    list_of_ip = parse_addresses(traceroute_list)
    print(get_result_list(list_of_ip))
