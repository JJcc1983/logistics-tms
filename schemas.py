from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BranchOut(BaseModel):
    id: int
    name: str
    area_code: str
    address: str
    lat: float
    lng: float

    model_config = {"from_attributes": True}


class DriverOut(BaseModel):
    id: int
    branch_id: int
    name: str
    employment_type: str
    vehicle_type: str
    current_lat: float
    current_lng: float
    status: str
    active_count: int = 0
    active_weight: float = 0.0
    max_weight: float = 0.0
    capacity_slots: int = 0
    used_slots: int = 0
    allowed_sizes: list[str] = []
    speed_kmh: float = 0.0
    stop_minutes: int = 0
    route_color: str = "#3b82f6"

    model_config = {"from_attributes": True}


class ShipmentOut(BaseModel):
    id: int
    tracking_number: str
    branch_id: int
    sender_customer_id: int
    recipient_name: str
    recipient_phone: str
    delivery_address: str
    delivery_lat: float
    delivery_lng: float
    cargo_type: str
    size_class: str
    weight_kg: float
    handling_flags: str
    shipping_fee: int
    driver_id: Optional[int] = None
    status: str
    created_at: datetime
    driver_name: Optional[str] = None
    stop_order: Optional[int] = None
    eta_minutes: Optional[int] = None
    estimated_arrival_time: Optional[str] = None

    model_config = {"from_attributes": True}


class ShipmentCreate(BaseModel):
    branch_id: int
    sender_customer_id: int
    recipient_name: str
    recipient_phone: str
    delivery_address: str
    delivery_lat: float
    delivery_lng: float
    cargo_type: str
    size_class: str = Field(pattern="^[SML]$")
    weight_kg: float = Field(gt=0)
    handling_flags: str = "通常"
    shipping_fee: int = 0


class AssignRequest(BaseModel):
    driver_id: int


class TrackingOut(BaseModel):
    tracking_number: str
    status: str
    recipient_name: str
    delivery_address: str
    cargo_type: str
    size_class: str
    weight_kg: float
    driver_name: Optional[str] = None
    driver_vehicle: Optional[str] = None
    delivery_lat: float
    delivery_lng: float
    created_at: datetime
    branch_name: str
    driver_lat: Optional[float] = None
    driver_lng: Optional[float] = None
    stop_order: Optional[int] = None
    total_stops: Optional[int] = None
    eta_minutes: Optional[int] = None
    estimated_arrival_time: Optional[str] = None
    route_color: Optional[str] = None

    model_config = {"from_attributes": True}


class AdminStats(BaseModel):
    total_shipments: int
    completed_shipments: int
    completion_rate: float
    active_shipments: int
    unassigned_shipments: int
    vehicle_utilization: list[dict]
    branches: list[dict]
