import multiprocessing
import argparse
from sentinel.orchestrator import SentinelOrchestrator
from sentinel import config

def main():
    # Needed for Windows multiprocessing safety
    multiprocessing.freeze_support()
    
    parser = argparse.ArgumentParser(description="SENTINEL | Swarm Orchestrator")
    parser.add_argument("-n", "--n-sim", type=int, default=config.DEFAULT_N_SIM, 
                        help=f"Number of simulated robots (default: {config.DEFAULT_N_SIM})")
    parser.add_argument("--no-vis", action="store_true", 
                        help="Run in headless mode (no PyGame dashboard)")
    parser.add_argument("-t", "--ticks", type=int, default=-1, 
                        help="Number of ticks to run (-1 for infinite)")
    
    args = parser.parse_args()
    
    print(f"Starting Sentinel Orchestrator with {args.n_sim} robots")
    orchestrator = SentinelOrchestrator(n_sim=args.n_sim, visualize=not args.no_vis)
    
    # Run loop
    orchestrator.run(ticks_to_run=args.ticks)
    print("Finished Orchestrator run.")

if __name__ == "__main__":
    main()
