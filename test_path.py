import os
import sys

FILE = __file__
print(f"FILE: {FILE}")
path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
print(f"Path: {path}")
print(f"Directory exists: {os.path.exists(path)}")
