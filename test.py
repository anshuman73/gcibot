import requests

r = requests.get("https://codein.withgoogle.com/dashboard/task-instances/6551477011087360/")
for h in r.history:
    print h.url
print r.url
