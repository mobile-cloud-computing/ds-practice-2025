from marshmallow import Schema, fields, validate


class UserSchema(Schema):
    name = fields.Str(required=True)
    contact = fields.Str(required=True)


class CreditCardSchema(Schema):
    number = fields.Str(required=True)
    expirationDate = fields.Str(required=True)
    cvv = fields.Str(required=True)


class ItemSchema(Schema):
    name = fields.Str(required=True)
    quantity = fields.Int(required=True)


class BillingAddressSchema(Schema):
    street = fields.Str(required=True)
    city = fields.Str(required=True)
    state = fields.Str(required=True)
    zip = fields.Str(required=True)
    country = fields.Str(required=True)


class DeviceSchema(Schema):
    type = fields.Str(missing=None)
    model = fields.Str(missing=None)
    os = fields.Str(missing=None)


class BrowserSchema(Schema):
    name = fields.Str(missing=None)
    version = fields.Str(missing=None)


class CheckoutSchema(Schema):
    user = fields.Nested(UserSchema, required=True)
    creditCard = fields.Nested(CreditCardSchema, required=True)
    userComment = fields.Str(missing=None)
    items = fields.List(fields.Nested(ItemSchema), required=True)
    discountCode = fields.Str(missing=None)
    shippingMethod = fields.Str(missing=None)
    giftMessage = fields.Str(missing=None)
    billingAddress = fields.Nested(BillingAddressSchema, required=True)
    giftWrapping = fields.Bool(missing=None)
    termsAndConditionsAccepted = fields.Bool(required=True)
    notificationPreferences = fields.List(fields.Str(), missing=None)
    device = fields.Nested(DeviceSchema, missing=None)
    browser = fields.Nested(BrowserSchema, missing=None)
    appVersion = fields.Str(missing=None)
    screenResolution = fields.Str(missing=None)
    referrer = fields.Str(missing=None)
    deviceLanguage = fields.Str(missing=None)


class SuggestedBookSchema(Schema):
    bookId = fields.Str(missing=None)
    title = fields.Str(missing=None)
    author = fields.Str(missing=None)


class OrderStatusResponseSchema(Schema):
    orderId = fields.Str(missing=None)
    status = fields.Str(missing=None,
                        description='Order status: "Order Approved" or "Order Rejected". If rejected, suggestedBooks is empty.')
    suggestedBooks = fields.List(fields.Nested(SuggestedBookSchema), missing=None)


class ErrorSchema(Schema):
    code = fields.Str(required=True)
    message = fields.Str(required=True)


class ErrorResponseSchema(Schema):
    error = fields.Nested(ErrorSchema, required=True)
