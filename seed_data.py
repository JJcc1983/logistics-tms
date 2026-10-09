from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models import Branch, Customer, Driver, Organization, Shipment, Staff

SIZE_SLOTS = {"S": 1, "M": 4, "L": 12}

VEHICLE_SPECS = {
    "moped": {"max_weight": 30.0, "capacity_slots": 10, "allowed_sizes": ["S"], "speed_kmh": 18.0, "stop_minutes": 2, "route_color": "#10b981"},
    "motorcycle": {"max_weight": 60.0, "capacity_slots": 25, "allowed_sizes": ["S", "M"], "speed_kmh": 28.0, "stop_minutes": 3, "route_color": "#f97316"},
    "van": {"max_weight": 350.0, "capacity_slots": 100, "allowed_sizes": ["S", "M", "L"], "speed_kmh": 22.0, "stop_minutes": 6, "route_color": "#3b82f6"},
}


def seed_data(db: Session) -> None:
    db.query(Shipment).delete()
    db.query(Driver).delete()
    db.query(Customer).delete()
    db.query(Staff).delete()
    db.query(Branch).delete()
    db.query(Organization).delete()
    db.flush()

    org = Organization(name="スマートロジ 本社")
    db.add(org)
    db.flush()

    branches = [
        Branch(
            organization_id=org.id,
            name="東京渋谷営業所",
            area_code="tokyo",
            address="東京都渋谷区渋谷1-2-3",
            lat=35.6580,
            lng=139.7016,
        ),
        Branch(
            organization_id=org.id,
            name="大阪梅田営業所",
            area_code="osaka",
            address="大阪府大阪市北区梅田4-5-6",
            lat=34.7024,
            lng=135.4959,
        ),
    ]
    db.add_all(branches)
    db.flush()

    drivers = [
        Driver(branch_id=branches[0].id, name="鈴木 一郎", employment_type="employee", vehicle_type="moped", current_lat=35.6595, current_lng=139.7030, status="online"),
        Driver(branch_id=branches[0].id, name="田中 二郎", employment_type="employee", vehicle_type="motorcycle", current_lat=35.6570, current_lng=139.7000, status="online"),
        Driver(branch_id=branches[0].id, name="佐藤 三郎", employment_type="contractor", vehicle_type="van", current_lat=35.6600, current_lng=139.7050, status="online"),
        Driver(branch_id=branches[1].id, name="高橋 四郎", employment_type="employee", vehicle_type="moped", current_lat=34.7035, current_lng=135.4970, status="online"),
        Driver(branch_id=branches[1].id, name="伊藤 五郎", employment_type="contractor", vehicle_type="motorcycle", current_lat=34.7010, current_lng=135.4940, status="online"),
        Driver(branch_id=branches[1].id, name="渡辺 六郎", employment_type="employee", vehicle_type="van", current_lat=34.7050, current_lng=135.5000, status="online"),
    ]
    db.add_all(drivers)
    db.flush()

    staff = [
        Staff(branch_id=branches[0].id, name="小林 マネージャー", role="manager"),
        Staff(branch_id=branches[0].id, name="加藤 オペレーター", role="operator"),
        Staff(branch_id=branches[1].id, name="木村 マネージャー", role="manager"),
        Staff(branch_id=branches[1].id, name="斎藤 オペレーター", role="operator"),
    ]
    db.add_all(staff)
    db.flush()

    customers = [
        Customer(name="山田 太郎", phone="090-1234-5678", default_address="東京都港区六本木1-1-1", lat=35.6628, lng=139.7317),
        Customer(name="佐藤 商事", phone="03-9876-5432", default_address="東京都千代田区丸の内2-2-2", lat=35.6812, lng=139.7671),
        Customer(name="鈴木 花子", phone="06-1111-2222", default_address="大阪府大阪市中央区道頓堀3-3-3", lat=34.6687, lng=135.5013),
        Customer(name="高橋 商店", phone="06-3333-4444", default_address="大阪府大阪市北区中之島4-4-4", lat=34.6915, lng=135.4950),
    ]
    db.add_all(customers)
    db.flush()

    base_time = datetime(2026, 10, 7, 8, 0, 0)
    shipments = [
        Shipment(tracking_number="TK-202610-001", branch_id=branches[0].id, sender_customer_id=customers[0].id, recipient_name="山田 太郎", recipient_phone="090-1234-5678", delivery_address="東京都渋谷区神宮前1-1-1", delivery_lat=35.6650, delivery_lng=139.7100, cargo_type="契約書パック", size_class="S", weight_kg=1.5, handling_flags="通常", shipping_fee=500, driver_id=drivers[0].id, status="delivering", created_at=base_time),
        Shipment(tracking_number="TK-202610-002", branch_id=branches[0].id, sender_customer_id=customers[1].id, recipient_name="佐藤 商事 御中", recipient_phone="03-9876-5432", delivery_address="東京都港区赤坂2-2-2", delivery_lat=35.6750, delivery_lng=139.7350, cargo_type="精密機器", size_class="M", weight_kg=12.0, handling_flags="精密機器", shipping_fee=1200, driver_id=drivers[1].id, status="delivering", created_at=base_time + timedelta(minutes=15)),
        Shipment(tracking_number="TK-202610-003", branch_id=branches[0].id, sender_customer_id=customers[0].id, recipient_name="山田 太郎", recipient_phone="090-1234-5678", delivery_address="東京都渋谷区桜丘町3-3-3", delivery_lat=35.6610, delivery_lng=139.7050, cargo_type="飲料水2ケース", size_class="L", weight_kg=24.0, handling_flags="通常", shipping_fee=1500, driver_id=None, status="in_hub", created_at=base_time + timedelta(minutes=30)),
        Shipment(tracking_number="TK-202610-004", branch_id=branches[0].id, sender_customer_id=customers[1].id, recipient_name="佐藤 商事 御中", recipient_phone="03-9876-5432", delivery_address="東京都渋谷区恵比寿4-4-4", delivery_lat=35.6450, delivery_lng=139.7100, cargo_type="衣類サンプル", size_class="M", weight_kg=8.0, handling_flags="通常", shipping_fee=900, driver_id=None, status="created", created_at=base_time + timedelta(minutes=45)),
        Shipment(tracking_number="TK-202610-005", branch_id=branches[0].id, sender_customer_id=customers[0].id, recipient_name="山田 太郎", recipient_phone="090-1234-5678", delivery_address="東京都渋谷区代々木5-5-5", delivery_lat=35.6840, delivery_lng=139.7030, cargo_type="書類", size_class="S", weight_kg=2.0, handling_flags="通常", shipping_fee=400, driver_id=None, status="completed", created_at=base_time - timedelta(hours=2)),
        Shipment(tracking_number="OS-202610-001", branch_id=branches[1].id, sender_customer_id=customers[2].id, recipient_name="鈴木 花子", recipient_phone="06-1111-2222", delivery_address="大阪府大阪市北区茶屋町1-1-1", delivery_lat=34.7050, delivery_lng=135.4980, cargo_type="契約書パック", size_class="S", weight_kg=1.0, handling_flags="通常", shipping_fee=500, driver_id=drivers[3].id, status="delivering", created_at=base_time + timedelta(minutes=10)),
        Shipment(tracking_number="OS-202610-002", branch_id=branches[1].id, sender_customer_id=customers[3].id, recipient_name="高橋 商店 御中", recipient_phone="06-3333-4444", delivery_address="大阪府大阪市中央区心斎橋2-2-2", delivery_lat=34.6750, delivery_lng=135.5020, cargo_type="精密機器", size_class="M", weight_kg=15.0, handling_flags="ワレモノ", shipping_fee=1300, driver_id=None, status="in_hub", created_at=base_time + timedelta(minutes=25)),
        Shipment(tracking_number="OS-202610-003", branch_id=branches[1].id, sender_customer_id=customers[2].id, recipient_name="鈴木 花子", recipient_phone="06-1111-2222", delivery_address="大阪府大阪市西区江戸堀3-3-3", delivery_lat=34.6850, delivery_lng=135.4900, cargo_type="飲料水2ケース", size_class="L", weight_kg=24.0, handling_flags="通常", shipping_fee=1500, driver_id=None, status="created", created_at=base_time + timedelta(minutes=40)),
        Shipment(tracking_number="OS-202610-004", branch_id=branches[1].id, sender_customer_id=customers[3].id, recipient_name="高橋 商店 御中", recipient_phone="06-3333-4444", delivery_address="大阪府大阪市北区曽根崎4-4-4", delivery_lat=34.7100, delivery_lng=135.4950, cargo_type="食品サンプル", size_class="S", weight_kg=3.0, handling_flags="通常", shipping_fee=600, driver_id=None, status="completed", created_at=base_time - timedelta(hours=1)),
    ]
    db.add_all(shipments)
    db.commit()
