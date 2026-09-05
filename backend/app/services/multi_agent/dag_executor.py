"""
Task Graph / DAG Executor — Asynchronous parallel execution engine for multi-agent workflows.
Coordinates concurrent agent execution, dependency resolution, and real-time event streaming.
"""
import asyncio
import time
from enum import Enum
from typing import Dict, Any, List, Callable, Optional, Set, AsyncGenerator
from datetime import datetime, timezone

from app.core.logging import logger
from app.services.multi_agent.blackboard import SharedBlackboard


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATED = "validated"
    SKIPPED = "skipped"


class TaskNode:
    """Represents an atomic task executed by an agent in the DAG."""

    def __init__(
        self,
        node_id: str,
        agent_name: str,
        display_name: str,
        fn: Callable,
        dependencies: Optional[List[str]] = None,
        description: str = "",
        category: str = "analysis",
    ):
        self.node_id = node_id
        self.agent_name = agent_name
        self.display_name = display_name
        self.fn = fn
        self.dependencies: Set[str] = set(dependencies or [])
        self.description = description
        self.category = category  # 'understanding', 'analysis', 'ml', 'dashboard', 'critic'
        
        self.status: TaskStatus = TaskStatus.PENDING
        self.result: Any = None
        self.error: Optional[str] = None
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        self.duration_ms: float = 0.0
        self.critic_review: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "agent_name": self.agent_name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "dependencies": list(self.dependencies),
            "status": self.status.value,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": round(self.duration_ms, 2),
            "critic_review": self.critic_review,
        }


class DAGExecutor:
    """Executes task nodes in parallel respecting DAG dependencies."""

    def __init__(self, blackboard: SharedBlackboard):
        self.blackboard = blackboard
        self.nodes: Dict[str, TaskNode] = {}
        self._completed_nodes: Set[str] = set()
        self._events_queue: asyncio.Queue = asyncio.Queue()

    def add_node(
        self,
        node_id: str,
        agent_name: str,
        display_name: str,
        fn: Callable,
        dependencies: Optional[List[str]] = None,
        description: str = "",
        category: str = "analysis",
    ) -> TaskNode:
        node = TaskNode(
            node_id=node_id,
            agent_name=agent_name,
            display_name=display_name,
            fn=fn,
            dependencies=dependencies,
            description=description,
            category=category,
        )
        self.nodes[node_id] = node
        return node

    def get_dag_spec(self) -> List[Dict[str, Any]]:
        return [node.to_dict() for node in self.nodes.values()]

    async def _execute_single_node(self, node: TaskNode) -> None:
        """Wait for dependencies, execute node, and record status."""
        node.status = TaskStatus.RUNNING
        node.started_at = time.time()
        
        await self._events_queue.put({
            "event": "node_started",
            "node": node.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        try:
            # Check if function is async or sync
            if asyncio.iscoroutinefunction(node.fn):
                result = await node.fn(self.blackboard)
            else:
                # Run sync in default executor thread to not block event loop
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(None, node.fn, self.blackboard)

            node.result = result
            node.status = TaskStatus.COMPLETED
            node.completed_at = time.time()
            node.duration_ms = (node.completed_at - node.started_at) * 1000

            self._completed_nodes.add(node.node_id)

            await self._events_queue.put({
                "event": "node_completed",
                "node": node.to_dict(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        except Exception as e:
            logger.error(f"Error executing agent task {node.node_id} ({node.agent_name}): {str(e)}", exc_info=True)
            node.status = TaskStatus.FAILED
            node.error = str(e)
            node.completed_at = time.time()
            node.duration_ms = (node.completed_at - node.started_at) * 1000

            await self._events_queue.put({
                "event": "node_failed",
                "node": node.to_dict(),
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    async def execute_all(self) -> Dict[str, Any]:
        """
        Executes all nodes in the DAG respecting dependencies with maximum parallelism.
        """
        pending_nodes = set(self.nodes.keys())
        running_tasks: Dict[str, asyncio.Task] = {}

        start_time = time.time()

        while pending_nodes or running_tasks:
            # Find nodes whose dependencies are all satisfied and are not yet running
            ready_nodes = [
                node_id for node_id in pending_nodes
                if self.nodes[node_id].dependencies.issubset(self._completed_nodes)
            ]

            for node_id in ready_nodes:
                pending_nodes.remove(node_id)
                node = self.nodes[node_id]
                task = asyncio.create_task(self._execute_single_node(node))
                running_tasks[node_id] = task

            if not running_tasks:
                if pending_nodes:
                    # Circular dependency or failed dependency
                    for node_id in list(pending_nodes):
                        node = self.nodes[node_id]
                        node.status = TaskStatus.SKIPPED
                        node.error = "Unsatisfied dependencies or upstream failure"
                        pending_nodes.remove(node_id)
                break

            # Wait for at least one running task to complete
            done, _ = await asyncio.wait(
                running_tasks.values(),
                return_when=asyncio.FIRST_COMPLETED
            )

            # Cleanup finished tasks
            for node_id, task in list(running_tasks.items()):
                if task in done:
                    del running_tasks[node_id]

        total_duration_ms = (time.time() - start_time) * 1000

        # Mark dag completed
        await self._events_queue.put({
            "event": "dag_completed",
            "total_duration_ms": round(total_duration_ms, 2),
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return {
            "total_duration_ms": round(total_duration_ms, 2),
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "completed_nodes": list(self._completed_nodes),
            "failed_nodes": [n.node_id for n in self.nodes.values() if n.status == TaskStatus.FAILED],
        }

    async def event_generator(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Async generator streaming events to SSE clients."""
        while True:
            event = await self._events_queue.get()
            yield event
            if event.get("event") == "dag_completed":
                break
