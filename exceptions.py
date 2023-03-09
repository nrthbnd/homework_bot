class NoHomeworkError(Exception):
    """Исключение для проверки ведений о домашней работе."""

    def __init__(self, error_text):
        """Проверка ответа API."""
        self.error_text = error_text
