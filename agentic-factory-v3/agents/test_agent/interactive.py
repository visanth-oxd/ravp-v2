"""
Interactive session with the Test Agent Agent.

Run with: python agents/test_agent/interactive.py

Then type questions or commands, e.g.:
  help
  mesh
  list agents
  agent cloud_reliability
  quit

When you copy this test_agent to a new agent, keep this interactive.py and
point it to your agent class so users can run the agent interactively
with LLM reasoning and mesh (list/invoke other agents).
"""

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
agent_sdk = repo_root / "agent-sdk"
if str(agent_sdk) not in sys.path:
    sys.path.insert(0, str(agent_sdk))

from agents.test_agent import TestAgent


def main():
    print("Test Agent Agent – interactive session")
    print("Type a command or question. Type 'help' for commands, 'quit' to exit.\n")

    try:
        agent = TestAgent()
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
