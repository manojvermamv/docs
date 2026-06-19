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
    $diff = git diff --staged --unified=1
    $stat = git diff --staged --stat

    if (-not $diff) {
        Write-Host "No staged changes found." -ForegroundColor Yellow
        return
    }

    $maxPromptSize = 40000

    $estimatedSize =
        ($diff | Out-String).Length +
        ($stat | Out-String).Length

    # if ($estimatedSize -gt $maxPromptSize) {
    #     Write-Host ""
    #     Write-Host "Staged changes are too large for AI commit generation." -ForegroundColor Yellow
    #     Write-Host "Prompt size: $estimatedSize characters" -ForegroundColor Yellow
    #     Write-Host "Limit: $maxPromptSize characters" -ForegroundColor Yellow
    #     Write-Host ""
    #     Write-Host "Commit manually or split the changes into smaller commits." -ForegroundColor Yellow
    #     return
    # }

    $gitDir = git rev-parse --git-dir
    $diffFile = Join-Path $gitDir "ai-commit-diff.tmp"
    $diff | Set-Content $diffFile -Encoding UTF8

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
- Do not output raw implementation details.
- Do not include file names unless important.
- Output ONLY the commit message.
- No SUBJECT/BODY labels.
- No markdown code blocks.
- No extra explanation.

Example output:

fix: improve authentication handling

- Updated token validation flow
- Improved session expiry handling
- Simplified error handling paths

Change summary:
$stat

Read diff from file:
$diffFile

Do NOT expect full diff inline.
"@

    # Run OpenCode
    $oldConsoleEncoding = [Console]::OutputEncoding
    $oldOutputEncoding = $OutputEncoding

    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8

    try {
        $msg = $prompt | opencode run 2>&1
    }
    finally {
        [Console]::OutputEncoding = $oldConsoleEncoding
        $OutputEncoding = $oldOutputEncoding
    }

    $exitCode = $LASTEXITCODE

    if (Test-Path $diffFile) {
        Remove-Item $diffFile -Force -ErrorAction SilentlyContinue
    }

    if ($exitCode -ne 0) {
        Write-Host ""
        Write-Host "OpenCode failed:" -ForegroundColor Red
        Write-Host $msg
        return
    }

    if ($msg -is [System.Management.Automation.ErrorRecord]) {

        Write-Host ""
        Write-Host "OpenCode error:" -ForegroundColor Red
        Write-Host $msg
        return

    }

    # If opencode returns multiple lines, [string]$msg joins them with spaces.
    if ($msg -is [array]) {
        $msg = $msg -join "`n"
    }
    else {
        $msg = [string]$msg
    }

    if ([string]::IsNullOrWhiteSpace($msg)) {
        Write-Host ""
        Write-Host "OpenCode returned no output." -ForegroundColor Red
        return
    }

    # Clean ANSI escape sequences and BOM
    $msg = $msg -replace '\x1B\[[0-9;]*[a-zA-Z]', ''
    $msg = $msg -replace '^\uFEFF', ''
    $msg = $msg.Trim()

    # First line = commit title
    # Remaining lines = commit body

    $lines = @($msg -split "`r?`n")

    if ($lines.Count -eq 0) {
        Write-Host "Failed to parse commit message." -ForegroundColor Red
        return
    }

    $commitLineIndex = -1

    for ($i = 0; $i -lt $lines.Count; $i++) {

        # Optional leading characters (like emojis or markdown) before conventional commit
        if ($lines[$i] -match '(?i)(feat|fix|docs|refactor|test|chore|build|ci|perf|style|revert|security)(\(.+\))?:\s') {

            $commitLineIndex = $i
            break
        }
    }

    if ($commitLineIndex -eq -1) {

        Write-Host "Could not find a valid conventional commit message." -ForegroundColor Red
        return
    }

    $title = $lines[$commitLineIndex].Trim(" ```t`r`n")

    $body = ""

    if ($commitLineIndex + 1 -lt $lines.Count) {

        $body = ($lines[($commitLineIndex + 1)..($lines.Count - 1)] -join "`n").Trim()

        $body = $body -replace '^\s*```[a-zA-Z]*\s*', ''
        $body = $body -replace '\s*```\s*$', ''
        $body = $body.Trim()
    }

    Write-Host ""
    Write-Host "Commit title:" -ForegroundColor Green
    Write-Host $title

    if (-not [string]::IsNullOrWhiteSpace($body)) {

        Write-Host ""
        Write-Host "Commit body:" -ForegroundColor Green
        Write-Host $body
    }

    Write-Host ""

    # Commit using a temporary file
    # Avoids quoting and multiline issues

    $tempFile = [System.IO.Path]::GetTempFileName()

    try {

        if (-not [string]::IsNullOrWhiteSpace($body)) {
            "$title`r`n`r`n$body" | Set-Content $tempFile -Encoding UTF8
        }
        else {
            $title | Set-Content $tempFile -Encoding UTF8
        }

        git commit -F $tempFile

    }
    finally {

        if (Test-Path $tempFile) {
            Remove-Item $tempFile -Force
        }

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
