# Copyright 2020-2026 The MathWorks, Inc.

import asyncio
from contextlib import suppress
from typing import Dict, Set, Union

from matlab_proxy.util import mwi

logger = mwi.logger.get()


def get_event_loop():
    """Returns an asyncio event loop by checking the Operating System and
    uses the appropriate asyncio API

    Returns:
        asyncio.loop: asyncio event loop.
    """
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        # No running event loop. Try to get a previously-set loop, or create a new one.
        # In Python 3.14+, get_event_loop() raises RuntimeError if no loop was ever set.
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Event loop is closed")
            return loop
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop


async def cancel_tasks(tasks: Union[Dict[str, asyncio.Task], Set[asyncio.Task]]):
    """Cancels asyncio tasks.

    Args:
        tasks: If a Dict[str, asyncio.Task], contains (task_name, task) as entries.
               If a Set[asyncio.Task], contains a set of asyncio.Task objects.
    """
    if isinstance(tasks, dict):
        for name, task in list(tasks.items()):
            if task:
                await __cancel_task(task)
                logger.debug(f"{name} task stopped successfully")

    elif isinstance(tasks, set):
        for task in tasks:
            if task:
                await __cancel_task(task)
                logger.debug("Task stopped successfully")


async def __cancel_task(task):
    """Cancels a given asyncio task, suppressing CancelledError.

    Args:
        task (asyncio.Task): The asyncio task to be cancelled.
    """
    with suppress(asyncio.CancelledError):
        task.cancel()
        await task
