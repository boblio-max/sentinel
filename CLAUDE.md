# sentinel

Sentinel is a swarm-intelligence / multi-robot orchestrator. `main.py` boots a `SentinelOrchestrator` (configurable count of simulated robots, optional pygame dashboard, headless mode, configurable tick count). The `sentinel/` package contains the orchestrator, controllers (boids, robot controller), a bus, models, config, and pluggable backends (`mock_backend`, `real_robot`, `sim_mujoco`, `sim_pybullet`). It depends on MuJoCo, NumPy, and pygame.

## Build / Test / Lint Commands

- Install: `pip install -r requirements.txt` (mujoco, numpy, pygame)
- Build: not applicable
- Test: `python -m pytest tests/` (or run `python tests/test_m3_integration.py` directly)
- Lint: not configured
- Dev / run:
  - Visual mode: `python main.py`
  - Headless: `python main.py --no-vis -t 1000`
  - Custom robot count: `python main.py -n 20`

## Code Style Rules

- Language/version: Python 3.10+
- Paradigm: package layout — `sentinel/` with `backends/`, `controllers/` subpackages; CLI flags parsed in `main.py`
- Types: type hints on orchestrator + backend methods
- Formatting: PEP 8 (no formatter configured)
- Imports / module style: absolute imports of `sentinel.*`; subpackages expose their own `__init__.py`
- Dependencies: `mujoco`, `numpy`, `pygame`; `multiprocessing` is the chosen concurrency primitive (note the `freeze_support()` Windows guard in `main.py`)

## Verification Criteria

Before claiming any task done, Claude MUST:
1. Run `python -c "from sentinel.orchestrator import SentinelOrchestrator; from sentinel import config"` to confirm core imports resolve.
2. Run `python tests/test_m3_integration.py` (or `pytest tests/`) and confirm the test suite passes.
3. Boot the orchestrator in headless mode (`python main.py --no-vis -t 10`) and confirm it exits cleanly with "Finished Orchestrator run.".
4. Report the exact commands run and their outcomes in the final message.
