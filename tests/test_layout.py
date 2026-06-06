from layout import _pick_row, _squarify, treemap
from models import Node


def sized_node(name, size):
    node = Node(name, False)
    node.size = size
    return node


def test_treemap_returns_empty_for_empty_or_zero_total():
    assert treemap([], 0, 0, 100, 100) == []
    assert treemap([sized_node("zero", 0)], 0, 0, 100, 100) == []


def test_treemap_single_node_fills_available_space():
    node = sized_node("only", 10)

    assert treemap([node], 1, 2, 30, 40) == [(node, 1, 2, 30, 40)]


def test_treemap_lays_out_horizontal_rows():
    first = sized_node("first", 3)
    second = sized_node("second", 1)

    result = treemap([first, second], 0, 0, 40, 20)

    assert result == [(first, 0, 0, 30.0, 20), (second, 30.0, 0, 10.0, 20)]


def test_treemap_lays_out_vertical_columns():
    first = sized_node("first", 3)
    second = sized_node("second", 1)

    result = treemap([first, second], 0, 0, 20, 40)

    assert result == [(first, 0, 0, 20, 30.0), (second, 0, 30.0, 20, 10.0)]


def test_treemap_ignores_non_positive_dimensions():
    result = []

    _squarify([], 0, 0, 10, 10, 1, result)
    _squarify([sized_node("bad", 1)], 0, 0, 0, 10, 1, result)
    _squarify([sized_node("bad", 1)], 0, 0, 10, 0, 1, result)

    assert result == []


def test_pick_row_handles_empty_short_and_zero_rows():
    assert _pick_row([], 10, 100) == ([], [])

    short_nodes = [sized_node("a", 1), sized_node("b", 2), sized_node("c", 3)]
    assert _pick_row(short_nodes, 6, 100) == ([short_nodes[0]], short_nodes[1:])

    zero = sized_node("zero", 0)
    one = sized_node("one", 1)
    assert _pick_row([zero, one], 1, 100) == ([zero], [one])


def test_pick_row_chooses_best_row_for_larger_inputs():
    nodes = [sized_node(str(index), size) for index, size in enumerate([6, 4, 3, 2])]

    row, rest = _pick_row(nodes, 15, 100)

    assert row
    assert row + rest == nodes


def test_pick_row_breaks_when_larger_input_starts_with_zero_size():
    nodes = [sized_node("zero", 0), sized_node("one", 1), sized_node("two", 2), sized_node("three", 3)]

    assert _pick_row(nodes, 6, 100) == ([], [])


def test_pick_row_penalizes_tiny_remainders():
    nodes = [sized_node(str(index), size) for index, size in enumerate([1000, 1, 1, 1])]

    row, rest = _pick_row(nodes, 1003, 100)

    assert row + rest == nodes
    assert rest


def test_pick_row_skips_zero_sized_nodes_inside_candidate_row():
    nodes = [sized_node("one", 1), sized_node("zero", 0), sized_node("two", 2), sized_node("three", 3)]

    row, rest = _pick_row(nodes, 6, 100)

    assert row + rest == nodes


def test_squarify_fallback_when_pick_row_returns_empty(monkeypatch):
    node = sized_node("fallback", 5)
    result = []

    monkeypatch.setattr("layout._pick_row", lambda nodes, total, space_len: ([], []))
    _squarify([node, sized_node("unused", 1)], 0, 0, 10, 10, 6, result)

    assert result[0] == (node, 0, 0, 8.333333333333334, 10)


def test_squarify_clamps_items_to_remaining_space(monkeypatch):
    first = sized_node("first", 1)
    second = sized_node("second", 1)
    result = []

    monkeypatch.setattr("layout._pick_row", lambda nodes, total, space_len: ([first, second], []))

    _squarify([first, second], 0, 0, 1.5, 1, 2, result)
    assert result[-1] == (second, 1, 0, 1, 1)

    result.clear()
    _squarify([first, second], 0, 0, 1, 1.5, 2, result)
    assert result[-1] == (second, 0, 1, 1, 1)
