# SPDX-FileCopyrightText: Copyright DB InfraGO AG and the capellambse-context-diagrams contributors
# SPDX-License-Identifier: Apache-2.0

import capellambse
import pytest

from capellambse_context_diagrams.builders import _makers


@pytest.mark.parametrize(
    ("uuid", "expected_labels"),
    [
        pytest.param(
            "d817767f-68b7-49a5-aa47-13419d41df0a",
            [
                "Really long label that needs",
                "wrapping else its parent box is",
                "also very long!",
            ],
            id="LogicalFunction",
        ),
    ],
)
def test_make_label_wraps_long_label(
    model: capellambse.MelodyModel, uuid: str, expected_labels: list[list[str]]
):
    obj = model.by_uuid(uuid)

    labels = _makers.make_label(obj.name, max_width=_makers.MAX_LABEL_WIDTH)

    actual = [label.text for label in labels]
    assert actual == expected_labels


def test_make_owner_box_accepts_default_child_id(
    model: capellambse.MelodyModel,
):
    obj = model.by_uuid("d817767f-68b7-49a5-aa47-13419d41df0a")
    boxes = {obj.uuid: _makers.make_box(obj)}
    boxes_to_delete: set[str] = set()

    def make_box(obj, **kwargs):
        box = _makers.make_box(obj, **kwargs)
        boxes[obj.uuid] = box
        return box

    owner = _makers.make_owner_box(
        obj,
        make_box,
        boxes,
        boxes_to_delete,
    )

    assert owner == obj.owner
    assert boxes_to_delete == {obj.uuid}
    assert boxes[obj.uuid] in boxes[obj.owner.uuid].children


def test_move_box_into_owner_accepts_synthetic_box_id(
    model: capellambse.MelodyModel,
):
    obj = model.by_uuid("d817767f-68b7-49a5-aa47-13419d41df0a")
    child_id = f"__{obj._get_styleclass()}:{obj.uuid}"
    boxes = {obj.uuid: _makers.make_box(obj)}
    boxes[obj.uuid].id = child_id
    boxes_to_delete: set[str] = set()

    def make_box(obj, **kwargs):
        box = _makers.make_box(obj, **kwargs)
        boxes[obj.uuid] = box
        return box

    owner = _makers.move_box_into_owner(
        obj,
        boxes[obj.uuid],
        obj.uuid,
        make_box,
        boxes_to_delete,
    )

    assert owner == obj.owner
    assert boxes_to_delete == {obj.uuid}
    assert boxes[obj.uuid] in boxes[obj.owner.uuid].children
