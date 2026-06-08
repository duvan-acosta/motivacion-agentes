"""Router del catálogo de productos monetizables."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from web.services import product_service

router = APIRouter(prefix="/api/products", tags=["products"])


class ProductUpsertRequest(BaseModel):
    id: str
    name: str
    short_name: str | None = None
    url: str
    description: str | None = ""
    price_usd: float | None = 0
    cta_style: str | None = "short"


class SetActiveRequest(BaseModel):
    active_product_id: str | None = None


@router.get("")
def list_products():
    return product_service.list_products()


@router.post("")
def upsert_product(body: ProductUpsertRequest):
    return product_service.upsert_product(body.model_dump())


@router.delete("/{product_id}")
def delete_product(product_id: str):
    return product_service.delete_product(product_id)


@router.post("/active")
def set_active(body: SetActiveRequest):
    return product_service.set_active(body.active_product_id)
