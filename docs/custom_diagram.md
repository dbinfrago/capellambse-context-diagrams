<!--
 ~ SPDX-FileCopyrightText: Copyright DB InfraGO AG and the capellambse-context-diagrams contributors
 ~ SPDX-License-Identifier: Apache-2.0
 -->

# Custom Diagrams

There are two main ways of customizing diagram contents.

## Procedural custom diagrams

The procedural API provides a simple interface for specifying the elements and
their basic relationships:

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

### Adding Elements

#### Element Addition Rules

When building a custom diagram, follow these important rules:

**Order Constraints:**

- Parent boxes must be added before their child boxes
- Owner boxes must be added before their ports
- Source and target elements (boxes or ports) must be added before edges connecting them

**Duplicate Handling:**

- Adding the same box twice will log a warning and ignore the second addition
- Adding the same port twice will log a warning and ignore the second addition
- Adding the same edge twice will log a warning and ignore the duplicate
- Element duplicates are detected by UUID - each UUID can only appear once in the diagram

**Example of correct order:**

```py
# ✓ Correct: parent first, then child
diag.box(parent)
diag.box(child, parent=parent)

# ✗ Incorrect: this will raise ValueError
diag.box(child, parent=parent)  # parent doesn't exist yet!
diag.box(parent)

# ✓ Correct: owner box first, then port
diag.box(component)
diag.port(port, parent=component)

# ✗ Incorrect: this will raise ValueError
diag.port(port, parent=component)  # component doesn't exist yet!
diag.box(component)
```

#### Building the Diagram

**Boxes** represent components, functions, or other model elements that appear
as rectangles in the diagram:

```py
diag.box(element)
```

Boxes can be nested by providing the optional `parent=` argument. Note that
parents must always be added before their children:

```py
diag.box(child_element, parent=parent_element)
```

**Ports** are attachment points on the sides of boxes. They may be used to
connect edges to specific sides of a box.

Like before, the parent box must be added first.

```py
diag.box(box_element)
diag.port(port_element, parent=box_element)
```

**Edges** connect boxes or ports together:

```py
diag.edge(exchange_element, source=source_port, target=target_port)
# Edges don't necessarily require ports:
diag.edge(exchange_element, source=source_element, target=target_element)
# You can also mix and match boxes and ports:
diag.edge(exchange_element, source=source_box, target=target_port)
```

You can optionally add custom labels to edges:

```py
diag.edge(
    exchange_element,
    source_port,
    target_port,
    labels=["Label 1", "Label 2"],
)
```

### Rendering and Saving

Once you've built your diagram, render it to visualize the result:

```py
# Render returns a dictionary mapping UUIDs to diagram elements
elements = diag.render(None)

# The dictionary maps element UUIDs (str) to diagram objects:
# - capellambse.diagram.Box for boxes and ports
# - capellambse.diagram.Edge for edges
# - capellambse.diagram.Circle for certain element types

# Save to SVG format
diag.render("svgdiagram").save(pretty=True)

# Or render to other formats supported by capellambse
svg_output = diag.render("svg")
```

**Common Styleclass Values:**

The `styleclass` parameter controls the visual styling (colors, icons) of diagram elements. It accepts:

- `"OAB"` or `"Operational Architecture Blank"` - For operational entities and activities
- `"SAB"` or `"System Architecture Blank"` - For system components and functions
- `"LAB"` or `"Logical Architecture Blank"` - For logical components and functions (used in example above)
- `"PAB"` or `"Physical Architecture Blank"` - For physical components
- `"CDB"` or `"Class Diagram Blank"` - For class diagrams
- Or use `capellambse.model.DiagramType` enum members directly

If not specified, an empty styleclass is used with default styling.

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
