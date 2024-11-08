from datetime import date
from flask import current_app
from werkzeug.security import generate_password_hash

from scheduler import db
from scheduler.models import User, Patient, DosuType, get_or_create

def create_defaults():
    """Create default records (admin user, blocked patient, and off-time dosutypes) if they don't exist"""
    try:
        # Create default admin user
        admin_user, created = get_or_create(
            User,
            username="admin",
            defaults={
                "password": generate_password_hash("a"),
                "email": None,
                "privilege": 5,
                "available": True
            }
        )
        if created:
            current_app.logger.info("Created default admin user")

        # Create default blocked patient
        blocked_patient, created = get_or_create(
            Patient,
            mrn=0,
            defaults={
                "name": "blocked",
                "sex": "male",
                "birthday": date(9999, 12, 31),
                "tel": "",
                "note": "This is a blocked patient for off-time slots"
            }
        )
        if created:
            current_app.logger.info("Created default blocked patient")

        # Create default dosutypes
        default_dosutypes = [
            {
                "name": "off",
                "order_code": "off",
                "slot_quantity": 100,
                "price": 0,
                "available": True
            },
            {
                "name": "off-half",
                "order_code": "off-half",
                "slot_quantity": 8,
                "price": 0,
                "available": True
            },
            {
                "name": "off-1slot",
                "order_code": "off-1slot",
                "slot_quantity": 1,
                "price": 0,
                "available": True
            }
        ]

        for dt_data in default_dosutypes:
            dosutype, created = get_or_create(
                DosuType,
                name=dt_data["name"],
                defaults=dt_data
            )
            if created:
                current_app.logger.info(f"Created default dosutype: {dt_data['name']}")

    except Exception as e:
        current_app.logger.error(f"Error creating defaults: {str(e)}")
        db.session.rollback()
        raise 