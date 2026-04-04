import multiprocessing
from sentinel.orchestrator import SentinelOrchestrator

def main():
    # Needed for Windows multiprocessing safety
    multiprocessing.freeze_support()
    
    print("Starting Sentinel Orchestrator")
    orchestrator = SentinelOrchestrator(n_sim=9)
    # Run loop for an automated test (500 monitoring ticks = ~50 seconds)
    orchestrator.run(ticks_to_run=500)
    print("Finished Orchestrator run.")

if __name__ == "__main__":
    main()
