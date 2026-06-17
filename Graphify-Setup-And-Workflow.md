# 🕸️ Graphify Setup & Workflow

## 📦 Installation

### Install UV

**Windows**

```bash
winget install astral-sh.uv
```

**Linux / macOS**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

### Install Graphify

```bash
uv tool install graphifyy
```

Restart your terminal after installation.

If `graphify` isn't found, reload your shell.

**Windows (PowerShell)**

```powershell
uv tool update-shell
```

**Linux**

```bash
source ~/.bashrc
# or
source ~/.zshrc
```

Verify:

```bash
graphify --version
```

---

# ⚙️ OpenCode Integration

Install the Graphify skill for OpenCode:

```bash
graphify install --platform opencode
```

Verify installation:

```bash
graphify --help
```

Launch OpenCode:

```bash
opencode
```

---

# 📁 Project Structure

```
project/
│
├── strategies/      ← Analyze only this folder
├── app/
├── docs/
└── ...
```

Move into the directory before running Graphify:

```bash
cd strategies
```

> All commands below assume the current directory is `./strategies`.

---

# 🚀 Build Graph

Generate the project graph:

```bash
graphify extract .
```

Outputs:

```
graphify-out/
├── graph.html
├── GRAPH_REPORT.md
└── graph.json
```

Generate Mermaid architecture diagrams:

```bash
graphify export callflow-html
```

---

# 📊 Update Graph

Re-extract only changed files:

```bash
graphify update .
```

Re-cluster without re-extraction:

```bash
graphify cluster-only .
```

Skip HTML visualization:

```bash
graphify cluster-only . --no-viz
```

---

# 🔍 Query Graph

Explain a symbol:

```bash
graphify explain "TradeEngine"
```

Shortest dependency path:

```bash
graphify path "OrderManager" "RiskManager"
```

Ask architecture questions:

```bash
graphify query "How does order execution work?"
```

Find impacted symbols:

```bash
graphify affected "RiskManager"
```

---

# 📈 Diagnostics

Detect graph issues:

```bash
graphify diagnose multigraph
```

Benchmark graph compression:

```bash
graphify benchmark
```

---

# 🔀 Merge Graphs

Merge multiple repositories:

```bash
graphify merge-graphs repo1.json repo2.json
```

---

# 🧠 Global Graph

Add project:

```bash
graphify global add graphify-out/graph.json --as strategies
```

List projects:

```bash
graphify global list
```

Remove project:

```bash
graphify global remove strategies
```

---

# 🔄 Git Hooks

Automatically refresh graphs after commits:

```bash
graphify hook install
```

Remove hooks:

```bash
graphify hook uninstall
```

Check status:

```bash
graphify hook status
```

---

# 📚 Useful Commands

```bash
graphify extract .
graphify update .
graphify cluster-only .
graphify cluster-only . --no-viz
graphify export callflow-html

graphify explain "TradeEngine"
graphify query "How is strategy execution implemented?"
graphify path "Strategy" "BrokerAPI"
graphify affected "PositionManager"

graphify diagnose multigraph
graphify benchmark

graphify hook install
graphify global list
```

---

# 📂 Generated Files

```
graphify-out/
├── graph.html
├── GRAPH_REPORT.md
├── graph.json
├── GRAPH_TREE.html
└── architecture.html
```

---

# 💡 OpenCode Workflow

```bash
cd strategies

graphify extract .

graphify export callflow-html

opencode
```

Then inside OpenCode:

```
Explain the architecture using graphify-out/GRAPH_REPORT.md.

Use graphify-out/graph.json as the primary source of truth.

Before answering implementation questions, inspect the graph relationships instead of scanning every file.

When discussing functions, classes, or modules, reference the graph structure first and then the source code only when necessary.
```

---

# 🔗 References

- **Official Graphify Repository:** [safishamsi/graphify on GitHub](https://github.com/safishamsi/graphify?utm_source=chatgpt.com)
- **Documentation & Releases:** Refer to the repository README, releases, and discussions for the latest installation instructions, supported AI assistants, and new features.
