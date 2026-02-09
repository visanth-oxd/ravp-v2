#!/usr/bin/env python3
"""
Test script for Tool Registry.
Run this to verify the tool registry is working.
"""

import sys
from pathlib import Path

# Add control-plane to path
repo_root = Path(__file__).resolve().parent.parent
control_plane = repo_root / "control-plane"
if str(control_plane) not in sys.path:
    sys.path.insert(0, str(control_plane))

from tool_registry.loader import get_tool, list_tools, load_tools


def test_list_tools():
    """Test listing all tools."""
    print("=" * 60)
    print("Testing: List Tools")
    print("=" * 60)
    
    tools = list_tools()
    print(f"Found {len(tools)} tool(s):")
    for tool in tools:
        print(f"  - {tool['name']}")
        print(f"    Description: {tool.get('description', 'N/A')}")
        print(f"    Risk Tier: {tool.get('risk_tier', 'N/A')}")
        print(f"    Requires Approval: {tool.get('requires_human_approval', False)}")
        print()
    print()


def test_get_tool():
    """Test loading a specific tool."""
    print("=" * 60)
    print("Testing: Get Tool")
    print("=" * 60)
    
    tool_name = "get_payment_exception"
    tool = get_tool(tool_name)
    
    if tool:
        print(f"✅ Successfully loaded: {tool_name}")
        print(f"\nTool Definition:")
        print(f"  Name: {tool.get('name')}")
        print(f"  Description: {tool.get('description', 'N/A')}")
        print(f"  Data Sources: {', '.join(tool.get('data_sources', []))}")
        print(f"  PII Level: {tool.get('pii_level', 'N/A')}")
        print(f"  Risk Tier: {tool.get('risk_tier', 'N/A')}")
        print(f"  Requires Approval: {tool.get('requires_human_approval', False)}")
    else:
        print(f"❌ Failed to load: {tool_name}")
    print()


def test_load_all():
    """Test loading all tools at once."""
    print("=" * 60)
    print("Testing: Load All Tools")
    print("=" * 60)
    
    data = load_tools()
    tools = data.get("tools", {})
    print(f"Loaded {len(tools)} tool(s) from registry")
    print()


if __name__ == "__main__":
    print("\n🧪 Testing Tool Registry\n")
    
    test_load_all()
    test_list_tools()
    test_get_tool()
    
    print("=" * 60)
    print("✅ Tests complete!")
    print("=" * 60)
