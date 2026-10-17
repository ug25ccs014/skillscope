"""Read-only API for the versioned source-traceable career knowledge graph."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas.knowledge_graph import GraphNodeType
from app.services.knowledge_graph import (
    KnowledgeGraphError,
    get_graph_node,
    graph_status,
    list_career_cards,
    list_graph_edges,
    list_graph_nodes,
)

router = APIRouter(prefix="/api/knowledge-graph", tags=["Career knowledge graph"])


def _status_or_http_error() -> dict[str, object]:
    try:
        status = graph_status()
    except KnowledgeGraphError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if status["status"] != "ready":
        raise HTTPException(
            status_code=503,
            detail="The career knowledge graph has not been built. Run the documented graph rebuild command.",
        )
    if status["is_stale"]:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "The graph was built from a different set of active source snapshots. Rebuild it before querying graph data.",
                "active_snapshots": status["active_snapshots"],
                "built_from_active_snapshots": status["built_from_active_snapshots"],
            },
        )
    return status


@router.get("/status")
def knowledge_graph_status() -> dict[str, object]:
    """Report coverage, active snapshot versions, and projection freshness."""
    try:
        return graph_status()
    except KnowledgeGraphError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/nodes")
def knowledge_graph_nodes(
    node_type: GraphNodeType | None = None,
    q: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=100_000),
) -> dict[str, object]:
    status = _status_or_http_error()
    try:
        items = list_graph_nodes(node_type=node_type.value if node_type else None, query=q, limit=limit, offset=offset)
    except KnowledgeGraphError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"items": items, "count": len(items), "limit": limit, "offset": offset, "graph_built_at": status.get("built_at")}


@router.get("/nodes/{node_id}")
def knowledge_graph_node(node_id: str) -> dict[str, object]:
    status = _status_or_http_error()
    result = get_graph_node(node_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Knowledge graph node not found.")
    result["graph_built_at"] = status.get("built_at")
    return result


@router.get("/edges")
def knowledge_graph_edges(
    relation_type: str | None = Query(default=None, min_length=1, max_length=80),
    mapping_type: str | None = Query(default=None, pattern="^(exact|reviewed_related|weak_lexical|unresolved)$"),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, object]:
    status = _status_or_http_error()
    items = list_graph_edges(relation_type=relation_type, mapping_type=mapping_type, limit=limit)
    return {"items": items, "count": len(items), "graph_built_at": status.get("built_at")}


@router.get("/crosswalks")
def knowledge_graph_crosswalks(
    review_status: str | None = Query(default=None, pattern="^(sourced|reviewed|proposed|unresolved|rejected)$"),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, object]:
    status = _status_or_http_error()
    crosswalk_relations = ("related_occupation", "related_work_activity", "crosswalk_candidate")
    items = [
        item
        for relation in crosswalk_relations
        for item in list_graph_edges(relation_type=relation, limit=500)
        if review_status is None or item["review_status"] == review_status
    ][:limit]
    return {"items": items, "count": len(items), "graph_built_at": status.get("built_at")}


@router.get("/careers")
def knowledge_graph_careers(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=100_000),
) -> dict[str, object]:
    status = _status_or_http_error()
    items = list_career_cards(limit=limit, offset=offset)
    return {
        "items": items,
        "count": len(items),
        "limit": limit,
        "offset": offset,
        "graph_built_at": status.get("built_at"),
        "note": "Career records cite their active source record/version. Curated summaries are static extracts, not live Indian labour-market data.",
    }
