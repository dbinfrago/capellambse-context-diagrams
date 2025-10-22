# SPDX-FileCopyrightText: Copyright DB InfraGO AG and the capellambse-context-diagrams contributors
# SPDX-License-Identifier: Apache-2.0

"""Builder for diagram view layouts.

Transforms collected diagram elements into ELK input data.
"""

from __future__ import annotations

import typing as t

from capellambse import model as m

from .. import _elkjs, context
from ..collectors import _generic, diagram_view
from . import _makers


class DiagramViewBuilder:
    """Build ELK input data from diagram elements."""

    def __init__(
        self, diagram: context.ELKDiagram, params: dict[str, t.Any]
    ) -> None:
        self.diagram = diagram
        self.params = params
        self.data = _generic.collector(self.diagram, no_symbol=True)
        self.data.children = []

        self.boxes: dict[str, _elkjs.ELKInputChild] = {}
        self.ports: dict[str, _elkjs.ELKInputPort] = {}
        self.boxes_to_delete: set[str] = set()

        self.collector = diagram_view.Collector(diagram)

    def __call__(self) -> _elkjs.ELKInputData:
        elements = self.collector.collect()

        for element in elements.components:
            self._make_box_with_hierarchy(element)

        for element in elements.functions:
            self._make_box_with_hierarchy(element)

        for port in elements.ports:
            self._make_port_for_element(port)

        for exchange in elements.exchanges:
            self._make_exchange(exchange)

        if self.diagram._include_port_allocations:
            for port_alloc in elements.port_allocations:
                self._make_port_allocation(port_alloc)

        for uuid in self.boxes_to_delete:
            del self.boxes[uuid]

        self.data.children = list(self.boxes.values())
        return self.data

    def _make_box_with_hierarchy(self, obj: m.ModelElement) -> None:
        """Make box and all parent boxes using proven hierarchy logic."""
        if obj.uuid not in self.boxes:
            box = self._make_box(obj)
            self.boxes[obj.uuid] = box

        current: m.ModelElement | None = obj
        while (
            current
            and hasattr(current, "owner")
            and not isinstance(current.owner, _makers.PackageTypes)
        ):
            current = _makers.make_owner_box(
                current, self._make_box, self.boxes, self.boxes_to_delete
            )

    def _make_box(
        self, obj: m.ModelElement, **kwargs: t.Any
    ) -> _elkjs.ELKInputChild:
        """Make a box for an element."""
        if box := self.boxes.get(obj.uuid):
            return box

        no_symbol = (
            kwargs.pop("no_symbol", True)
            or self.diagram._display_symbols_as_boxes
        )
        box = _makers.make_box(obj, no_symbol=no_symbol, **kwargs)
        self.boxes[obj.uuid] = box
        return box

    def _make_port_for_element(
        self, port_obj: m.ModelElement
    ) -> _elkjs.ELKInputPort | None:
        """Create port and attach to owner box."""
        if port := self.ports.get(port_obj.uuid):
            return port

        label = ""
        if self.diagram._display_port_labels:
            label = port_obj.name or "UNKNOWN"

        port = _makers.make_port(port_obj.uuid, label=label)
        self.ports[port_obj.uuid] = port

        if port_obj.owner.uuid not in self.boxes:
            self._make_box_with_hierarchy(port_obj.owner)

        if owner_box := self.boxes.get(port_obj.owner.uuid):
            owner_box.ports.append(port)

        return port

    def _make_exchange(self, exchange: m.ModelElement) -> None:
        """Create edge for exchange."""
        label = _generic.collect_label(exchange)
        edge = _elkjs.ELKInputEdge(
            id=exchange.uuid,
            sources=[exchange.source.uuid],
            targets=[exchange.target.uuid],
            labels=_makers.make_label(label, max_width=_makers.MAX_LABEL_WIDTH)
            if label
            else [],
        )

        self._make_port_for_element(exchange.source)
        self._make_port_for_element(exchange.target)

        self.data.edges.append(edge)

        if src_box := self.boxes.get(exchange.source.owner.uuid):
            _makers.adjust_box_height_for_ports(src_box)
        if tgt_box := self.boxes.get(exchange.target.owner.uuid):
            _makers.adjust_box_height_for_ports(tgt_box)

        _generic.move_edges(self.boxes, [exchange], self.data)

    def _make_port_allocation(self, port_alloc: m.ModelElement) -> None:
        """Create edge for port allocation between function and component port."""
        self._make_port_for_element(port_alloc.source)
        self._make_port_for_element(port_alloc.target)


def build_from_diagram(
    diagram: context.ELKDiagram, params: dict[str, t.Any]
) -> _elkjs.ELKInputData:
    """Build ELK input data from a diagram."""
    diagram._slim_center_box = False
    return DiagramViewBuilder(diagram, params)()
