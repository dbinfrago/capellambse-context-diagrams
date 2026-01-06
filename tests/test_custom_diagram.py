# SPDX-FileCopyrightText: Copyright DB InfraGO AG and the capellambse-context-diagrams contributors
# SPDX-License-Identifier: Apache-2.0

"""Tests for the declarative CustomDiagram API."""

import json
import pathlib
import typing as t

import capellambse
import capellambse.diagram as cdiagram
import capellambse.metamodel as mm
import capellambse.model as m
import pytest

import capellambse_context_diagrams as ccd

TEST_ROOT = pathlib.Path(__file__).parent / "data"
TEST_COMP_UUID = "0d2edb8f-fa34-4e73-89ec-fb9a63001440"
TEST_EXCHANGE_UUID = "a900a6e0-c994-42e8-ae94-2b61a7fabc18"


class TestBasicDiagramCreation:
    """Test basic diagram creation and element addition."""

    def test_create_empty_diagram(self, model: capellambse.MelodyModel):
        diag = ccd.CustomDiagram(model.project)

        render = diag.render(None)

        assert len(render) == 0

    def test_add_single_element(self, model: capellambse.MelodyModel):
        component = model.by_uuid(TEST_COMP_UUID)

        diag = ccd.CustomDiagram(component)
        diag.box(component)
        render = diag.render(None)

        assert len(render) == 1
        assert TEST_COMP_UUID in render
        assert isinstance(render[TEST_COMP_UUID], cdiagram.Box)

    def test_add_nested_elements(self, model: capellambse.MelodyModel):
        parent = model.by_uuid(TEST_COMP_UUID)
        child = parent.components[0]

        diag = ccd.CustomDiagram(parent)
        diag.box(parent)
        diag.box(child, parent=parent)
        render = diag.render(None)

        assert len(render) == 2
        pbox = render[parent.uuid]
        assert isinstance(pbox, cdiagram.Box)
        assert len(pbox.children) == 1

    def test_duplicate_elements_are_not_added(
        self, model: capellambse.MelodyModel
    ):
        component = model.by_uuid(TEST_COMP_UUID)

        diag = ccd.CustomDiagram(component)
        diag.box(component)
        diag.box(component)
        render = diag.render(None)

        assert len(render) == 1

    def test_add_portless_edge(self, model: capellambse.MelodyModel):
        exchange = model.by_uuid(TEST_EXCHANGE_UUID)
        assert isinstance(exchange, mm.fa.ComponentExchange)
        assert exchange.source is not None
        assert exchange.target is not None
        comp1 = exchange.source.owner
        comp2 = exchange.target.owner
        assert isinstance(comp1, mm.la.LogicalComponent)
        assert isinstance(comp2, mm.la.LogicalComponent)

        diag = ccd.CustomDiagram(exchange)
        diag.box(comp1)
        diag.box(comp2)
        diag.edge(exchange, comp1, comp2)
        render = diag.render(None)

        assert len(render) == 3
        box1 = render[comp1.uuid]
        box2 = render[comp2.uuid]
        edge = render[exchange.uuid]
        assert isinstance(edge, cdiagram.Edge)
        assert edge.source is box1
        assert edge.target is box2

    def test_add_port_based_edge(self, model: capellambse.MelodyModel):
        exchange = model.by_uuid(TEST_EXCHANGE_UUID)
        assert isinstance(exchange, mm.fa.ComponentExchange)
        port1 = exchange.source
        port2 = exchange.target
        assert isinstance(port1, mm.fa.ComponentPort)
        assert isinstance(port2, mm.fa.ComponentPort)
        comp1 = port1.owner
        comp2 = port2.owner
        assert isinstance(comp1, mm.la.LogicalComponent)
        assert isinstance(comp2, mm.la.LogicalComponent)

        diag = ccd.CustomDiagram(exchange)
        diag.box(comp1)
        diag.port(port1, comp1)
        diag.box(comp2)
        diag.port(port2, comp2)
        diag.edge(exchange, port1, port2)
        render = diag.render(None)

        box1 = render[port1.uuid]
        box2 = render[port2.uuid]
        edge = render[exchange.uuid]
        assert isinstance(edge, cdiagram.Edge)
        assert edge.source is box1
        assert edge.target is box2


class TestErrorHandling:
    """Test error handling and validation."""

    def test_port_without_parent_box_raises_error(
        self, model: capellambse.MelodyModel
    ):
        """Test that adding a port without its parent box raises ValueError."""
        exchange = model.by_uuid(TEST_EXCHANGE_UUID)
        port = exchange.source
        parent = port.owner

        diag = ccd.CustomDiagram(model.project)

        with pytest.raises(
            ValueError, match="must be added via box\\(\\) first"
        ):
            diag.port(port, parent)

    def test_port_with_port_as_parent_raises_error(
        self, model: capellambse.MelodyModel
    ):
        """Test that adding a port with another port as parent raises ValueError."""
        exchange = model.by_uuid(TEST_EXCHANGE_UUID)
        port1 = exchange.source
        port2 = exchange.target
        comp = port1.owner

        diag = ccd.CustomDiagram(model.project)
        diag.box(comp)
        diag.port(port1, comp)

        with pytest.raises(ValueError, match="must be a regular box"):
            diag.port(port2, port1)  # Trying to use port1 as parent

    def test_edge_with_missing_source_raises_error(
        self, model: capellambse.MelodyModel
    ):
        """Test that adding an edge with missing source raises ValueError."""
        exchange = model.by_uuid(TEST_EXCHANGE_UUID)
        comp1 = exchange.source.owner
        comp2 = exchange.target.owner

        diag = ccd.CustomDiagram(model.project)
        diag.box(comp2)

        with pytest.raises(
            ValueError, match="must be added via box\\(\\) or port\\(\\) first"
        ):
            diag.edge(exchange, comp1, comp2)

    def test_edge_with_missing_target_raises_error(
        self, model: capellambse.MelodyModel
    ):
        """Test that adding an edge with missing target raises ValueError."""
        exchange = model.by_uuid(TEST_EXCHANGE_UUID)
        comp1 = exchange.source.owner
        comp2 = exchange.target.owner

        diag = ccd.CustomDiagram(model.project)
        diag.box(comp1)

        with pytest.raises(
            ValueError, match="must be added via box\\(\\) or port\\(\\) first"
        ):
            diag.edge(exchange, comp1, comp2)

    def test_edge_with_both_missing_raises_error(
        self, model: capellambse.MelodyModel
    ):
        """Test that adding an edge with both endpoints missing raises ValueError."""
        exchange = model.by_uuid(TEST_EXCHANGE_UUID)
        comp1 = exchange.source.owner
        comp2 = exchange.target.owner

        diag = ccd.CustomDiagram(model.project)

        with pytest.raises(
            ValueError, match="must be added via box\\(\\) or port\\(\\) first"
        ):
            diag.edge(exchange, comp1, comp2)


class TestDuplicateDetection:
    """Test duplicate detection and handling."""

    def test_duplicate_port_is_not_added(self, model: capellambse.MelodyModel):
        """Test that adding the same port twice is ignored with a warning."""
        exchange = model.by_uuid(TEST_EXCHANGE_UUID)
        port = exchange.source
        comp = port.owner

        diag = ccd.CustomDiagram(model.project)
        diag.box(comp)
        diag.port(port, comp)
        diag.port(port, comp)  # Add same port again

        render = diag.render(None)

        assert len(render) == 2
        assert port.uuid in render

    def test_duplicate_edge_is_not_added(self, model: capellambse.MelodyModel):
        """Test that adding the same edge twice is ignored with a warning."""
        exchange = model.by_uuid(TEST_EXCHANGE_UUID)
        comp1 = exchange.source.owner
        comp2 = exchange.target.owner

        diag = ccd.CustomDiagram(model.project)
        diag.box(comp1)
        diag.box(comp2)
        diag.edge(exchange, comp1, comp2)
        diag.edge(exchange, comp1, comp2)  # Add same edge again

        render = diag.render(None)

        assert len(render) == 3
        edges = [e for e in render if isinstance(e, cdiagram.Edge)]
        assert len(edges) == 1

    def test_add_child_before_parent_raises_error(
        self, model: capellambse.MelodyModel
    ):
        """Test that adding a child box before its parent causes render error."""
        parent = model.by_uuid(TEST_COMP_UUID)
        child = parent.components[0]

        diag = ccd.CustomDiagram(model.project)

        diag.box(child, parent=parent)
        diag.box(parent)

        with pytest.raises(KeyError, match=TEST_COMP_UUID):
            diag.render(None)


class TestEdgeCases:
    """Test edge cases and complex scenarios."""

    def test_deeply_nested_hierarchy(self, model: capellambse.MelodyModel):
        """Test creating a hierarchy with multiple levels of nesting."""
        parent = model.by_uuid(TEST_COMP_UUID)
        assert parent.components

        child = parent.components[0]
        grandchild = child.components[0] if child.components else None

        diag = ccd.CustomDiagram(model.project)
        diag.box(parent)
        diag.box(child, parent=parent)
        if grandchild:
            diag.box(grandchild, parent=child)

        render = diag.render(None)

        parent_box = render[parent.uuid]
        assert isinstance(parent_box, cdiagram.Box)
        assert len(parent_box.children) >= 1

        child_box = render[child.uuid]
        assert isinstance(child_box, cdiagram.Box)

    def test_edge_between_nested_elements(
        self, model: capellambse.MelodyModel
    ):
        """Test creating edges between nested elements."""
        exchange = model.by_uuid(TEST_EXCHANGE_UUID)
        comp1 = exchange.source.owner
        comp2 = exchange.target.owner

        parent = model.by_uuid(TEST_COMP_UUID)

        diag = ccd.CustomDiagram(model.project)
        diag.box(parent)
        diag.box(comp1, parent=parent)
        diag.box(comp2)
        diag.edge(exchange, comp1, comp2)

        render = diag.render(None)

        edge = render[exchange.uuid]
        assert isinstance(edge, cdiagram.Edge)
        assert hasattr(comp1, "uuid")
        assert hasattr(comp2, "uuid")
        assert edge.source is not None
        assert edge.target is not None
        assert edge.source.uuid == comp1.uuid
        assert edge.target.uuid == comp2.uuid

    def test_mixed_port_and_box_edges(self, model: capellambse.MelodyModel):
        """Test edges between boxes, ports, and mixed combinations."""
        exchange1 = model.by_uuid(TEST_EXCHANGE_UUID)
        comp1 = exchange1.source.owner
        comp2 = exchange1.target.owner
        port1 = exchange1.source
        port2 = exchange1.target

        diag = ccd.CustomDiagram(model.project)
        diag.box(comp1)
        diag.port(port1, comp1)
        diag.box(comp2)
        diag.port(port2, comp2)

        diag.edge(exchange1, port1, port2)

        render = diag.render(None)

        assert exchange1.uuid in render
        assert isinstance(render[exchange1.uuid], cdiagram.Edge)

    def test_multiple_ports_on_same_box(self, model: capellambse.MelodyModel):
        """Test adding multiple ports to a single box."""
        component = model.by_uuid(TEST_COMP_UUID)

        ports = (
            list(component.ports)[:5]
            if len(component.ports) >= 5
            else list(component.ports)
        )

        assert len(ports) >= 2

        diag = ccd.CustomDiagram(model.project)
        diag.box(component)

        for port in ports:
            diag.port(port, component)

        render = diag.render(None)

        for port in ports:
            assert port.uuid in render

        comp_box = render[component.uuid]
        assert isinstance(comp_box, cdiagram.Box)

    def test_port_added_in_different_order(
        self, model: capellambse.MelodyModel
    ):
        """Test that ports can be added in any order as long as parent exists."""
        exchange = model.by_uuid(TEST_EXCHANGE_UUID)
        port1 = exchange.source
        port2 = exchange.target
        comp1 = port1.owner
        comp2 = port2.owner

        diag = ccd.CustomDiagram(model.project)

        diag.box(comp1)
        diag.box(comp2)

        diag.port(port2, comp2)
        diag.port(port1, comp1)

        diag.edge(exchange, port1, port2)

        render = diag.render(None)

        assert port1.uuid in render
        assert port2.uuid in render
        assert exchange.uuid in render


class TestIntegration:
    """Test full pipeline integration and rendering."""

    def test_integration_full_render_pipeline(
        self, model: capellambse.MelodyModel
    ):
        """Test complete diagram creation and rendering pipeline."""
        parent = model.by_uuid(TEST_COMP_UUID)
        child = parent.components[0] if parent.components else None
        exchange = model.by_uuid(TEST_EXCHANGE_UUID)
        comp1 = exchange.source.owner
        comp2 = exchange.target.owner
        port1 = exchange.source
        port2 = exchange.target

        diag = ccd.CustomDiagram(parent, styleclass="LAB")

        diag.box(parent)
        if child:
            diag.box(child, parent=parent)
        diag.box(comp1)
        diag.box(comp2)

        diag.port(port1, comp1)
        diag.port(port2, comp2)

        diag.edge(exchange, port1, port2, labels=["Test Exchange"])

        render = diag.render(None)

        assert isinstance(render, cdiagram.Diagram)
        assert len(render) > 0

        assert parent.uuid in render
        if child:
            assert child.uuid in render
        assert comp1.uuid in render
        assert comp2.uuid in render
        assert port1.uuid in render
        assert port2.uuid in render
        assert exchange.uuid in render

        assert isinstance(render[parent.uuid], cdiagram.Box)
        assert isinstance(render[port1.uuid], cdiagram.Box | cdiagram.Circle)
        assert isinstance(render[exchange.uuid], cdiagram.Edge)

        _compare_with_golden_file(render, "full_render_pipeline.json")

    def test_integration_with_styleclass_parameter(
        self, model: capellambse.MelodyModel
    ):
        """Test diagram creation with different styleclass parameters."""
        component = model.by_uuid(TEST_COMP_UUID)

        diag_lab = ccd.CustomDiagram(component, styleclass="LAB")
        diag_lab.box(component)
        render_lab = diag_lab.render(None)
        assert len(render_lab) == 1

        if hasattr(m.DiagramType, "SAB"):
            diag_sab = ccd.CustomDiagram(
                component, styleclass=m.DiagramType.SAB
            )
            diag_sab.box(component)
            render_sab = diag_sab.render(None)
            assert len(render_sab) == 1

        diag_none = ccd.CustomDiagram(component)
        diag_none.box(component)
        render_none = diag_none.render(None)
        assert len(render_none) == 1

        assert diag_lab.uuid == f"{component.uuid}_custom"

        _compare_with_golden_file(render_lab, "with_styleclass_lab.json")

    def test_integration_render_completes_without_elk_errors(
        self, model: capellambse.MelodyModel
    ):
        """Test that rendering completes without ELK layout errors."""
        parent = model.by_uuid(TEST_COMP_UUID)
        exchange = model.by_uuid(TEST_EXCHANGE_UUID)
        comp1 = exchange.source.owner
        comp2 = exchange.target.owner

        diag = ccd.CustomDiagram(parent)
        diag.box(parent)
        diag.box(comp1, parent=parent)
        diag.box(comp2)
        diag.edge(exchange, comp1, comp2)

        render = diag.render(None)
        assert len(render) > 0

        elk_input = diag.elk_input_data({})
        all_ids: set[str] = set()
        _collect_elk_ids(elk_input, all_ids)
        assert len(all_ids) > 0

        _compare_with_golden_file(render, "without_elk_errors.json")


# =============================================================================
# Helper Functions
# =============================================================================


def _compare_with_golden_file(render: cdiagram.Diagram, filename: str) -> None:
    """Compare render output against golden file."""
    golden_path = TEST_ROOT / "custom_diagrams" / filename
    expected: dict[str, t.Any] = json.loads(golden_path.read_text())

    actual: dict[str, dict[str, str]] = {}
    for element in render:
        uuid = str(element.uuid)
        actual[uuid] = {
            "type": type(element).__name__,
            "uuid": uuid,
        }

    assert actual == expected, (
        f"Render output differs from golden file {filename}.\n"
        f"Expected UUIDs: {sorted(expected)}\n"
        f"Actual UUIDs: {sorted(actual)}"
    )


def _collect_elk_ids(obj: t.Any, ids: set[str]) -> None:
    """Recursively collect all IDs from ELK input data."""
    if hasattr(obj, "id"):
        obj_id = obj.id
        if obj_id:
            if obj_id in ids:
                raise ValueError(f"Duplicate ELK ID found: {obj_id}")
            ids.add(obj_id)

    if hasattr(obj, "children"):
        for child in obj.children:
            _collect_elk_ids(child, ids)

    if hasattr(obj, "edges"):
        for edge in obj.edges:
            _collect_elk_ids(edge, ids)

    if hasattr(obj, "ports"):
        for port in obj.ports:
            _collect_elk_ids(port, ids)
