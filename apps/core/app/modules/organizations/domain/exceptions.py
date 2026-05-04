class OrganizationNotFound(Exception):
    pass


class OrganizationAlreadyExists(Exception):
    pass


class RootOrganizationAlreadyExists(Exception):
    """В дереве холдинга уже есть корневая организация (parent IS NULL).
    Дерево холдинга имеет ровно один корень."""


class CannotDeactivateRoot(Exception):
    """Корневую организацию нельзя деактивировать: это превратит весь
    инстанс в нерабочее состояние."""
