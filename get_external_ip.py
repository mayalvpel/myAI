import urllib.request

request = urllib.request.Request(
    "https://api.ipify.org",
    headers={"User-Agent": "Jarvis/1.0"},
)

with urllib.request.urlopen(request, timeout=10) as response:
    ip = response.read().decode("utf-8").strip()

print(ip)
