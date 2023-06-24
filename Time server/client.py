import socket
import datetime
from server import convert_fraction

HOST = 'localhost'
PORT = 123

if __name__ == '__main__':
    client_s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_s.sendto('msg'.encode(), (HOST, PORT))

    try:
        while True:
            data, address = client_s.recvfrom(1024)
            seconds = int.from_bytes(data[:4], byteorder='big')
            fraction = int.from_bytes(data[4:], byteorder='big')

            new_fraction = convert_fraction(fraction)
            timestamp = seconds + new_fraction

            dt = datetime.datetime.fromtimestamp(timestamp)

            print(
                f"Время с учетом изменений: {dt.strftime('%d %B %Y %H:%M:%S')}")

    except KeyboardInterrupt:
        client_s.close()
