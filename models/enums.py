import enum


class RoleType(enum.Enum):
    NEW_USER = "user"
    AGENT = "agent"
    ProductOwner = "ProductOwner"
    ADMIN = "admin"
    PackageUploader = "PackageUploader"
    MANAGEMENT = "management"
