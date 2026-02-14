from __future__ import annotations

import json

from langchain.tools import tool

from app.core.node_runtime import node_runtime


@tool
def node_list() -> str:
    """List available local nodes and capabilities."""
    nodes = [node.model_dump() for node in node_runtime.list_nodes()]
    return json.dumps({"nodes": nodes}, indent=2)


@tool
def node_invoke(node_id: str, action: str, args_json: str = "{}") -> str:
    """
    Invoke a local node action.

    Args:
        node_id: Target node id (use node_list first).
        action: Action name (e.g. system.notify, system.run).
        args_json: JSON object string for action args.
    """
    try:
        args = json.loads(args_json) if args_json else {}
        if not isinstance(args, dict):
            return "Error: args_json must decode to a JSON object."
    except Exception as exc:
        return f"Error: invalid args_json: {exc}"

    result = node_runtime.invoke(node_id=node_id, action=action, args=args)
    return result.model_dump_json(indent=2)


def get_node_tools():
    return [node_list, node_invoke]
