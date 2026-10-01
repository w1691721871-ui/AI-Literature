from fastapi import APIRouter
from app.services.product_showcase_service import ProductShowcaseService
router=APIRouter(prefix="/api",tags=["product-showcase"]);service=ProductShowcaseService()
@router.get("/demo/overview")
def overview():return service.overview()
@router.get("/demo/workflow")
def workflow():return service.workflow()
@router.get("/product/capabilities")
def capabilities():return service.capabilities()
@router.get("/product/releases")
def releases():return service.releases()
@router.get("/business/dashboard")
def business():return service.business()
