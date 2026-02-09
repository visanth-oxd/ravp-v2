"""
Interactive session with the Cloud Reliability Agent.

Run with: python agents/cloud_reliability/interactive.py

Then type questions or commands, e.g.:
  investigate INC-GCP-2025-001
  What's wrong with INC-GCP-2025-001?
  metrics
  logs
  suggest INC-GCP-2025-001
  Invoke the healing agent to resize the Cloud SQL instance
  Please ask the healing agent to apply remediation
  help
  quit
"""

import sys
from pathlib import Path

# Add repo root to sys.path so we can import 'agents' and 'tools'
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Also ensure /app is in path if running in container
if "/app" not in sys.path:
    sys.path.insert(0, "/app")

try:
    from agents.cloud_reliability.agent import CloudReliabilityAgent
except ImportError:
    # Fallback if running from within the package
    from agent import CloudReliabilityAgent


def main():
    print("Cloud Reliability Agent – interactive session")
    print("Type a question or command. Type 'help' for commands, 'quit' to exit.\n")

    try:
        agent = CloudReliabilityAgent()
        if agent.regulated.llm:
            print("(LLM reasoning enabled – you can ask in natural language.)\n")
    except Exception as e:
        print(f"Failed to start agent: {e}")
        return 1

    while True:
        try:
            user_input = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user_input:
            continue

        response = agent.answer(user_input)
        if response is None:
            print("Bye.")
            break
        print("\nAgent>\n" + response + "\n")


if __name__ == "__main__":
    sys.exit(main())
