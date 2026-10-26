import msgspec
import enum
from src.users.schemas import UserProfileCache


class RequestSchema(msgspec.Struct):
    id: int = msgspec.field(name="WORKORDERID")
    subject: str = msgspec.field(name="SUBJECT", default="Без темы")
    status: str = msgspec.field(name="STATUS", default="-")
    technician: str = msgspec.field(name="TECHNICIAN", default="")


class OperationResultSchema(msgspec.Struct):
    status: str = ""
    message: str = ""


class OperationDetailsSchema(msgspec.Struct):
    result: OperationResultSchema | None = None
    details: list[RequestSchema] | RequestSchema | None = None


class SdpResponseSchema(msgspec.Struct):
    operation: OperationDetailsSchema


class RequestFullSchema(msgspec.Struct):
    id: int = msgspec.field(name="WORKORDERID")
    subject: str = msgspec.field(name="SUBJECT", default="-")
    status: str = msgspec.field(name="STATUS", default="Не распределено")
    technician: str = msgspec.field(name="TECHNICIAN", default="Не назначено")
    description: str = msgspec.field(name="SHORTDESCRIPTION", default="-")
    requester: str = msgspec.field(name="REQUESTER", default="-")


