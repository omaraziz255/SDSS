import sys
import os
import threading
import socket
import time
import uuid
import datetime
from datetime import timezone
import struct
# https://bluesock.org/~willkg/dev/ansi.html
ANSI_RESET = "\u001B[0m"
ANSI_RED = "\u001B[31m"
ANSI_GREEN = "\u001B[32m"
ANSI_YELLOW = "\u001B[33m"
ANSI_BLUE = "\u001B[34m"

_NODE_UUID = str(uuid.uuid4())[:8]


def print_yellow(msg):
    print(f"{ANSI_YELLOW}{msg}{ANSI_RESET}")


def print_blue(msg):
    print(f"{ANSI_BLUE}{msg}{ANSI_RESET}")


def print_red(msg):
    print(f"{ANSI_RED}{msg}{ANSI_RESET}")


def print_green(msg):
    print(f"{ANSI_GREEN}{msg}{ANSI_RESET}")


def get_broadcast_port():
    return 35498


def get_node_uuid():
    return _NODE_UUID


class NeighborInfo(object):
    def __init__(self, delay, broadcast_count, ip=None, tcp_port=None):
        # Ip and port are optional, if you want to store them.
        self.delay = delay
        self.broadcast_count = broadcast_count
        self.ip = ip
        self.tcp_port = tcp_port


############################################
#######  Y  O  U  R     C  O  D  E  ########
############################################


# Don't change any variable's name.
# Use this hashmap to store the information of your neighbor nodes.
neighbor_information = {}
# Leave the server socket as global variable.
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Leave broadcaster as a global variable.
broadcaster = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# Setup the UDP socket
broadcaster.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
broadcaster.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
broadcaster.bind(("", get_broadcast_port()))


def get_timestamp():
    dt = datetime.datetime.now()
    utc = dt.replace(tzinfo=timezone.utc)
    return utc.timestamp()


def print_neighbours():
    for node, data in neighbor_information.items():
        print(f"Node: {node}  Port: {data.tcp_port}  Delay: {data.delay} ms")


# def refresh_neighbours():
#     threads = []
#     for node in neighbor_information.keys():
#         ip = neighbor_information[node].ip
#         port = neighbor_information[node].tcp_port
#         threads.append(daemon_thread_builder(exchange_timestamps_thread, args=(node, ip, port)))
#         threads[-1].start()
#     for thread in threads:
#         thread.join()
#     print_neighbours()


def send_broadcast_thread():

    node_uuid = get_node_uuid()
    message = " ".join([node_uuid, "ON", str(server.getsockname()[1])])
    print("Message to be broadcast: " + message)
    message = message.encode("UTF-8")
    while True:
        # TODO: write logic for sending broadcasts.
        broadcaster.sendto(message, ('<broadcast>', get_broadcast_port()))
        time.sleep(1)  # Leave as is.


def receive_broadcast_thread():
    """
    Receive broadcasts from other nodes,
    launches a thread to connect to new nodes
    and exchange timestamps.
    """
    while True:
        # TODO: write logic for receiving broadcasts.
        data, (ip, port) = broadcaster.recvfrom(4096)
        data = data.decode("UTF-8")
        node, _, port = data.split(" ")
        print_blue(f"RECV: {data} FROM: {ip}:{port}")
        if node != get_node_uuid():
            if node not in neighbor_information.keys():
                timestamp_thread = daemon_thread_builder(target=exchange_timestamps_thread, args=(node, ip, int(port)))
                timestamp_thread.start()
                time.sleep(1)
            else:
                neighbor_information[node].broadcast_count += 1
                if neighbor_information[node].broadcast_count == 10:
                    timestamp_thread = daemon_thread_builder(target=exchange_timestamps_thread, args=(node, ip, int(port)))
                    timestamp_thread.start()




def tcp_server_thread():
    """
    Accept connections from other nodes and send them
    this node's timestamp once they connect.
    """
    server.bind(("", 0))
    print(f"TCP Server Socket was assigned port number: {server.getsockname()[1]}")
    server.listen(20)
    while True:
        client, address = server.accept()
        timestamp = struct.pack("!d", get_timestamp())
        client.sendto(timestamp, address)
        client.close()


def exchange_timestamps_thread(other_uuid: str, other_ip: str, other_tcp_port: int):
    """
    Open a connection to the other_ip, other_tcp_port
    and do the steps to exchange timestamps.
    Then update the neighbor_info map using other node's UUID.
    """
    print_yellow(f"ATTEMPTING TO CONNECT TO {other_uuid}")
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((other_ip, other_tcp_port))
    except ConnectionRefusedError:
        print_red("Required Node has refused the connection")
        if other_uuid in neighbor_information.keys():
            neighbor_information.pop(other_uuid)
        return
    timestamp, address = client.recvfrom(4096)
    timestamp = struct.unpack("!d", timestamp)[0]
    delay = (get_timestamp() - timestamp) * 1000
    neighbor_information[other_uuid] = NeighborInfo(delay, 0, other_ip, other_tcp_port)
    print_neighbours()


def daemon_thread_builder(target, args=()) -> threading.Thread:
    """
    Use this function to make threads. Leave as is.
    """
    th = threading.Thread(target=target, args=args)
    th.setDaemon(True)
    return th


def entrypoint():
    server_thread = daemon_thread_builder(tcp_server_thread)
    broadcast_thread = daemon_thread_builder(send_broadcast_thread)
    receiver_thread = daemon_thread_builder(receive_broadcast_thread)

    server_thread.start()
    broadcast_thread.start()
    receiver_thread.start()

    broadcast_thread.join()
    receiver_thread.join()
    server_thread.join()

############################################
############################################


def main():
    """
    Leave as is.
    """
    print("*" * 50)
    print_red("To terminate this program use: CTRL+C")
    print_red("If the program blocks/throws, you have to terminate it manually.")
    print_green(f"NODE UUID: {get_node_uuid()}")
    print("*" * 50)
    time.sleep(2)   # Wait a little bit.
    entrypoint()


if __name__ == "__main__":
    main()


