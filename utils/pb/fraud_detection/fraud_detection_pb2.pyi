from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class FraudDetectionRequest(_message.Message):
    __slots__ = ("user", "orderData", "creditCard", "billingAddress", "telemetry")
    class User(_message.Message):
        __slots__ = ("name", "contact")
        NAME_FIELD_NUMBER: _ClassVar[int]
        CONTACT_FIELD_NUMBER: _ClassVar[int]
        name: str
        contact: str
        def __init__(self, name: _Optional[str] = ..., contact: _Optional[str] = ...) -> None: ...
    class OrderData(_message.Message):
        __slots__ = ("orderItems", "discountCode", "shippingMethod")
        class OrderItem(_message.Message):
            __slots__ = ("name", "quantity")
            NAME_FIELD_NUMBER: _ClassVar[int]
            QUANTITY_FIELD_NUMBER: _ClassVar[int]
            name: str
            quantity: int
            def __init__(self, name: _Optional[str] = ..., quantity: _Optional[int] = ...) -> None: ...
        ORDERITEMS_FIELD_NUMBER: _ClassVar[int]
        DISCOUNTCODE_FIELD_NUMBER: _ClassVar[int]
        SHIPPINGMETHOD_FIELD_NUMBER: _ClassVar[int]
        orderItems: _containers.RepeatedCompositeFieldContainer[FraudDetectionRequest.OrderData.OrderItem]
        discountCode: str
        shippingMethod: str
        def __init__(self, orderItems: _Optional[_Iterable[_Union[FraudDetectionRequest.OrderData.OrderItem, _Mapping]]] = ..., discountCode: _Optional[str] = ..., shippingMethod: _Optional[str] = ...) -> None: ...
    class CreditCard(_message.Message):
        __slots__ = ("number", "expirationDate", "cvv")
        NUMBER_FIELD_NUMBER: _ClassVar[int]
        EXPIRATIONDATE_FIELD_NUMBER: _ClassVar[int]
        CVV_FIELD_NUMBER: _ClassVar[int]
        number: str
        expirationDate: str
        cvv: str
        def __init__(self, number: _Optional[str] = ..., expirationDate: _Optional[str] = ..., cvv: _Optional[str] = ...) -> None: ...
    class BillingAddress(_message.Message):
        __slots__ = ("street", "city", "state", "zip", "country")
        STREET_FIELD_NUMBER: _ClassVar[int]
        CITY_FIELD_NUMBER: _ClassVar[int]
        STATE_FIELD_NUMBER: _ClassVar[int]
        ZIP_FIELD_NUMBER: _ClassVar[int]
        COUNTRY_FIELD_NUMBER: _ClassVar[int]
        street: str
        city: str
        state: str
        zip: str
        country: str
        def __init__(self, street: _Optional[str] = ..., city: _Optional[str] = ..., state: _Optional[str] = ..., zip: _Optional[str] = ..., country: _Optional[str] = ...) -> None: ...
    class Telemetry(_message.Message):
        __slots__ = ("device", "browser", "screenResolution", "referrer")
        class Browser(_message.Message):
            __slots__ = ("name", "version")
            NAME_FIELD_NUMBER: _ClassVar[int]
            VERSION_FIELD_NUMBER: _ClassVar[int]
            name: str
            version: str
            def __init__(self, name: _Optional[str] = ..., version: _Optional[str] = ...) -> None: ...
        class Device(_message.Message):
            __slots__ = ("type", "model", "os")
            TYPE_FIELD_NUMBER: _ClassVar[int]
            MODEL_FIELD_NUMBER: _ClassVar[int]
            OS_FIELD_NUMBER: _ClassVar[int]
            type: str
            model: str
            os: str
            def __init__(self, type: _Optional[str] = ..., model: _Optional[str] = ..., os: _Optional[str] = ...) -> None: ...
        DEVICE_FIELD_NUMBER: _ClassVar[int]
        BROWSER_FIELD_NUMBER: _ClassVar[int]
        SCREENRESOLUTION_FIELD_NUMBER: _ClassVar[int]
        REFERRER_FIELD_NUMBER: _ClassVar[int]
        device: FraudDetectionRequest.Telemetry.Device
        browser: FraudDetectionRequest.Telemetry.Browser
        screenResolution: str
        referrer: str
        def __init__(self, device: _Optional[_Union[FraudDetectionRequest.Telemetry.Device, _Mapping]] = ..., browser: _Optional[_Union[FraudDetectionRequest.Telemetry.Browser, _Mapping]] = ..., screenResolution: _Optional[str] = ..., referrer: _Optional[str] = ...) -> None: ...
    USER_FIELD_NUMBER: _ClassVar[int]
    ORDERDATA_FIELD_NUMBER: _ClassVar[int]
    CREDITCARD_FIELD_NUMBER: _ClassVar[int]
    BILLINGADDRESS_FIELD_NUMBER: _ClassVar[int]
    TELEMETRY_FIELD_NUMBER: _ClassVar[int]
    user: FraudDetectionRequest.User
    orderData: FraudDetectionRequest.OrderData
    creditCard: FraudDetectionRequest.CreditCard
    billingAddress: FraudDetectionRequest.BillingAddress
    telemetry: FraudDetectionRequest.Telemetry
    def __init__(self, user: _Optional[_Union[FraudDetectionRequest.User, _Mapping]] = ..., orderData: _Optional[_Union[FraudDetectionRequest.OrderData, _Mapping]] = ..., creditCard: _Optional[_Union[FraudDetectionRequest.CreditCard, _Mapping]] = ..., billingAddress: _Optional[_Union[FraudDetectionRequest.BillingAddress, _Mapping]] = ..., telemetry: _Optional[_Union[FraudDetectionRequest.Telemetry, _Mapping]] = ...) -> None: ...

class FraudDetectionResponse(_message.Message):
    __slots__ = ("isFraudulent", "reason")
    ISFRAUDULENT_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    isFraudulent: bool
    reason: str
    def __init__(self, isFraudulent: bool = ..., reason: _Optional[str] = ...) -> None: ...
