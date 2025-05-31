from mongoengine import Document, EmbeddedDocument, fields

class CustomField(EmbeddedDocument):
    key = fields.StringField()
    label = fields.StringField()
    type = fields.StringField()
    required = fields.BooleanField(default=False)
    placeholder = fields.StringField()
    options = fields.ListField(fields.DictField())  # To store option value and label for select type

class ProductDetails(Document):
    entityName = fields.ListField(fields.StringField(), required=True)
    customFields = fields.EmbeddedDocumentListField(CustomField)

    def __str__(self):
        return f"{self.entityName} - {len(self.customFields)} custom fields"
