import ast
import os
import json
import argparse
from typing import Dict, Any, List

class StructureVisitor(ast.NodeVisitor):
    def __init__(self):
        self.classes: List[Dict[str, Any]] = []
        self.functions: List[Dict[str, Any]] = []
        self.imports: List[str] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ''
        for alias in node.names:
            self.imports.append(f"{module}.{alias.name}")
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        bases = [self._get_name(b) for b in node.bases]
        methods = []
        
        # Check for methods within the class
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append({
                    'name': item.name,
                    'line': item.lineno,
                    'args': [a.arg for a in item.args.args if a.arg != 'self'],
                    'docstring_len': len(ast.get_docstring(item) or "")
                })

        self.classes.append({
            'name': node.name,
            'line': node.lineno,
            'bases': bases,
            'methods': methods,
            'docstring': ast.get_docstring(node)
        })
        # We don't generic_visit ClassDef to avoid duplicating methods in the global function list

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._handle_func(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._handle_func(node)

    def _handle_func(self, node):
        self.functions.append({
            'name': node.name,
            'line': node.lineno,
            'args': [a.arg for a in node.args.args],
            'docstring_len': len(ast.get_docstring(node) or "")
        })

    def _get_name(self, node):
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return "complex_type"

def parse_file(filepath: str) -> Dict[str, Any]:
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read(), filename=filepath)
            visitor = StructureVisitor()
            visitor.visit(tree)
            return {
                "file": filepath,
                "classes": visitor.classes,
                "functions": visitor.functions,
                "imports": visitor.imports
            }
        except Exception as e:
            return {"file": filepath, "error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="AST Mapper for Retrodocumentation")
    parser.add_argument("target", help="Directory or file to map")
    parser.add_argument("--exclude", nargs='*', default=['venv', '__pycache__', '.git', 'tests'])
    parser.add_argument("--format", choices=['json'], default='json', help="Output format (currently only json supported)")
    args = parser.parse_args()

    results = []
    
    if os.path.isfile(args.target):
        results.append(parse_file(args.target))
    else:
        for root, dirs, files in os.walk(args.target):
            # Modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if d not in args.exclude]
            
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    results.append(parse_file(full_path))

    # Output JSON compact enough for an LLM
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
