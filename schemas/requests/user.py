from marshmallow import Schema, fields, validate


class BaseUser(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=3, max=255))


class TravelLoginRequestSchema(BaseUser):
    pass


class TravelRegisterRequestSchema(BaseUser):
    password2 = fields.String(required=True, validate=validate.Length(min=3, max=255))
    role = fields.String(validate=validate.OneOf(["user", "admin", "management"]))
