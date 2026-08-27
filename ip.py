import requests
def get_public_ip():
    url = "https://api.ipify.org"
    response = requests.get(url)
    if response.status_code == 200:
        ip = response.text
        if validate_ipv4(ip):
            return ip
        else:
            return "Invalid IP address"
    else:
        return "Failed to retrieve IP address"

def validate_ipv4(ip):
    try:
        parts = list(map(int, ip.split('.')))
        if len(parts) != 4:
            return False
        for part in parts:
            if part < 0 or part > 255:
                return False
        return True
    except ValueError:
        return False

if __name__ == "__main__":
    ip = get_public_ip()
    print(ip)