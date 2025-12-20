import os
import sys
import subprocess
import shutil
import json
import time

# ANSI Colors for a cool CLI experience
GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RESET = "\033[0m"

SKILLS_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(SKILLS_DIR, "_mission_test_scaffold")

def print_status(step, message, status="..."):
    sys.stdout.write(f"{CYAN}[{step}]{RESET} {message:<50} {YELLOW}{status}{RESET}\r")
    sys.stdout.flush()

def print_result(step, message, success):
    symbol = f"{GREEN}✔ PASS{RESET}" if success else f"{RED}✘ FAIL{RESET}"
    print(f"{CYAN}[{step}]{RESET} {message:<50} {symbol}")

def create_mock_environment():
    """Creates a temporary folder with 2 python files to test relations and parsing."""
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR)

    # File 1: Dependency
    with open(os.path.join(TEMP_DIR, "db_driver.py"), "w") as f:
        f.write('''
class Database:
    """Handles connection."""
    def connect(self):
        pass
''')

    # File 2: Main Logic (Imports dependency, has TODO)
    with open(os.path.join(TEMP_DIR, "main_app.py"), "w") as f:
        f.write('''
import db_driver

def run():
    # TODO: This needs error handling
    db = db_driver.Database()
    db.connect()
''')

def run_test(script_name, args, validator_func):
    """Runs a skill script and validates stdout."""
    script_path = os.path.join(SKILLS_DIR, script_name)
    
    if not os.path.exists(script_path):
        return False, "Script not found"

    cmd = [sys.executable, script_path] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return False, f"Error: {result.stderr}"
        
        valid, msg = validator_func(result.stdout)
        return valid, msg
    except Exception as e:
        return False, str(e)

# --- Validators ---

def validate_ast(output):
    try:
        data = json.loads(output)
        # Check if we found the class in db_driver
        found = False
        for file_entry in data:
            for cls in file_entry.get("classes", []):
                if cls["name"] == "Database":
                    found = True
        return found, "Found 'Database' class"
    except json.JSONDecodeError:
        return False, "Invalid JSON output"

def validate_graph(output):
    if "graph TD" in output and "db_driver" in output:
        return True, "Generated Mermaid graph"
    return False, "Mermaid syntax missing"

def validate_doc(output):
    if "TODO" in output and "error handling" in output:
        return True, "Found TODO comment"
    return False, "Failed to extract comment"

# --- Main Mission ---

def main():
    print(f"{CYAN}🚀 INITIATING MISSION CONTROL: SKILL DIAGNOSTICS{RESET}")
    print(f"{'='*60}")

    # 1. Setup
    print_status("SETUP", "Creating mock environment")
    create_mock_environment()
    time.sleep(0.5)
    print_result("SETUP", "Creating mock environment", True)

    # 2. Test AST Map
    print_status("AST", "Testing ast_map.py")
    success, msg = run_test("ast_map.py", [TEMP_DIR], validate_ast)
    print_result("AST", f"Parser Check ({msg})", success)

    # 3. Test Graph Builder
    print_status("GRAPH", "Testing graph_builder.py")
    success, msg = run_test("graph_builder.py", [TEMP_DIR, "--format", "mermaid"], validate_graph)
    print_result("GRAPH", f"Dependency Check ({msg})", success)

    # 4. Test Doc Extract
    print_status("DOCS", "Testing doc_extract.py")
    target = os.path.join(TEMP_DIR, "main_app.py")
    success, msg = run_test("doc_extract.py", [target], validate_doc)
    print_result("DOCS", f"Intent Check ({msg})", success)

    # 5. Cleanup
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    print(f"{'='*60}")
    
    if success:
        print(f"{GREEN}✅ SYSTEM OPERATIONAL. READY FOR DEPLOYMENT.{RESET}")
    else:
        print(f"{RED}⚠️ SYSTEM FAILURE. CHECK ERROR LOGS.{RESET}")

if __name__ == "__main__":
    main()
