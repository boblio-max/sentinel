import time
import json
import os
from datetime import datetime
from typing import Callable, Any
from sentinel import Node, NodeResult, Workflow

class WaitNode(Node):
    def __init__(self, seconds: float):
        super().__init__(name=f"Wait({seconds}s)")
        self.description = f"Pause execution for {seconds} seconds."
        self.seconds = seconds

    def execute(self, context: dict) -> NodeResult:
        if context.get("simulation_mode"):
            print(f"[Sentinel SIM] Waiting for {self.seconds} seconds")
        else:
            time.sleep(self.seconds)
        return self.ok(data={"waited_seconds": self.seconds})


class PrintNode(Node):
    def __init__(self, message: str = "", context_key: str = None):
        super().__init__(name="Print")
        self.description = "Print a message or a value from the context."
        self.message = message
        self.context_key = context_key

    def execute(self, context: dict) -> NodeResult:
        if self.context_key:
            val = context.get(self.context_key, "<NOT FOUND>")
            out = f"{self.message}{val}"
        else:
            out = self.message
        print(out)
        return self.ok(data={"printed": out})


class LogNode(Node):
    def __init__(self, output: str = None):
        super().__init__(name="Log")
        self.description = "Log context snapshot to a list in context and optionally to a file."
        self.output = output

    def execute(self, context: dict) -> NodeResult:
        import copy
        
        # safely snapshot context
        snapshot = {}
        for k, v in context.items():
            if k == "_log_history":
                continue
            try:
                json.dumps({k: v})
                snapshot[k] = copy.deepcopy(v)
            except Exception:
                snapshot[k] = str(v)
                
        snapshot_time = datetime.now().isoformat()
        entry = {"time": snapshot_time, "context": snapshot}
        
        if "_log_history" not in context:
            context["_log_history"] = []
        context["_log_history"].append(entry)
        
        if self.output:
            try:
                os.makedirs(os.path.dirname(os.path.abspath(self.output)), exist_ok=True)
                with open(self.output, "a") as f:
                    f.write(json.dumps(entry) + "\n")
            except Exception as e:
                return self.fail(f"Failed to write to {self.output}: {str(e)}")
                
        return self.ok(data={"logged": True})


class BranchNode(Node):
    def __init__(self, condition: Callable[[dict], bool], if_true: Workflow, if_false: Workflow = None):
        super().__init__(name="Branch")
        self.description = "Conditional branch execution."
        self.condition = condition
        self.if_true = if_true
        self.if_false = if_false

    def execute(self, context: dict) -> NodeResult:
        try:
            cond = self.condition(context)
        except Exception as e:
            return self.fail(f"Condition evaluation failed: {str(e)}")
            
        if cond:
            res = self.if_true.run(context)
            return self.ok(data={"branch": "true", "result": res.success})
        elif self.if_false:
            res = self.if_false.run(context)
            return self.ok(data={"branch": "false", "result": res.success})
            
        return self.ok(data={"branch": "skipped"})


class LoopNode(Node):
    def __init__(self, workflow: Workflow, times: int = None, until: Callable[[dict], bool] = None, max_iterations: int = 1000):
        super().__init__(name="Loop")
        self.description = "Repeat a workflow a set number of times or until a condition is met."
        self.workflow = workflow
        self.times = times
        self.until = until
        self.max_iterations = max_iterations

    def execute(self, context: dict) -> NodeResult:
        iters = 0
        while True:
            if self.times is not None and iters >= self.times:
                break
            if self.until is not None:
                try:
                    if self.until(context):
                        break
                except Exception as e:
                    return self.fail(f"Until condition evaluation failed: {str(e)}")
            if iters >= self.max_iterations:
                return self.fail(f"Max iterations ({self.max_iterations}) reached.")
                
            res = self.workflow.run(context)
            if not res.success:
                return self.fail(f"Workflow iteration {iters} failed: {res.failed_node}")
            
            iters += 1
            
        return self.ok(data={"iterations": iters})


class RepeatNode(Node):
    def __init__(self, node: Node, times: int):
        super().__init__(name=f"Repeat({node.name})")
        self.description = f"Repeat node {node.name} {times} times."
        self.node = node
        self.times = times

    def execute(self, context: dict) -> NodeResult:
        for i in range(self.times):
            res = self.node.run(context)
            if not res.success:
                return self.fail(f"Iteration {i} failed: {res.error}")
        return self.ok(data={"times_repeated": self.times})


class SetContextNode(Node):
    def __init__(self, key: str, value: Any = None, fn: Callable[[dict], Any] = None):
        super().__init__(name=f"SetContext({key})")
        self.description = f"Set context value for {key}."
        self.key = key
        self.value = value
        self.fn = fn

    def execute(self, context: dict) -> NodeResult:
        if self.fn:
            try:
                val = self.fn(context)
            except Exception as e:
                return self.fail(f"Function evaluation failed: {str(e)}")
        else:
            val = self.value
            
        context[self.key] = val
        return self.ok(data={"key": self.key, "value": val})
