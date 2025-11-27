# SPDX-FileCopyrightText: Copyright DB InfraGO AG and the capellambse-context-diagrams contributors
# SPDX-License-Identifier: Apache-2.0

"""Builder for diagram view layouts.

Transforms collected diagram elements into ELK input data.
"""

from __future__ import annotations

import logging
import typing as t

from capellambse import model as m

from .. import _elkjs, context
from ..collectors import _generic, diagram_view
from . import _makers

logger = logging.getLogger(__name__)


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
        self.collected_elements: set[str] = set()
        self.redirected_edges_per_box: dict[str, int] = {}

    def __call__(self) -> _elkjs.ELKInputData:
        elements = self.collector.collect()

        for element in elements.components:
            self.collected_elements.add(element.uuid)
            self._make_box_with_hierarchy(element)

        for element in elements.functions:
            self.collected_elements.add(element.uuid)
            self._make_box_with_hierarchy(element)

        for port in elements.ports:
            self._make_port_for_element(port)

        for exchange in elements.exchanges:
            self._make_exchange(exchange)

        if self.diagram._include_port_allocations:
            for port_alloc in elements.port_allocations:
                self._make_port_allocation(port_alloc)

        for box_id, redirect_count in self.redirected_edges_per_box.items():
            if box := self.boxes.get(box_id):
                num_ports = len(box.ports)
                total_connections = num_ports + redirect_count
                box.height = (_makers.PORT_SIZE + 2 * _makers.PORT_PADDING) * (
                    total_connections + 1
                )
            else:
                logger.warning(
                    "Box %s in redirected_edges_per_box but not found",
                    box_id[:8],
                )

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

    def _find_highest_collected_owner(
        self, element: m.ModelElement
    ) -> m.ModelElement | None:
        """Find the highest owner of an element that is in collected elements.

        Walks up the ownership chain to find the first owner that was
        collected in the diagram.
        """
        current = element
        while current:
            if current.uuid in self.collected_elements:
                return current
            if hasattr(current, "owner") and not isinstance(
                current.owner, _makers.PackageTypes
            ):
                current = current.owner
            else:
                break
        return None

    def _move_redirected_edge(
        self,
        edge: _elkjs.ELKInputEdge,
        source_element: m.ModelElement,
        target_element: m.ModelElement,
    ) -> None:
        """Move a redirected edge to the correct container.

        For redirected edges that connect directly to components (not ports),
        we need to find the common ancestor box and move the edge there.
        """
        source_owners = list(_generic.get_all_owners(source_element))
        target_owners = list(_generic.get_all_owners(target_element))

        # Find common owner
        common_owner_uuid = None
        for owner in source_owners:
            if owner in target_owners:
                common_owner_uuid = owner
                break

        if common_owner_uuid and (
            owner_box := self.boxes.get(common_owner_uuid)
        ):
            if edge in self.data.edges:
                self.data.edges.remove(edge)

            owner_box.edges.append(edge)

    def _make_exchange(self, exchange: m.ModelElement) -> None:
        """Create edge for exchange."""
        label = _generic.collect_label(exchange)

        source_owner_collected = (
            exchange.source.owner.uuid in self.collected_elements
        )
        target_owner_collected = (
            exchange.target.owner.uuid in self.collected_elements
        )

        source_element: m.ModelElement
        target_element: m.ModelElement
        if source_owner_collected:
            source_id = exchange.source.uuid
            source_element = exchange.source
            self._make_port_for_element(exchange.source)
        else:
            source_owner = self._find_highest_collected_owner(
                exchange.source.owner
            )
            if source_owner:
                source_id = source_owner.uuid
                source_element = source_owner
            else:
                return

        if target_owner_collected:
            target_id = exchange.target.uuid
            target_element = exchange.target
            self._make_port_for_element(exchange.target)
        else:
            target_owner = self._find_highest_collected_owner(
                exchange.target.owner
            )
            if target_owner:
                target_id = target_owner.uuid
                target_element = target_owner
            else:
                return

        if not source_owner_collected or not target_owner_collected:
            edge_id = f"{_makers.STYLECLASS_PREFIX}-ComponentExchange:{exchange.uuid}"
            if not source_owner_collected and source_id in self.boxes:
                self.redirected_edges_per_box[source_id] = (
                    self.redirected_edges_per_box.get(source_id, 0) + 1
                )
            if not target_owner_collected and target_id in self.boxes:
                self.redirected_edges_per_box[target_id] = (
                    self.redirected_edges_per_box.get(target_id, 0) + 1
                )
        else:
            edge_id = exchange.uuid

        edge = _elkjs.ELKInputEdge(
            id=edge_id,
            sources=[source_id],
            targets=[target_id],
            labels=_makers.make_label(label, max_width=_makers.MAX_LABEL_WIDTH)
            if label
            else [],
        )

        self.data.edges.append(edge)

        if source_owner_collected and (
            src_box := self.boxes.get(exchange.source.owner.uuid)
        ):
            _makers.adjust_box_height_for_ports(src_box)

        if target_owner_collected and (
            tgt_box := self.boxes.get(exchange.target.owner.uuid)
        ):
            _makers.adjust_box_height_for_ports(tgt_box)

        if not source_owner_collected or not target_owner_collected:
            self._move_redirected_edge(edge, source_element, target_element)
        else:
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
