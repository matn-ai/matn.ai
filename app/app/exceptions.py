from flask import flash

class ValidationError(ValueError):
    def __init__(self, message):
        flash(message, 'error')
        super().__init__(message)
        return False