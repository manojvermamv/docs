import requests

BASE_REPO = "marketcalls/openalgo"
FORKS_API = f"https://api.github.com/repos/{BASE_REPO}/forks"

print(f"""
🌐 You can run this script directly in a browser using
👉 https://cliprun.com
""")
print("\n🔍 Fetching forks...\n")

response = requests.get(FORKS_API)

# ---- SAFETY CHECK ----
if response.status_code != 200:
    print("❌ GitHub API Error:", response.text)
    exit()

try:
    forks_data = response.json()
except Exception as e:
    print("❌ JSON Parse Error:", e)
    exit()

# Ensure it's a list
if not isinstance(forks_data, list):
    print("❌ Unexpected response:", forks_data)
    exit()

forks = []
for repo in forks_data:
    if isinstance(repo, dict) and "full_name" in repo:
        forks.append(repo["full_name"])

print(f"Total forks found: {len(forks)}\n")

ahead_forks = []

for fork in forks:
    url = f"https://api.github.com/repos/{fork}/compare/main...marketcalls:main"

    r = requests.get(url)

    # skip bad responses safely
    if r.status_code != 200:
        continue

    data = r.json()

    ahead = data.get("ahead_by", 0)
    behind = data.get("behind_by", 0)

    if ahead > 0:
        ahead_forks.append((fork, ahead, behind))

# Sort by most ahead commits
ahead_forks.sort(key=lambda x: x[1], reverse=True)

# ---------------- TABLE OUTPUT ----------------

print("\n🚀 FINAL AHEAD FORKS LIST (Sorted)\n")

print(f"{'RANK':<5}{'FORK':<35}{'AHEAD':<10}{'BEHIND':<10}")
print("-" * 65)

for i, (fork, ahead, behind) in enumerate(ahead_forks, 1):
    print(f"{i:<5}{fork:<35}{ahead:<10}{behind:<10}")

print("-" * 65)
print(f"Total active forks: {len(ahead_forks)}\n")
