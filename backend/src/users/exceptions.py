class UserDomainError(Exception):
    """Base exception for users domain"""


class TechnicianNameNotFound(UserDomainError):
    """Technician not found in provided HelpDesk space"""


class TelegramAlreadyUsed(UserDomainError):
    """This telegram-id is already used by someone else"""


class HdApiAlreadyUsed(UserDomainError):
    """This helpdesk API-key is already used by someone else"""


class UserNotFound(UserDomainError):
    """User with provided telegram_id not found"""


class PresetNotFound(UserDomainError):
    """Settings preset not found"""


class PresetLimitExceeded(UserDomainError):
    """User cannot create more than max allowed presets"""


class CannotDeleteLastPreset(UserDomainError):
    """User must have at least one settings preset"""