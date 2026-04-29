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


class DiagramBuilder(default.DiagramBuilder):
    """Collect the data context for a DataFlow diagram."""

    def __init__(
        self,
        diagram: context.ContextDiagram,
        params: dict[str, t.Any],
    ) -> None:
        super().__init__(diagram, params)

        self.diagram_target_owners = []

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
        return f"__{involved._get_styleclass()}:{obj.uuid}"

    def _make_involvement_box(
        self,
        obj: fa.FunctionalChainInvolvement,
    ) -> _elkjs.ELKInputChild:
        if box := self.boxes.get(obj.uuid):
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

        self.boxes[obj.uuid] = box
        return box

    def _make_involvement_edge(
        self,
        obj: fa.FunctionalChainInvolvementLink,
    ) -> _elkjs.ELKInputEdge | None:
        if self.edges.get(obj.uuid):
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
        )
        _generic.exchange_data_collector(
            edge_data,
            endpoint_collector=lambda _: (source, target),
        )
        edge = self.data.edges.pop()
        edge.id = obj.uuid
        edge.sources = [self._get_involvement_node_id(source)]
        edge.targets = [self._get_involvement_node_id(target)]
        self.edges[obj.uuid] = edge
        return edge

    def _make_whitebox_target(
        self,
        obj: m.ModelElement,
    ) -> _elkjs.ELKInputChild | _elkjs.ELKInputEdge | None:
        if self.diagram._collect_from_involvements:
            if isinstance(obj, fa.FunctionalChainInvolvementLink):
                return self._make_involvement_edge(obj)
            if isinstance(obj, fa.FunctionalChainInvolvement):
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
