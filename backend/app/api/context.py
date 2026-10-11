from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
import json
import yaml
import logging

from app.database import get_db
from app.models import EndpointProfile
from app.schemas import (
    OpenAPIImportRequest,
    OpenAPIImportResponse,
    EndpointProfileResponse,
    SensitivityEnum,
)
from app.context.openapi import get_app_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/context", tags=["Application Context"])


@router.post("/openapi/import", response_model=OpenAPIImportResponse)
async def import_openapi(
    request: OpenAPIImportRequest,
):
    """Import OpenAPI specification."""
    try:
        app_context = get_app_context()

        # Parse spec based on source
        if request.source == "json":
            spec = request.spec
        elif request.source == "yaml":
            if isinstance(request.spec, str):
                spec = yaml.safe_load(request.spec)
            else:
                spec = request.spec
        elif request.source == "url":
            # For security, only allow local URLs in demo
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(str(request.base_url))
                spec = resp.json()
        else:
            raise HTTPException(status_code=400, detail="Invalid source type")

        # Load endpoints
        count = app_context.load_from_spec(spec)

        # Persist to database
        persisted = await app_context.persist_endpoints()

        return OpenAPIImportResponse(
            imported=count,
            updated=persisted,
            errors=[],
        )
    except Exception as e:
        logger.error(f"OpenAPI import error: {e}")
        return OpenAPIImportResponse(
            imported=0,
            updated=0,
            errors=[str(e)],
        )


@router.post("/openapi/import/file", response_model=OpenAPIImportResponse)
async def import_openapi_file(
    file: UploadFile = File(...),
):
    """Import OpenAPI specification from file upload."""
    try:
        content = await file.read()
        text = content.decode("utf-8")

        if file.filename.endswith((".yaml", ".yml")):
            spec = yaml.safe_load(text)
        else:
            spec = json.loads(text)

        app_context = get_app_context()
        count = app_context.load_from_spec(spec)
        persisted = await app_context.persist_endpoints()

        return OpenAPIImportResponse(
            imported=count,
            updated=persisted,
            errors=[],
        )
    except Exception as e:
        logger.error(f"OpenAPI file import error: {e}")
        return OpenAPIImportResponse(
            imported=0,
            updated=0,
            errors=[str(e)],
        )


@router.get("/endpoints", response_model=List[EndpointProfileResponse])
async def get_endpoints(
    db: AsyncSession = Depends(get_db),
):
    """Get all known endpoints from database."""
    result = await db.execute(select(EndpointProfile).order_by(EndpointProfile.path_template))
    endpoints = result.scalars().all()
    return [EndpointProfileResponse.model_validate(e) for e in endpoints]


@router.get("/endpoints/summary")
async def get_endpoints_summary():
    """Get endpoints summary from in-memory context."""
    app_context = get_app_context()
    return app_context.get_endpoints_summary()


@router.get("/endpoints/{endpoint_id}", response_model=EndpointProfileResponse)
async def get_endpoint(
    endpoint_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get specific endpoint details."""
    result = await db.execute(
        select(EndpointProfile).where(EndpointProfile.id == endpoint_id)
    )
    endpoint = result.scalar_one_or_none()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return EndpointProfileResponse.model_validate(endpoint)


@router.post("/endpoints/{endpoint_id}/sensitivity")
async def update_endpoint_sensitivity(
    endpoint_id: int,
    sensitivity: SensitivityEnum,
    db: AsyncSession = Depends(get_db),
):
    """Update endpoint sensitivity level."""
    result = await db.execute(
        select(EndpointProfile).where(EndpointProfile.id == endpoint_id)
    )
    endpoint = result.scalar_one_or_none()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    endpoint.sensitivity_level = sensitivity
    await db.commit()

    # Update in-memory context
    app_context = get_app_context()
    key = f"{endpoint.method}:{endpoint.path_template}"
    if key in app_context.endpoints:
        app_context.endpoints[key].sensitivity = sensitivity

    return {"message": "Sensitivity updated", "sensitivity": sensitivity.value}