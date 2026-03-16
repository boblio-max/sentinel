from dataclasses import dataclass, field
from typing import Any, Optional
import time

@dataclass
class NodeResult:
    success: bool
    data: Any
    error: str
    duration_ms: float
    node_name: str

class Node:
    """Base class for all Sentinel behaviors."""
    def __init__(self, name: str):
        self.name = name
        self.description = "Base Node"
        self._enabled = True

    def execute(self, context: dict) -> NodeResult:
        """Abstract execution method. Override in subclasses."""
        raise NotImplementedError("Node must implement execute()")

    def ok(self, data: Any = None) -> NodeResult:
        """Helper to return a successful NodeResult."""
        return NodeResult(success=True, data=data, error="", duration_ms=0.0, node_name=self.name)

    def fail(self, error: str) -> NodeResult:
        """Helper to return a failed NodeResult."""
        return NodeResult(success=False, data=None, error=error, duration_ms=0.0, node_name=self.name)

    def run(self, context: dict) -> NodeResult:
        """Internal runner wrapping execute() with timing and error handling. Never raises."""
        if not self._enabled:
            return self.ok(data={"status": "disabled"})
            
        start_time = time.perf_counter()
        try:
            result = self.execute(context)
            if not isinstance(result, NodeResult):
                result = self.fail(f"Execute must return NodeResult, got {type(result)}")
        except Exception as e:
            result = self.fail(str(e))
            
        end_time = time.perf_counter()
        result.duration_ms = (end_time - start_time) * 1000
        result.node_name = self.name
        return result

    def test(self) -> None:
        """Runs the node in simulation mode and prints pass/fail with timing."""
        print(f"Testing {self.name} ({self.description})")
        context = {}
        result = self.run(context)
        if result.success:
            print(f"[\033[92mPASS\033[0m] {self.name} in {result.duration_ms:.2f}ms")
            if result.data:
                print(f"       Data: {result.data}")
        else:
            print(f"[\033[91mFAIL\033[0m] {self.name} in {result.duration_ms:.2f}ms")
            print(f"       Error: {result.error}")

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False
