from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class User(_message.Message):
    __slots__ = ("name", "contact")
    NAME_FIELD_NUMBER: _ClassVar[int]
    CONTACT_FIELD_NUMBER: _ClassVar[int]
    name: str
    contact: str
    def __init__(self, name: _Optional[str] = ..., contact: _Optional[str] = ...) -> None: ...

class CreditCard(_message.Message):
    __slots__ = ("number", "expirationDate", "cvv")
    NUMBER_FIELD_NUMBER: _ClassVar[int]
    EXPIRATIONDATE_FIELD_NUMBER: _ClassVar[int]
    CVV_FIELD_NUMBER: _ClassVar[int]
    number: str
    expirationDate: str
    cvv: str
    def __init__(self, number: _Optional[str] = ..., expirationDate: _Optional[str] = ..., cvv: _Optional[str] = ...) -> None: ...

class Item(_message.Message):
    __slots__ = ("name", "quantity")
    NAME_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    name: str
    quantity: int
    def __init__(self, name: _Optional[str] = ..., quantity: _Optional[int] = ...) -> None: ...

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

class Device(_message.Message):
    __slots__ = ("type", "model", "os")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    OS_FIELD_NUMBER: _ClassVar[int]
    type: str
    model: str
    os: str
    def __init__(self, type: _Optional[str] = ..., model: _Optional[str] = ..., os: _Optional[str] = ...) -> None: ...

class Browser(_message.Message):
    __slots__ = ("name", "version")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    name: str
    version: str
    def __init__(self, name: _Optional[str] = ..., version: _Optional[str] = ...) -> None: ...

class FraudRequest(_message.Message):
    __slots__ = ("user", "creditCard", "userComment", "items", "discountCode", "shippingMethod", "giftMessage", "billingAddress", "termsAndConditionsAccepted", "notificationPreferences", "device", "browser", "appVersion", "screenResolution", "referrer", "deviceLanguage")
    USER_FIELD_NUMBER: _ClassVar[int]
    CREDITCARD_FIELD_NUMBER: _ClassVar[int]
    USERCOMMENT_FIELD_NUMBER: _ClassVar[int]
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    DISCOUNTCODE_FIELD_NUMBER: _ClassVar[int]
    SHIPPINGMETHOD_FIELD_NUMBER: _ClassVar[int]
    GIFTMESSAGE_FIELD_NUMBER: _ClassVar[int]
    BILLINGADDRESS_FIELD_NUMBER: _ClassVar[int]
    TERMSANDCONDITIONSACCEPTED_FIELD_NUMBER: _ClassVar[int]
    NOTIFICATIONPREFERENCES_FIELD_NUMBER: _ClassVar[int]
    DEVICE_FIELD_NUMBER: _ClassVar[int]
    BROWSER_FIELD_NUMBER: _ClassVar[int]
    APPVERSION_FIELD_NUMBER: _ClassVar[int]
    SCREENRESOLUTION_FIELD_NUMBER: _ClassVar[int]
    REFERRER_FIELD_NUMBER: _ClassVar[int]
    DEVICELANGUAGE_FIELD_NUMBER: _ClassVar[int]
    user: User
    creditCard: CreditCard
    userComment: str
    items: _containers.RepeatedCompositeFieldContainer[Item]
    discountCode: str
    shippingMethod: str
    giftMessage: str
    billingAddress: BillingAddress
    termsAndConditionsAccepted: bool
    notificationPreferences: _containers.RepeatedScalarFieldContainer[str]
    device: Device
    browser: Browser
    appVersion: str
    screenResolution: str
    referrer: str
    deviceLanguage: str
    def __init__(self, user: _Optional[_Union[User, _Mapping]] = ..., creditCard: _Optional[_Union[CreditCard, _Mapping]] = ..., userComment: _Optional[str] = ..., items: _Optional[_Iterable[_Union[Item, _Mapping]]] = ..., discountCode: _Optional[str] = ..., shippingMethod: _Optional[str] = ..., giftMessage: _Optional[str] = ..., billingAddress: _Optional[_Union[BillingAddress, _Mapping]] = ..., termsAndConditionsAccepted: bool = ..., notificationPreferences: _Optional[_Iterable[str]] = ..., device: _Optional[_Union[Device, _Mapping]] = ..., browser: _Optional[_Union[Browser, _Mapping]] = ..., appVersion: _Optional[str] = ..., screenResolution: _Optional[str] = ..., referrer: _Optional[str] = ..., deviceLanguage: _Optional[str] = ...) -> None: ...

class FraudResponse(_message.Message):
    __slots__ = ("isFraud", "message")
    ISFRAUD_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    isFraud: bool
    message: str
    def __init__(self, isFraud: bool = ..., message: _Optional[str] = ...) -> None: ...

class HealthCheckRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class HealthCheckResponse(_message.Message):
    __slots__ = ("status",)
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: str
    def __init__(self, status: _Optional[str] = ...) -> None: ...
