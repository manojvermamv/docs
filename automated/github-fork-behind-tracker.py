import requests

BASE_REPO = "marketcalls/openalgo"

# ---------------- CONFIG ----------------
SORT = "newest"          # newest | oldest | stargazers | watchers
PER_PAGE = 100
MAX_PAGES = 10

# ---------------- MODE SWITCH ----------------
TRACK_MODE = "BEHIND"     # AHEAD | BEHIND

# ---------------- CONSTANTS ----------------
COMPARE_UPSTREAM = "marketcalls:main"

# format strings (centralized)
HEADER_FMT = "{:<5}{:<40}{:<12}{:<12}"
ROW_FMT = "{:<5}{:<40}{:<12}{:<12}"

FORKS_API = f"https://api.github.com/repos/{BASE_REPO}/forks"

print(f"""
🌐 You can run this script directly in a browser using
👉 https://cliprun.com
""")
print("\n🔍 Fetching forks...\n")

# ---------------- FETCH FORKS (PAGINATED) ----------------
all_forks = []

for page in range(1, MAX_PAGES + 1):
    url = f"{FORKS_API}?sort={SORT}&per_page={PER_PAGE}&page={page}"
    r = requests.get(url)

    if r.status_code != 200:
        print("❌ API Error:", r.text)
        break

    data = r.json()
    if not data:
        break

    all_forks.extend(data)

forks = [
    repo["full_name"]
    for repo in all_forks
    if isinstance(repo, dict) and "full_name" in repo
]

print(f"Total forks fetched: {len(forks)}\n")

results = []

# ---------------- COMPARE LOGIC ----------------
for fork in forks:
    compare_url = f"https://api.github.com/repos/{fork}/compare/main...{COMPARE_UPSTREAM}"
    r = requests.get(compare_url)

    print(f"✅ {compare_url} → {r}")

    if r.status_code != 200:
        print(f"❌ Error Detail [{fork}]: {r.status_code} - {r.text}")
        continue

    data = r.json()

    ahead = data.get("ahead_by", 0)
    behind = data.get("behind_by", 0)

    # ---------------- SWITCH LOGIC ----------------
    if TRACK_MODE == "AHEAD" and ahead > 0:
        results.append((fork, ahead, behind))

    elif TRACK_MODE == "BEHIND" and behind > 0:
        results.append((fork, ahead, behind))

# ---------------- SORTING ----------------
if TRACK_MODE == "AHEAD":
    results.sort(key=lambda x: x[1], reverse=True)
else:
    results.sort(key=lambda x: x[2], reverse=True)

# ---------------- OUTPUT ----------------
print(f"\n🚀 FINAL FORK LIST MODE: {TRACK_MODE}\n")

print(HEADER_FMT.format("RANK", "FORK", "AHEAD", "BEHIND"))
print("-" * 70)

for i, (fork, ahead, behind) in enumerate(results, 1):
    print(ROW_FMT.format(i, fork, ahead, behind))

print("-" * 70)
print(f"Total matched forks ({TRACK_MODE}): {len(results)}\n")
