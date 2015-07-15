"""
Generic Exceptions for Orchestrator
"""


class OrchestratorError(Exception):
    """
    Base Orchestrator error.
    """
    def __init__(self, message, code=None, details=None, traceback=None):
        self.message = message
        self.code = code or 'ORCHESTRATOR_ERROR'
        self.details = details or {}
        self.traceback = traceback
        super(OrchestratorError, self).__init__(message, code, details,
                                                traceback)

    def to_dict(self):
        return {
            'message': self.message,
            'code': self.code,
            'details': self.details,
            'traceback': self.traceback
        }

    def __str__(self):
        return self.message


class BusinessRuleViolation(OrchestratorError):
    """
    Error corresponding to business rule violation.
    """

    def __init__(self, message, code='BUSINESS_RULE_VIOLATION', details=None):
        super(BusinessRuleViolation, self).__init__(
            message, code=code, details=details)
