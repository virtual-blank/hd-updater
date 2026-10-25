import msgspec


class RequestSchema(msgspec.Struct):
    id: str = msgspec.field(name="WORKORDERID")
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