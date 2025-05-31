import json
import uuid
from datetime import datetime

from flask_mongoengine import MongoEngine

db = MongoEngine()

class PassengerType(db.Document):
    passenger_type_id = db.IntField(primary_key=True)
    created_by = db.StringField(required=True)
    created_date = db.DateTimeField(default=datetime.utcnow)
    deleted = db.BooleanField(default=False)
    is_active = db.BooleanField(default=True)
    max_age = db.IntField(required=True)
    min_age = db.IntField(required=True)
    passenger_type = db.StringField(required=True)

    def __str__(self):
        return f"{self.passenger_type} (Age range: {self.min_age}-{self.max_age})"

class Passenger(db.Document):
    title = db.StringField()
    firstName = db.StringField(required=True)
    lastName = db.StringField(required=True)
    dateOfBirth = db.DateTimeField()
    gender = db.StringField()
    nationality = db.StringField()
    passportNumber = db.StringField()
    email = db.EmailField(required=True)
    phoneNumber = db.StringField()
    address = db.StringField()
    emergencyContactName = db.StringField()
    emergencyContactPhone = db.StringField()
    frequentFlyerNumber = db.StringField()
    specialRequests = db.StringField()
    bookingId = db.StringField()
    isActive = db.BooleanField(default=True)
    isDeleted = db.BooleanField(default=False)
    createdDate = db.DateTimeField(default=datetime.now)
    createdBy = db.StringField(default=lambda: str(uuid.uuid4()))
    updatedBy = db.StringField()
    updatedDate = db.DateTimeField()
    cartId = db.StringField()
    orderId = db.IntField()
    passengerType = db.StringField()

    def __repr__(self):
        return f'<Passenger {self.firstName} {self.lastName}>'

    def to_json(self):
        data = {
            "id": str(self.id),
            "name": f"{self.firstName} {self.lastName}",
            "dob": self.dateOfBirth.strftime('%Y-%m-%d') if self.dateOfBirth else "",
            "email": self.email,
            "mobile": self.phoneNumber

        }
        return json.dumps(data)

def initialize_passenger_types():
    if PassengerType.objects.count() == 0:
        initial_data = [
            {"passenger_type_id": 1, "created_by": "ac176b23-df4a-488b-8ef4-a6d1ac33d6d5", "created_date": datetime(2024, 7, 9), "deleted": False, "is_active": True, "max_age": 65, "min_age": 18, "passenger_type": "Adults"},
            {"passenger_type_id": 2, "created_by": "2bfb9fbd-4f07-47d6-b0a4-af84c498efdr", "created_date": datetime(2024, 7, 3), "deleted": False, "is_active": True, "max_age": 17, "min_age": 5, "passenger_type": "Children"},
            {"passenger_type_id": 3, "created_by": "87c35a4b-d829-4dee-847f-75634487b030", "created_date": datetime(2024, 7, 3), "deleted": False, "is_active": True, "max_age": 4, "min_age": 1, "passenger_type": "Infants"},
            {"passenger_type_id": 4, "created_by": "87c35a4b-d829-4dee-847f-75634487b031", "created_date": datetime(2024, 7, 10), "deleted": False, "is_active": True, "max_age": 6, "min_age": 12, "passenger_type": "Kids"}
        ]
        PassengerType.objects.insert([PassengerType(**data) for data in initial_data])
        print("Initialized passenger types in database.")


