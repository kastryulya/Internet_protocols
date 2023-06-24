import configparser
import datetime
import socket

HOST = 'localhost'
PORT = 123


def run():
    config = configparser.ConfigParser()
    config.read('configuration.ini')
    offset = config['Settings']['offset']

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((HOST, PORT))

    try:
        while True:
            data, address = s.recvfrom(1024)
            time = get_time_from_other_server()

            new_time = time + int(offset)

            seconds, fraction = str(new_time).split('.')
            new_data = int(seconds).to_bytes(4, byteorder='big') + \
                       int(fraction).to_bytes(4, byteorder='big')
            s.sendto(new_data, address)
    except KeyboardInterrupt:
        exit(0)


def get_time_from_other_server():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = ('time.windows.com', 123)
    client_socket.connect(server_address)
    data = b'\x1b' + 47 * b'\0'
    client_socket.sendall(data)
    response = client_socket.recv(1024)
    client_socket.close()

    if response:
        response = response[40:]
        seconds = int.from_bytes(response[:4], byteorder='big')
        fraction = int.from_bytes(response[4:], byteorder='big')
        ntp_epoch = 2208988800
        timestamp = seconds + fraction / 2 ** 32 - ntp_epoch

        dt = datetime.datetime.fromtimestamp(timestamp)
        print(
            f"От сервера time.windows.com получили время: {dt.strftime('%d %B %Y %H:%M:%S')}")

        return timestamp


def convert_fraction(fraction):
    count_of_zeros = len(str(fraction))
    return int(fraction) / 10 ** count_of_zeros


if __name__ == '__main__':
    run()
