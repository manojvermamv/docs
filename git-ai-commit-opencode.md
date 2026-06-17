# AI Generated Git Commit Messages using OpenCode + PowerShell

Automatically generate clean **Conventional Commit** messages using your existing **OpenCode CLI** configuration.

No need for:

- ❌ aichat
- ❌ Ollama
- ❌ Local LLM
- ❌ OpenAI API key

Requirements:

- Git installed
- PowerShell
- OpenCode CLI configured with a model/provider

---

# 1. Verify Requirements

Check Git:

```powershell
git --version
```

Check OpenCode:

```powershell
opencode --version
```

Test OpenCode:

```powershell
opencode run "Say hello in one word"
```

Expected:

```
Hello
```

---

# 2. Create PowerShell Profile

Use `CurrentUserAllHosts` so the function works across PowerShell hosts.

Check profile location:

```powershell
echo $PROFILE.CurrentUserAllHosts
```

Example:

```
C:\Users\Manoj\Documents\WindowsPowerShell\profile.ps1
```

Create profile if it does not exist:

```powershell
New-Item -ItemType File -Path $PROFILE.CurrentUserAllHosts -Force
```

Open profile:

```powershell
notepad $PROFILE.CurrentUserAllHosts
```

---

# 3. Add `git-ai-commit` Function

Add this function:

```powershell
function git-ai-commit {

    $diff = git diff --staged
    $stat = git diff --staged --stat

    if (-not $diff) {
        Write-Host "No staged changes found." -ForegroundColor Yellow
        return
    }


    $prompt = @"
Generate a git commit message from the staged diff.

IMPORTANT:
Always output TWO parts:

1. First line: conventional commit title
2. After a blank line: commit description body


Rules:
- Use Conventional Commits format:
  feat:, fix:, refactor:, docs:, test:, chore:, etc.

- Title max 72 characters.
- Body is required.
- Keep the message concise and meaningful.


For small changes:
- Use a short clear title.
- Keep body minimal.


For large changes:
- Summarize the overall purpose in the title.
- Use the body to compactly describe the important changes.
- Avoid repeating the diff or listing raw code changes.
- Do not mention every file or every line changed.
- Group related changes together.
- Prefer 3-7 bullet points for larger changes.
- Use fewer bullets for simple changes.
- Each bullet should represent a meaningful grouped change, not individual code edits.


General:
- Explain what changed and why it matters.
- Do not include unnecessary file names.
- Output ONLY the commit message.
- No SUBJECT/BODY labels.
- No markdown code blocks.
- No extra explanation.


Example:

fix: improve authentication handling

- Updated token validation flow
- Improved session expiry handling
- Simplified error handling paths


Change summary:

$stat


Diff:

$diff
"@


    $msg = opencode run $prompt 2>$null
    $msg = $msg.Trim()


    # First line = commit title
    # Remaining lines = commit body

    $lines = $msg -split "`r?`n"

    $title = $lines[0].Trim()


    if ($lines.Length -gt 1) {

        $bodyLines = $lines[1..($lines.Length - 1)]


        # Remove blank lines after title

        while ($bodyLines.Count -gt 0 -and $bodyLines[0].Trim() -eq "") {
            $bodyLines = $bodyLines[1..($bodyLines.Count - 1)]
        }


        $body = ($bodyLines -join "`n").Trim()

    }
    else {

        $body = ""

    }


    Write-Host ""
    Write-Host "Commit title:" -ForegroundColor Green
    Write-Host $title


    if ($body) {

        Write-Host ""
        Write-Host "Commit body:" -ForegroundColor Green
        Write-Host $body

    }


    Write-Host ""


    # Use Git subject + body separation

    if ($body) {

        git commit -m "$title" -m "$body"

    }
    else {

        git commit -m "$title"

    }

}
```

---

# 4. Reload PowerShell

After saving:

```powershell
. $PROFILE.CurrentUserAllHosts
```

Verify:

```powershell
Get-Command git-ai-commit
```

Expected:

```
CommandType     Name
-----------     ----
Function        git-ai-commit
```

---

# 5. Usage

Stage changes:

```powershell
git add .
```

Generate AI commit:

```powershell
git-ai-commit
```

---

# Workflow

```
git add .
      |
      v
git-ai-commit
      |
      v
git diff --staged
      |
      v
OpenCode AI
      |
      v
Generate commit title + body
      |
      v
git commit -m "title" -m "body"
```

---

# Example Output

## Small change

Generated:

```
fix: handle empty task input

- Added validation before processing
```

Git stores:

```
fix: handle empty task input

- Added validation before processing
```

---

## Large change

Generated:

```
refactor: simplify task processing workflow

- Consolidated validation logic
- Improved database interaction flow
- Reduced duplicate processing paths
- Updated error handling behavior
- Improved debugging logs
```

Git stores:

```
refactor: simplify task processing workflow

- Consolidated validation logic
- Improved database interaction flow
- Reduced duplicate processing paths
- Updated error handling behavior
- Improved debugging logs
```

---

# Benefits

✅ Uses your existing OpenCode setup  
✅ No API key required  
✅ No local model required  
✅ Supports multi-line commit messages  
✅ Uses Git native subject/body format  
✅ Works across PowerShell hosts  
✅ Keeps commit history clean  
✅ Handles small and large changes
