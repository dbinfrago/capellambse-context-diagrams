# SPDX-FileCopyrightText: Copyright DB InfraGO AG and the capellambse-context-diagrams contributors
# SPDX-License-Identifier: Apache-2.0
"""Declarative API for building fully customized auto-layouted diagrams.

This module provides a high-level, declarative API for creating custom
diagrams. Unlike the collector-based approach, this API allows you to
explicitly specify boxes, edges, ports, and nesting relationships.

Example
-------
>>> import capellambse_context_diagrams as ccd
>>>
>>> diag = ccd.CustomDiagram(component1)
>>> diag.box(component1)
>>> diag.box(component2, parent=component1)
>>> diag.port(port, parent=component2)
>>> diag.edge(exchange, source=component1, target=port)
>>>
>>> svg = diag.render("svg")
"""

from __future__ import annotations

import collections
import collections.abc as cabc
import dataclasses
import logging
import typing as t

import capellambse.model as m
import typing_extensions as te

from . import _elkjs, context, styling
from .builders import _makers

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class _EdgeSpec:
    """Configuration for an edge in the diagram."""

    obj: m.ModelElement
    """The model element representing this edge (e.g., Exchange)."""
    source: m.ModelElement
    """Source box element."""
    target: m.ModelElement
    """Target box element."""
    labels: list[str]
    """Optional custom labels for the edge."""


@dataclasses.dataclass
class _BoxSpec:
    """Configuration for a box in the diagram."""

    obj: m.ModelElement
    """The model element representing this box."""
    parent: str | None
    """UUID of the parent box for nesting (None for root-level)."""
    ports: set[str]
    """UUIDs of the ports associated with this box."""


@dataclasses.dataclass
class _PortSpec:
    """Configuration for a port in the diagram."""

    obj: m.ModelElement
    """The model element representing this port."""
    parent: str
    """UUID of the parent box that owns this port."""


class CustomDiagram(context.ContextDiagram):
    """A custom diagram builder.

    Parameters
    ----------
    target
        The target model element for this diagram. Can be any model
        element, but it's recommended to use either one of the visible
        elements or a common ancestor.

        Use ``model.project`` as a fallback if needed.
    styleclass
        Style class for the diagram, defining colors and icons of
        visible objects. Can be a DiagramType enum value or a string
        like "OAB" or "Operational Architecture Blank".
    """

    @property
    def uuid(self) -> str:
        return f"{self.target.uuid}_custom"

    def __init__(
        self,
        target: m.ModelElement,
        /,
        *,
        styleclass: m.DiagramType | str | None = None,
    ) -> None:
        if styleclass is None:
            styleclass = ""
        elif isinstance(styleclass, m.DiagramType):
            styleclass = styleclass.value
        elif styleclass in m.DiagramType._member_map_:
            styleclass = m.DiagramType[styleclass].value
        te.assert_type(styleclass, str)
        super().__init__(
            styleclass,
            target,
            default_render_parameters={},
        )

        self.__boxes = collections.OrderedDict[str, _BoxSpec | _PortSpec]()
        self.__edges: list[_EdgeSpec] = []

    def box(
        self,
        element: m.ModelElement,
        /,
        *,
        parent: m.ModelElement | None = None,
    ) -> None:
        """Add a box to the diagram.

        Boxes are rectangular elements representing components, functions,
        or other model elements.

        Adding the same element twice will be ignored with a warning.

        Parameters
        ----------
        element
            The model element to add as a box.
        parent
            Nest this box below the given parent's box. The parent must
            be added to the diagram before any of its children.
        """
        if element.uuid in self.__boxes:
            logger.warning("Not adding duplicate element %r", element.uuid)
            return
        self.invalidate_cache()

        self.__boxes[element.uuid] = _BoxSpec(
            obj=element,
            parent=parent.uuid if parent else None,
            ports=set(),
        )

    def port(
        self,
        port: m.ModelElement,
        /,
        parent: m.ModelElement,
    ) -> None:
        """Add a port to an element.

        Ports are attachment points on the sides of boxes, used to
        connect edges.

        Parameters
        ----------
        port
            The port element to add.
        parent
            The parent element that this port belongs to. Must be added
            beforehand using :meth:`box()`.

        Raises
        ------
        ValueError
            If the parent element has not been added via box() first, or
            if the parent is a port instead of a box.
        """
        if parent.uuid not in self.__boxes:
            raise ValueError(
                f"Owner element {parent.uuid} must be added via box() first"
            )
        self.invalidate_cache()

        owner_spec = self.__boxes[parent.uuid]
        if not isinstance(owner_spec, _BoxSpec):
            portrepr = port._short_repr_()
            raise ValueError(f"Owner of port {portrepr} must be a regular box")

        self.__boxes[port.uuid] = _PortSpec(
            obj=port,
            parent=parent.uuid,
        )
        owner_spec.ports.add(port.uuid)

    def edge(
        self,
        edge: m.ModelElement,
        /,
        source: m.ModelElement,
        target: m.ModelElement,
        *,
        labels: list[str] | None = None,
    ) -> None:
        """Add an edge (connection) between elements.

        Both source and target must be added to the diagram via
        :meth:`box()` or :meth:`port()` before creating the edge.

        Parameters
        ----------
        edge
            The model element representing this edge, for example a
            FunctionalExchange or ComponentExchange.
        source
            The source of the edge.
        target
            The target of the edge.
        labels
            Optional labels for the edge.

        Raises
        ------
        ValueError
            If source or target elements have not been added to the
            diagram.
        """
        if source.uuid not in self.__boxes or target.uuid not in self.__boxes:
            raise ValueError(
                "source and target must be added via box() or port() first"
            )

        spec = _EdgeSpec(
            obj=edge,
            source=source,
            target=target,
            labels=labels or [],
        )
        self.__edges.append(spec)

    def elk_input_data(
        self, params: dict[str, t.Any]
    ) -> context.CollectorOutputData:
        params = self._default_render_parameters | params
        if "pvmt_styling" in params:
            params["pvmt_styling"] = styling.normalize_pvmt_styling(
                params["pvmt_styling"]  # type: ignore[arg-type]
            )

        for param_name in self._default_render_parameters:
            setattr(self, f"_{param_name}", params.pop(param_name))

        return _build_elk_input(self.__boxes, self.__edges)


def _build_elk_input(
    boxes: cabc.Mapping[str, _BoxSpec | _PortSpec],
    edges: cabc.Sequence[_EdgeSpec],
    /,
) -> _elkjs.ELKInputData:
    elk_data = _elkjs.ELKInputData(
        id="custom_diagram",
        layoutOptions=_elkjs.get_global_layered_layout_options(),
        children=[],
        edges=[],
    )

    elkboxes: dict[
        str,
        (
            tuple[_BoxSpec, _elkjs.ELKInputChild]
            | tuple[_PortSpec, _elkjs.ELKInputPort]
        ),
    ] = {}
    for boxid, box in boxes.items():
        match box:
            case _BoxSpec(obj):
                elkbox = _makers.make_box(
                    obj, layout_options=_makers.DEFAULT_LABEL_LAYOUT_OPTIONS
                )
                elkboxes[boxid] = (box, elkbox)
                if box.parent:
                    _, elkparent = elkboxes[box.parent]
                    assert isinstance(elkparent, _elkjs.ELKInputChild)
                    elkparent.children.append(elkbox)
                else:
                    elk_data.children.append(elkbox)

            case _PortSpec(obj):
                elkport = _makers.make_port(obj.uuid)
                elkboxes[boxid] = (box, elkport)
                _, elkparent = elkboxes[box.parent]
                assert isinstance(elkparent, _elkjs.ELKInputChild)
                elkparent.ports.append(elkport)

            case b:
                te.assert_never(b)

    for edge in edges:
        labels = []
        for label in edge.labels:
            labels.extend(
                _makers.make_label(label, max_width=_makers.MAX_LABEL_WIDTH)
            )
        elkedge = _elkjs.ELKInputEdge(
            id=edge.obj.uuid,
            sources=[edge.source.uuid],
            targets=[edge.target.uuid],
            labels=labels,
        )
        anc = _find_nearest_common_ancestor(boxes, edge.source, edge.target)
        if anc is None:
            elk_data.edges.append(elkedge)
        else:
            _, elkparent = elkboxes[anc]
            assert isinstance(elkparent, _elkjs.ELKInputChild)
            elkparent.edges.append(elkedge)

    return elk_data


def _find_nearest_common_ancestor(
    boxes: cabc.Mapping[str, _BoxSpec | _PortSpec],
    box1: m.ModelElement,
    box2: m.ModelElement,
) -> str | None:
    """Find the nearest common ancestor of two boxes."""
    ancestors: set[str] = set()
    current = boxes[box1.uuid]
    while current:
        if not isinstance(current, _PortSpec):
            ancestors.add(current.obj.uuid)
        if current.parent is None:
            break
        current = boxes[current.parent]

    current = boxes[box2.uuid]
    while current:
        if (
            not isinstance(current, _PortSpec)
            and current.obj.uuid in ancestors
        ):
            return current.obj.uuid
        if current.parent is None:
            break
        current = boxes[current.parent]

    return None
