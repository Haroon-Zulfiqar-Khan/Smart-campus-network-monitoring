class DomainError(Exception):
    """Framework-independent application error mapped to HTTP by the View layer."""

    def __init__(self, status_code, detail, headers=None):
        self.status_code = status_code
        self.detail = detail
        self.headers = headers
        super().__init__(detail)
