# OmniRoute on Windows — Node 24 Isolation, Installation, and Persistent CLI Setup

## 1. Final Architecture

The goal is:

```text
Normal development
    ↓
Node.js 20.19.5
    ↓
Existing React Native / Node tooling


OmniRoute
    ↓
Node.js 24.19.0
    ↓
OmniRoute 3.8.49
```

The normal Node version should remain **20.19.5**.

OmniRoute should use **Node 24.19.0**.

The project does **not** need to be cloned from GitHub. It was installed as an npm global package:

```cmd
npm install -g omniroute
```

The published package at the time of installation was **OmniRoute 3.8.49**. Its package metadata defines the CLI entry point as `bin/omniroute.mjs`.

---

# 2. Prerequisites

The following were established during setup:

| Component | Final value |
|---|---:|
| OS | Windows 10/11 environment |
| NVM for Windows | Installed |
| Normal Node | `20.19.5` |
| OmniRoute Node | `24.19.0` |
| npm under Node 24 | `11.17.0` |
| OmniRoute | `3.8.49` |
| Bun | Installed, but not used for OmniRoute |
| OmniRoute installation | Global npm installation |
| Clone required | No |

Current OmniRoute package metadata requires a supported Node runtime; the published package currently lists Node `>=22.22.2`, while its package engine range accepts Node `>=24.0.0 <27`. Node `24.19.0` therefore fits the Node-24 path used here.

---

# 3. Why Node 20 Was Not Used for OmniRoute

The first installation attempt used:

```text
Node v20.19.5
npm 10.8.2
```

Installation failed while building `better-sqlite3`.

The important errors were:

```text
prebuild-install warn install No prebuilt binaries found
```

followed by:

```text
gyp ERR! find VS
gyp ERR! find VS Could not find any Visual Studio installation to use
```

There was also an engine warning:

```text
undici@8.10.0
required: node >=22.19.0
current: node v20.19.5
```

Therefore, installing Visual Studio C++ build tools was **not chosen as the primary solution**.

Instead, Node 24 was installed through NVM.

---

# 4. Install Node 24 Without Replacing the Normal Node Version

NVM for Windows was already installed.

Install Node 24:

```cmd
nvm install 24
```

This installed:

```text
v24.19.0
```

Switch to it:

```cmd
nvm use 24.19.0
```

Verify:

```cmd
node --version
```

Expected:

```text
v24.19.0
```

Check npm:

```cmd
npm --version
```

The confirmed Node-24 npm version was:

```text
11.17.0
```

---

# 5. Fixing the NVM PATH Problem

Initially:

```cmd
nvm use 24
```

reported success, but:

```cmd
node --version
```

still returned:

```text
v20.19.5
```

The cause was a version-specific Node directory appearing before the NVM symlink in `PATH`.

The problematic entry was equivalent to:

```text
%USERPROFILE%\nvm\v20.19.5
```

The correct NVM-managed path is:

```text
%USERPROFILE%\nvm\nodejs
```

After removing the hard-coded Node-20 directory from `PATH`, the following worked correctly:

```cmd
nvm use 20.19.5
node --version
```

Result:

```text
v20.19.5
```

Then:

```cmd
nvm use 24.19.0
node --version
```

Result:

```text
v24.19.0
```

The correct NVM resolution was:

```cmd
where node
```

Result:

```text
%USERPROFILE%\nvm\nodejs\node.exe
```

This is the expected arrangement because NVM controls the `nodejs` symlink.

---

# 6. Install OmniRoute

Switch to Node 24:

```cmd
nvm use 24.19.0
```

Verify:

```cmd
node --version
npm --version
```

Expected:

```text
v24.19.0
11.17.0
```

Then install:

```cmd
npm install -g omniroute
```

The confirmed installation downloaded OmniRoute:

```text
omniroute@3.8.49
```

and completed with:

```text
added 1187 packages
```

The installation produced peer-dependency warnings involving packages such as React and `marked`. Those warnings were not the installation failure.

---

# 7. npm `allow-scripts` Requirement

During the Node 24 installation, npm reported:

```text
npm warn allow-scripts
```

and listed packages with installation scripts, including:

```text
omniroute
keytar
tls-client-node
onnxruntime-node
sharp
core-js
@parcel/watcher
@swc/core
protobufjs
koffi
esbuild
```

npm 11 provides an `allow-scripts` policy for global installations, and the setting can be persisted at user scope.

The configuration used during the troubleshooting was:

```cmd
npm config set allow-scripts=omniroute,keytar,tls-client-node,onnxruntime-node,sharp,core-js,@parcel/watcher,@swc/core,protobufjs,koffi,esbuild --location=user
```

Then OmniRoute was reinstalled:

```cmd
npm install -g omniroute
```

The purpose is to allow the required package lifecycle scripts instead of leaving them pending.

Do **not** use:

```cmd
npm config set dangerously-allow-all-scripts=true
```

as a general solution. npm documents that option as a broad bypass and recommends against it.

---

# 8. Verify the Actual OmniRoute CLI

The OmniRoute package exposes:

```text
omniroute → bin/omniroute.mjs
```

This is confirmed by the project/package metadata.

Check the installed CLI file:

```cmd
dir "%APPDATA%\npm\node_modules\omniroute\bin\omniroute.mjs"
```

The file should exist.

Then:

```cmd
omniroute --version
```

Expected version:

```text
3.8.49
```

OmniRoute documents `--version` as the CLI version command.

---

# 9. Why the First `omniroute --version` Failed

The first Node-20 installation failed, leaving an incomplete package.

The resulting command produced:

```text
Cannot find module:
...\omniroute\bin\omniroute.mjs
```

After moving to Node 24, OmniRoute installed successfully.

A later problem was introduced while creating a custom Windows wrapper.

The screenshot showed:

```text
Select an app to open 'omniroute'
```

This indicates that Windows/PowerShell was resolving an incorrect command/file rather than executing the intended `.cmd` wrapper.

The most likely confirmed issue from the session is that the wrapper was not created/resolved as the intended executable `.cmd` file.

---

# 10. Permanent OmniRoute Command

The desired user experience is:

```cmd
omniroute
```

instead of manually typing:

```cmd
nvm use 24.19.0
omniroute
```

The intended wrapper is:

```text
C:\Tools\bin\omniroute.cmd
```

and the real npm-generated OmniRoute command is:

```text
%APPDATA%\npm\omniroute.cmd
```

The wrapper must be placed **before** the npm global directory in `PATH`.

---

# 11. Recreate the Wrapper Safely

Do not use Notepad for this step because Windows may hide the `.cmd` extension.

Use PowerShell to create the file directly.

Open PowerShell and run:

```powershell
New-Item -ItemType Directory -Force C:\Tools\bin | Out-Null
```

Then:

```powershell
@'
@echo off

nvm use 24.19.0 >nul
if errorlevel 1 (
    echo Failed to switch to Node 24.19.0
    exit /b 1
)

call "%APPDATA%\npm\omniroute.cmd" %*

nvm use 20.19.5 >nul
'@ | Set-Content -Encoding ASCII C:\Tools\bin\omniroute.cmd
```

This creates exactly:

```text
C:\Tools\bin\omniroute.cmd
```

---

# 12. Remove an Incorrect Extensionless Wrapper

Because the previous screenshot showed Windows trying to open `omniroute` as an application/file, check the directory:

```powershell
Get-ChildItem C:\Tools\bin | Select-Object Name, Extension
```

The desired file is:

```text
omniroute.cmd
```

If an extensionless file named:

```text
omniroute
```

exists, remove it:

```powershell
Remove-Item C:\Tools\bin\omniroute -Force
```

Also remove an incorrectly created text file if present:

```powershell
Remove-Item C:\Tools\bin\omniroute.txt -Force -ErrorAction SilentlyContinue
Remove-Item C:\Tools\bin\omniroute.cmd.txt -Force -ErrorAction SilentlyContinue
```

Do not remove the real npm installation under `%APPDATA%\npm`.

---

# 13. Put the Wrapper First in PATH

The user PATH should contain:

```text
C:\Tools\bin
```

before:

```text
%APPDATA%\npm
```

The ordering matters.

Check from PowerShell:

```powershell
$env:PATH -split ';'
```

Check command resolution:

```powershell
Get-Command omniroute -All
```

Or from CMD:

```cmd
where omniroute
```

The first result should be:

```text
C:\Tools\bin\omniroute.cmd
```

and the npm-generated command should appear after it:

```text
%APPDATA%\npm\omniroute.cmd
```

---

# 14. Test the Wrapper Directly

Before relying on PATH, execute the wrapper directly:

```powershell
C:\Tools\bin\omniroute.cmd --version
```

It should:

1. Switch to Node `24.19.0`.
2. Execute the actual OmniRoute CLI.
3. Return to Node `20.19.5`.

Then check:

```powershell
node --version
```

Expected after OmniRoute exits:

```text
v20.19.5
```

---

# 15. Final Usage

Once the wrapper is correctly resolved:

```cmd
omniroute
```

or:

```cmd
omniroute --version
```

No manual:

```cmd
nvm use 24.19.0
```

is required.

The intended flow is:

```text
omniroute
    ↓
C:\Tools\bin\omniroute.cmd
    ↓
nvm use 24.19.0
    ↓
%APPDATA%\npm\omniroute.cmd
    ↓
OmniRoute
    ↓
nvm use 20.19.5
```

---

# 16. CMD and PowerShell

The same `.cmd` wrapper can be invoked from both environments.

### CMD

```cmd
node --version
```

Normal result:

```text
v20.19.5
```

Then:

```cmd
omniroute --version
```

### PowerShell

```powershell
node --version
```

Normal result:

```text
v20.19.5
```

Then:

```powershell
omniroute --version
```

The wrapper handles the temporary Node 24 switch.

---

# 17. Important NVM Limitation

The wrapper is a **convenience isolation mechanism**, not a separate Node runtime namespace.

`nvm use` changes the NVM-managed Node symlink. Therefore, while OmniRoute is running, the active NVM version for that environment is Node 24.

The wrapper restores Node 20 after OmniRoute exits:

```cmd
nvm use 20.19.5
```

For a long-running OmniRoute server, Node 24 remains active until the process exits and the wrapper reaches the restore command.

This distinction matters if multiple shells/processes are simultaneously relying on the NVM-managed symlink.

---

# 18. Direct Runtime Isolation Alternative

If true process-level isolation is required, the wrapper can directly execute the Node 24 executable rather than calling `nvm use`.

The confirmed NVM installation root was:

```text
%USERPROFILE%\nvm
```

and Node 24 was installed at:

```text
%USERPROFILE%\nvm\v24.19.0
```

The OmniRoute CLI entry point is:

```text
%APPDATA%\npm\node_modules\omniroute\bin\omniroute.mjs
```

Therefore the conceptual direct invocation is:

```cmd
"%USERPROFILE%\nvm\v24.19.0\node.exe" "%APPDATA%\npm\node_modules\omniroute\bin\omniroute.mjs" --version
```

This avoids changing the NVM symlink for the process.

**However, this direct-runtime wrapper was not tested during the session.** Treat it as an optional refinement, not as a confirmed final configuration.

---

# 19. Troubleshooting

## `omniroute` is not recognized

Check:

```cmd
where omniroute
```

If nothing is returned, verify:

```cmd
dir "%APPDATA%\npm\omniroute.cmd"
```

Also verify that `%APPDATA%\npm` is in PATH.

---

## PowerShell says "Select an app to open 'omniroute'"

Check:

```powershell
Get-Command omniroute -All
```

and:

```powershell
Get-ChildItem C:\Tools\bin | Select-Object Name, Extension
```

The first resolved command should be:

```text
C:\Tools\bin\omniroute.cmd
```

There should not be an extensionless:

```text
C:\Tools\bin\omniroute
```

Delete it if present:

```powershell
Remove-Item C:\Tools\bin\omniroute -Force
```

Then recreate the `.cmd` wrapper exactly as described above.

---

## Wrapper says the npm OmniRoute command cannot be found

Check:

```cmd
dir "%APPDATA%\npm\omniroute.cmd"
```

Then:

```cmd
dir "%APPDATA%\npm\node_modules\omniroute\bin\omniroute.mjs"
```

Both should exist.

---

## `node --version` remains Node 20 after `nvm use 24.19.0`

Check:

```cmd
where node
```

The correct result is:

```text
%USERPROFILE%\nvm\nodejs\node.exe
```

If a version-specific path such as:

```text
%USERPROFILE%\nvm\v20.19.5
```

appears before the NVM symlink, remove that version-specific path from Windows PATH.

---

## OmniRoute installation fails with `better-sqlite3` / `node-gyp`

First check:

```cmd
node --version
```

The OmniRoute installation should be performed with the supported Node runtime, not the old Node 20 environment.

For this setup:

```cmd
nvm use 24.19.0
```

Then:

```cmd
npm install -g omniroute
```

The original Node-20 failure occurred because no compatible `better-sqlite3` prebuilt binary was found and npm attempted a local native compilation.

---

## npm shows peer dependency warnings

Warnings such as:

```text
ERESOLVE overriding peer dependency
```

were observed during the successful OmniRoute installation.

They involved dependencies such as:

```text
@emoji-mart/react
react
marked-terminal
marked
```

These warnings did not cause the final `npm install -g omniroute` command to fail.

---

## npm shows `allow-scripts`

Check:

```cmd
npm config get allow-scripts
```

If the required scripts are not permitted, configure the user-level policy:

```cmd
npm config set allow-scripts=omniroute,keytar,tls-client-node,onnxruntime-node,sharp,core-js,@parcel/watcher,@swc/core,protobufjs,koffi,esbuild --location=user
```

Then reinstall:

```cmd
npm install -g omniroute
```

npm documents `allow-scripts` specifically for controlling lifecycle scripts in global installations.

---

# 20. Useful OmniRoute Commands

Once the CLI is working:

```cmd
omniroute --version
```

Show help:

```cmd
omniroute --help
```

Start OmniRoute:

```cmd
omniroute
```

The documented CLI also includes commands such as:

```cmd
omniroute setup
```

```cmd
omniroute doctor
```

```cmd
omniroute providers list
```

```cmd
omniroute providers test-all
```

```cmd
omniroute health
```

```cmd
omniroute logs
```

The project documents `omniroute` as the server-start command and `20128` as its default port.

---

# 21. Confirmed Final State

The confirmed working Node/NVM state is:

```text
NVM root:
%USERPROFILE%\nvm

Normal Node:
20.19.5

OmniRoute Node:
24.19.0

Node 20:
nvm use 20.19.5

Node 24:
nvm use 24.19.0

OmniRoute:
3.8.49

Global npm package:
%APPDATA%\npm\node_modules\omniroute

CLI entry:
%APPDATA%\npm\node_modules\omniroute\bin\omniroute.mjs
```

The Node switching itself was successfully fixed and verified:

```cmd
nvm use 20.19.5
node --version
```

```text
v20.19.5
```

and:

```cmd
nvm use 24.19.0
node --version
```

```text
v24.19.0
```

The remaining issue at the end of the session was **only the persistent `omniroute` wrapper resolution**: PowerShell was opening `omniroute` through the Windows "Select an app" dialog instead of executing the `.cmd` wrapper.

---

# 22. Gap / Assumption

The following was **not explicitly confirmed after the final wrapper recreation**:

- That `C:\Tools\bin\omniroute.cmd` was successfully recreated.
- That `Get-Command omniroute -All` / `where omniroute` now resolves the wrapper first.
- That `omniroute --version` successfully returns `3.8.49` through the final wrapper.
- That OmniRoute has been successfully started as a long-running server after the wrapper fix.

Therefore, those should be treated as the **remaining verification steps**, not as completed facts.

---

# References

- [OmniRoute on npm](https://www.npmjs.com/package/omniroute?utm_source=chatgpt.com) — published package and runtime/package information.
- [OmniRoute CLI entry point on GitHub](https://github.com/diegosouzapw/OmniRoute/blob/release/v3.8.50/bin/omniroute.mjs?utm_source=chatgpt.com) — confirms `bin/omniroute.mjs` as the CLI entry point.
- [npm configuration documentation](https://docs.npmjs.com/cli/using-npm/config/?utm_source=chatgpt.com) — `allow-scripts` behavior for global installations.
- [npm install-scripts documentation](https://docs.npmjs.com/cli/v11/commands/npm-install-scripts/?utm_source=chatgpt.com) — lifecycle-script approval behavior.
