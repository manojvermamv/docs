# Git Advanced: Modifying Historical Commits

This guide explains how to modify the **second-to-last (or older)** commit—even after it has been pushed to a remote repository.

---

## ⚠️ Important Warning

These processes involve **rewriting Git history**.

* ❌ Do NOT use on shared branches (`main`, `develop`)
* ⚠️ Always coordinate with your team before force pushing
* ✅ Safe for personal/feature branches

---

## 🧠 Key Concepts

| Term               | Definition                       |
| ------------------ | -------------------------------- |
| Interactive Rebase | Modify, reorder, or edit commits |
| Amend              | Update the latest commit         |
| Force Push         | Overwrites remote history        |
| Force-with-lease   | Safer force push                 |
| Detached HEAD      | Not on a branch                  |

---

# 🧰 Method 1: Terminal (Interactive Rebase)

## 1. Start Rebase

```bash
git rebase -i HEAD~2
```

---

## 2. Select Commit to Edit

```text
pick abc1234 Older commit (2nd latest)
pick def5678 Latest commit
```

Change to:

```text
edit abc1234 Older commit (2nd latest)
pick def5678 Latest commit
```

---

## 3. Apply Fix

```bash
git add .
git commit --amend --no-edit
```

---

## 4. Continue

```bash
git rebase --continue
```

Git will replay newer commits on top.

---

## ⚠️ Handle Conflicts

```bash
# Resolve conflicts in your editor
git add .

git rebase --continue
```

---

## 🛑 Abort if Needed

```bash
git rebase --abort
```

---

## 5. Force Push

```bash
git push origin <branch-name> --force-with-lease
```

---

# 🖥️ Method 2: GitHub Desktop

> ⚠️ This recreates commits (not a true rebase)

### Steps

1. **History** → Right-click latest commit → **Amend Commit**
   *(This "undoes" the top commit but keeps your changes in the working directory.)*

2. Make your new code changes in your editor.

3. In GitHub Desktop, check **Amend last commit** to update the historical commit.

4. **Commit** those changes.

5. You will still have the "latest" changes sitting in your **Changes** tab — commit them now using the original message.

6. **Force Push** to origin.

---

# 🛠️ Recovery with `git reflog`

If something goes wrong (bad rebase, lost commits), Git keeps a local history of HEAD movements.

---

## View History

```bash
git reflog
```

---

## Restore Previous State

```bash
git reset --hard HEAD@{2}
```

Or:

```bash
git reset --hard <commit-hash>
```

---

## Recover Deleted Branch

```bash
git checkout -b recovered-branch <commit-hash>
```

---

## ⚠️ Notes

* Works **locally only**
* Entries expire (default ~90 days)
* `--hard` will overwrite working directory changes

---

# ✅ Best Practices

* Use feature branches
* Communicate before force pushing
* Prefer `--force-with-lease`
* Keep commits clean and meaningful
* Use `reflog` as a safety net

---

# 📌 Summary

| Task            | Command                       |
| --------------- | ----------------------------- |
| Start rebase    | `git rebase -i HEAD~2`        |
| Amend commit    | `git commit --amend`          |
| Continue rebase | `git rebase --continue`       |
| Abort rebase    | `git rebase --abort`          |
| Force push      | `git push --force-with-lease` |
| Recover commits | `git reflog`                  |

---
