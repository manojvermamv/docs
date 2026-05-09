# Git Fork Comparison Guide (Ahead / Behind Commits)

This guide shows how to compare a forked repository against the original repository and extract:

- Ahead commits
- Behind commits
- Commit titles
- Full commit messages/descriptions
- Code differences
- Changed files
- Patch files
- Statistics
- Export results to files

Works on:

- Windows CMD
- PowerShell
- Linux
- macOS

---

# Example Repositories

Original Repository:

```text
https://github.com/marketcalls/openalgo.git
```

Fork Repository:

```text
https://github.com/shangita/openalgo.git
```

---

# 1. Clone Original Repository

## Windows CMD / PowerShell

```cmd
git clone https://github.com/marketcalls/openalgo.git
cd openalgo
```

## Linux / macOS

```bash
git clone https://github.com/marketcalls/openalgo.git
cd openalgo
```

---

# 2. Add Fork Repository as Remote

## Windows CMD / PowerShell

```cmd
git remote add shangita https://github.com/shangita/openalgo.git
git fetch shangita
```

## Linux / macOS

```bash
git remote add shangita https://github.com/shangita/openalgo.git
git fetch shangita
```

---

# 3. Verify Remotes

## Windows CMD / PowerShell

```cmd
git remote -v
```

## Linux / macOS

```bash
git remote -v
```

Expected output:

```text
origin      https://github.com/marketcalls/openalgo.git
shangita    https://github.com/shangita/openalgo.git
```

---

# Understanding Ahead / Behind

```text
origin/main..shangita/main
```

Means:

```text
Commits present in shangita/main
BUT NOT present in origin/main
```

These are the "ahead" commits.

---

```text
shangita/main..origin/main
```

Means:

```text
Commits present in origin/main
BUT NOT present in shangita/main
```

These are the "behind" commits.

---

# 4. Show Ahead Commits (Compact)

## Windows CMD / PowerShell

```cmd
git log origin/main..shangita/main --oneline
```

## Linux / macOS

```bash
git log origin/main..shangita/main --oneline
```

Example output:

```text
abc1234 Added websocket support
def5678 Fixed broker login issue
```

---

# 5. Show Behind Commits (Compact)

## Windows CMD / PowerShell

```cmd
git log shangita/main..origin/main --oneline
```

## Linux / macOS

```bash
git log shangita/main..origin/main --oneline
```

---

# 6. Show Full Commit Titles + Descriptions

## Ahead Commits

## Windows CMD / PowerShell

```cmd
git log origin/main..shangita/main --pretty=format:"%h | %s%n%b%n---"
```

## Linux / macOS

```bash
git log origin/main..shangita/main --pretty=format:"%h | %s%n%b%n---"
```

Output example:

```text
abc1234 | Added websocket support

Implemented live websocket stream
Added reconnect handler

---
```

---

# 7. Export Ahead Commits to File

## Windows CMD / PowerShell

```cmd
git log origin/main..shangita/main --pretty=format:"%h | %s%n%b%n---" > ahead_commits.txt
```

## Linux / macOS

```bash
git log origin/main..shangita/main --pretty=format:"%h | %s%n%b%n---" > ahead_commits.txt
```

---

# 8. Export Behind Commits to File

## Windows CMD / PowerShell

```cmd
git log shangita/main..origin/main --pretty=format:"%h | %s%n%b%n---" > behind_commits.txt
```

## Linux / macOS

```bash
git log shangita/main..origin/main --pretty=format:"%h | %s%n%b%n---" > behind_commits.txt
```

---

# 9. Show Full Code Differences

## Ahead Changes

## Windows CMD / PowerShell

```cmd
git diff origin/main..shangita/main
```

## Linux / macOS

```bash
git diff origin/main..shangita/main
```

---

# 10. Export Full Code Diff to File

## Windows CMD / PowerShell

```cmd
git diff origin/main..shangita/main > ahead_changes.diff
```

## Linux / macOS

```bash
git diff origin/main..shangita/main > ahead_changes.diff
```

---

# 11. Show Changed Files Only

## Windows CMD / PowerShell

```cmd
git diff --name-only origin/main..shangita/main
```

## Linux / macOS

```bash
git diff --name-only origin/main..shangita/main
```

---

# 12. Show File Change Statistics

## Windows CMD / PowerShell

```cmd
git diff --stat origin/main..shangita/main
```

## Linux / macOS

```bash
git diff --stat origin/main..shangita/main
```

Example output:

```text
api/server.py      | 120 +++++++++++
broker/login.py    |  45 ++++
README.md          |  20 ++
```

---

# 13. Show Commits with Changed Files

## Windows CMD / PowerShell

```cmd
git log --name-only --oneline origin/main..shangita/main
```

## Linux / macOS

```bash
git log --name-only --oneline origin/main..shangita/main
```

---

# 14. Show Detailed Commit + File Stats

## Windows CMD / PowerShell

```cmd
git log --stat origin/main..shangita/main
```

## Linux / macOS

```bash
git log --stat origin/main..shangita/main
```

---

# 15. Create Patch Files

Useful for:

- Code review
- Applying changes manually
- Sending patches

## Windows CMD / PowerShell

```cmd
git format-patch origin/main..shangita/main
```

## Linux / macOS

```bash
git format-patch origin/main..shangita/main
```

This creates `.patch` files.

---

# 16. Count Ahead Commits

## Windows CMD / PowerShell

```cmd
git rev-list --count origin/main..shangita/main
```

## Linux / macOS

```bash
git rev-list --count origin/main..shangita/main
```

---

# 17. Count Behind Commits

## Windows CMD / PowerShell

```cmd
git rev-list --count shangita/main..origin/main
```

## Linux / macOS

```bash
git rev-list --count shangita/main..origin/main
```

---

# 18. Visual Commit Graph

## Windows CMD / PowerShell

```cmd
git log --graph --oneline --all
```

## Linux / macOS

```bash
git log --graph --oneline --all
```

---

# 19. Compare Specific Branches

```text
git log branch1..branch2
git diff branch1..branch2
```

Example:

```text
git log develop..feature-x
```

---

# 20. Compare Specific Commits

```text
git diff COMMIT1 COMMIT2
```

Example:

```text
git diff abc1234 def5678
```

---

# 21. GitHub Compare URL

Open directly in browser:

```text
https://github.com/marketcalls/openalgo/compare/main...shangita:main
```

Or reverse:

```text
https://github.com/shangita/openalgo/compare/main...marketcalls:main
```

Shows:

- Ahead commits
- Behind commits
- Pull request style diff
- Changed files

---

# 22. GitHub API Compare

```text
https://api.github.com/repos/marketcalls/openalgo/compare/main...shangita:main
```

Useful for:

- Automation
- Scripts
- CI/CD
- JSON parsing

---

# 23. Export Everything into Single Report

## Windows CMD / PowerShell

```cmd
(
echo ===== AHEAD COMMITS =====
git log origin/main..shangita/main --oneline

echo.
echo ===== FULL COMMIT DETAILS =====
git log origin/main..shangita/main --pretty=format:"%%h | %%s%%n%%b%%n---"

echo.
echo ===== CHANGED FILES =====
git diff --name-only origin/main..shangita/main

echo.
echo ===== DIFF STATS =====
git diff --stat origin/main..shangita/main
) > full_report.txt
```

## Linux / macOS

```bash
{
echo "===== AHEAD COMMITS ====="
git log origin/main..shangita/main --oneline

echo
echo "===== FULL COMMIT DETAILS ====="
git log origin/main..shangita/main --pretty=format:"%h | %s%n%b%n---"

echo
echo "===== CHANGED FILES ====="
git diff --name-only origin/main..shangita/main

echo
echo "===== DIFF STATS ====="
git diff --stat origin/main..shangita/main
} > full_report.txt
```

---

# 24. Useful Git Comparison Shortcuts

| Purpose | Command |
|---|---|
| Ahead commits | `git log origin/main..fork/main` |
| Behind commits | `git log fork/main..origin/main` |
| Code diff | `git diff origin/main..fork/main` |
| Changed files | `git diff --name-only` |
| Diff stats | `git diff --stat` |
| Count commits | `git rev-list --count` |
| Create patches | `git format-patch` |

---

# 25. Cleanup Remote

Remove remote if needed.

## Windows CMD / PowerShell

```cmd
git remote remove shangita
```

## Linux / macOS

```bash
git remote remove shangita
```

---

# 26. Common Errors

## Error

```text
fatal: ambiguous argument
```

Cause:

- Remote not fetched
- Wrong branch name
- Linux `\` used in Windows CMD

Fix:

```cmd
git fetch shangita
```

Then retry command.

---

## Error

```text
unknown revision or path
```

Fix:

Check branch names:

```cmd
git branch -r
```

---

# 27. Best Workflow

Recommended workflow:

```text
1. Clone original repo
2. Add fork as remote
3. Fetch fork
4. Compare branches
5. Export reports
6. Review diffs
```

---

# 28. Quick Start (Fastest Method)

## Windows CMD

```cmd
git clone https://github.com/marketcalls/openalgo.git
cd openalgo
git remote add shangita https://github.com/shangita/openalgo.git
git fetch shangita
git log origin/main..shangita/main --oneline
```

## Linux / macOS

```bash
git clone https://github.com/marketcalls/openalgo.git
cd openalgo
git remote add shangita https://github.com/shangita/openalgo.git
git fetch shangita
git log origin/main..shangita/main --oneline
```

---

# Done

You can now fully inspect:

- Ahead commits
- Behind commits
- Full commit descriptions
- Source code differences
- File changes
- Patch files
- GitHub compare view
- Automated reports

without any manual GitHub browsing.
