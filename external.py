import socket

def get_external_ip():
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        return ip_address
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    print(get_external_ip())