import ast
import os
import argparse
import sys
from collections import defaultdict
from pathlib import Path

# --- Graph Logic ---

class ImportVisitor(ast.NodeVisitor):
    def __init__(self, current_file, root_dir):
        self.current_file = Path(current_file).resolve()
        self.root_dir = Path(root_dir).resolve()
        self.imports = set()

    def visit_Import(self, node):
        for alias in node.names:
            self._resolve_import(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module or ""
        level = node.level or 0
        
        if level > 0:
            # Handle relative imports (., ..)
            # This is a simplified resolver for static analysis
            pkg_path = self.current_file.parent
            for _ in range(level - 1):
                pkg_path = pkg_path.parent
            
            if module:
                # Attempt to resolve relative import to a file
                self._resolve_relative(pkg_path, module)
            else:
                # import from .
                pass
        else:
            self._resolve_import(module)
            
        self.generic_visit(node)

    def _resolve_relative(self, base_path, module_name):
        # Convert module dot notation to path
        rel_path = module_name.replace('.', os.sep)
        potential_paths = [
            base_path / f"{rel_path}.py",
            base_path / rel_path / "__init__.py"
        ]
        for p in potential_paths:
            if p.exists():
                try:
                    # Normalize relative to root for the graph
                    rel = p.relative_to(self.root_dir)
                    self.imports.add(str(rel))
                    return
                except ValueError:
                    continue

    def _resolve_import(self, module_name):
        # Maps "my_pkg.utils" -> "my_pkg/utils.py"
        parts = module_name.split('.')
        current_check = self.root_dir
        
        # Walk down the path to find the file
        for i, part in enumerate(parts):
            current_check = current_check / part
            
            # Check if it's a file (.py) or package (dir/__init__.py)
            py_file = current_check.with_suffix('.py')
            init_file = current_check / "__init__.py"

            target = None
            if py_file.exists() and py_file.is_file():
                target = py_file
            elif init_file.exists() and init_file.is_file():
                target = init_file
            
            if target:
                try:
                    rel_path = target.relative_to(self.root_dir)
                    self.imports.add(str(rel_path))
                    return # Found the internal dependency
                except ValueError:
                    pass # Outside root, ignore (external lib)

# --- Mermaid Formatter ---

def sanitize(name):
    """Sanitize filenames for Mermaid node IDs."""
    return name.replace(os.sep, '_').replace('.', '_').replace('-', '_')

def generate_mermaid(graph, root_dir):
    lines = ["graph TD"]
    
    # Define styles
    lines.append("    classDef component fill:#e1f5fe,stroke:#01579b,stroke-width:2px;")
    lines.append("    classDef util fill:#f3e5f5,stroke:#4a148c,stroke-width:1px;")
    
    # Nodes and Edges
    sorted_sources = sorted(graph.keys())
    for source in sorted_sources:
        targets = sorted(graph[source])
        src_id = sanitize(source)
        
        # Simple heuristic for styling: "utils" or "common" usually means utility
        style_class = "util" if "util" in source or "common" in source else "component"
        lines.append(f"    {src_id}[{source}]:::{style_class}")
        
        for target in targets:
            tgt_id = sanitize(target)
            lines.append(f"    {src_id} --> {tgt_id}")
            
    return "\n".join(lines)

# --- Main Execution ---

def analyze_directory(target_dir):
    root = Path(target_dir).resolve()
    dependency_graph = defaultdict(set)
    
    for path in root.rglob("*.py"):
        if any(part in path.parts for part in ["venv", ".git", "__pycache__", "tests"]):
            continue
            
        try:
            rel_path = path.relative_to(root)
            with open(path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(path))
            
            visitor = ImportVisitor(path, root)
            visitor.visit(tree)
            
            if visitor.imports:
                dependency_graph[str(rel_path)] = visitor.imports
            else:
                # Add isolated files too
                dependency_graph[str(rel_path)] = set()
                
        except Exception:
            # Fail silently on syntax errors in target code to keep the tool robust
            continue
            
    return dependency_graph

def main():
    parser = argparse.ArgumentParser(description="Generate Mermaid Dependency Graph")
    parser.add_argument("target", help="Root directory to analyze")
    parser.add_argument("--format", choices=["mermaid", "json"], default="mermaid")
    args = parser.parse_args()

    graph = analyze_directory(args.target)

    if args.format == "mermaid":
        print(generate_mermaid(graph, args.target))
    else:
        # JSON output useful for intermediate processing
        import json
        # Convert sets to lists for JSON serialization
        json_graph = {k: list(v) for k, v in graph.items()}
        print(json.dumps(json_graph, indent=2))

if __name__ == "__main__":
    main()
