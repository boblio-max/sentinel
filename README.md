# Sentinel

Sentinel is the modular robot control framework — the n8n of robotics. Every robot behavior is a "node." Nodes connect into "workflows" that execute in sequence. Users write workflows in Python or in Origin, a hardware-first DSL with native servo control built into the language.

Sentinel's mission: give every robot AI superpowers while keeping full control in the hands of the builder. It is not a SaaS tool. It is not a black box. It is open infrastructure — the layer every robot project builds on top of, the way React is to web apps or ROS is to robotics middleware.

## Core Philosophy
- **Nodes are the unit of behavior.** Every action, wait, branch, loop, sensor read, and motor command is a node.
- **Workflows are the unit of logic.** Nodes connect into workflows. Workflows compose into larger workflows.
- **Context is shared state.** A dict flows through every node in a workflow. Each node can read from and write to it.
- **Hardware is always optional.** Every hardware node must fall back to simulation mode gracefully if hardware is not detected.
- **Users own everything.** Custom nodes, custom workflows, custom Origin scripts — all first-class. No registration, no API keys, no cloud required.
- **Origin is the DSL layer.** Users can write robot behavior in Origin (`.org` files) instead of Python. The interpreter maps Origin hardware commands directly to Sentinel nodes.

## Installation
```bash
pip install sentinel
# Optional, for hardware support on Raspberry Pi:
pip install "sentinel[hardware]"
```

## Quick Start (Python)
```python
from sentinel import Workflow
from sentinel.nodes.core import WaitNode
from sentinel.nodes.arm import ArmNode

flow = Workflow(name="autonomous", stop_on_failure=True)
flow.add(WaitNode(seconds=1))
flow.add(ArmNode(pose="home"))

result = flow.run()
print(result.summary())
```

## Quick Start (Origin)
```origin
set servo.angle 0, 90
wait 500
set servo.angle 0, 0
```
Run with: `sentinel run routine.org`

## Full Node Reference
- `WaitNode`, `PrintNode`, `LogNode`, `BranchNode`, `LoopNode`, `SetContextNode`, `RepeatNode`
- `ArmNode`, `ArmSequenceNode` (PCA9685 servos)
- `MotorNode` (DC Motors via GPIO PWM)
- `GPIONode`

## Custom Node
```python
from sentinel import Node

class MyNode(Node):
    def __init__(self, my_param):
        super().__init__(name="MyNode")
        self.description = "Does something amazing."
        self.my_param = my_param

    def execute(self, context):
        return self.ok(data={"result": self.my_param})
```

## CLI Commands
- `sentinel run example.org` - run an Origin file
- `sentinel run example.py` - run a Python workflow
- `sentinel init` - scaffold a new project
- `sentinel new node MyNode` - generate a custom node template
- `sentinel replay session_id` - replay a recorded session

## Hive Mind & Recording
```python
flow.record("session_id_123")
```
Saves JSON to `sentinel_sessions/session_id_123.json`. Replay in simulation with `sentinel replay session_id_123`. This provides the foundation for future opt-in collective learning across robots.

## Roadmap
- Web interface for drag-and-drop workflows
- Hive mind cloud synchronization
- `sentinel-ai` package for embodied ML integration
