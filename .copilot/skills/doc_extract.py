import ast
import tokenize
import argparse
import sys
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class DocItem:
    name: str
    kind: str  # 'class', 'function', 'method'
    line_start: int
    line_end: int
    docstring: Optional[str] = None
    comments: List[str] = field(default_factory=list)
    todos: List[str] = field(default_factory=list)

class DocExtractor:
    def __init__(self, filepath):
        self.filepath = filepath
        self.source_lines = []
        self.items: List[DocItem] = []
        self.orphaned_comments: List[str] = [] # Comments at top of file
        
    def parse(self):
        with open(self.filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            self.source_lines = content.splitlines()
        
        # 1. Parse Structure (AST)
        tree = ast.parse(content)
        self._visit_nodes(tree)
        
        # 2. Extract Comments (Tokenize)
        self._attach_comments(content)
        
        return self

    def _visit_nodes(self, tree):
        # Flatten the tree into a list of items we care about
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                kind = 'class' if isinstance(node, ast.ClassDef) else 'function'
                name = node.name
                
                # Handle methods (heuristic: indented implies method if inside class)
                if getattr(node, 'col_offset', 0) > 0:
                     kind = 'method'

                item = DocItem(
                    name=name,
                    kind=kind,
                    line_start=node.lineno,
                    line_end=node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
                    docstring=ast.get_docstring(node)
                )
                self.items.append(item)
        
        # Sort items by line number to make comment attachment easier
        self.items.sort(key=lambda x: x.line_start)

    def _attach_comments(self, content):
        import io
        # We use a generator to process tokens
        tokens = tokenize.generate_tokens(io.StringIO(content).readline)
        
        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                comment_text = tok.string.strip()
                line_no = tok.start[0]
                
                # Check for TODOs
                if "TODO" in comment_text or "FIXME" in comment_text:
                    # Find nearest item (the one wrapping this line or immediately following)
                    owner = self._find_owner(line_no)
                    if owner:
                        owner.todos.append(f"Line {line_no}: {comment_text}")
                
                # Logic to attach comment to the "next" function (Preceding comments)
                # or "current" function (Inline/Internal comments)
                attached = False
                
                # 1. Check if it belongs to a known item (inside its body)
                for item in self.items:
                    if item.line_start <= line_no <= item.line_end:
                        item.comments.append(f"L{line_no}: {comment_text}")
                        attached = True
                        break
                
                # 2. If not inside, check if it's immediately BEFORE an item (Header comment)
                if not attached:
                    for item in self.items:
                        if item.line_start > line_no:
                            # Verify proximity (e.g. within 5 lines of the definition)
                            if item.line_start - line_no < 5:
                                item.comments.insert(0, comment_text) # Prepend to appear at top
                                attached = True
                            break
                            
                if not attached:
                    self.orphaned_comments.append(f"L{line_no}: {comment_text}")

    def _find_owner(self, line_no):
        # Find tightest matching scope
        matches = [i for i in self.items if i.line_start <= line_no <= i.line_end]
        if matches:
            return matches[-1] # Return the most nested one
        return None

    def to_markdown(self):
        md = [f"# Documentation: {self.filepath}", ""]
        
        if self.orphaned_comments:
            md.append("## Module Comments")
            for c in self.orphaned_comments:
                md.append(f"- `{c}`")
            md.append("")

        for item in self.items:
            icon = "C" if item.kind == 'class' else "f"
            md.append(f"### ({icon}) {item.name}")
            if item.docstring:
                md.append(f"> **Docstring**: {item.docstring.strip().splitlines()[0]}...") # Summary only
            
            if item.comments:
                md.append("\n**Comments**:")
                for c in item.comments:
                    if "TODO" in c or "FIXME" in c:
                        md.append(f"- 🔴 {c}")
                    else:
                        md.append(f"- {c}")
            
            md.append(f"\n*Defined at line {item.line_start}*")
            md.append("---")
            
        return "\n".join(md)

def main():
    parser = argparse.ArgumentParser(description="Extract Docstrings and Comments")
    parser.add_argument("file", help="Python file to analyze")
    parser.add_argument("--format", choices=["json", "md"], default="md")
    args = parser.parse_args()

    extractor = DocExtractor(args.file).parse()
    
    if args.format == "json":
        # Simple serialization
        print(json.dumps([vars(i) for i in extractor.items], indent=2))
    else:
        print(extractor.to_markdown())

if __name__ == "__main__":
    main()
