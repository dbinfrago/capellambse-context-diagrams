# SPDX-FileCopyrightText: Copyright DB InfraGO AG and the capellambse-context-diagrams contributors
# SPDX-License-Identifier: Apache-2.0
"""Define enumerations for ContextDiagram types."""

import enum

from capellambse import model as m


@m.stringy_enum
class MODE(enum.Enum):
    """Context collection mode.

    Attributes
    ----------
    WHITEBOX
        Collect target context and its children's context.
    BLACKBOX
        Collect target context only.
    GREYBOX
        Collect target context and its children's context, but limit
        parent relationship resolution to first level only.
    """

    WHITEBOX = enum.auto()
    BLACKBOX = enum.auto()
    GREYBOX = enum.auto()


@m.stringy_enum
class EDGE_DIRECTION(enum.Enum):
    """Reroute direction of edges.

    Attributes
    ----------
    NONE
        No rerouting of edges.
    SMART
        Reroute edges to follow the primary direction of data flow.
    LEFT
        Edges are always placed on the left side.
    RIGHT
        Edges are always placed on the right side.
    TREE
        Reroute edges to follow a tree-like structure.
    """

    NONE = enum.auto()
    SMART = enum.auto()
    LEFT = enum.auto()
    RIGHT = enum.auto()
    TREE = enum.auto()
