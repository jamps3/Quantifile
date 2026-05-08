def treemap(nodes, x, y, w, h):
    total = sum(n.size for n in nodes)

    if total <= 0 or not nodes:
        return []

    result = []
    _squarify(nodes, x, y, w, h, total, result)
    return result


def _squarify(nodes, x, y, w, h, total, result):
    """Squarified treemap layout algorithm.
    Recursively places nodes to minimize worst-case aspect ratio.
    """
    if not nodes:
        return

    if w <= 0 or h <= 0:
        return

    # For very small areas or single node, just fill
    if len(nodes) == 1:
        result.append((nodes[0], x, y, w, h))
        return

    # Decide primary axis: use the longer side for rows/columns
    vertical = h > w  # If height > width, lay out in columns (vertical)

    # Find the row of nodes that best fits the available space
    row, rest = _pick_row(nodes, total, w if not vertical else h)

    if not row:
        # Fallback: treat first node as row
        row = [nodes[0]]
        rest = nodes[1:]

    row_total = sum(n.size for n in row)

    if vertical:
        # Lay out row as a column (fixed width, split height)
        row_height = max(1, h * row_total / total)
        row_height = min(row_height, h)

        current_y = y
        for node in row:
            node_h = max(1, row_height * node.size / row_total) if row_total > 0 else 1
            if node_h < 1:
                node_h = 1
            # Ensure we don't exceed remaining height
            if current_y + node_h > y + h:
                node_h = max(1, y + h - current_y)
            result.append((node, x, current_y, w, node_h))
            current_y += node_h

        # Remaining space for rest
        remaining_h = max(0, h - (current_y - y))
        if rest and remaining_h > 1:
            _squarify(rest, x, current_y, w, remaining_h,
                     total - row_total, result)
    else:
        # Lay out row as a row (fixed height, split width)
        row_width = max(1, w * row_total / total)
        row_width = min(row_width, w)

        current_x = x
        for node in row:
            node_w = max(1, row_width * node.size / row_total) if row_total > 0 else 1
            if node_w < 1:
                node_w = 1
            # Ensure we don't exceed remaining width
            if current_x + node_w > x + w:
                node_w = max(1, x + w - current_x)
            result.append((node, current_x, y, node_w, h))
            current_x += node_w

        # Remaining space for rest
        remaining_w = max(0, w - (current_x - x))
        if rest and remaining_w > 1:
            _squarify(rest, current_x, y, remaining_w, h,
                     total - row_total, result)


def _pick_row(nodes, total, space_len):
    """Select a row of nodes that minimizes the worst-case aspect ratio.
    Returns (row_nodes, remaining_nodes).
    """
    if not nodes:
        return [], []

    # For very small sets, take first few
    if len(nodes) <= 3:
        return nodes[:1], nodes[1:]

    best_row = []
    best_worst_ratio = float('inf')
    best_remainder = []

    # Try different row sizes, find best worst-case aspect ratio
    for i in range(1, min(len(nodes) + 1, 20)):  # Cap at 20 for performance
        row = nodes[:i]
        remain = nodes[i:]
        row_sum = sum(n.size for n in row)
        rest_sum = total - row_sum

        if row_sum <= 0:
            break

        # Calculate aspect ratios for this row
        # Space fraction for this row: row_sum / total
        row_space = space_len * row_sum / total

        # Worst aspect ratio in the row
        worst_ratio = 0
        for node in row:
            if node.size <= 0:
                continue
            node_space = row_space * node.size / row_sum
            if row_space > 0 and node_space > 0:
                # Aspect ratio: max(w,h) / min(w,h)
                ratio = max(row_space, node_space) / min(row_space, node_space)
                worst_ratio = max(worst_ratio, ratio)

        # Also consider the remainder would get squished too small
        if remain and rest_sum > 0:
            remain_space = space_len * rest_sum / total
            if remain_space < space_len * 0.01:  # Less than 1% of space
                # Penalize tiny remainders
                worst_ratio *= 3

        # Better if worst ratio is smaller
        if worst_ratio < best_worst_ratio:
            best_worst_ratio = worst_ratio
            best_row = row
            best_remainder = remain

    return best_row, best_remainder
