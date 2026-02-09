#!/usr/bin/env python3
"""
CLI interface for Payment Failed Agent.

Interactive command-line interface for interacting with the payment failed agent.
"""

import sys
import json
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from agents.payment_failed.agent import PaymentFailedAgent


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_json(data: dict, indent: int = 2):
    """Print JSON data in a formatted way."""
    print(json.dumps(data, indent=indent))


def main():
    """Main CLI loop."""
    print_section("Payment Failed Agent - Interactive CLI")
    print("\nCommands:")
    print("  1. investigate <exception_id>  - Investigate a payment exception")
    print("  2. explain <exception_id>     - Get explanation of payment failure")
    print("  3. retry <exception_id>       - Execute payment retry")
    print("  4. retry-force <exception_id> - Force retry (skip checks)")
    print("  5. help                       - Show this help")
    print("  6. exit                       - Exit the CLI")
    
    # Initialize agent
    try:
        print("\nInitializing agent...")
        agent = PaymentFailedAgent()
        print("✓ Agent initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize agent: {e}")
        return 1
    
    # Main loop
    while True:
        try:
            print("\n" + "-" * 60)
            command = input("agent> ").strip()
            
            if not command:
                continue
            
            parts = command.split()
            cmd = parts[0].lower()
            
            if cmd == "exit" or cmd == "quit":
                print("Goodbye!")
                break
            
            elif cmd == "help":
                print("\nCommands:")
                print("  investigate <exception_id>  - Investigate a payment exception")
                print("  explain <exception_id>     - Get explanation of payment failure")
                print("  retry <exception_id>       - Execute payment retry")
                print("  retry-force <exception_id>  - Force retry (skip checks)")
                print("  help                       - Show this help")
                print("  exit                       - Exit the CLI")
            
            elif cmd == "investigate":
                if len(parts) < 2:
                    print("Usage: investigate <exception_id>")
                    continue
                
                exception_id = parts[1]
                print(f"\nInvestigating exception: {exception_id}...")
                
                try:
                    result = agent.investigate_payment_exception(exception_id)
                    print_section("Investigation Result")
                    print_json(result)
                except Exception as e:
                    print(f"✗ Error: {e}")
            
            elif cmd == "explain":
                if len(parts) < 2:
                    print("Usage: explain <exception_id>")
                    continue
                
                exception_id = parts[1]
                print(f"\nGenerating explanation for: {exception_id}...")
                
                try:
                    explanation = agent.explain_payment_failure(exception_id)
                    print_section("Explanation")
                    print(explanation)
                except Exception as e:
                    print(f"✗ Error: {e}")
            
            elif cmd == "retry":
                if len(parts) < 2:
                    print("Usage: retry <exception_id>")
                    continue
                
                exception_id = parts[1]
                print(f"\nExecuting retry for: {exception_id}...")
                
                try:
                    result = agent.retry_payment(exception_id, force=False)
                    print_section("Retry Result")
                    print_json(result)
                except Exception as e:
                    print(f"✗ Error: {e}")
            
            elif cmd == "retry-force":
                if len(parts) < 2:
                    print("Usage: retry-force <exception_id>")
                    continue
                
                exception_id = parts[1]
                print(f"\n⚠ Force retrying (skipping checks) for: {exception_id}...")
                confirm = input("Are you sure? (yes/no): ").strip().lower()
                
                if confirm != "yes":
                    print("Cancelled.")
                    continue
                
                try:
                    result = agent.retry_payment(exception_id, force=True)
                    print_section("Retry Result")
                    print_json(result)
                except Exception as e:
                    print(f"✗ Error: {e}")
            
            else:
                print(f"Unknown command: {cmd}. Type 'help' for available commands.")
        
        except KeyboardInterrupt:
            print("\n\nInterrupted. Type 'exit' to quit.")
        except EOFError:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
