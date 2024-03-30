from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class HelloRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class HelloResponse(_message.Message):
    __slots__ = ("greeting",)
    GREETING_FIELD_NUMBER: _ClassVar[int]
    greeting: str
    def __init__(self, greeting: _Optional[str] = ...) -> None: ...

class OrderIdStorageRequest(_message.Message):
    __slots__ = ("orderId",)
    ORDERID_FIELD_NUMBER: _ClassVar[int]
    orderId: str
    def __init__(self, orderId: _Optional[str] = ...) -> None: ...

class UserdataFraudDetectionRequest(_message.Message):
    __slots__ = ("orderId", "user", "item", "creditCard", "vectorClock")
    ORDERID_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    ITEM_FIELD_NUMBER: _ClassVar[int]
    CREDITCARD_FIELD_NUMBER: _ClassVar[int]
    VECTORCLOCK_FIELD_NUMBER: _ClassVar[int]
    orderId: str
    user: User
    item: Item
    creditCard: CreditCard
    vectorClock: VectorClock
    def __init__(self, orderId: _Optional[str] = ..., user: _Optional[_Union[User, _Mapping]] = ..., item: _Optional[_Union[Item, _Mapping]] = ..., creditCard: _Optional[_Union[CreditCard, _Mapping]] = ..., vectorClock: _Optional[_Union[VectorClock, _Mapping]] = ...) -> None: ...

class CardinfoFraudDetectionRequest(_message.Message):
    __slots__ = ("orderId", "user", "item", "creditCard", "vectorClock")
    ORDERID_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    ITEM_FIELD_NUMBER: _ClassVar[int]
    CREDITCARD_FIELD_NUMBER: _ClassVar[int]
    VECTORCLOCK_FIELD_NUMBER: _ClassVar[int]
    orderId: str
    user: User
    item: Item
    creditCard: CreditCard
    vectorClock: VectorClock
    def __init__(self, orderId: _Optional[str] = ..., user: _Optional[_Union[User, _Mapping]] = ..., item: _Optional[_Union[Item, _Mapping]] = ..., creditCard: _Optional[_Union[CreditCard, _Mapping]] = ..., vectorClock: _Optional[_Union[VectorClock, _Mapping]] = ...) -> None: ...

class User(_message.Message):
    __slots__ = ("name", "contact")
    NAME_FIELD_NUMBER: _ClassVar[int]
    CONTACT_FIELD_NUMBER: _ClassVar[int]
    name: str
    contact: str
    def __init__(self, name: _Optional[str] = ..., contact: _Optional[str] = ...) -> None: ...

class Item(_message.Message):
    __slots__ = ("name", "quantity")
    NAME_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_FIELD_NUMBER: _ClassVar[int]
    name: str
    quantity: int
    def __init__(self, name: _Optional[str] = ..., quantity: _Optional[int] = ...) -> None: ...

class CreditCard(_message.Message):
    __slots__ = ("number", "expirationDate", "cvv")
    NUMBER_FIELD_NUMBER: _ClassVar[int]
    EXPIRATIONDATE_FIELD_NUMBER: _ClassVar[int]
    CVV_FIELD_NUMBER: _ClassVar[int]
    number: str
    expirationDate: str
    cvv: str
    def __init__(self, number: _Optional[str] = ..., expirationDate: _Optional[str] = ..., cvv: _Optional[str] = ...) -> None: ...

class VectorClock(_message.Message):
    __slots__ = ("vcArray", "timestamp")
    VCARRAY_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    vcArray: _containers.RepeatedScalarFieldContainer[int]
    timestamp: float
    def __init__(self, vcArray: _Optional[_Iterable[int]] = ..., timestamp: _Optional[float] = ...) -> None: ...

class Book(_message.Message):
    __slots__ = ("id", "title", "author", "description", "copies", "copiesAvailable", "category", "img", "price")
    ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    COPIES_FIELD_NUMBER: _ClassVar[int]
    COPIESAVAILABLE_FIELD_NUMBER: _ClassVar[int]
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    IMG_FIELD_NUMBER: _ClassVar[int]
    PRICE_FIELD_NUMBER: _ClassVar[int]
    id: str
    title: str
    author: str
    description: str
    copies: int
    copiesAvailable: int
    category: str
    img: str
    price: float
    def __init__(self, id: _Optional[str] = ..., title: _Optional[str] = ..., author: _Optional[str] = ..., description: _Optional[str] = ..., copies: _Optional[int] = ..., copiesAvailable: _Optional[int] = ..., category: _Optional[str] = ..., img: _Optional[str] = ..., price: _Optional[float] = ...) -> None: ...

class OrderIdStorageResponse(_message.Message):
    __slots__ = ("isValid",)
    ISVALID_FIELD_NUMBER: _ClassVar[int]
    isValid: bool
    def __init__(self, isValid: bool = ...) -> None: ...

class UserdataFraudDetectionResponse(_message.Message):
    __slots__ = ("isValid", "errorMessage", "books")
    ISVALID_FIELD_NUMBER: _ClassVar[int]
    ERRORMESSAGE_FIELD_NUMBER: _ClassVar[int]
    BOOKS_FIELD_NUMBER: _ClassVar[int]
    isValid: bool
    errorMessage: str
    books: _containers.RepeatedCompositeFieldContainer[Book]
    def __init__(self, isValid: bool = ..., errorMessage: _Optional[str] = ..., books: _Optional[_Iterable[_Union[Book, _Mapping]]] = ...) -> None: ...

class CardinfoFraudDetectionResponse(_message.Message):
    __slots__ = ("isValid", "errorMessage", "books")
    ISVALID_FIELD_NUMBER: _ClassVar[int]
    ERRORMESSAGE_FIELD_NUMBER: _ClassVar[int]
    BOOKS_FIELD_NUMBER: _ClassVar[int]
    isValid: bool
    errorMessage: str
    books: _containers.RepeatedCompositeFieldContainer[Book]
    def __init__(self, isValid: bool = ..., errorMessage: _Optional[str] = ..., books: _Optional[_Iterable[_Union[Book, _Mapping]]] = ...) -> None: ...
