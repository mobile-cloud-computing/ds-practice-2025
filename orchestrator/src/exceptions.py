class FraudActivityException(Exception):
    def __init__(self, message="Fraudulent activity detected"):
        self.message = message
        super().__init__(self.message)
