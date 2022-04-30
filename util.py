def merge_intervals(ranges: list[tuple[int, int]]):
    if ranges is None or len(ranges) == 0:
        return None

    result = [(ranges[0][0], ranges[0][1])]

    for i in range(1, len(ranges)):
        x1 = ranges[i][0]
        y1 = ranges[i][1]
        x2 = result[len(result) - 1][0]
        y2 = result[len(result) - 1][1]

        if y2 >= x1:
            result[len(result) - 1] = (result[len(result) - 1][0], max(y1, y2))
        else:
            result.append((x1, y1))

    return result
