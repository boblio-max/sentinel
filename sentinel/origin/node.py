import os
from sentinel import Node, NodeResult
from .interpreter import OriginInterpreter, RuntimeException

class OriginNode(Node):
    def __init__(self, filepath: str):
        super().__init__(name=f"Origin({os.path.basename(filepath)})")
        self.description = f"Executes Origin script: {filepath}"
        self.filepath = filepath

    def execute(self, context: dict) -> NodeResult:
        if not os.path.exists(self.filepath):
            return self.fail(f"Origin script not found: {self.filepath}")

        try:
            with open(self.filepath, "r") as f:
                code = f.read()
        except Exception as e:
            return self.fail(f"Could not read {self.filepath}: {e}")

        interpreter = OriginInterpreter(context=context)
        try:
            interpreter.run_script(code)
        except RuntimeError as e:
            # We already format nice RuntimeExceptions inside OriginInterpreter
            return self.fail(str(e))
        except Exception as e:
            return self.fail(f"Unhandled Origin execution error: {str(e)}")

        return self.ok(data={"script": self.filepath, "completed": True})
