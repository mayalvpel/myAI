import requests

def check_website():
    url = "https://www.google.com"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        print("Website is up and running.")
    except requests.exceptions.RequestException as e:
        print(f"Error checking website: {e}")

if __name__ == "__main__":
    check_website()