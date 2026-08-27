import socket

sock = socket.socket(
    socket.AF_INET,
    socket.SOCK_DGRAM,
)

try:
    sock.connect(("8.8.8.8", 80))
    ip = sock.getsockname()[0]
finally:
    sock.close()

print(ip)
