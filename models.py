from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)


class Branch(Base):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(100), nullable=False)
    area_code = Column(String(20), nullable=False)
    address = Column(String(255), nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)

    organization = relationship("Organization")


class Staff(Base):
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="operator")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(30), nullable=False)
    default_address = Column(String(255), nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)


class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    name = Column(String(100), nullable=False)
    employment_type = Column(String(20), nullable=False, default="employee")
    vehicle_type = Column(String(20), nullable=False, default="moped")
    current_lat = Column(Float, nullable=False)
    current_lng = Column(Float, nullable=False)
    status = Column(String(20), nullable=False, default="online")

    branch = relationship("Branch")


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    tracking_number = Column(String(30), unique=True, nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    sender_customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    recipient_name = Column(String(100), nullable=False)
    recipient_phone = Column(String(30), nullable=False)
    delivery_address = Column(String(255), nullable=False)
    delivery_lat = Column(Float, nullable=False)
    delivery_lng = Column(Float, nullable=False)
    cargo_type = Column(String(100), nullable=False)
    size_class = Column(String(5), nullable=False)
    weight_kg = Column(Float, nullable=False)
    handling_flags = Column(String(100), nullable=False, default="通常")
    shipping_fee = Column(Integer, nullable=False, default=0)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    status = Column(String(20), nullable=False, default="created")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    branch = relationship("Branch")
    driver = relationship("Driver")
    sender_customer = relationship("Customer")
