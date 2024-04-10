from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Book(_message.Message):
    __slots__ = ("id", "name", "author")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_FIELD_NUMBER: _ClassVar[int]
    id: int
    name: str
    author: str
    def __init__(self, id: _Optional[int] = ..., name: _Optional[str] = ..., author: _Optional[str] = ...) -> None: ...

class SuggestionRequest(_message.Message):
    __slots__ = ("book_titles",)
    BOOK_TITLES_FIELD_NUMBER: _ClassVar[int]
    book_titles: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, book_titles: _Optional[_Iterable[str]] = ...) -> None: ...

class SuggestionResponse(_message.Message):
    __slots__ = ("book_suggestions",)
    BOOK_SUGGESTIONS_FIELD_NUMBER: _ClassVar[int]
    book_suggestions: _containers.RepeatedCompositeFieldContainer[Book]
    def __init__(self, book_suggestions: _Optional[_Iterable[_Union[Book, _Mapping]]] = ...) -> None: ...

class VectorClock(_message.Message):
    __slots__ = ("process_id", "clock")
    PROCESS_ID_FIELD_NUMBER: _ClassVar[int]
    CLOCK_FIELD_NUMBER: _ClassVar[int]
    process_id: int
    clock: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, process_id: _Optional[int] = ..., clock: _Optional[_Iterable[int]] = ...) -> None: ...

class CheckoutRequest(_message.Message):
    __slots__ = ("user", "creditCard", "billingAddress", "device", "browser", "items", "referrer", "vector_clock")
    USER_FIELD_NUMBER: _ClassVar[int]
    CREDITCARD_FIELD_NUMBER: _ClassVar[int]
    BILLINGADDRESS_FIELD_NUMBER: _ClassVar[int]
    DEVICE_FIELD_NUMBER: _ClassVar[int]
    BROWSER_FIELD_NUMBER: _ClassVar[int]
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    REFERRER_FIELD_NUMBER: _ClassVar[int]
    VECTOR_CLOCK_FIELD_NUMBER: _ClassVar[int]
    user: UserData
    creditCard: CreditCardData
    billingAddress: BillingAddressData
    device: DeviceData
    browser: BrowserData
    items: _containers.RepeatedCompositeFieldContainer[ItemData]
    referrer: str
    vector_clock: VectorClockMessage
    def __init__(self, user: _Optional[_Union[UserData, _Mapping]] = ..., creditCard: _Optional[_Union[CreditCardData, _Mapping]] = ..., billingAddress: _Optional[_Union[BillingAddressData, _Mapping]] = ..., device: _Optional[_Union[DeviceData, _Mapping]] = ..., browser: _Optional[_Union[BrowserData, _Mapping]] = ..., items: _Optional[_Iterable[_Union[ItemData, _Mapping]]] = ..., referrer: _Optional[str] = ..., vector_clock: _Optional[_Union[VectorClockMessage, _Mapping]] = ...) -> None: ...

class UserData(_message.Message):
    __slots__ = ("name", "contact")
    NAME_FIELD_NUMBER: _ClassVar[int]
    CONTACT_FIELD_NUMBER: _ClassVar[int]
    name: str
    contact: str
    def __init__(self, name: _Optional[str] = ..., contact: _Optional[str] = ...) -> None: ...

class CreditCardData(_message.Message):
    __slots__ = ("number", "expirationDate", "cvv")
    NUMBER_FIELD_NUMBER: _ClassVar[int]
    EXPIRATIONDATE_FIELD_NUMBER: _ClassVar[int]
    CVV_FIELD_NUMBER: _ClassVar[int]
    number: str
    expirationDate: str
    cvv: str
    def __init__(self, number: _Optional[str] = ..., expirationDate: _Optional[str] = ..., cvv: _Optional[str] = ...) -> None: ...

class BillingAddressData(_message.Message):
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

class DeviceData(_message.Message):
    __slots__ = ("type", "model", "os")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    OS_FIELD_NUMBER: _ClassVar[int]
    type: str
    model: str
    os: str
    def __init__(self, type: _Optional[str] = ..., model: _Optional[str] = ..., os: _Optional[str] = ...) -> None: ...

class BrowserData(_message.Message):
    __slots__ = ("name", "version")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    name: str
    version: str
    def __init__(self, name: _Optional[str] = ..., version: _Optional[str] = ...) -> None: ...

class ItemData(_message.Message):
    __slots__ = ("name", "quantity")
    NAME_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    name: str
    quantity: str
    def __init__(self, name: _Optional[str] = ..., quantity: _Optional[str] = ...) -> None: ...

class Determination(_message.Message):
    __slots__ = ("suggestion_response", "vector_clock")
    SUGGESTION_RESPONSE_FIELD_NUMBER: _ClassVar[int]
    VECTOR_CLOCK_FIELD_NUMBER: _ClassVar[int]
    suggestion_response: SuggestionResponse
    vector_clock: VectorClockMessage
    def __init__(self, suggestion_response: _Optional[_Union[SuggestionResponse, _Mapping]] = ..., vector_clock: _Optional[_Union[VectorClockMessage, _Mapping]] = ...) -> None: ...

class VectorClockMessage(_message.Message):
    __slots__ = ("process_id", "clock", "order_id")
    PROCESS_ID_FIELD_NUMBER: _ClassVar[int]
    CLOCK_FIELD_NUMBER: _ClassVar[int]
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    process_id: int
    clock: _containers.RepeatedScalarFieldContainer[int]
    order_id: int
    def __init__(self, process_id: _Optional[int] = ..., clock: _Optional[_Iterable[int]] = ..., order_id: _Optional[int] = ...) -> None: ...
