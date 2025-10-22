# SPDX-FileCopyrightText: Copyright DB InfraGO AG and the capellambse-context-diagrams contributors
# SPDX-License-Identifier: Apache-2.0

"""Collector for the DiagramView.

Collects all model elements from a Capella diagram.
"""

from __future__ import annotations

import dataclasses

from capellambse import model as m

from .. import context, helpers


@dataclasses.dataclass
class DiagramElements:
    """Collected elements from a diagram."""

    components: list[m.ModelElement] = dataclasses.field(default_factory=list)
    functions: list[m.ModelElement] = dataclasses.field(default_factory=list)
    exchanges: list[m.ModelElement] = dataclasses.field(default_factory=list)
    ports: list[m.ModelElement] = dataclasses.field(default_factory=list)
    port_allocations: list[m.ModelElement] = dataclasses.field(
        default_factory=list
    )


class Collector:
    """Collects model elements from a diagram."""

    def __init__(self, diagram: context.ELKDiagram):
        self.diagram = diagram
        self._diagram = diagram.target

    def collect(self) -> DiagramElements:
        """Collect all relevant elements from the diagram."""
        elements = DiagramElements()

        for node in self._diagram.nodes:
            if helpers.is_function(node):
                elements.functions.append(node)
            elif helpers.is_part(node):
                elements.components.append(node.type)
            elif helpers.is_allocation(node):
                elements.port_allocations.append(node)
            elif helpers.is_exchange(node):
                elements.exchanges.append(node)
            elif helpers.is_port(node):
                elements.ports.append(node)

        return elements
