# SPDX-FileCopyrightText: Copyright DB InfraGO AG and the capellambse-context-diagrams contributors
# SPDX-License-Identifier: Apache-2.0

"""Build an ELK DataFlow diagram from collected capellambse context."""

from __future__ import annotations

import typing as t

import capellambse.model as m
from capellambse.metamodel import fa

from .. import _elkjs, _registry, context
from ..collectors import _generic
from . import _makers, default

SUPPORTED_CLASSES: tuple[type[m.ModelElement], ...] = tuple(
    t[0] for t in _registry.DATAFLOW_CLASSES
)


def collect_involved_exchange_endpoints(
    exchange: m.ModelElement,
) -> _generic.SourceAndTarget:
    """Collect endpoints from an involvement link's involved exchange."""
    involved = getattr(exchange, "involved", None)
    if isinstance(involved, m.ModelElement):
        return _generic.collect_exchange_endpoints(involved)
    return _generic.collect_exchange_endpoints(exchange)


class DiagramBuilder(default.DiagramBuilder):
    """Collect the data context for a DataFlow diagram."""

    def __init__(
        self,
        diagram: context.ContextDiagram,
        params: dict[str, t.Any],
    ) -> None:
        super().__init__(diagram, params)

        self.diagram_target_owners = []
        collection = list(self.collection)
        self.collection = iter(collection)
        self.involvement_exchange_items: dict[
            str, tuple[m.ModelElement, ...]
        ] = {}
        for obj in collection:
            if not isinstance(obj, fa.FunctionalChainInvolvementLink):
                continue
            involved = getattr(obj, "involved", None)
            if not isinstance(involved, m.ModelElement):
                continue
            items = list(
                self.involvement_exchange_items.setdefault(involved.uuid, ())
            )
            known = {item.uuid for item in items}
            for item in obj.exchanged_items:
                if item.uuid not in known:
                    items.append(item)
                    known.add(item.uuid)
            self.involvement_exchange_items[involved.uuid] = tuple(items)

    def _handle_boxeable_target(self) -> None:
        """Do nothing."""
        return

    def _get_involvement_node_id(
        self,
        obj: fa.FunctionalChainInvolvement,
    ) -> str:
        involved = getattr(obj, "involved", None)
        if not isinstance(involved, m.ModelElement):
            return obj.uuid
        if isinstance(obj, fa.FunctionalChainReference):
            return f"__FunctionalChainReference:{involved.uuid}"
        return f"__{involved._get_styleclass()}:{involved.uuid}"

    def _get_involvement_box_key(
        self,
        obj: fa.FunctionalChainInvolvement,
    ) -> str:
        involved = getattr(obj, "involved", None)
        if isinstance(involved, m.ModelElement):
            return involved.uuid
        return obj.uuid

    def _get_involvement_port_id(
        self,
        involvement: fa.FunctionalChainInvolvement,
        port: m.ModelElement,
    ) -> str:
        return f"__{port._get_styleclass()}:{port.uuid}_{involvement.uuid}"

    def _make_involvement_box(
        self,
        obj: fa.FunctionalChainInvolvement,
    ) -> _elkjs.ELKInputChild:
        box_key = self._get_involvement_box_key(obj)
        if box := self.boxes.get(box_key):
            return box

        involved = getattr(obj, "involved", None)
        if isinstance(involved, m.ModelElement):
            box = _makers.make_box(
                involved,
                no_symbol=self.diagram._display_symbols_as_boxes,
                slim_width=self.diagram._slim_center_box,
            )
            box.id = self._get_involvement_node_id(obj)
        else:
            box = _makers.make_box(
                obj,
                no_symbol=self.diagram._display_symbols_as_boxes,
                slim_width=self.diagram._slim_center_box,
            )

        self.boxes[box_key] = box
        if self.diagram._display_parent_relation and isinstance(
            involved, m.ModelElement
        ):
            self.common_owners.add(
                self._make_involvement_owner_boxes(obj, involved)
            )
        return box

    def _make_involvement_port(
        self,
        involvement: fa.FunctionalChainInvolvement,
        port_obj: m.ModelElement,
    ) -> str:
        box = self._make_involvement_box(involvement)
        port_id = self._get_involvement_port_id(involvement, port_obj)
        if port_id not in self.ports:
            label = ""
            if self.diagram._display_port_labels:
                label = port_obj.name or "UNKNOWN"
                _makers.set_port_label_placement(
                    box, self.diagram._port_label_position
                )
            port = _makers.make_port(port_id, label=label)
            box.ports.append(port)
            self.ports[port_id] = port
            _makers.adjust_box_height_for_ports(box)
        return port_id

    def _make_involvement_owner_boxes(
        self,
        involvement: fa.FunctionalChainInvolvement,
        involved: m.ModelElement,
    ) -> str:
        box_key = self._get_involvement_box_key(involvement)
        owner_box = self.boxes[box_key]
        current = involved
        depth = 0
        while (
            current
            and current.uuid not in self.diagram_target_owners
            and getattr(current, "owner", None) is not None
            and not isinstance(current.owner, _makers.PackageTypes)
            and depth < self.max_depth
        ):
            if current is involved:
                current = _makers.move_box_into_owner(
                    current,
                    owner_box,
                    box_key,
                    self._make_box,
                    self.boxes_to_delete,
                )
            else:
                current = _makers.make_owner_box(
                    current,
                    self._make_box,
                    self.boxes,
                    self.boxes_to_delete,
                )
            depth += 1
        return current.uuid

    def _make_involvement_edge(
        self,
        obj: fa.FunctionalChainInvolvementLink,
    ) -> _elkjs.ELKInputEdge | None:
        involved = getattr(obj, "involved", None)
        edge_key = (
            involved.uuid if isinstance(involved, m.ModelElement) else obj.uuid
        )
        if self.edges.get(edge_key):
            return None
        source = obj.source
        target = obj.target
        if source is None or target is None:
            return None

        self._make_involvement_box(source)
        self._make_involvement_box(target)

        edge_data = _generic.ExchangeData(
            obj,
            self.data,
            self.diagram.filters,
            self.params,
            self.involvement_exchange_items.get(edge_key),
        )
        _generic.exchange_data_collector(
            edge_data,
            endpoint_collector=collect_involved_exchange_endpoints,
        )
        edge = self.data.edges.pop()
        if isinstance(involved, m.ModelElement):
            edge.id = f"__{involved._get_styleclass()}:{obj.uuid}"
            edge.sources = [
                self._make_involvement_port(source, involved.source)
            ]
            edge.targets = [
                self._make_involvement_port(target, involved.target)
            ]
        else:
            edge.id = obj.uuid
            edge.sources = [self._get_involvement_node_id(source)]
            edge.targets = [self._get_involvement_node_id(target)]
        self.edges[edge_key] = edge
        if self.diagram._display_parent_relation:
            self._store_involvement_edge_owner(edge_key, source, target)
        return edge

    def _store_involvement_edge_owner(
        self,
        edge_key: str,
        source: fa.FunctionalChainInvolvement,
        target: fa.FunctionalChainInvolvement,
    ) -> None:
        source_involved = getattr(source, "involved", None)
        target_involved = getattr(target, "involved", None)
        if not isinstance(source_involved, m.ModelElement) or not isinstance(
            target_involved, m.ModelElement
        ):
            return

        source_owners = list(_generic.get_all_owners(source_involved))
        target_owners = list(_generic.get_all_owners(target_involved))
        if source_involved.owner == target_involved.owner:
            common_owner = getattr(source_involved.owner, "uuid", None)
        else:
            common_owner = next(
                (owner for owner in source_owners if owner in target_owners),
                None,
            )
        if common_owner:
            self.edge_owners[edge_key] = common_owner

    def _make_whitebox_target(
        self,
        obj: m.ModelElement,
    ) -> _elkjs.ELKInputChild | _elkjs.ELKInputEdge | None:
        if self.diagram._collect_from_involvements:
            if isinstance(obj, fa.FunctionalChainInvolvementLink):
                return self._make_involvement_edge(obj)
            if isinstance(
                obj,
                fa.FunctionalChainInvolvement | fa.FunctionalChainReference,
            ):
                return self._make_involvement_box(obj)

        return super()._make_whitebox_target(obj)

    def _make_greybox_target(
        self,
        obj: m.ModelElement,
    ) -> _elkjs.ELKInputChild | _elkjs.ELKInputEdge | None:
        if self.diagram._collect_from_involvements:
            return self._make_whitebox_target(obj)

        return super()._make_greybox_target(obj)

    def _get_data(self) -> _elkjs.ELKInputData:
        self.data.children = list(self.boxes.values())
        self.data.edges = list(self.edges.values())
        return self.data

    def _make_edge_and_ports(
        self,
        edge_obj: m.ModelElement,
        edge_data: default.EdgeData | None = None,
    ) -> _elkjs.ELKInputEdge | None:
        if self.edges.get(edge_obj.uuid):
            return None

        if edge_data is None:
            edge_data = self._collect_edge_data(edge_obj)

        return self._update_edge_common(edge_data)


def builder(
    diagram: context.ContextDiagram, params: dict[str, t.Any]
) -> _elkjs.ELKInputData:
    return default.builder(diagram, params, DiagramBuilder)
