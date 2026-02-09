"""
Agent Code Generator - Generate agent implementation code from templates.

This module generates agent code from the template when a user creates a new agent
definition via the UI. It ensures that the agent has working code in agents/{agent_id}/
before deployment.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Tuple


def get_repo_root() -> Path:
    """Get repository root directory."""
    # Path: control-plane/code_generator/agent_generator.py
    # Go up: agent_generator.py -> code_generator -> control-plane -> repo root
    return Path(__file__).resolve().parent.parent.parent


def to_class_name(agent_id: str) -> str:
    """
    Convert agent_id to PascalCase class name.
    
    Examples:
        payment_failed -> PaymentFailedAgent
        my_agent -> MyAgentAgent
        cloud_reliability -> CloudReliabilityAgent
    """
    parts = agent_id.split("_")
    class_name = "".join(word.capitalize() for word in parts)
    if not class_name.endswith("Agent"):
        class_name += "Agent"
    return class_name


def to_display_name(agent_id: str) -> str:
    """
    Convert agent_id to display name.
    
    Examples:
        payment_failed -> Payment Failed
        my_agent -> My Agent
    """
    return agent_id.replace("_", " ").title()


def validate_agent_directory(agent_id: str) -> Tuple[bool, str]:
    """
    Check if agent directory already exists.
    
    Returns:
        (exists, path_or_message)
    """
    repo_root = get_repo_root()
    agent_dir = repo_root / "agents" / agent_id
    
    if agent_dir.exists():
        return True, str(agent_dir)
    return False, f"Agent directory does not exist: {agent_dir}"


def generate_agent_code(
    agent_id: str,
    agent_definition: Dict[str, Any],
    overwrite: bool = False
) -> Tuple[bool, str, Optional[str]]:
    """
    Generate agent code from template.
    
    Args:
        agent_id: Agent identifier (e.g., "my_agent")
        agent_definition: Agent definition dict (from YAML)
        overwrite: If True, overwrite existing agent directory
    
    Returns:
        (success, message, agent_dir_path)
    """
    repo_root = get_repo_root()
    template_dir = repo_root / "agents" / "template"
    agent_dir = repo_root / "agents" / agent_id
    
    # Check if template exists
    if not template_dir.exists():
        return False, f"Template directory not found: {template_dir}", None
    
    # Check if agent already exists
    if agent_dir.exists() and not overwrite:
        return False, f"Agent directory already exists: {agent_dir}. Use overwrite=True to replace.", str(agent_dir)
    
    # Create agent directory
    try:
        if agent_dir.exists():
            shutil.rmtree(agent_dir)
        agent_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate files
        class_name = to_class_name(agent_id)
        display_name = to_display_name(agent_id)
        
        # Copy and customize agent.py
        _generate_agent_py(template_dir, agent_dir, agent_id, class_name, display_name, agent_definition)
        
        # Copy and customize interactive.py
        _generate_interactive_py(template_dir, agent_dir, agent_id, class_name, display_name)
        
        # Copy and customize __init__.py
        _generate_init_py(template_dir, agent_dir, agent_id, class_name)
        
        return True, f"Agent code generated successfully at {agent_dir}", str(agent_dir)
    
    except Exception as e:
        return False, f"Failed to generate agent code: {e}", None


def _generate_agent_py(
    template_dir: Path,
    agent_dir: Path,
    agent_id: str,
    class_name: str,
    display_name: str,
    agent_definition: Dict[str, Any]
):
    """Generate agent.py from template."""
    template_file = template_dir / "agent.py"
    output_file = agent_dir / "agent.py"
    
    with open(template_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Get agent details
    purpose_goal = agent_definition.get("purpose", {}).get("goal", "Describe what this agent does")
    allowed_tools = agent_definition.get("allowed_tools", [])
    
    # Replace placeholders
    content = content.replace("Template Agent", f"{display_name} Agent")
    content = content.replace("template agent", f"{agent_id} agent")
    content = content.replace('AGENT_ID = "template"', f'AGENT_ID = "{agent_id}"')
    content = content.replace("class TemplateAgent:", f"class {class_name}:")
    content = content.replace("TemplateAgent", class_name)
    content = content.replace("template", agent_id)
    content = content.replace("This agent [describe what it does].", purpose_goal)
    
    # Add tool registration hints if tools are specified
    if allowed_tools:
        tool_registration_code = "\n".join([
            f"        # TODO: Register implementation for '{tool}'"
            for tool in allowed_tools[:5]  # Show first 5 tools
        ])
        content = content.replace(
            "        # TODO: Import and register your tools",
            f"        # Register your allowed tools:\n{tool_registration_code}"
        )
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)


def _generate_interactive_py(
    template_dir: Path,
    agent_dir: Path,
    agent_id: str,
    class_name: str,
    display_name: str
):
    """Generate interactive.py from template."""
    template_file = template_dir / "interactive.py"
    output_file = agent_dir / "interactive.py"
    
    with open(template_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Replace placeholders
    content = content.replace("Template Agent", f"{display_name} Agent")
    content = content.replace("template/interactive.py", f"{agent_id}/interactive.py")
    content = content.replace("from agents.template import TemplateAgent", f"from agents.{agent_id} import {class_name}")
    content = content.replace("TemplateAgent", class_name)
    content = content.replace("template", agent_id)
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)


def _generate_init_py(
    template_dir: Path,
    agent_dir: Path,
    agent_id: str,
    class_name: str
):
    """Generate __init__.py from template."""
    template_file = template_dir / "__init__.py"
    output_file = agent_dir / "__init__.py"
    
    with open(template_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Replace placeholders
    content = content.replace("Template Agent", f"{agent_id.replace('_', ' ').title()} Agent")
    content = content.replace("TemplateAgent", class_name)
    content = content.replace('"TemplateAgent"', f'"{class_name}"')
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)


def generate_agent_readme(
    agent_id: str,
    agent_definition: Dict[str, Any],
    agent_dir: Path
) -> None:
    """Generate README.md for the agent (optional)."""
    readme_file = agent_dir / "README.md"
    
    display_name = to_display_name(agent_id)
    purpose = agent_definition.get("purpose", {})
    goal = purpose.get("goal", "N/A")
    domain = agent_definition.get("domain", "general")
    version = agent_definition.get("version", "1.0.0")
    allowed_tools = agent_definition.get("allowed_tools", [])
    policies = agent_definition.get("policies", [])
    
    content = f"""# {display_name} Agent

## Overview

**Agent ID**: `{agent_id}`  
**Version**: {version}  
**Domain**: {domain}  

## Purpose

{goal}

## Configuration

### Allowed Tools

{chr(10).join(f'- `{tool}`' for tool in allowed_tools) if allowed_tools else '(No tools configured)'}

### Policies

{chr(10).join(f'- `{policy}`' for policy in policies) if policies else '(No policies configured)'}

## Running

### Interactive Mode

```bash
python -m agents.{agent_id}.interactive
```

### Programmatic Use

```python
from agents.{agent_id} import {to_class_name(agent_id)}

agent = {to_class_name(agent_id)}()
result = agent.process("your input here")
print(result)
```

## Development

This agent was auto-generated from the template. To customize:

1. Edit `agents/{agent_id}/agent.py`
2. Implement tool registrations in `_register_tools()`
3. Customize `process()` and/or `answer()` methods
4. Add any domain-specific logic

See [Agent SDK documentation](../../agent-sdk/README.md) for details.
"""
    
    with open(readme_file, "w", encoding="utf-8") as f:
        f.write(content)
