#!/usr/bin/env python3
"""
Deployment script for agent factory.

Deploys agents and control-plane to specified environment.
"""

import sys
import argparse
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))


def deploy_control_plane(env: str):
    """Deploy control-plane to environment."""
    print(f"🚀 Deploying control-plane to {env}...")
    # Add your deployment logic here
    # Examples:
    # - Copy files to server
    # - Run docker build/push
    # - Update Kubernetes manifests
    # - Run terraform apply
    print(f"✓ Control-plane deployed to {env}")


def deploy_agents(env: str):
    """Deploy agents to environment."""
    print(f"🚀 Deploying agents to {env}...")
    # Add your deployment logic here
    print(f"✓ Agents deployed to {env}")


def deploy_config(env: str):
    """Deploy configuration to environment."""
    print(f"🚀 Deploying configuration to {env}...")
    # Add your deployment logic here
    print(f"✓ Configuration deployed to {env}")


def main():
    """Main deployment function."""
    parser = argparse.ArgumentParser(description="Deploy agent factory")
    parser.add_argument(
        "--env",
        required=True,
        choices=["staging", "production"],
        help="Environment to deploy to"
    )
    parser.add_argument(
        "--component",
        choices=["all", "control-plane", "agents", "config"],
        default="all",
        help="Component to deploy"
    )
    
    args = parser.parse_args()
    
    print(f"📦 Deploying to {args.env} environment\n")
    
    if args.component in ["all", "control-plane"]:
        deploy_control_plane(args.env)
    
    if args.component in ["all", "agents"]:
        deploy_agents(args.env)
    
    if args.component in ["all", "config"]:
        deploy_config(args.env)
    
    print(f"\n✅ Deployment to {args.env} complete!")


if __name__ == "__main__":
    main()
