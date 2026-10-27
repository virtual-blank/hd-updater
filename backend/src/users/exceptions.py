class TechnicianNameNotFound(Exception):
    """
    Technician not found in provided HelpDesk space
    """

class TelegramAlreadyUsed(Exception):
    """
    This telegram-id is already used by someone else
    """

class HdApiAlreadyUsed(Exception):
    """
    This helpdesk API-key is already used by someone else
    """

class InternalServerError(Exception):
    """
    {"status_code": 500, "message": "Internal Server Error"}
    """