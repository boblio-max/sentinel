from typing import List, Callable, Dict, Any, Union
from dataclasses import dataclass, field
from .node import Node, NodeResult
import time
import os
import json
import concurrent.futures

@dataclass
class WorkflowResult:
    success: bool
    failed_node: str
    total_duration_ms: float
    results: List[NodeResult] = field(default_factory=list)

    def summary(self) -> str:
        """Color-coded terminal output."""
        output = [f"Workflow Result: {'\033[92mSUCCESS\033[0m' if self.success else '\033[91mFAILED\033[0m'} ({self.total_duration_ms:.1f}ms)"]
        for res in self.results:
            icon = "\033[92m✓\033[0m" if res.success else "\033[91m✗\033[0m"
            output.append(f"  {icon} {res.node_name} ({res.duration_ms:.1f}ms)")
            if not res.success:
                output.append(f"      Error: {res.error}")
        return "\n".join(output)

class Workflow:
    def __init__(self, name: str = "workflow", stop_on_failure: bool = True):
        self.name = name
        self.stop_on_failure = stop_on_failure
        self.nodes = [] # Can be Node or List[Node] for parallel
        self.context = {}
        self._on_node_start_hooks = []
        self._on_node_end_hooks = []
        self._session_id = None
        self._session_data = {
            "session_id": "",
            "workflow": self.name,
            "timestamp": 0,
            "nodes": []
        }

    def add(self, node: Node) -> 'Workflow':
        self.nodes.append(node)
        return self

    def add_parallel(self, nodes: List[Node]) -> 'Workflow':
        self.nodes.append(nodes)
        return self

    def set_context(self, key: str, value: Any) -> 'Workflow':
        self.context[key] = value
        return self

    def on_node_start(self, fn: Callable[[str], None]):
        self._on_node_start_hooks.append(fn)

    def on_node_end(self, fn: Callable[[NodeResult], None]):
        self._on_node_end_hooks.append(fn)

    def record(self, session_id: str):
        self._session_id = session_id
        self._session_data["session_id"] = session_id

    def dry_run(self) -> WorkflowResult:
        """Simulates entire workflow without touching hardware."""
        self.set_context("simulation_mode", True)
        print(f"[Sentinel SIM] Starting Dry Run for workflow '{self.name}'")
        return self.run(self.context.copy())

    def _execute_node(self, node: Node, context: dict) -> NodeResult:
        for hook in self._on_node_start_hooks:
            hook(node.name)
            
        result = node.run(context)
        
        for hook in self._on_node_end_hooks:
            hook(result)
            
        if self._session_id:
            import copy
            ctx_snapshot = {}
            for k, v in context.items():
                try:
                    # attempt basic serializable copy
                    json.dumps({k: v})
                    ctx_snapshot[k] = copy.deepcopy(v)
                except Exception:
                    ctx_snapshot[k] = str(v)
            self._session_data["nodes"].append({
                "node_name": result.node_name,
                "success": result.success,
                "duration_ms": result.duration_ms,
                "data": result.data,
                "context_snapshot": ctx_snapshot
            })
            
        return result

    def retry(self, node: Node, attempts: int = 3) -> 'Workflow':
        """Wraps a node in a retry mechanism."""
        class RetryNode(Node):
            def __init__(self, wrapped: Node, max_attempts: int):
                super().__init__(name=f"Retry({wrapped.name})")
                self.wrapped = wrapped
                self.max_attempts = max_attempts
            def execute(self, context: dict) -> NodeResult:
                last_result = None
                for i in range(self.max_attempts):
                    last_result = self.wrapped.run(context)
                    if last_result.success:
                        return last_result
                    print(f"[Retry] {self.wrapped.name} failed (Attempt {i+1}/{self.max_attempts}). Retrying...")
                return last_result

        self.add(RetryNode(node, attempts))
        return self


    def run(self, context: dict = None) -> WorkflowResult:
        start_time = time.perf_counter()
        
        if context is not None:
            self.context.update(context)
            
        if self._session_id:
            self._session_data["timestamp"] = int(time.time())
            self._session_data["nodes"] = []
            
        results = []
        overall_success = True
        failed_node = ""

        def execute_parallel(nodes: List[Node], ctx: dict) -> List[NodeResult]:
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(nodes)) as executor:
                # pass copies of context or same context? We use same context for now, though thread safety is user's responsibility
                futures = {executor.submit(self._execute_node, n, ctx): n for n in nodes}
                res = []
                for f in concurrent.futures.as_completed(futures):
                    res.append(f.result())
                return res

        for item in self.nodes:
            if isinstance(item, list):
                # Parallel execution
                par_results = execute_parallel(item, self.context)
                results.extend(par_results)
                for res in par_results:
                    if not res.success:
                        overall_success = False
                        failed_node = res.node_name
                        if self.stop_on_failure:
                            break
            else:
                # Sequential execute
                res = self._execute_node(item, self.context)
                results.append(res)
                if not res.success:
                    overall_success = False
                    failed_node = res.node_name
                    if self.stop_on_failure:
                        break
                        
            if not overall_success and self.stop_on_failure:
                break

        end_time = time.perf_counter()
        
        if self._session_id:
            os.makedirs("sentinel_sessions", exist_ok=True)
            with open(f"sentinel_sessions/{self._session_id}.json", "w") as f:
                json.dump(self._session_data, f, indent=2)

        return WorkflowResult(
            success=overall_success,
            failed_node=failed_node,
            total_duration_ms=(end_time - start_time) * 1000,
            results=results
        )

    def visualize(self) -> str:
        """Prints ASCII tree of all nodes."""
        lines = [f"Workflow: {self.name}"]
        for i, item in enumerate(self.nodes):
            prefix = "└── " if i == len(self.nodes) - 1 else "├── "
            if isinstance(item, list):
                lines.append(f"{prefix}PARALLEL:")
                for j, n in enumerate(item):
                    sub_prefix = "    └── " if j == len(item) - 1 else "    ├── "
                    lines.append(f"{sub_prefix}{n.name}")
            else:
                lines.append(f"{prefix}{item.name}")
        out = "\n".join(lines)
        print(out)
        return out
