"""
Interactive session with the Fraud Detection Agent.

Run with: python agents/fraud_detection/interactive.py

Then type questions or commands, e.g.:
  help
  analyze EX-2025-001
  mesh
  list agents
  agent payment_failed
  invoke payment_failed investigate_payment_exception EX-2025-001
  quit
"""

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
agent_sdk = repo_root / "agent-sdk"
if str(agent_sdk) not in sys.path:
    sys.path.insert(0, str(agent_sdk))

from agents.fraud_detection import FraudDetectionAgent


def main():
    print("Fraud Detection Agent – interactive session")
    print("Type a command or question. Type 'help' for commands, 'quit' to exit.\n")

    try:
        agent = FraudDetectionAgent()
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

        response = agent.answer(user_input)
        if response is None:
            print("Bye.")
            break
        print("\nAgent>\n" + response + "\n")


if __name__ == "__main__":
    sys.exit(main())
