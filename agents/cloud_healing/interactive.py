"""
Interactive session with the Cloud Healing Agent.

Run with: python agents/cloud_healing/interactive.py

Then type questions or commands, e.g.:
  help
  instance cloud-sql-instance-1
  resize cloud-sql-instance-1 db-n1-standard-4
  restart cloud-sql-instance-1
  mesh
  list agents
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

from agents.cloud_healing import CloudHealingAgent


def main():
    print("Cloud Healing Agent – interactive session")
    print("Type a command. Type 'help' for commands, 'quit' to exit.\n")

    try:
        agent = CloudHealingAgent()
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
