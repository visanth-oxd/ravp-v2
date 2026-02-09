"""
Incident Coordinator tools: meeting scheduling, coordination (synthetic).

In production, request_meeting would integrate with Calendar/Meet and runbooks.
"""

from .request_meeting import request_meeting

__all__ = ["request_meeting"]
