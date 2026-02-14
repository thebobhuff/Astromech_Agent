from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.node_runtime import NodeDescriptor, NodeInvokeResult, node_runtime

router = APIRouter(tags=["Nodes"])
logger = logging.getLogger(__name__)


class NodeInvokeRequest(BaseModel):
    node_id: str = Field(description="Target node id")
    action: str = Field(description="Action name, e.g. system.notify or system.run")
    args: Dict[str, Any] = Field(default_factory=dict)


@router.get("/", response_model=List[NodeDescriptor])
async def list_nodes() -> List[NodeDescriptor]:
    try:
        return node_runtime.list_nodes()
    except Exception as exc:
        logger.exception("Failed to list nodes: %s", exc, extra={"event": "nodes_list"})
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/invoke", response_model=NodeInvokeResult)
async def invoke_node_action(req: NodeInvokeRequest) -> NodeInvokeResult:
    try:
        return node_runtime.invoke(node_id=req.node_id, action=req.action, args=req.args)
    except Exception as exc:
        logger.exception(
            "Failed to invoke node action '%s' on node '%s': %s",
            req.action,
            req.node_id,
            exc,
            extra={"event": "nodes_invoke"},
        )
        raise HTTPException(status_code=500, detail=str(exc))
