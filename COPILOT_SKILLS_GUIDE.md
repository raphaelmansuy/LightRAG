# 🚀 Using Claude Skills in VSCode Copilot (Dec 2025)

This project is equipped with **Claude Skills**: local Python-based intelligence tools that allow VSCode Copilot to "see" the architecture and intent of the codebase without hallucination.

## 1. Setup (One-Time)

To enable Copilot to use these tools, you must "teach" it the protocols.

1.  Open **[SKILLS.md](SKILLS.md)**.
2.  Scroll to the **Master Prompt: Project Instructions** section.
3.  Copy the entire Markdown block.
4.  Open your **Copilot Chat Settings** (or "Project Instructions" in the Chat view) and paste the content.

---

## 2. Common Prompting Workflows

In the VSCode Chat window, you can now use specific "SOPs" (Standard Operating Procedures) defined in the skills.

### 🔍 Feature Deep Dive (SOP 1)
Use this when you want to understand how a specific part of the system works.
> **Prompt:** `@workspace Perform a 'Feature Deep Dive' on the storage implementation. How does it handle Neo4j?`
>
> **What happens:** Copilot will run `ast_map.py` to find storage files, `graph_builder.py` to see the connections, and `doc_extract.py` to read the developer's notes.

### 🏗️ Architecture Overview (SOP 2)
Use this to get a visual map of a directory.
> **Prompt:** `@workspace Give me an 'Architecture Overview' of the /lightrag/kg folder. Render it as a Mermaid diagram.`
>
> **What happens:** Copilot runs `graph_builder.py` and generates a visual DAG of the internal dependencies.

### 🧹 Technical Debt Audit (SOP 3)
Use this to find TODOs and potential bugs.
> **Prompt:** `@workspace Run a 'Debt Audit' on the core logic. Are there any FIXME or TODO markers I should worry about?`
>
> **What happens:** Copilot runs `doc_extract.py` across the core files and presents a table of technical debt.

---

## 3. Manual Tool Execution

If you want to run the tools yourself to see the raw data:

| Skill | Command | Purpose |
| :--- | :--- | :--- |
| **Cartographer** | `python .copilot/skills/ast_map.py [path]` | Map classes and methods. |
| **Connector** | `python .copilot/skills/graph_builder.py [path]` | Generate Mermaid graphs. |
| **Librarian** | `python .copilot/skills/doc_extract.py [file]` | Extract docstrings and TODOs. |
| **Diagnostics** | `python .copilot/skills/mission_control.py` | Verify the tools are working. |

---

## 🛠️ VSCode Integration

We have integrated these skills into VSCode Tasks for quick access:

1.  Press `Cmd + Shift + P` (macOS) or `Ctrl + Shift + P` (Windows).
2.  Type `Run Task`.
3.  Select one of the **Skill:** tasks.

---

## 🚦 Troubleshooting

If Copilot says it "cannot run local scripts," ensure you have approved the terminal commands in your `.vscode/settings.json`. You can also run the diagnostic tool to check for environment issues:
```bash
python .copilot/skills/mission_control.py
```
