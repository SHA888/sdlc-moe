#!/usr/bin/env python3
"""Test asyncio event loop policy compatibility for Windows."""

import asyncio
import sys
import platform


def test_event_loop_policy():
    """Test that asyncio.run works with default event loop policy."""
    print(f"Platform: {platform.system()}")
    print(f"Python version: {sys.version}")

    # Get current event loop policy
    policy = asyncio.get_event_loop_policy()
    print(f"Current policy: {policy.__class__.__name__}")

    # Test asyncio.run with a simple async function
    async def test_func():
        await asyncio.sleep(0.1)
        return "success"

    try:
        result = asyncio.run(test_func())
        print(f"asyncio.run() test: {result}")
        return True
    except Exception as e:
        print(f"asyncio.run() failed: {e}")
        return False


if __name__ == "__main__":
    success = test_event_loop_policy()
    sys.exit(0 if success else 1)
