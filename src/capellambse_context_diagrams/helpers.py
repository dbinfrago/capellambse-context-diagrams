# SPDX-FileCopyrightText: Copyright DB InfraGO AG and the capellambse-context-diagrams contributors
# SPDX-License-Identifier: Apache-2.0

from capellambse import model as m
from capellambse.metamodel import fa


def get_model_object(model: m.MelodyModel, uuid: str) -> m.ModelElement | None:
    """Try to return a Capella model element."""
    try:
        return model.by_uuid(uuid)
    except KeyError:
        return None


def has_same_type(obj1: m.ModelElement, obj2: m.ModelElement) -> bool:
    """Check if two model elements have the same type."""
    return type(obj1).__name__ == type(obj2).__name__


def is_function(obj: m.ModelElement) -> bool:
    """Check if the object is a function."""
    return isinstance(obj, fa.AbstractFunction)


def is_part(obj: m.ModelElement) -> bool:
    """Check if the object is a part."""
    return obj.xtype is not None and obj.xtype.endswith("Part")


def is_port(obj: m.ModelElement) -> bool:
    """Check if the object is a port."""
    return obj.xtype is not None and obj.xtype.endswith("Port")


def is_exchange(obj: m.ModelElement) -> bool:
    """Check if the object is an exchange."""
    return hasattr(obj, "source") and hasattr(obj, "target")


def is_allocation(obj: m.ModelElement) -> bool:
    """Check if the object is an allocation."""
    return obj.xtype is not None and obj.xtype.endswith("PortAllocation")


def is_functional_chain(obj: m.ModelElement) -> bool:
    """Check if the object is a functional chain or operational process."""
    return type(obj).__name__.endswith(
        ("FunctionalChain", "OperationalProcess")
    )
