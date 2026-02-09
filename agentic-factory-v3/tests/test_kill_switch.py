#!/usr/bin/env python3
"""
Test script for Kill Switch.
Run this to verify the kill switch is working.
"""

import sys
from pathlib import Path

# Add control-plane to path
repo_root = Path(__file__).resolve().parent.parent
control_plane = repo_root / "control-plane"
if str(control_plane) not in sys.path:
    sys.path.insert(0, str(control_plane))

from kill_switch.state import (
    disable_agent,
    disable_model,
    enable_agent,
    enable_model,
    is_agent_disabled,
    is_model_disabled,
    list_disabled,
)


def test_agent_kill_switch():
    """Test agent kill switch."""
    print("=" * 60)
    print("Testing: Agent Kill Switch")
    print("=" * 60)
    
    agent_id = "payment_failed"
    
    # Check initial state (should be enabled)
    disabled = is_agent_disabled(agent_id)
    print(f"Initial state: {agent_id} disabled = {disabled}")
    assert not disabled, "Agent should be enabled initially"
    print()
    
    # Disable agent
    disable_agent(agent_id)
    disabled = is_agent_disabled(agent_id)
    print(f"After disable: {agent_id} disabled = {disabled}")
    assert disabled, "Agent should be disabled"
    print()
    
    # Enable agent
    enable_agent(agent_id)
    disabled = is_agent_disabled(agent_id)
    print(f"After enable: {agent_id} disabled = {disabled}")
    assert not disabled, "Agent should be enabled"
    print()


def test_model_kill_switch():
    """Test model kill switch."""
    print("=" * 60)
    print("Testing: Model Kill Switch")
    print("=" * 60)
    
    model_id = "gemini-1.5-pro"
    
    # Check initial state (should be enabled)
    disabled = is_model_disabled(model_id)
    print(f"Initial state: {model_id} disabled = {disabled}")
    assert not disabled, "Model should be enabled initially"
    print()
    
    # Disable model
    disable_model(model_id)
    disabled = is_model_disabled(model_id)
    print(f"After disable: {model_id} disabled = {disabled}")
    assert disabled, "Model should be disabled"
    print()
    
    # Enable model
    enable_model(model_id)
    disabled = is_model_disabled(model_id)
    print(f"After enable: {model_id} disabled = {disabled}")
    assert not disabled, "Model should be enabled"
    print()


def test_list_disabled():
    """Test listing disabled agents and models."""
    print("=" * 60)
    print("Testing: List Disabled")
    print("=" * 60)
    
    # Disable some agents and models
    disable_agent("payment_failed")
    disable_agent("test_agent")
    disable_model("gemini-1.5-pro")
    
    disabled = list_disabled()
    print(f"Disabled agents: {disabled['agents']}")
    print(f"Disabled models: {disabled['models']}")
    print()
    
    # Clean up
    enable_agent("payment_failed")
    enable_agent("test_agent")
    enable_model("gemini-1.5-pro")
    
    disabled = list_disabled()
    print(f"After cleanup - Disabled agents: {disabled['agents']}")
    print(f"After cleanup - Disabled models: {disabled['models']}")
    print()


if __name__ == "__main__":
    print("\n🧪 Testing Kill Switch\n")
    
    test_agent_kill_switch()
    test_model_kill_switch()
    test_list_disabled()
    
    print("=" * 60)
    print("✅ Tests complete!")
    print("=" * 60)
