import math
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

import models
import schemas
from database import Base, engine, get_db
from seed_data import SIZE_SLOTS, VEHICLE_SPECS, seed_data

app = FastAPI(title="Logistics TMS", version="1.0.0")


class NoCacheStaticMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


app.add_middleware(NoCacheStaticMiddleware)


def calculate_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def optimize_deliveries_and_calc_eta(shipments: list, driver, db: Session) -> list:
    spec = VEHICLE_SPECS.get(driver.vehicle_type, VEHICLE_SPECS["moped"])
    speed = spec["speed_kmh"]
    stop_min = spec["stop_minutes"]

    branch = db.query(models.Branch).filter(models.Branch.id == driver.branch_id).first()
    start_lat = branch.lat if branch else driver.current_lat
    start_lng = branch.lng if branch else driver.current_lng

    remaining = list(shipments)
    ordered = []
    cur_lat, cur_lng = start_lat, start_lng
    total_minutes = 0.0

    while remaining:
        nearest = min(
            remaining,
            key=lambda s: calculate_distance_km(cur_lat, cur_lng, s.delivery_lat, s.delivery_lng),
        )
        dist = calculate_distance_km(cur_lat, cur_lng, nearest.delivery_lat, nearest.delivery_lng)
        travel_min = dist / speed * 60.0
        total_minutes += travel_min
        eta = int(round(total_minutes))
        arrival = datetime.utcnow() + timedelta(minutes=total_minutes)
        arrival_str = arrival.strftime("%H:%M") + "頃"
        ordered.append((nearest, len(ordered) + 1, eta, arrival_str))
        total_minutes += stop_min
        cur_lat, cur_lng = nearest.delivery_lat, nearest.delivery_lng
        remaining.remove(nearest)

    return ordered

STATIC_DIR = Path(__file__).parent / "static"


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        if db.query(models.Organization).count() == 0:
            seed_data(db)
    finally:
        db.close()


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "admin.html")


@app.get("/admin", include_in_schema=False)
def admin_page():
    return FileResponse(STATIC_DIR / "admin.html")


@app.get("/branch", include_in_schema=False)
def branch_page():
    return FileResponse(STATIC_DIR / "branch.html")


@app.get("/driver", include_in_schema=False)
def driver_page():
    return FileResponse(STATIC_DIR / "driver.html")


@app.get("/customer", include_in_schema=False)
def customer_page():
    return FileResponse(STATIC_DIR / "customer.html")


@app.get("/api/branches", response_model=list[schemas.BranchOut])
def list_branches(db: Session = Depends(get_db)):
    return db.query(models.Branch).all()


@app.get("/api/drivers", response_model=list[schemas.DriverOut])
def list_drivers(branch_id: int, db: Session = Depends(get_db)):
    drivers = db.query(models.Driver).filter(models.Driver.branch_id == branch_id).all()
    result = []
    for d in drivers:
        active = (
            db.query(models.Shipment)
            .filter(models.Shipment.driver_id == d.id, models.Shipment.status == "delivering")
            .all()
        )
        spec = VEHICLE_SPECS.get(d.vehicle_type, VEHICLE_SPECS["moped"])
        out = schemas.DriverOut.model_validate(d)
        out.active_count = len(active)
        out.active_weight = sum(s.weight_kg for s in active)
        out.max_weight = spec["max_weight"]
        out.capacity_slots = spec["capacity_slots"]
        out.used_slots = sum(SIZE_SLOTS.get(s.size_class, 1) for s in active)
        out.allowed_sizes = spec["allowed_sizes"]
        out.speed_kmh = spec["speed_kmh"]
        out.stop_minutes = spec["stop_minutes"]
        out.route_color = spec["route_color"]
        result.append(out)
    return result


@app.get("/api/shipments", response_model=list[schemas.ShipmentOut])
def list_shipments(
    branch_id: int,
    status: str | None = None,
    driver_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.Shipment).filter(models.Shipment.branch_id == branch_id)
    if status:
        query = query.filter(models.Shipment.status == status)
    if driver_id is not None:
        query = query.filter(models.Shipment.driver_id == driver_id)
    shipments = query.order_by(models.Shipment.created_at.desc()).all()

    eta_map: dict[int, tuple[int, int, str]] = {}
    if driver_id is not None and status == "delivering" and shipments:
        driver = db.query(models.Driver).filter(models.Driver.id == driver_id).first()
        if driver:
            for shipment, order, eta, arrival_str in optimize_deliveries_and_calc_eta(shipments, driver, db):
                eta_map[shipment.id] = (order, eta, arrival_str)

    result = []
    for s in shipments:
        out = schemas.ShipmentOut.model_validate(s)
        out.driver_name = s.driver.name if s.driver else None
        if s.id in eta_map:
            order, eta, arrival_str = eta_map[s.id]
            out.stop_order = order
            out.eta_minutes = eta
            out.estimated_arrival_time = arrival_str
        result.append(out)
    return result


@app.post("/api/shipments", response_model=schemas.ShipmentOut, status_code=201)
def create_shipment(payload: schemas.ShipmentCreate, db: Session = Depends(get_db)):
    branch = db.query(models.Branch).filter(models.Branch.id == payload.branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="営業所が見つかりません")
    customer = db.query(models.Customer).filter(models.Customer.id == payload.sender_customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="荷主顧客が見つかりません")

    prefix = "TK" if branch.area_code == "tokyo" else "OS"
    today = datetime.utcnow().strftime("%Y%m%d")
    count_today = (
        db.query(models.Shipment)
        .filter(models.Shipment.tracking_number.like(f"{prefix}-{today}-%"))
        .count()
    )
    tracking_number = f"{prefix}-{today}-{count_today + 1:03d}"

    shipment = models.Shipment(
        tracking_number=tracking_number,
        branch_id=payload.branch_id,
        sender_customer_id=payload.sender_customer_id,
        recipient_name=payload.recipient_name,
        recipient_phone=payload.recipient_phone,
        delivery_address=payload.delivery_address,
        delivery_lat=payload.delivery_lat,
        delivery_lng=payload.delivery_lng,
        cargo_type=payload.cargo_type,
        size_class=payload.size_class,
        weight_kg=payload.weight_kg,
        handling_flags=payload.handling_flags,
        shipping_fee=payload.shipping_fee,
        status="created",
        created_at=datetime.utcnow(),
    )
    db.add(shipment)
    db.commit()
    db.refresh(shipment)
    out = schemas.ShipmentOut.model_validate(shipment)
    out.driver_name = None
    return out


@app.post("/api/shipments/{shipment_id}/assign", response_model=schemas.ShipmentOut)
def assign_shipment(shipment_id: int, payload: schemas.AssignRequest, db: Session = Depends(get_db)):
    shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="伝票が見つかりません")
    if shipment.status not in ("created", "in_hub"):
        raise HTTPException(status_code=400, detail=f"現在のステータス「{shipment.status}」では受託できません")

    driver = db.query(models.Driver).filter(models.Driver.id == payload.driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="ドライバーが見つかりません")
    if driver.branch_id != shipment.branch_id:
        raise HTTPException(status_code=400, detail="他拠点のドライバーには割当できません")

    spec = VEHICLE_SPECS.get(driver.vehicle_type, VEHICLE_SPECS["moped"])
    active = (
        db.query(models.Shipment)
        .filter(models.Shipment.driver_id == driver.id, models.Shipment.status == "delivering")
        .all()
    )
    current_weight = sum(s.weight_kg for s in active)
    current_count = len(active)
    used_slots = sum(SIZE_SLOTS.get(s.size_class, 1) for s in active)
    needed_slots = SIZE_SLOTS.get(shipment.size_class, 1)

    if shipment.size_class not in spec["allowed_sizes"]:
        raise HTTPException(
            status_code=400,
            detail=f"積載オーバー: サイズ「{shipment.size_class}」は {driver.vehicle_type} の許容サイズ {spec['allowed_sizes']} に含まれていません",
        )
    if used_slots + needed_slots > spec["capacity_slots"]:
        raise HTTPException(
            status_code=400,
            detail=f"積載オーバー: 荷台容量 {spec['capacity_slots']}スロット を超えます（現在{used_slots}スロット + {needed_slots}スロット）",
        )
    if current_weight + shipment.weight_kg > spec["max_weight"]:
        raise HTTPException(
            status_code=400,
            detail=f"積載オーバー: 最大積載重量 {spec['max_weight']}kg を超えます（現在{current_weight}kg + {shipment.weight_kg}kg）",
        )

    shipment.driver_id = driver.id
    shipment.status = "delivering"
    driver.status = "delivering"
    db.commit()
    db.refresh(shipment)
    out = schemas.ShipmentOut.model_validate(shipment)
    out.driver_name = driver.name
    return out


@app.post("/api/shipments/{shipment_id}/complete", response_model=schemas.ShipmentOut)
def complete_shipment(shipment_id: int, db: Session = Depends(get_db)):
    shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="伝票が見つかりません")
    if shipment.status != "delivering":
        raise HTTPException(status_code=400, detail="配達中の伝票のみ完了にできます")

    shipment.status = "completed"
    driver = db.query(models.Driver).filter(models.Driver.id == shipment.driver_id).first()
    if driver:
        remaining = (
            db.query(models.Shipment)
            .filter(models.Shipment.driver_id == driver.id, models.Shipment.status == "delivering")
            .count()
        )
        if remaining == 0:
            driver.status = "online"
    db.commit()
    db.refresh(shipment)
    out = schemas.ShipmentOut.model_validate(shipment)
    out.driver_name = driver.name if driver else None
    return out


@app.get("/api/shipments/track/{tracking_number}", response_model=schemas.TrackingOut)
def track_shipment(tracking_number: str, db: Session = Depends(get_db)):
    shipment = (
        db.query(models.Shipment)
        .filter(models.Shipment.tracking_number == tracking_number)
        .first()
    )
    if not shipment:
        raise HTTPException(status_code=404, detail="伝票番号が見つかりません")

    driver_lat = None
    driver_lng = None
    stop_order = None
    total_stops = None
    eta_minutes = None
    estimated_arrival_time = None
    route_color = None

    if shipment.status == "delivering" and shipment.driver:
        driver = shipment.driver
        driver_lat = driver.current_lat
        driver_lng = driver.current_lng
        spec = VEHICLE_SPECS.get(driver.vehicle_type, VEHICLE_SPECS["moped"])
        route_color = spec["route_color"]

        active = (
            db.query(models.Shipment)
            .filter(models.Shipment.driver_id == driver.id, models.Shipment.status == "delivering")
            .all()
        )
        total_stops = len(active)
        for s, order, eta, arrival_str in optimize_deliveries_and_calc_eta(active, driver, db):
            if s.id == shipment.id:
                stop_order = order
                eta_minutes = eta
                estimated_arrival_time = arrival_str
                break

    return schemas.TrackingOut(
        tracking_number=shipment.tracking_number,
        status=shipment.status,
        recipient_name=shipment.recipient_name,
        delivery_address=shipment.delivery_address,
        cargo_type=shipment.cargo_type,
        size_class=shipment.size_class,
        weight_kg=shipment.weight_kg,
        driver_name=shipment.driver.name if shipment.driver else None,
        driver_vehicle=shipment.driver.vehicle_type if shipment.driver else None,
        delivery_lat=shipment.delivery_lat,
        delivery_lng=shipment.delivery_lng,
        created_at=shipment.created_at,
        branch_name=shipment.branch.name,
        driver_lat=driver_lat,
        driver_lng=driver_lng,
        stop_order=stop_order,
        total_stops=total_stops,
        eta_minutes=eta_minutes,
        estimated_arrival_time=estimated_arrival_time,
        route_color=route_color,
    )


@app.get("/api/admin/stats", response_model=schemas.AdminStats)
def admin_stats(db: Session = Depends(get_db)):
    total = db.query(models.Shipment).count()
    completed = db.query(models.Shipment).filter(models.Shipment.status == "completed").count()
    active = db.query(models.Shipment).filter(models.Shipment.status == "delivering").count()
    unassigned = (
        db.query(models.Shipment)
        .filter(models.Shipment.status.in_(["created", "in_hub"]))
        .count()
    )

    vehicle_util = []
    for vtype, spec in VEHICLE_SPECS.items():
        v_drivers = db.query(models.Driver).filter(models.Driver.vehicle_type == vtype).all()
        total_d = len(v_drivers)
        busy_d = len([d for d in v_drivers if d.status == "delivering"])
        vehicle_util.append(
            {
                "vehicle_type": vtype,
                "total": total_d,
                "busy": busy_d,
                "utilization_rate": round(busy_d / total_d * 100, 1) if total_d else 0.0,
            }
        )

    branches = []
    for b in db.query(models.Branch).all():
        b_total = db.query(models.Shipment).filter(models.Shipment.branch_id == b.id).count()
        b_completed = (
            db.query(models.Shipment)
            .filter(models.Shipment.branch_id == b.id, models.Shipment.status == "completed")
            .count()
        )
        branches.append(
            {
                "id": b.id,
                "name": b.name,
                "total": b_total,
                "completed": b_completed,
                "completion_rate": round(b_completed / b_total * 100, 1) if b_total else 0.0,
            }
        )

    return schemas.AdminStats(
        total_shipments=total,
        completed_shipments=completed,
        completion_rate=round(completed / total * 100, 1) if total else 0.0,
        active_shipments=active,
        unassigned_shipments=unassigned,
        vehicle_utilization=vehicle_util,
        branches=branches,
    )


@app.post("/api/demo/reset")
def demo_reset(db: Session = Depends(get_db)):
    seed_data(db)
    return {"message": "デモデータを初期化しました"}


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
