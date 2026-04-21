from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, Index, Boolean
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    bikes = relationship("Bike", back_populates="customer")
    services = relationship("Service", back_populates="customer")


class Bike(Base):
    __tablename__ = "bikes"
    __table_args__ = (Index("idx_bike_number", "bike_number"),)

    id = Column(Integer, primary_key=True, index=True)
    bike_number = Column(String(50), nullable=False, unique=True)
    bike_model = Column(String(255), nullable=True)          # nullable: Excel has no model column
    chassis_number = Column(String(50), nullable=True)       # Chachis No.
    visit_count = Column(Integer, default=0, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", back_populates="bikes")
    services = relationship("Service", back_populates="bike", order_by="Service.service_date.desc()")


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    bike_id = Column(Integer, ForeignKey("bikes.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    service_date = Column(DateTime(timezone=True), nullable=False)
    service_details = Column(Text, nullable=False)
    cost = Column(Float, nullable=False)
    odometer_km = Column(Integer, nullable=True)             # K. M.
    job_card = Column(Boolean, nullable=True)                # J/C (Y/N)
    payment_mode = Column(String(20), nullable=True)         # MODE OF PAYMNET
    mechanic_incentive = Column(Boolean, nullable=True)      # Deepak Incentive
    incentive_paid = Column(String(50), nullable=True)       # Incentive Given
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    bike = relationship("Bike", back_populates="services")
    customer = relationship("Customer", back_populates="services")
