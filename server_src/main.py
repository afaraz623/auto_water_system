import socket
import time
from logs import log_init, log

# Constants
HEADERSIZE = 10

def handle_client(client_socket):
    while True:
        msg = 'Hello World\n'
        msg = bytes(f'{len(msg):<{HEADERSIZE}}', 'utf-8') + bytes(msg, 'utf-8')
        
        try:
            client_socket.send(msg)
        except socket.error as e:
            log.error(f'Error while sending data: {e}')
            break

        time.sleep(1)

    client_socket.close()

def main():
    server_address = (socket.gethostname(), 9001)

    log_init()
    log.info('Server started!')

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(server_address)
        server_socket.listen(5)

        while True:
            log.info('Waiting for a connection...')
            client_socket, address = server_socket.accept()
            log.info(f'Connection from {address} has been established!')

            handle_client(client_socket)
            log.info(f'Connection with {address} has been closed.')


if __name__ == '__main__':
    main()
