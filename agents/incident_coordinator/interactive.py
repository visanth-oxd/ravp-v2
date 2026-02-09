"""
Interactive session with the Incident Coordinator Agent.

Run with: python -m agents.incident_coordinator.interactive

Then try:
  list open incidents
  status INC-GCP-2025-001
  schedule meeting with on-call and cloud_reliability
  resolution steps for INC-GCP-2025-001
  fix / invoke healing (then approve or cancel)
  help
  quit
"""

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from agents.incident_coordinator import IncidentCoordinatorAgent


def main():
    print("Incident Coordinator Agent – interactive session")
    print("I find incidents, organize meetings, discuss resolution, and coordinate fixes.")
    print("Type 'help' for commands, 'quit' to exit.\n")

    try:
        agent = IncidentCoordinatorAgent()
        if agent.regulated.llm:
            print("(LLM enabled – you can ask in natural language.)\n")
    except Exception as e:
        print(f"Failed to start agent: {e}")
        return 1

    while True:
        try:
            user_input = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        response = agent.answer(user_input)
        if response is None:
            print("Bye.")
            break
        print("\nCoordinator>\n" + response + "\n")


if __name__ == "__main__":
    sys.exit(main())
