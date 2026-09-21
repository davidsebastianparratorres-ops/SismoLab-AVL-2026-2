class OperationResult:
    def __init__(self, success: bool, message: str , event=None):
        self.success = success
        self.message = message
        self.event = event