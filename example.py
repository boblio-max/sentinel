from sentinel import Workflow, Node, NodeResult
from sentinel.nodes.core import PrintNode, WaitNode, BranchNode, LoopNode, SetContextNode
from sentinel.nodes.arm import ArmNode
from sentinel.origin.node import OriginNode

class CustomMathNode(Node):
    def __init__(self, key: str, factor: int):
        super().__init__(name="CustomMath")
        self.description = "Multiplies a context value by a factor."
        self.key = key
        self.factor = factor

    def execute(self, context: dict) -> NodeResult:
        val = context.get(self.key, 0)
        new_val = val * self.factor
        context[self.key] = new_val
        return self.ok(data={"old": val, "new": new_val})

if __name__ == "__main__":
    # Create workflow, recording session
    flow = Workflow("example_flow", stop_on_failure=True)
    # Ensure it prints simulation output
    flow.set_context("simulation_mode", True)
    flow.record("run_001")
    
    # Parallel Nodes
    flow.add_parallel([
        PrintNode("Starting Parallel Execution"),
        WaitNode(0.5)
    ])
    
    # Hardware Demo (will fallback to SIM cleanly because of context flag or missing hardware)
    flow.add(ArmNode(pose="home"))
    flow.add(ArmNode(pose="extend"))
    
    # Context Logic
    flow.add(SetContextNode("sensor_value", 42))
    
    # Custom Node
    flow.add(CustomMathNode("sensor_value", factor=2))
    
    # Branching
    flow.add(BranchNode(
        condition=lambda ctx: ctx.get("sensor_value", 0) > 50,
        if_true=Workflow("high_value").add(PrintNode("Sensor reading was HIGH")),
        if_false=Workflow("low_value").add(PrintNode("Sensor reading was LOW"))
    ))
    
    # Origin Integration
    # Create a quick org file for demo
    with open("temp_demo.org", "w") as f:
        f.write('print "Hello from embedded Origin block!"\n')
    flow.add(OriginNode("temp_demo.org"))
    
    print("\n--- Visualizing Workflow ---")
    flow.visualize()
    
    print("\n--- Dry Run Execution ---")
    result = flow.dry_run()
    
    print("\n--- Summary ---")
    print(result.summary())
