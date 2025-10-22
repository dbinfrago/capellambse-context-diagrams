# SPDX-FileCopyrightText: Copyright DB InfraGO AG and the capellambse-context-diagrams contributors
# SPDX-License-Identifier: Apache-2.0
"""Extends the capellambse.model.diagram module with context diagrams.

Definitions of Custom Accessor- and Diagram-Classtypes based on
[`Accessor`][capellambse.model.Accessor] and
[`AbstractDiagram`][capellambse.model.diagram.AbstractDiagram].
"""

from __future__ import annotations

import collections.abc as cabc
import copy
import enum
import json
import logging
import typing as t

from capellambse import diagram as cdiagram
from capellambse import helpers as chelpers
from capellambse import model as m

from . import _elkjs, enums, filters, helpers, serializers, styling
from .builders import dataflow, diagram_view, fchain, interface
from .builders import default as db
from .collectors import (
    _generic,
    cable_tree,
    dataflow_view,
    default,
    exchanges,
    portless,
    realization_view,
    tree_view,
)

logger = logging.getLogger(__name__)

STANDARD_FILTERS = {
    "Operational Capabilities Blank": filters.SYSTEM_EX_RELABEL,
    "Missions Capabilities Blank": filters.SYSTEM_EX_RELABEL,
}
STANDARD_STYLES = {
    "Operational Capabilities Blank": styling.SYSTEM_CAP_STYLING,
    "Missions Capabilities Blank": styling.SYSTEM_CAP_STYLING,
}

CollectorOutputData: t.TypeAlias = (
    _elkjs.ELKInputData
    | tuple[
        _elkjs.ELKInputData, _elkjs.ELKInputData | list[_elkjs.ELKInputEdge]
    ]
)
"""The output of a collector or the input prepared for ELK."""


@m.stringy_enum
class CustomDiagramType(enum.Enum):
    """Custom Diagram types."""

    REALIZATION_VIEW = "RealizationView Diagram"


class ContextAccessor(m.Accessor):
    """Provides access to the custom context diagrams."""

    def __init__(
        self, dgcls: str, render_params: dict[str, t.Any] | None = None
    ) -> None:
        super().__init__()
        self._dgcls = dgcls
        self._default_render_params = render_params or {}

    @t.overload
    def __get__(self, obj: None, objtype: type[t.Any]) -> ContextAccessor: ...
    @t.overload
    def __get__(
        self, obj: m.T, objtype: type[m.T] | None = None
    ) -> ContextDiagram: ...
    def __get__(
        self, obj: m.T | None, objtype: type | None = None
    ) -> m.Accessor | ContextDiagram:
        """Make a ContextDiagram for the given model object."""
        del objtype
        if obj is None:  # pragma: no cover
            return self
        assert isinstance(obj, m.ModelElement)
        return self._get(obj, ContextDiagram)

    def _get(
        self, obj: m.ModelElement, diagram_class: type[ContextDiagram]
    ) -> m.Accessor | ContextDiagram:
        new_diagram = diagram_class(
            self._dgcls,
            obj,
            default_render_parameters=self._default_render_params,
        )
        new_diagram.filters.add(filters.NO_UUID)
        return new_diagram


class InterfaceContextAccessor(ContextAccessor):
    """Provides access to the interface context diagrams."""

    def __init__(  # pylint: disable=super-init-not-called
        self,
        diagclass: dict[type[m.ModelElement], str],
        render_params: dict[str, t.Any] | None = None,
    ) -> None:
        self._dgclasses = diagclass
        self._default_render_params = render_params or {}

    def __get__(  # type: ignore
        self, obj: m.T | None, objtype: type | None = None
    ) -> m.Accessor | ContextDiagram:
        """Make a ContextDiagram for the given model object."""
        del objtype
        if obj is None:  # pragma: no cover
            return self
        assert isinstance(obj, m.ModelElement)
        assert isinstance(obj.parent, m.ModelElement)
        self._dgcls = self._dgclasses[obj.parent.__class__]
        return self._get(obj, InterfaceContextDiagram)


class PhysicalPortContextAccessor(ContextAccessor):
    def __get__(  # type: ignore
        self,
        obj: m.T | None,
        objtype: type | None = None,
    ) -> m.Accessor | ContextDiagram:
        """Make a ContextDiagram for the given model object."""
        del objtype
        if obj is None:  # pragma: no cover
            return self
        assert isinstance(obj, m.ModelElement)
        return self._get(obj, PhysicalPortContextDiagram)


class ClassTreeAccessor(ContextAccessor):
    """Provides access to the tree view diagrams."""

    # pylint: disable=super-init-not-called
    def __init__(
        self, diagclass: str, render_params: dict[str, t.Any] | None = None
    ) -> None:
        self._dgcls = diagclass
        self._default_render_params = render_params or {}

    def __get__(  # type: ignore
        self,
        obj: m.T | None,
        objtype: type | None = None,
    ) -> m.Accessor | ContextDiagram:
        """Make a ClassTreeDiagram for the given model object."""
        del objtype
        if obj is None:  # pragma: no cover
            return self
        assert isinstance(obj, m.ModelElement)
        return self._get(obj, ClassTreeDiagram)


class RealizationViewContextAccessor(ContextAccessor):
    """Provides access to the realization view diagrams."""

    # pylint: disable=super-init-not-called
    def __init__(
        self, diagclass: str, render_params: dict[str, t.Any] | None = None
    ) -> None:
        self._dgcls = diagclass
        self._default_render_params = render_params or {}

    def __get__(  # type: ignore
        self,
        obj: m.T | None,
        objtype: type | None = None,
    ) -> m.Accessor | ContextDiagram:
        """Make a RealizationViewDiagram for the given model object."""
        del objtype
        if obj is None:  # pragma: no cover
            return self
        assert isinstance(obj, m.ModelElement)
        return self._get(obj, RealizationViewDiagram)


class DataFlowAccessor(ContextAccessor):
    # pylint: disable=super-init-not-called
    def __init__(
        self, diagclass: str, render_params: dict[str, t.Any] | None = None
    ) -> None:
        self._dgcls = diagclass
        self._default_render_params = render_params or {}

    def __get__(  # type: ignore
        self,
        obj: m.T | None,
        objtype: type | None = None,
    ) -> m.Accessor | ContextDiagram:
        """Make a DataFlowViewDiagram for the given model object."""
        del objtype
        if obj is None:  # pragma: no cover
            return self
        assert isinstance(obj, m.ModelElement)
        return self._get(obj, DataFlowViewDiagram)


class CableTreeAccessor(ContextAccessor):
    """Provides access to the cable tree diagrams."""

    def __get__(  # type: ignore
        self,
        obj: m.T | None,
        objtype: type | None = None,
    ) -> m.Accessor | ContextDiagram:
        """Make a CableTreeView for the given model object."""
        del objtype
        if obj is None:  # pragma: no cover
            return self
        assert isinstance(obj, m.ModelElement)
        return self._get(obj, CableTreeViewDiagram)


class DiagramLayoutAccessor(m.Accessor):
    """Provides access to an ELK layout of a diagram."""

    def __init__(
        self,
        dgls_to_render_params: (
            dict[m.DiagramType, dict[str, t.Any]] | None
        ) = None,
    ) -> None:
        super().__init__()
        self._dgls_to_render_params = dgls_to_render_params or {}

    @t.overload
    def __get__(
        self, obj: None, objtype: type[t.Any]
    ) -> DiagramLayoutAccessor: ...
    @t.overload
    def __get__(
        self, obj: m.T, objtype: type[m.T] | None = None
    ) -> ELKDiagram: ...
    def __get__(
        self, obj: m.T | None, objtype: type | None = None
    ) -> m.Accessor | ELKDiagram:
        del objtype
        if obj is None:  # pragma: no cover
            return self
        assert isinstance(obj, m.Diagram)
        return self._get(obj)

    def _get(self, obj: m.Diagram) -> m.Accessor | ELKDiagram:
        default_render_params = self._dgls_to_render_params.get(obj.type, {})
        new_diagram = ELKDiagram(
            obj.type.value,
            obj,
            default_render_parameters=default_render_params,
        )
        new_diagram.filters.add(filters.NO_UUID)
        return new_diagram


class FunctionalChainContextAccessor(InterfaceContextAccessor):
    """Provides access to the functional chain view diagrams."""

    def __get__(  # type: ignore
        self, obj: m.T | None, objtype: type | None = None
    ) -> m.Accessor | ContextDiagram:
        """Make a ContextDiagram for the given model object."""
        del objtype
        if obj is None:  # pragma: no cover
            return self
        assert isinstance(obj, m.ModelElement)
        assert isinstance(obj.layer, m.ModelElement)
        self._dgcls = self._dgclasses[obj.layer.__class__]
        return self._get(obj, FunctionalChainContextDiagram)


class ContextDiagram(m.AbstractDiagram):
    """An automatically generated context diagram.

    Attributes
    ----------
    target
        The `m.ModelElement` from which the context is collected
        from.
    styleclass
        The diagram class (for e.g. [LAB]).
    render_styles
        Dictionary with the `ElkChildType` in str format as keys and
        `styling.Styler` functions as values. An example is given by:
        [`styling.BLUE_ACTOR_FNCS`][capellambse_context_diagrams.styling.BLUE_ACTOR_FNCS]
    serializer
        The serializer builds a `Diagram` via
        [`serializers.DiagramSerializer.make_diagram`][capellambse_context_diagrams.serializers.DiagramSerializer.make_diagram]
        by converting every
        [`_elkjs.ELKOutputChild`][capellambse_context_diagrams._elkjs.ELKOutputChild]
        into a `Box`, `Edge` or `Circle`.
    filters
        A list of filter names that are applied during collection of
        context. Currently this is only done in
        [`exchange_data_collector`][capellambse_context_diagrams.collectors._generic.exchange_data_collector].

    Notes
    -----
    The following render parameters are supported:

    * display_symbols_as_boxes: Display objects that are normally
      displayed as symbol as a simple box instead, with the symbol
      being the box' icon. This avoids the object of interest to
      become one giant, oversized symbol in the middle of the diagram,
      and instead keeps the symbol small and only enlarges the
      surrounding box.
    * display_parent_relation: Display objects with a parent
      relationship to the object of interest as the parent box.
    * display_derived_interfaces: Display derived objects collected
      from additional collectors beside the main collector for building
      the context.
    * slim_center_box: Minimal width for the center box, containing
      just the icon and the label. This is False if hierarchy was
      identified.
    * display_port_labels: Display port labels on the diagram.
    * port_label_position: Position of the port labels. See
      [`PORT_LABEL_POSITION`][capellambse_context_diagrams.context._elkjs.PORT_LABEL_POSITION].
    * transparent_background: Make the background transparent.
    * context_groups: Render context UUID groups in the class attribute
      of every context element when an SVG is rendered.
    * display_unused_ports: Display ports that are not connected to an
      edge.
    * edge_direction: Reroute direction of edges.
    * mode: Context collection mode.
    * display_actor_relation: Show the connections between the context
      actors.
    * hide_context_owner: Hide the context owner in the diagram.
    * include_children_context: Include the context of the target's
      children.
    * include_external_context: Include all children of external actors
      in context.
    * hide_functions: Hide functions from the diagram.
    * display_functional_parent_relation: Display the parent relation of
      functions within the context.
    * display_internal_relations: Show exchanges that connect to
      children of a box from the diagram. Only useful with ``BLACKBOX``
      mode.
    * display_cyclic_relations: Show cyclic exchanges that connect
      either the box of interest or a child with itself or a child.
      Only useful with ``BLACKBOX`` mode and
      ``display_cyclic_relations`` turned on.
    * restrict_external_depth: In GREYBOX mode, restrict external
      components to the same depth as max_depth. This prevents showing
      deeply nested children from external components.
    * pvmt_styling: Style the diagram according to the PVMT group
      applied to the diagram elements.
    * child_shadow: Add a white background box (5px padding, 50%
      opacity) behind elements that have a parent box.

    The following properties are used by the internal builders:

    * collect: A callable that yields model elements from a given
      context diagram.
    * is_portless: Boolean flag, if the diagram is portless.
    """

    _display_symbols_as_boxes: bool
    _display_parent_relation: bool
    _display_derived_interfaces: bool
    _slim_center_box: bool
    _display_port_labels: bool
    _port_label_position: _elkjs.PORT_LABEL_POSITION
    _transparent_background: bool
    _context_groups: bool
    _display_unused_ports: bool
    _edge_direction: enums.EDGE_DIRECTION
    _mode: enums.MODE
    _display_actor_relation: bool
    _hide_context_owner: bool
    _include_children_context: bool
    _include_external_context: bool
    _include_interface: bool
    _hide_functions: bool
    _display_functional_parent_relation: bool
    _display_internal_relations: bool
    _display_cyclic_relations: bool
    _restrict_external_depth: bool
    _pvmt_styling: dict[str, t.Any] | None
    _child_shadow: bool

    _collect: cabc.Callable[[ContextDiagram], cabc.Iterator[m.ModelElement]]
    _is_portless: bool

    target: m.ModelElement

    def __init__(
        self,
        class_: str,
        obj: m.ModelElement | m.Diagram,
        *,
        render_styles: dict[str, styling.Styler] | None = None,
        default_render_parameters: dict[str, t.Any],
    ) -> None:
        super().__init__(obj._model)
        self.target = obj  # type: ignore[assignment]
        self.styleclass = class_

        self.render_styles = render_styles or {}
        self.serializer = serializers.DiagramSerializer(self)

        self._elk_input_data: CollectorOutputData | None = None
        self.__filters: cabc.MutableSet[str] = self.FilterSet(self)
        render_params = {
            "display_symbols_as_boxes": False,
            "display_parent_relation": False,
            "display_derived_interfaces": False,
            "slim_center_box": True,
            "display_port_labels": False,
            "port_label_position": _elkjs.PORT_LABEL_POSITION.OUTSIDE,
            "display_unused_ports": False,
            "transparent_background": False,
            "context_groups": False,
            "edge_direction": enums.EDGE_DIRECTION.SMART,
            "mode": enums.MODE.WHITEBOX,
            "display_actor_relation": False,
            "hide_context_owner": False,
            "include_children_context": True,
            "include_external_context": False,
            "include_interface": True,
            "hide_functions": False,
            "display_functional_parent_relation": False,
            "display_internal_relations": True,
            "display_cyclic_relations": False,
            "restrict_external_depth": True,
            "pvmt_styling": None,
            "child_shadow": False,
        }
        if not _generic.DIAGRAM_TYPE_TO_CONNECTOR_NAMES.get(self.type, ()):
            render_params |= {
                "collect": portless.collector,
                "is_portless": True,
            }
        else:
            render_params |= {
                "collect": default.collector,
                "is_portless": False,
            }
        self._default_render_parameters = (
            render_params | default_render_parameters
        )

        if standard_filter := STANDARD_FILTERS.get(class_):
            self.filters.add(standard_filter)
        if standard_styles := STANDARD_STYLES.get(class_):
            self.render_styles = standard_styles

        self.builder: cabc.Callable[
            [ContextDiagram, dict[str, t.Any]], CollectorOutputData
        ] = db.builder

    @property
    def uuid(self) -> str:
        """Returns diagram UUID."""
        return f"{self.target.uuid}_context"

    @property
    def name(self) -> str:
        """Returns the diagram name."""
        class_ = self.__class__.__name__
        return f"{class_} of {self.target.name.replace('/', '- or -')}"

    @property
    def type(self) -> m.DiagramType:
        """Return the type of this diagram."""
        try:
            return m.DiagramType(self.styleclass)
        except ValueError:  # pragma: no cover
            logger.warning("Unknown diagram type %r", self.styleclass)
            return m.DiagramType.UNKNOWN

    @property
    def default_render_parameters(self) -> dict[str, t.Any]:
        return self._default_render_parameters

    @default_render_parameters.setter
    def default_render_parameters(self, params: dict[str, t.Any]) -> None:
        self._default_render_parameters = params

    @property
    def nodes(self) -> m.ElementList:
        """Return a list of all nodes visible in this diagram.

        See Also
        --------
        [`nodes`][capellambse.model.diagram.AbstractDiagram.nodes]
        """
        base = (
            self._render
            if hasattr(self, "_render")
            else self.render(None, params=self._default_render_parameters)
        )
        allids = {
            e.uuid.split(":")[-1].split("_")[0]
            for e in base
            if not e.hidden and e.uuid is not None
        }
        elems = []
        for elemid in allids:
            assert elemid is not None
            try:
                elem = self._model.by_uuid(elemid)
            except KeyError:
                continue
            except ValueError as err:
                if (
                    isinstance(err.args, tuple)
                    and len(err.args) == 1
                    and isinstance(err.args[0], str)
                    and err.args[0].startswith("Malformed link:")
                ):
                    continue
                raise

            elems.append(elem._element)
        return m.ElementList(self._model, elems, m.ModelElement)

    def elk_input_data(self, params: dict[str, t.Any]) -> CollectorOutputData:
        """Return the collected ELK input data."""
        params = self._default_render_parameters | params
        if "pvmt_styling" in params:
            params["pvmt_styling"] = styling.normalize_pvmt_styling(
                params["pvmt_styling"]  # type: ignore[arg-type]
            )

        for param_name in self._default_render_parameters:
            setattr(self, f"_{param_name}", params.pop(param_name))

        data: CollectorOutputData
        if data := params.get("elkdata", None):  # type: ignore[assignment]
            self._elk_input_data = data

        if self._elk_input_data is None:
            self._elk_input_data = self.builder(self, params)

        return self._elk_input_data

    def invalidate_cache(self) -> None:
        super().invalidate_cache()
        self._elk_input_data = None

    class FilterSet(cabc.MutableSet):
        """A set that stores filter_names and invalidates diagram cache."""

        def __init__(
            self,
            diagram: m.AbstractDiagram,
        ) -> None:
            self._set: set[str] = set()
            self._diagram = diagram

        def add(self, value: str) -> None:
            if value not in filters.FILTER_LABEL_ADJUSTERS:
                logger.error("The filter '%s' is not yet supported.", value)
                return
            if value not in self._set:
                self._set.add(value)
                self._diagram.invalidate_cache()

        def discard(self, value: str) -> None:
            if value in self._set:
                self._diagram.invalidate_cache()
            return self._set.discard(value)

        def __contains__(self, x: object) -> bool:
            return self._set.__contains__(x)

        def __iter__(self) -> cabc.Iterator[str]:
            return self._set.__iter__()

        def __len__(self) -> int:
            return self._set.__len__()

    def _create_diagram(self, params: dict[str, t.Any]) -> cdiagram.Diagram:
        data = self.elk_input_data(params)
        assert not isinstance(data, tuple)
        layout = try_to_layout(data)
        is_legend: bool = params.get("is_legend", False)
        add_context(layout, is_legend)
        return self.serializer.make_diagram(
            layout,
            transparent_background=self._transparent_background,
            context_groups=self._context_groups,
        )

    @property
    def filters(self) -> cabc.MutableSet[str]:
        return self.__filters

    @filters.setter
    def filters(self, value: cabc.Iterable[str]) -> None:
        self.__filters.clear()
        self.__filters |= set(value)


class InterfaceContextDiagram(ContextDiagram):
    """A Context Diagram exclusively for ``ComponentExchange``s.

    Attributes
    ----------
    dangling_functional_exchanges: list[fa.AbstractExchange]
        A list of ``dangling`` functional exchanges for which either the
        source or target function were not allocated to a Component,
        part of the context.

    Notes
    -----
    The following render parameters are available:

    * include_interface: Boolean flag to enable inclusion of the
      context diagram target: The interface ComponentExchange.
    * include_port_allocations: Boolean flag to enable rendering of
      port allocations.
    * hide_functions: Boolean flag to enable white box view: Only
      displaying Components or Entities.


    In addition to all other render parameters of
    [`ContextDiagram`][capellambse_context_diagrams.context.ContextDiagram].
    """

    _include_interface: bool
    _hide_functions: bool
    _include_port_allocations: bool

    def __init__(
        self,
        class_: str,
        obj: m.ModelElement,
        *,
        render_styles: dict[str, styling.Styler] | None = None,
        default_render_parameters: dict[str, t.Any],
    ) -> None:
        default_render_parameters = {
            "include_interface": False,
            "include_port_allocations": False,
            "hide_functions": False,
            "display_symbols_as_boxes": True,
            "display_port_labels": False,
            "port_label_position": _elkjs.PORT_LABEL_POSITION.OUTSIDE,
            "display_parent_relation": True,
            "collect": exchanges.interface_context_collector,
            "hide_context_owner": True,
            "edge_direction": enums.EDGE_DIRECTION.RIGHT,
            "display_functional_parent_relation": True,
        } | default_render_parameters
        super().__init__(
            class_,
            obj,
            render_styles=render_styles,
            default_render_parameters=default_render_parameters,
        )
        self.builder = interface.builder

    def _create_diagram(self, params: dict[str, t.Any]) -> cdiagram.Diagram:
        data = self.elk_input_data(params)
        assert not isinstance(data, tuple)
        layout = try_to_layout(data)
        if (
            self._include_interface
            and self._include_port_allocations
            and not self._hide_functions
        ):
            self._add_port_allocations(layout)

        is_legend: bool = params.get("is_legend", False)
        add_context(layout, is_legend)
        return self.serializer.make_diagram(
            layout,
            transparent_background=self._transparent_background,
            context_groups=self._context_groups,
        )

    def _add_port_allocations(self, layout: _elkjs.ELKOutputData) -> None:
        uuids = (self.target.source.owner.uuid, self.target.target.owner.uuid)
        port_uuids = (self.target.source.uuid, self.target.target.uuid)
        for i, _ in enumerate(port_uuids):
            node, node_ref = _find_node_in_layout(layout, uuids[i])
            assert isinstance(node, _elkjs.ELKOutputNode)
            port = next((p for p in node.children if p.id in port_uuids), None)
            assert isinstance(port, _elkjs.ELKOutputPort)
            if port is not None:
                layout.children.extend(
                    self._yield_port_allocations(node, port, node_ref)
                )

    def _yield_port_allocations(
        self,
        node: _elkjs.ELKOutputNode,
        interface_port: _elkjs.ELKOutputPort,
        ref: cdiagram.Vector2D,
    ) -> cabc.Iterator[_elkjs.ELKOutputEdge]:
        for position, port in _get_all_ports(node, ref=ref):
            if port == interface_port:
                continue
            port_middle = _calculate_middle(position, port.size)
            interface_middle = _calculate_middle(
                interface_port.position, interface_port.size, ref
            )
            styleclass = self.serializer.get_styleclass(port.id)
            if styleclass in {"FIP", "FOP"}:
                yield _create_port_allocation_edge(
                    styleclass,
                    port.id,
                    interface_port.id,
                    port_middle,
                    interface_middle,
                )

    @property
    def name(self) -> str:
        return f"Interface Context of {self.target.name}"


def _find_node_in_layout(
    layout: _elkjs.ELKOutputData | _elkjs.ELKOutputNode,
    uuid: str,
    ref: cdiagram.Vector2D | None = None,
) -> tuple[_elkjs.ELKOutputNode, cdiagram.Vector2D]:
    """Find a node in the layout by UUID and return with its position.

    Parameters
    ----------
    layout
        The layout data or node to search in.
    uuid
        The UUID of the node to find.
    ref
        The reference position (accumulated offset from parent nodes).

    Returns
    -------
    tuple
        The found node and its absolute position in the layout.

    Raises
    ------
    ValueError
        If the node with the given UUID is not found.
    """
    if ref is None:
        ref = cdiagram.Vector2D(0, 0)

    for node in layout.children:
        if node.type != "node":
            continue

        current_ref = cdiagram.Vector2D(
            ref.x + node.position.x, ref.y + node.position.y
        )
        if node.id == uuid:
            return node, current_ref
        try:
            return _find_node_in_layout(node, uuid, ref=current_ref)
        except ValueError:
            pass

    raise ValueError(f"Node with id {uuid!r} doesn't exist in layout.")


def _find_port_in_node(
    node: _elkjs.ELKOutputNode, port_uuid: str
) -> _elkjs.ELKOutputPort | None:
    """Find a port in a node's children by UUID.

    Parameters
    ----------
    node
        The node to search in.
    port_uuid
        The UUID of the port to find.

    Returns
    -------
    _elkjs.ELKOutputPort | None
        The found port or None if not found.
    """
    return next(
        (
            p
            for p in node.children
            if p.id == port_uuid and isinstance(p, _elkjs.ELKOutputPort)
        ),
        None,
    )


def _create_port_allocation_edge(
    styleclass: str,
    function_port_id: str,
    other_port_id: str,
    function_port_middle: _elkjs.ELKPoint,
    other_port_middle: _elkjs.ELKPoint,
) -> _elkjs.ELKOutputEdge:
    """Create a port allocation edge between a function port and another port.

    Parameters
    ----------
    styleclass
        The style class of the function port (FIP or FOP).
    function_port_id
        UUID of the function port.
    other_port_id
        UUID of the other port (component or physical port).
    function_port_middle
        Center position of the function port.
    other_port_middle
        Center position of the other port.

    Returns
    -------
    _elkjs.ELKOutputEdge
        The port allocation edge with proper direction and routing.
    """
    if styleclass == "FIP":
        eid = f"__PortInputAllocation:{function_port_id}"
        src_id, trg_id = function_port_id, other_port_id
        routing_points = [function_port_middle, other_port_middle]
    else:
        eid = f"__PortOutputAllocation:{function_port_id}"
        src_id, trg_id = other_port_id, function_port_id
        routing_points = [other_port_middle, function_port_middle]

    return _elkjs.ELKOutputEdge(
        id=eid,
        type="edge",
        routingPoints=routing_points,
        sourceId=src_id,
        targetId=trg_id,
    )


class ClassTreeDiagram(ContextDiagram):
    """An automatically generated ClassTree Diagram.

    This diagram is exclusively for ``Class``es.
    """

    _edgeRouting: t.Literal["UNDEFINED", "POLYLINE", "ORTHOGONAL", "SPLINES"]
    _direction: t.Literal["DOWN", "UP", "LEFT", "RIGHT"]
    _nodeSizeConstraints: t.Literal[
        "PORTS", "PORT_LABELS", "NODE_LABELS", "MINIMUM_SIZE"
    ]
    _edgeLabelsSide: t.Literal[
        "ALWAYS_UP",
        "ALWAYS_DOWN",
        "DIRECTION_UP",
        "DIRECTION_DOWN",
        "SMART_UP",
        "SMART_DOWN",
    ]
    _partitioning: bool
    _depth: int | None
    _super: t.Literal["ROOT", "ALL"]
    _sub: t.Literal["ROOT", "ALL"]

    def __init__(
        self,
        class_: str,
        obj: m.ModelElement,
        *,
        render_styles: dict[str, styling.Styler] | None = None,
        default_render_parameters: dict[str, t.Any],
    ) -> None:
        default_render_parameters = {
            "display_symbols_as_boxes": True,
            "edgeRouting": "POLYLINE",
            "direction": "DOWN",
            "nodeSizeConstraints": "NODE_LABELS",
            "edgeLabelsSide": "SMART_DOWN",
            "partitioning": False,
            "depth": None,
            "super": "ROOT",
            "sub": "ROOT",
        } | default_render_parameters
        super().__init__(
            class_,
            obj,
            render_styles=render_styles,
            default_render_parameters=default_render_parameters,
        )
        self.builder = tree_view.collector  # type: ignore[assignment]

    @property
    def uuid(self) -> str:
        """Returns the UUID of the diagram."""
        return f"{self.target.uuid}_tree_view"

    @property
    def name(self) -> str:
        """Returns the name of the diagram."""
        return f"Tree view of {self.target.name}"

    def _create_diagram(self, params: dict[str, t.Any]) -> cdiagram.Diagram:
        data, legend = self.elk_input_data(params)
        assert isinstance(data, _elkjs.ELKInputData)
        assert isinstance(legend, _elkjs.ELKInputData)
        params["elkdata"] = data
        class_diagram = super()._create_diagram(params)
        assert class_diagram.viewport is not None
        width, height = class_diagram.viewport.size
        axis: t.Literal["x", "y"]
        if self._direction in {"DOWN", "UP"}:
            legend.layoutOptions["aspectRatio"] = width / height
            axis = "x"
        else:
            legend.layoutOptions["aspectRatio"] = width
            axis = "y"

        params["elkdata"] = legend
        params["is_legend"] = True
        legend_diagram = super()._create_diagram(params)
        stack_diagrams(class_diagram, legend_diagram, axis)
        return class_diagram


def add_context(data: _elkjs.ELKOutputData, is_legend: bool = False) -> None:
    """Add all connected nodes as context to all elements."""
    if is_legend:
        for child in data.children:
            if child.type == "node":
                child.context = [child.id]
        return

    ids: set[str] = set()

    def get_ids(
        obj: (
            _elkjs.ELKOutputNode
            | _elkjs.ELKOutputPort
            | _elkjs.ELKOutputJunction
            | _elkjs.ELKOutputEdge
        ),
    ) -> None:
        if obj.id and not obj.id.startswith("g_"):
            ids.add(obj.id)
        for child in getattr(obj, "children", []):
            if child.type in {"node", "port", "junction", "edge"}:
                assert child.type != "label"
                get_ids(child)

    def set_ids(
        obj: _elkjs.ELKOutputChild,
        ids: set[str],
    ) -> None:
        obj.context = list(ids)
        for child in getattr(obj, "children", []):
            set_ids(child, ids)

    for child in data.children:
        if child.type in {"node", "port", "junction", "edge"}:
            assert child.type != "label"
            get_ids(child)

    for child in data.children:
        set_ids(child, ids)


class RealizationViewDiagram(ContextDiagram):
    """An automatically generated realization view diagram.

    This diagram is exclusively for ``Activity``, ``Function``s,
    ``Entity`` and ``Components`` of all layers.
    """

    _depth: int
    _search_direction: t.Literal["ALL", "ABOVE", "BELOW"]
    _show_owners: bool
    _layer_sizing: t.Literal["UNION", "HEIGHT", "WIDTH", "INDIVIDUAL"]

    def __init__(
        self,
        class_: str,
        obj: m.ModelElement,
        *,
        render_styles: dict[str, styling.Styler] | None = None,
        default_render_parameters: dict[str, t.Any],
    ) -> None:
        default_render_parameters = {
            "display_symbols_as_boxes": True,
            "depth": 1,
            "search_direction": "ALL",
            "show_owners": True,
            "layer_sizing": "WIDTH",
        } | default_render_parameters
        super().__init__(
            class_,
            obj,
            render_styles=render_styles,
            default_render_parameters=default_render_parameters,
        )
        self.builder = realization_view.collector  # type: ignore[assignment]

    @property
    def uuid(self) -> str:
        """Returns the UUID of the diagram."""
        return f"{self.target.uuid}_realization_view"

    @property
    def name(self) -> str:
        """Returns the name of the diagram."""
        return f"Realization view of {self.target.name}"

    @property
    def type(self) -> CustomDiagramType:  # type: ignore[override]
        """Return the type of this diagram."""
        return CustomDiagramType(self.styleclass)

    def _create_diagram(self, params: dict[str, t.Any]) -> cdiagram.Diagram:
        data, edges = self.elk_input_data(params)
        assert isinstance(data, _elkjs.ELKInputData)
        assert isinstance(edges, list)
        layout = try_to_layout(data)
        adjust_layer_sizing(data, layout, self._layer_sizing)
        layout = try_to_layout(data)
        for edge in edges:
            assert isinstance(edge, _elkjs.ELKInputEdge)
            layout.children.append(
                _elkjs.ELKOutputEdge(
                    id=f"__Realization:{edge.id}",
                    type="edge",
                    sourceId=edge.sources[0],
                    targetId=edge.targets[0],
                    routingPoints=[],
                )
            )
        self._add_layer_labels(layout)
        return self.serializer.make_diagram(
            layout,
            transparent_background=self._transparent_background,
            context_groups=self._context_groups,
        )

    def _add_layer_labels(self, layout: _elkjs.ELKOutputData) -> None:
        for layer in layout.children:
            if layer.type != "node":
                continue

            layer_obj = self.serializer.model.by_uuid(layer.id)
            _, layer_name = realization_view.find_layer(layer_obj)
            pos = layer.position.x, layer.position.y
            size = layer.size.width, layer.size.height
            width, height = chelpers.get_text_extent(layer_name)
            x, y, tspan_y = calculate_label_position(*pos, *size)
            label_box = _elkjs.ELKOutputLabel(
                type="label",
                id="None",
                text=layer_name,
                position=_elkjs.ELKPoint(x=x, y=y),
                size=_elkjs.ELKSize(width=width, height=height),
                style={
                    "text_transform": f"rotate(-90, {x}, {y}) {tspan_y}",
                    "text_fill": "grey",
                },
            )
            layer.children.insert(0, label_box)
            layer.style = {"stroke": "grey", "rx": 5, "ry": 5}


class DataFlowViewDiagram(ContextDiagram):
    """An automatically generated DataFlowViewDiagram."""

    def __init__(
        self,
        class_: str,
        obj: m.ModelElement,
        *,
        render_styles: dict[str, styling.Styler] | None = None,
        default_render_parameters: dict[str, t.Any],
    ) -> None:
        default_render_parameters = {
            "display_symbols_as_boxes": True,
            "display_parent_relation": True,
            "edge_direction": enums.EDGE_DIRECTION.NONE,
            "mode": enums.MODE.WHITEBOX,
            "collect": dataflow_view.collector,
        } | default_render_parameters
        super().__init__(
            class_,
            obj,
            render_styles=render_styles,
            default_render_parameters=default_render_parameters,
        )
        self.builder = dataflow.builder

    @property
    def uuid(self) -> str:
        """Returns the UUID of the diagram."""
        return f"{self.target.uuid}_data_flow_view"

    @property
    def name(self) -> str:
        """Returns the name of the diagram."""
        return f"DataFlow view of {self.target.name}"


class CableTreeViewDiagram(ContextDiagram):
    """An automatically generated CableTreeView."""

    def __init__(
        self,
        class_: str,
        obj: m.ModelElement,
        *,
        render_styles: dict[str, styling.Styler] | None = None,
        default_render_parameters: dict[str, t.Any],
    ) -> None:
        default_render_parameters = {
            "display_port_labels": True,
            "port_label_position": _elkjs.PORT_LABEL_POSITION.OUTSIDE,
            "include_external_context": True,
            "collect": cable_tree.collector,
            "edge_direction": enums.EDGE_DIRECTION.TREE,
        } | default_render_parameters
        super().__init__(
            class_,
            obj,
            render_styles=render_styles,
            default_render_parameters=default_render_parameters,
        )

    @property
    def uuid(self) -> str:
        """Returns the UUID of the diagram."""
        return f"{self.target.uuid}_cable_tree"

    @property
    def name(self) -> str:
        return f"Cable Tree View of {self.target.name}"


class PhysicalPortContextDiagram(ContextDiagram):
    """A custom Context Diagram exclusively for PhysicalPorts."""

    def __init__(
        self,
        class_: str,
        obj: m.ModelElement,
        *,
        render_styles: dict[str, styling.Styler] | None = None,
        default_render_parameters: dict[str, t.Any],
    ) -> None:
        default_render_parameters = {
            "collect": default.physical_port_context_collector,
            "display_parent_relation": True,
            "edge_direction": enums.EDGE_DIRECTION.TREE,
            "display_port_labels": True,
            "port_label_position": _elkjs.PORT_LABEL_POSITION.OUTSIDE,
        } | default_render_parameters

        super().__init__(
            class_,
            obj,
            render_styles=render_styles,
            default_render_parameters=default_render_parameters,
        )


class ELKDiagram(ContextDiagram):
    """A former diagram layouted by ELKJS."""

    _include_port_allocations: bool
    _hide_elements: set[str]

    def __init__(
        self,
        class_: str,
        obj: m.Diagram,
        *,
        render_styles: dict[str, styling.Styler] | None = None,
        default_render_parameters: dict[str, t.Any],
    ) -> None:
        default_render_parameters = {
            "include_port_allocations": True,
            "hide_elements": set(),
            "pvmt_styling": None,
            "display_port_labels": False,
            "display_symbols_as_boxes": False,
        } | default_render_parameters
        super().__init__(
            class_,
            obj,
            render_styles=render_styles,
            default_render_parameters=default_render_parameters,
        )

        self.builder = diagram_view.build_from_diagram  # type: ignore[assignment]
        self.target: m.Diagram = obj  # type: ignore[assignment]

        self.__nodes: m.ElementList | None = None

    @property
    def uuid(self) -> str:
        """Returns diagram UUID."""
        return f"{self.target.uuid}_elk"

    @property
    def name(self) -> str:
        """Returns the diagram name."""
        return f"ELK Layout of {self.target.name.replace('/', '- or -')}"

    @property
    def nodes(self) -> m.ElementList:
        """Return a list of all nodes visible in this diagram."""
        if not self.__nodes:
            self.__nodes = super().nodes
        assert self.__nodes is not None
        return self.__nodes

    def _create_diagram(self, params: dict[str, t.Any]) -> cdiagram.Diagram:
        data = self.elk_input_data(params)
        assert not isinstance(data, tuple)
        layout = try_to_layout(data)
        if self._include_port_allocations:
            self._add_port_allocations(layout)

        add_context(layout)
        return self.serializer.make_diagram(
            layout, transparent_background=self._transparent_background
        )

    def _add_port_allocations(self, layout: _elkjs.ELKOutputData) -> None:
        for node in self.target.nodes:
            if helpers.is_allocation(node):
                try:
                    src_middle, tgt_middle = (
                        self._find_port_positions_from_allocation(layout, node)
                    )
                except ValueError:
                    continue

                src_styleclass = self.serializer.get_styleclass(
                    node.source.uuid
                )
                tgt_styleclass = self.serializer.get_styleclass(
                    node.target.uuid
                )

                if src_styleclass in {"FIP", "FOP"}:
                    layout.children.append(
                        _create_port_allocation_edge(
                            src_styleclass,
                            node.source.uuid,
                            node.target.uuid,
                            src_middle,
                            tgt_middle,
                        )
                    )
                elif tgt_styleclass in {"FIP", "FOP"}:
                    layout.children.append(
                        _create_port_allocation_edge(
                            tgt_styleclass,
                            node.target.uuid,
                            node.source.uuid,
                            tgt_middle,
                            src_middle,
                        )
                    )
            elif helpers.is_port(node) and hasattr(
                node, "allocated_function_ports"
            ):
                for fnc_port in node.allocated_function_ports:
                    try:
                        node_ref, port_ref = self._find_port_positions(
                            layout, node, fnc_port
                        )
                    except ValueError:
                        continue

                    layout.children.extend(
                        self._yield_port_allocations(
                            node, fnc_port, node_ref, port_ref
                        )
                    )

    def _find_port_positions_from_allocation(
        self,
        layout: _elkjs.ELKOutputData,
        port_alloc: m.ModelElement,
    ) -> tuple[_elkjs.ELKPoint, _elkjs.ELKPoint]:
        src_node, src_ref = _find_node_in_layout(
            layout, port_alloc.source.owner.uuid
        )
        tgt_node, tgt_ref = _find_node_in_layout(
            layout, port_alloc.target.owner.uuid
        )

        src_port = _find_port_in_node(src_node, port_alloc.source.uuid)
        tgt_port = _find_port_in_node(tgt_node, port_alloc.target.uuid)

        if src_port is None or tgt_port is None:
            raise ValueError("Port not found in layout")

        src_middle = _calculate_middle(
            src_port.position, src_port.size, src_ref
        )
        tgt_middle = _calculate_middle(
            tgt_port.position, tgt_port.size, tgt_ref
        )

        return src_middle, tgt_middle

    def _find_port_positions(
        self,
        layout: _elkjs.ELKOutputData,
        component_port: m.ModelElement,
        function_port: m.ModelElement,
    ) -> tuple[cdiagram.Vector2D, cdiagram.Vector2D]:
        comp_node, comp_ref = _find_node_in_layout(
            layout, component_port.owner.uuid
        )
        comp_port = _find_port_in_node(comp_node, component_port.uuid)
        if comp_port is None:
            raise ValueError(f"Port {component_port.uuid} not found")

        fnc_node, fnc_ref = _find_node_in_layout(
            layout, function_port.owner.uuid
        )
        fnc_port = _find_port_in_node(fnc_node, function_port.uuid)
        if fnc_port is None:
            raise ValueError(f"Port {function_port.uuid} not found")

        comp_port_pos = cdiagram.Vector2D(
            comp_ref.x + comp_port.position.x,
            comp_ref.y + comp_port.position.y,
        )
        fnc_port_pos = cdiagram.Vector2D(
            fnc_ref.x + fnc_port.position.x,
            fnc_ref.y + fnc_port.position.y,
        )

        comp_middle_pt = _calculate_middle(comp_port_pos, comp_port.size)
        fnc_middle_pt = _calculate_middle(fnc_port_pos, fnc_port.size)

        comp_middle = cdiagram.Vector2D(comp_middle_pt.x, comp_middle_pt.y)
        fnc_middle = cdiagram.Vector2D(fnc_middle_pt.x, fnc_middle_pt.y)

        return comp_middle, fnc_middle

    def _yield_port_allocations(
        self,
        component_port: m.ModelElement,
        function_port: m.ModelElement,
        comp_middle: cdiagram.Vector2D,
        fnc_middle: cdiagram.Vector2D,
    ) -> cabc.Iterator[_elkjs.ELKOutputEdge]:
        styleclass = self.serializer.get_styleclass(function_port.uuid)
        if styleclass in {"FIP", "FOP"}:
            comp_middle_pt = _elkjs.ELKPoint(x=comp_middle.x, y=comp_middle.y)
            fnc_middle_pt = _elkjs.ELKPoint(x=fnc_middle.x, y=fnc_middle.y)
            yield _create_port_allocation_edge(
                styleclass,
                function_port.uuid,
                component_port.uuid,
                fnc_middle_pt,
                comp_middle_pt,
            )


class FunctionalChainContextDiagram(ContextDiagram):
    """A custom Context Diagram exclusively for FunctionalChains."""

    def __init__(
        self,
        class_: str,
        obj: m.ModelElement,
        *,
        render_styles: dict[str, styling.Styler] | None = None,
        default_render_parameters: dict[str, t.Any],
    ) -> None:
        default_render_parameters = {
            "display_symbols_as_boxes": True,
            "display_parent_relation": True,
            "edge_direction": enums.EDGE_DIRECTION.SMART,
            "mode": enums.MODE.WHITEBOX,
            "collect": default.functional_chain_collector,
        } | default_render_parameters

        super().__init__(
            class_,
            obj,
            render_styles=render_styles,
            default_render_parameters=default_render_parameters,
        )

        self.builder = fchain.builder


def try_to_layout(data: _elkjs.ELKInputData) -> _elkjs.ELKOutputData:
    """Try calling elkjs, raise a JSONDecodeError if it fails."""
    try:
        return _elkjs.elk_manager.call_elkjs(data)
    except json.JSONDecodeError as error:
        logger.error(json.dumps(data, indent=4))
        raise error


def adjust_layer_sizing(
    data: _elkjs.ELKInputData,
    layout: _elkjs.ELKOutputData,
    layer_sizing: t.Literal["UNION", "WIDTH", "HEIGHT", "INDIVIDUAL"],
) -> None:
    """Set `nodeSize.minimum` config in the layoutOptions."""

    def calculate_min(key: t.Literal["width", "height"] = "width") -> float:
        return max(getattr(child.size, key) for child in layout.children)  # type: ignore[union-attr]

    if layer_sizing not in {"UNION", "WIDTH", "HEIGHT", "INDIVIDUAL"}:
        raise NotImplementedError(
            "For ``layer_sizing`` only UNION, WIDTH, HEIGHT or INDIVIDUAL is supported"
        )

    min_w = calculate_min() + 15.0 if layer_sizing in {"UNION", "WIDTH"} else 0
    min_h = (
        calculate_min("height") if layer_sizing in {"UNION", "HEIGHT"} else 0
    )
    for layer in data.children:
        layer.layoutOptions["nodeSize.minimum"] = f"({min_w},{min_h})"


def stack_diagrams(
    first: cdiagram.Diagram,
    second: cdiagram.Diagram,
    axis: t.Literal["x", "y"] = "x",
) -> None:
    """Add the diagram elements from ``right`` to left inline."""
    if first.viewport:
        offset = first.viewport.pos + first.viewport.size
        offset @= (1, 0) if axis == "x" else (0, 1)
        for element in second:
            new = copy.deepcopy(element)
            new.move(offset)
            first += new
    else:
        for element in second:
            new = copy.deepcopy(element)
            first += new


def calculate_label_position(
    x: float,
    y: float,
    width: float,
    height: float,
    padding: float = 10.0,
) -> tuple[float, float, float]:
    """Calculate the position of the label and tspan.

    The function calculates the center of the rectangle and uses the
    rectangle's width and height to adjust its position within it. The
    text is assumed to be horizontally and vertically centered within
    the rectangle. The tspan y coordinate is for positioning the label
    right under the left side of the rectangle.

    Parameters
    ----------
    x
        The x coordinate of the label position.
    y
        The y coordinate of the label position.
    width
        Width of the label.
    height
        Height of the label
    padding
        The padding for the label.

    Returns
    -------
    position
        A tuple containing the x- and y-coordinate for the text element
        and the adjusted y-coordinate for the tspan element.
    """
    center_y = y + height / 2
    tspan_y = center_y - width / 2 + padding
    return (x + width / 2, center_y, tspan_y)


def _get_all_ports(
    node: _elkjs.ELKOutputNode, ref: cdiagram.Vector2D
) -> cabc.Iterator[tuple[cdiagram.Vector2D, _elkjs.ELKOutputPort]]:
    """Yield all ports from a given ``node`` and its children."""
    for child in node.children:
        if isinstance(child, _elkjs.ELKOutputPort):
            yield ref + (child.position.x, child.position.y), child

        if isinstance(child, _elkjs.ELKOutputNode):
            yield from _get_all_ports(
                child, ref=ref + (child.position.x, child.position.y)
            )


def _calculate_middle(
    position: _elkjs.ELKPoint | cdiagram.Vector2D,
    size: _elkjs.ELKSize,
    offset: cdiagram.Vector2D | None = None,
) -> _elkjs.ELKPoint:
    x = position.x + size.width / 2
    y = position.y + size.height / 2
    if offset is not None:
        x += offset.x
        y += offset.y
    return _elkjs.ELKPoint(x=x, y=y)
