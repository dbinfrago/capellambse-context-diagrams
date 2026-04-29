# SPDX-FileCopyrightText: Copyright DB InfraGO AG and the capellambse-context-diagrams contributors
# SPDX-License-Identifier: Apache-2.0

import typing as t

import capellambse
import pytest
from capellambse import diagram

from capellambse_context_diagrams import filters

from .conftest import (  # type: ignore[import-not-found]
    TEST_ELK_INPUT_ROOT,
    TEST_ELK_LAYOUT_ROOT,
    compare_elk_input_data,
    generic_collecting_test,
    generic_layouting_test,
    generic_serializing_test,
)

TEST_FNC_CHAIN_UUID = "ec1ecf8b-d58b-4468-9742-6fdfd6cff702"
TEST_OA_PROCESS_UUID = "bec38a21-cc4b-4c06-8acf-067bd5f44824"
TEST_LOCAL_EX_ITEMS_INVOLVEMENT_UUID = "ebacf052-fe7c-492f-9564-679c0d835bce"
TEST_CONTEXT_SET = [
    pytest.param(
        (TEST_FNC_CHAIN_UUID, "functional_chain_context_diagram.json", {}),
        id="FunctionalChain",
    ),
    pytest.param(
        (
            TEST_FNC_CHAIN_UUID,
            "functional_chain_no_parent_relation_context_diagram.json",
            {"display_parent_relation": False},
        ),
        id="FunctionalChain with hidden owners",
    ),
    pytest.param(
        (
            TEST_FNC_CHAIN_UUID,
            "functional_chain_collect_from_involvements_context_diagram.json",
            {"collect_from_involvements": True},
        ),
        id="FunctionalChain from involvements",
    ),
    pytest.param(
        (TEST_OA_PROCESS_UUID, "operational_process_context_diagram.json", {}),
        id="OperationalProcess",
    ),
    pytest.param(
        (
            TEST_OA_PROCESS_UUID,
            "operational_process_no_parent_relation_context_diagram.json",
            {"display_parent_relation": False},
        ),
        id="OperationalProcess with hidden owners",
    ),
]

TEST_CONTEXT_DATA_ROOT = TEST_ELK_INPUT_ROOT / "functional_chain_diagrams"
TEST_CONTEXT_LAYOUT_ROOT = TEST_ELK_LAYOUT_ROOT / "functional_chain_diagrams"


class TestContextDiagrams:
    @staticmethod
    @pytest.mark.parametrize("params", TEST_CONTEXT_SET)
    def test_collecting(
        model: capellambse.MelodyModel,
        params: tuple[str, str, dict[str, t.Any]],
    ):
        result, expected = generic_collecting_test(
            model, params, TEST_CONTEXT_DATA_ROOT, "context_diagram"
        )

        compare_elk_input_data(result, expected)

    @staticmethod
    @pytest.mark.parametrize("params", TEST_CONTEXT_SET)
    def test_layouting(params: tuple[str, str, dict[str, t.Any]]):
        generic_layouting_test(
            params, TEST_CONTEXT_DATA_ROOT, TEST_CONTEXT_LAYOUT_ROOT
        )

    @staticmethod
    @pytest.mark.parametrize("params", TEST_CONTEXT_SET)
    def test_serializing(
        model: capellambse.MelodyModel,
        params: tuple[str, str, dict[str, t.Any]],
    ):
        generic_serializing_test(
            model, params, TEST_CONTEXT_LAYOUT_ROOT, "context_diagram"
        )

    @staticmethod
    def test_collect_from_involvements_show_ex_items_uses_local_items(
        model: capellambse.MelodyModel,
    ):
        diag = model.by_uuid(TEST_FNC_CHAIN_UUID).context_diagram
        diag.filters.add(filters.SHOW_EX_ITEMS)

        rendered = diag.render(None, collect_from_involvements=True)
        edge = rendered[TEST_LOCAL_EX_ITEMS_INVOLVEMENT_UUID]

        assert isinstance(edge, diagram.Edge)
        assert len(edge.labels) == 1
        assert edge.labels[0].label == "[Water]"
