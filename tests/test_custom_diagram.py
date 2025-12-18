# SPDX-FileCopyrightText: Copyright DB InfraGO AG and the capellambse-context-diagrams contributors
# SPDX-License-Identifier: Apache-2.0

"""Tests for the declarative CustomDiagram API."""

import capellambse
import capellambse.diagram as cdiagram
import capellambse.metamodel as mm

import capellambse_context_diagrams as ccd


def test_create_empty_diagram(model: capellambse.MelodyModel):
    diag = ccd.CustomDiagram(model.project)

    render = diag.render(None)

    assert len(render) == 0


def test_add_single_element(model: capellambse.MelodyModel):
    component = model.by_uuid("0d2edb8f-fa34-4e73-89ec-fb9a63001440")

    diag = ccd.CustomDiagram(component)
    diag.box(component)
    render = diag.render(None)

    assert len(render) == 1
    assert "0d2edb8f-fa34-4e73-89ec-fb9a63001440" in render
    assert isinstance(
        render["0d2edb8f-fa34-4e73-89ec-fb9a63001440"], cdiagram.Box
    )


def test_add_nested_elements(model: capellambse.MelodyModel):
    parent = model.by_uuid("0d2edb8f-fa34-4e73-89ec-fb9a63001440")
    child = parent.components[0]

    diag = ccd.CustomDiagram(parent)
    diag.box(parent)
    diag.box(child, parent=parent)
    render = diag.render(None)

    assert len(render) == 2
    pbox = render[parent.uuid]
    assert isinstance(pbox, cdiagram.Box)
    assert len(pbox.children) == 1


def test_duplicate_elements_are_not_added(model: capellambse.MelodyModel):
    component = model.by_uuid("0d2edb8f-fa34-4e73-89ec-fb9a63001440")

    diag = ccd.CustomDiagram(component)
    diag.box(component)
    diag.box(component)
    render = diag.render(None)

    assert len(render) == 1


def test_add_portless_edge(model: capellambse.MelodyModel):
    exchange = model.by_uuid("a900a6e0-c994-42e8-ae94-2b61a7fabc18")
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


def test_add_port_based_edge(model: capellambse.MelodyModel):
    exchange = model.by_uuid("a900a6e0-c994-42e8-ae94-2b61a7fabc18")
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
