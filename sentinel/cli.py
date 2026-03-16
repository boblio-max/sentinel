import argparse
import sys
import os
import json
import importlib.util

def create_template(filepath: str, content: str):
    """Utility to safely create scaffolding files."""
    if os.path.exists(filepath):
        print(f"Skipping existing file {filepath}")
        return
    
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(filepath, "w") as f:
        f.write(content)
    print(f"Created {filepath}")

def init_project(args):
    """Scaffold a new Sentinel project."""
    project_name = "my_sentinel_project"
    print(f"Initializing Sentinel project '{project_name}'...")
    
    os.makedirs(project_name, exist_ok=True)
    os.makedirs(os.path.join(project_name, "nodes"), exist_ok=True)
    
    main_py = """import os
from sentinel import Workflow
from sentinel.nodes.core import PrintNode
# from nodes.my_custom_node import MyCustomNode

if __name__ == "__main__":
    flow = Workflow("main", stop_on_failure=True)
    flow.add(PrintNode("Hello from Sentinel Python Workflow!"))
    # flow.add(MyCustomNode("test param"))
    
    result = flow.run()
    print(result.summary())
"""

    main_org = """# Origin Routine
print "Hello from Sentinel Origin Workflow!"
let x: int = 42
print "Value of x is: " + str(x)
"""

    readme = f"""# {project_name}
Sentinel robot project.
Run with: `sentinel run main.py` or `sentinel run main.org`.
"""

    custom_node = """from sentinel import Node, NodeResult

class MyCustomNode(Node):
    def __init__(self, my_param: str):
        super().__init__(name="MyCustomNode")
        self.description = "A template for custom behavior."
        self.my_param = my_param

    def execute(self, context: dict) -> NodeResult:
        # Do custom robot logic here
        return self.ok(data={"processed": self.my_param})
"""

    create_template(os.path.join(project_name, "main.py"), main_py)
    create_template(os.path.join(project_name, "main.org"), main_org)
    create_template(os.path.join(project_name, "README.md"), readme)
    create_template(os.path.join(project_name, "nodes", "__init__.py"), "")
    create_template(os.path.join(project_name, "nodes", "my_custom_node.py"), custom_node)
    
    print("\nProject initialized! Try:")
    print(f"cd {project_name}")
    print("sentinel run main.py")

def new_node(args):
    """Generate a custom node template."""
    node_name = args.name
    filename = f"{node_name}.py"
    
    content = f"""from sentinel import Node, NodeResult

class {node_name}(Node):
    def __init__(self, my_param):
        super().__init__(name="{node_name}")
        self.description = "One sentence explaining what this node does."
        self.my_param = my_param

    def execute(self, context: dict) -> NodeResult:
        # 1. Read from context if needed: val = context.get('key')
        # 2. Perform action (API call, motor spin, calculation)
        # 3. Handle errors: if error: return self.fail("Explanation")
        # 4. Write back to context if needed: context['key'] = new_val
        
        return self.ok(data={{"result": self.my_param}})
"""
    create_template(filename, content)

def run_script(args):
    """Run a Python or Origin file."""
    target = args.file
    if not os.path.exists(target):
        print(f"Error: File '{target}' not found.")
        sys.exit(1)
        
    if target.endswith(".org"):
        from sentinel.origin.interpreter import OriginInterpreter
        with open(target, "r") as f:
            code = f.read()
        interpreter = OriginInterpreter()
        try:
            interpreter.run_script(code)
        except RuntimeError as e:
            print(f"[Origin Error] {e}")
            sys.exit(1)
            
    elif target.endswith(".py"):
        # standard python run
        spec = importlib.util.spec_from_file_location("__main__", target)
        module = importlib.util.module_from_spec(spec)
        sys.modules["__main__"] = module
        spec.loader.exec_module(module)
        
    else:
        print("Error: Unsupported file type. Must be .py or .org")
        sys.exit(1)

def replay_session(args):
    """Replay a recorded session."""
    session_id = args.session_id
    path = os.path.join("sentinel_sessions", f"{session_id}.json")
    
    if not os.path.exists(path):
        print(f"Error: Session file {path} not found.")
        sys.exit(1)
        
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading session: {e}")
        sys.exit(1)
        
    print(f"Replaying Session: {data.get('session_id')}")
    print(f"Workflow: {data.get('workflow')} | Nodes: {len(data.get('nodes', []))}")
    print("-" * 40)
    
    for idx, node_data in enumerate(data.get('nodes', [])):
        status = "\033[92mSUCCESS\033[0m" if node_data.get('success') else "\033[91mFAILED\033[0m"
        node_name = node_data.get('node_name', 'Unknown')
        dur = node_data.get('duration_ms', 0)
        
        print(f"[{idx+1}] {node_name} - {status} ({dur:.1f}ms)")
        
        ctx = node_data.get("context_snapshot", {})
        if ctx:
            print(f"    Context: {json.dumps(ctx)}")
        
        node_output = node_data.get("data", {})
        if node_output:
            print(f"    Data: {json.dumps(node_output)}")
        print()
        
    print("Replay Complete.")

def main():
    parser = argparse.ArgumentParser(description="Sentinel Robotics Framework CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Run
    run_parser = subparsers.add_parser("run", help="Run an Origin (.org) or Python (.py) workflow file.")
    run_parser.add_argument("file", type=str, help="Target file to run")
    
    # Init
    init_parser = subparsers.add_parser("init", help="Scaffold a new Sentinel project.")
    
    # New
    new_parser = subparsers.add_parser("new", help="Generate scaffolding items.")
    new_sub = new_parser.add_subparsers(dest="item", required=True)
    
    new_node_parser = new_sub.add_parser("node", help="Generate a custom node template.")
    new_node_parser.add_argument("name", type=str, help="Name of the Node class (e.g. MyNode)")
    
    # Replay
    replay_parser = subparsers.add_parser("replay", help="Replay a recorded session in simulation.")
    replay_parser.add_argument("session_id", type=str, help="Session ID to replay")
    
    args = parser.parse_args()
    
    if args.command == "run":
        run_script(args)
    elif args.command == "init":
        init_project(args)
    elif args.command == "new":
        if args.item == "node":
            new_node(args)
    elif args.command == "replay":
        replay_session(args)

if __name__ == "__main__":
    main()
