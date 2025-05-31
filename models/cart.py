from datetime import datetime
from flask_mongoengine import MongoEngine
from mongoengine import EmbeddedDocument, EmbeddedDocumentField, ListField, ReferenceField

db = MongoEngine()

class TravelDetails(EmbeddedDocument):
    departureDate = db.DateTimeField(required=True)
    returnDate = db.DateTimeField()
    fromAirport = db.StringField(required=True)
    toAirport = db.StringField(required=True)
    time = db.StringField(required=True)
    # arrivalDate = db.StringField(),
    flightNumber = db.StringField(required=True)
    selectedOptions = ListField(db.StringField())

class ItemDetails(EmbeddedDocument):
    name = db.StringField(required=True)
    imageUrl = db.StringField(required=True)
    entityId = db.StringField(required=True)
    quantity = db.IntField(required=True)
    productEntityId = db.IntField(required=True)
    variantEntityId = db.IntField(required=True)
    extendedListPrice = db.FloatField(required=True)
    extendedSalePrice = db.FloatField(required=True)
    discountedAmount = db.FloatField(required=True)
    selectedOptions = ListField(db.StringField())


class Order(db.Document):
    cartId = db.StringField(required=True)
    isTaxIncluded = db.BooleanField(required=True)
    currencyCode = db.StringField(required=True)
    lineItems = ListField(EmbeddedDocumentField(ItemDetails))
    travelDetails = ListField(EmbeddedDocumentField(TravelDetails))
    status = db.StringField(default='Pending', choices=('Pending', 'Confirmed', 'Cancelled'))
    createdDate = db.DateTimeField(default=datetime.now)
    createdBy = ReferenceField('Users', reverse_delete_rule=db.CASCADE)

    def __repr__(self):
        return f'<Order {self.cartId}>'
