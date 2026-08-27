import requests

url = "https://www.bbc.com/"
response = requests.get(url)
if "Russia" in response.text:
    print("Website contains Russia")
else:
    print("Website does not contain Russia")