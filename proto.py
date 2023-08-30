import socket
from base.logs import log_init, log


HEADERSIZE = 10
server_address = ('172.19.0.3', 9001)

log_init()

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
    client_socket.connect(server_address)
    
    full_msg = b''
    new_msg = True
    
    try:
        while True:
            msg = client_socket.recv(16)

            if new_msg:
                msg_len = int(msg[:HEADERSIZE].decode('utf-8'))
                new_msg = False
            
            full_msg += msg 

            if len(full_msg) - HEADERSIZE == msg_len:
                log.info(f'new message length: {msg_len}')
                
                log.info(full_msg[HEADERSIZE:].decode('utf-8'))
                
                new_msg = True
                full_msg = b''

    except Exception as e:
        log.info(f'An exception occured: {e}')