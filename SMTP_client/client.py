import base64
import json
import mimetypes
import os
import socket
import ssl


def request(socket, request):
    socket.send((request + '\n').encode())
    recv_data = ''
    while True:
        data = socket.recv(1024)
        recv_data += data.decode()
        if not data or len(data) < 1024:
            break
    return recv_data


def get_attachments():
    atts = ''
    atts_list = []

    # получение списка вложений
    for root, dirs, files in os.walk("attachments"):
        for filename in files:
            atts_list.append(filename)

    for atts_name in atts_list:
        att_type = mimetypes.guess_type(atts_name)[0]
        with open(f'attachments/{atts_name}', 'rb') as attachment_file:
            attachment = attachment_file.read()
            att = base64.b64encode(attachment).decode()

        atts += f'Content-Disposition: attachment;\n'
        atts += f'\tfilename="{atts_name}"\n'
        atts += f'Content-Transfer-Encoding: base64\n'
        atts += f'Content-Type: {att_type};\n'
        atts += f'\tname="{atts_name}"\n'
        atts += f'\n'
        atts += f'{att}\n'
        atts += f'--{boundary_msg}\n'

    return atts


def message_prepare():
    with open('msg.txt') as file_msg:
        headers = f'from: {user_name_from}\n'

        user_names = ', '.join(user_names_to)
        headers += f'to: {user_names}\n'  # список получателей

        headers += f'subject: {subject_msg}\n'
        headers += 'MIME-Version: 1.0\n'
        headers += 'Content-Type: multipart/mixed;\n' \
                   f'    boundary={boundary_msg}\n'

        # тело сообщения началось
        message_body = f'--{boundary_msg}\n'
        message_body += 'Content-Type: text/plain; charset=utf-8\n\n'

        msg = file_msg.read()  # текстовое сообщение
        message_body += msg + '\n'

        message_body += f'--{boundary_msg}\n'

        attachments = get_attachments()
        message_body += f'{attachments}\n'  # добавление вложений
        message_body += f'--{boundary_msg}--'

        message = headers + '\n' + message_body + '\n.\n'
        print(message)
        return message


if __name__ == '__main__':
    with open('config.json', 'r') as json_file:
        file = json.load(json_file)
        user_name_from = file['from']  # считываем из конфига кто отправляет
        user_names_to = file['to']
        subject_msg = file['subject']
        host_addr = file['host_addr']
        port = file['port']
        boundary_msg = file['boundary_msg']

    with open("pswd.txt", "r", encoding="UTF-8") as file:
        password = file.read().strip()  # считываем пароль из файла

    ssl_contex = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_contex.check_hostname = False
    ssl_contex.verify_mode = ssl.CERT_NONE

    with socket.create_connection((host_addr, port)) as sock:
        with ssl_contex.wrap_socket(sock, server_hostname=host_addr) as client:
            print(client.recv(1024))  # в smpt сервер первый говорит
            print(request(client, f'ehlo {user_name_from}'))

            base64login = base64.b64encode(user_name_from.encode()).decode()
            base64password = base64.b64encode(password.encode()).decode()

            print(request(client, 'AUTH LOGIN'))
            print(request(client, base64login))
            print(request(client, base64password))
            print(request(client, f'MAIL FROM:{user_name_from}'))

            for name in user_names_to:
                print(request(client, f"RCPT TO:{name}"))  # список получателей

            print(request(client, 'DATA'))
            print(request(client, message_prepare()))
