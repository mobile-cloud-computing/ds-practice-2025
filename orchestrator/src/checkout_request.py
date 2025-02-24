from typing import TypedDict

class User(TypedDict):
    name: str
    contact: str

class CreditCard(TypedDict):
    number: str
    expirationDate: str
    cvv: str

class Item(TypedDict):
    name: str
    quantity: int

class BillingAddress(TypedDict):
    street: str
    city: str
    state: str
    zip: str
    country: str

class Device(TypedDict):
    name: str
    model: str
    os: str

class Browser(TypedDict):
    name: str
    version: str

class Book(TypedDict):
    bookId: str
    title: str
    author: str

class OrderStatusResponse(TypedDict):
    orderId: str
    status: str
    suggestedBooks: list[Book]

class CheckoutRequest(TypedDict):
    user: User
    creditCard: CreditCard
    userComment: str
    items: list[Item]
    discountCode: str
    shippingMethod: str
    giftMessage: str
    giftWrapping: bool
    billingAddress: BillingAddress
    termsAndConditionsAccepted: bool
    notificationPreferences: list[str]
    device: Device
    browser: Browser
    appVersion: str
    screenResolution: str
    referrer: str
    deviceLanguage: str
