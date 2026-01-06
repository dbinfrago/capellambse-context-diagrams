<!--
 ~ SPDX-FileCopyrightText: Copyright DB InfraGO AG and the capellambse-context-diagrams contributors
 ~ SPDX-License-Identifier: Apache-2.0
 -->

# Custom Diagrams

There are two main ways of customizing diagram contents:

1. **Procedural API** - Explicitly specify boxes, ports, edges, and their relationships
2. **Custom collector function** - Override automatic content collection with custom logic

## Procedural custom diagrams

The procedural API provides a simple, declarative interface for building custom
diagrams. You explicitly specify:

- Which elements appear as boxes, ports and edges
- How boxes nest inside each other
- How edges connect the elements

The layout is then automatically computed using the ELK (Eclipse Layout Kernel)
algorithm.

<figure>
  <img src="../assets/images/CustomDiagram of Logical Architecture (853cb005-cba0-489b-8fe3-bb694ad4543b_custom).svg">
  <figcaption>CustomDiagram of Logical Architecture</figcaption>
</figure>

??? example "Code for the diagram above"

    ```py
    import capellambse
    import capellambse_context_diagrams as ccd

    model = capellambse.MelodyModel("tests/data/ContextDiagram.aird")

    lc_1 = model.by_uuid("f632888e-51bc-4c9f-8e81-73e9404de784")  # Logical Component 1
    lc_2 = model.by_uuid("8bcb11e6-443b-4b92-bec2-ff1d87a224e7")  # Logical Component 2
    lc_3 = model.by_uuid("8d89e6f5-38e3-4bba-bdac-01e6cbf8dc93")  # Logical Component 3

    cp_out = model.by_uuid("3ef23099-ce9a-4f7d-812f-935f47e7938d")  # ComponentPort OUT
    cp_in = model.by_uuid("dc30be45-caa9-4acd-a85c-82f9e23c617b")   # ComponentPort IN
    cex = model.by_uuid("beaa5eb3-1b8f-49d2-8dfe-4b1c50b67f98")    # ComponentExchange 1

    # Create the custom diagram with LAB styleclass for Logical Architecture styling
    # The target (lc_1) determines the diagram context and default styling scope
    diag = ccd.CustomDiagram(lc_1, styleclass="LAB")

    # Add boxes for the logical components
    diag.box(lc_1)
    diag.box(lc_2)
    diag.box(lc_3)

    # Add ports to the boxes
    diag.port(cp_out, parent=lc_1)
    diag.port(cp_in, parent=lc_2)

    # Add an edge connecting the ports
    diag.edge(cex, source=cp_out, target=cp_in, labels=["Component Exchange 1"])

    # Render and save the diagram
    diag.save("svgdiagram").save(pretty=True)
    ```

### Creating a Custom Diagram

To create a custom diagram, instantiate `CustomDiagram` with a target model
element:

```py
import capellambse_context_diagrams as ccd

diag = ccd.CustomDiagram(target_element)
```

The `target` parameter can be any model element. It's recommended to use either
one of the elements that will be visible in the diagram, or a common ancestor
of all visible elements. If you don't have a specific element, you can use
`model.project` as a fallback, which is the common ancestor of all model
elements.

Optionally, you can specify a `styleclass` to define the basic styles (colors,
icons, etc.) of visible objects. This can be a
[DiagramType](https://dbinfrago.github.io/py-capellambse/code/capellambse.model.html#capellambse.model.diagram.DiagramType)
instance, or the name or value of one of its members:

```py
# These three are equivalent:
diag = ccd.CustomDiagram(target_element, styleclass=m.DiagramType.LAB)
diag = ccd.CustomDiagram(target_element, styleclass="LAB")
diag = ccd.CustomDiagram(target_element, styleclass="Logical Architecture Blank")
```

It accepts:

- `"OAB"` or `"Operational Architecture Blank"` - For operational entities and activities
- `"SAB"` or `"System Architecture Blank"` - For system components and functions
- `"LAB"` or `"Logical Architecture Blank"` - For logical components and functions (used in example above)
- `"PAB"` or `"Physical Architecture Blank"` - For physical components
- `"CDB"` or `"Class Diagram Blank"` - For class diagrams
- Or use `capellambse.model.DiagramType` enum members directly

If not specified, an empty styleclass is used with default styling.

### Building the Diagram

Custom diagrams are built by adding elements in a specific order. Understanding
the ordering constraints is essential for successful diagram construction.

!!! important "Element Ordering Rules"
    - **Parent before child**: Parent boxes must be added before their nested children
    - **Owner before port**: Boxes must be added before their ports
    - **Endpoints before edge**: Source and target elements must exist before connecting them with edges

    Attempting to add an element that references a non-existent parent, owner, or endpoint will result in an error.

!!! note "Duplicate Handling"
    Elements are identified by their UUID. Adding the same element multiple times will be ignored.

#### Boxes

**Boxes** represent components, functions, or other model elements that appear
as rectangles in the diagram:

```py
diag.box(element)
```

Boxes can be nested by providing the optional `parent=` argument to create
hierarchical structures:

```py
# Add parent first
diag.box(parent_element)
# Then add children
diag.box(child_element, parent=parent_element)
```

#### Ports

**Ports** are attachment points on the sides of boxes that allow edges to
connect to specific locations. The parent box must be added before its ports:

```py
# Add the box first
diag.box(box_element)
# Then add its port
diag.port(port_element, parent=box_element)
```

#### Edges

**Edges** connect boxes or ports together. Both the source and target must be
added to the diagram before creating the edge:

```py
# Connect two ports
diag.edge(exchange_element, source=source_port, target=target_port)

# Connect boxes directly (edges don't require ports)
diag.edge(exchange_element, source=source_element, target=target_element)

# Mix boxes and ports
diag.edge(exchange_element, source=source_box, target=target_port)
```

You can optionally add custom labels to edges:

```py
diag.edge(
    exchange_element,
    source=source_port,
    target=target_port,
    labels=["Label 1", "Label 2"],
)
```

### Rendering and Saving

Once you've built your diagram, render it to visualize the result.

The `render()` method accepts a format string and returns the diagram in that
format. When called with `None`, it returns a
[`capellambse.diagram.Diagram`][capellambse.diagram.Diagram]
object for programmatic access:

```py
# Get the Diagram object
diagram = diag.render(None)
```

For most use cases, render directly to a specific format:

```py
# Save to SVG file
diag.render("svgdiagram").save(pretty=True)

# Or get the SVG as a string
svg_output = diag.render("svg")

# Other formats supported by capellambse
png_output = diag.render("png")
```

## Custom collector function

Another option involves writing a custom collector function, which `yield`s the
elements that should be visible in the diagram, thus overriding the
automatically collected contents.

??? example "Custom Diagram of `PP 1 `"

    ``` py
    import capellambse

    def _collector(
        target: m.ModelElement,
    ) -> cabc.Iterator[m.ModelElement]:
        visited = set()
        def collector(
            target: m.ModelElement,
        ) -> cabc.Iterator[m.ModelElement]:
            if target.uuid in visited:
                return
            visited.add(target.uuid)
            for link in target.links:
                yield link
                yield from collector(link.source)
                yield from collector(link.target)
        yield from collector(target)

    model = capellambse.MelodyModel("tests/data/ContextDiagram.aird")
    obj = model.by_uuid("c403d4f4-9633-42a2-a5d6-9e1df2655146")
    diag = obj.context_diagram
    diag.render("svgdiagram", collect=_collector(obj)).save(pretty=True)
    ```
    <figure markdown>
        <img src="../assets/images/PhysicalPortContextDiagram of PP 1.svg" width="1000000">
        <figcaption>PhysicalPortContextDiagram of PP 1 [PAB]</figcaption>
    </figure>

You can find more examples of collectors in the
[`collectors`][capellambse_context_diagrams.collectors]

### Check out the code

To understand the collection have a look into the
[`builders`][capellambse_context_diagrams.builders]
module.
