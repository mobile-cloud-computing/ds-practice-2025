# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: transaction_verification.proto
# Protobuf Python Version: 4.25.1
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x1etransaction_verification.proto\x12\x18transaction_verification\"K\n\x0f\x43heckoutRequest\x12\x38\n\ncreditcard\x18\x01 \x01(\x0b\x32$.transaction_verification.CreditCard\"A\n\nCreditCard\x12\x0e\n\x06number\x18\x01 \x01(\t\x12\x16\n\x0e\x65xpirationDate\x18\x02 \x01(\t\x12\x0b\n\x03\x63vv\x18\x03 \x01(\t\"&\n\rDetermination\x12\x15\n\rdetermination\x18\x01 \x01(\x08\x32}\n\x12TransactionService\x12g\n\x11verifyTransaction\x12).transaction_verification.CheckoutRequest\x1a\'.transaction_verification.Determinationb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'transaction_verification_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
  DESCRIPTOR._options = None
  _globals['_CHECKOUTREQUEST']._serialized_start=60
  _globals['_CHECKOUTREQUEST']._serialized_end=135
  _globals['_CREDITCARD']._serialized_start=137
  _globals['_CREDITCARD']._serialized_end=202
  _globals['_DETERMINATION']._serialized_start=204
  _globals['_DETERMINATION']._serialized_end=242
  _globals['_TRANSACTIONSERVICE']._serialized_start=244
  _globals['_TRANSACTIONSERVICE']._serialized_end=369
# @@protoc_insertion_point(module_scope)
