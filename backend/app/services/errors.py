import uuid


class ResourceNotFoundError(Exception):
    def __init__(self, resource: str, resource_id: uuid.UUID) -> None:
        super().__init__(f"{resource} with id {resource_id} was not found")
        self.resource = resource
        self.resource_id = resource_id


class DuplicateResourceError(Exception):
    pass


class AccessDeniedError(Exception):
    pass


class UnsupportedFileTypeError(Exception):
    pass


class FileTooLargeError(Exception):
    pass