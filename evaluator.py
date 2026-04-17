from __future__ import annotations

import math
import subprocess
import sys
from collections import deque
from dataclasses import dataclass


ROWS = 20
COLS = 20
DIRS = {
    "W": (-1, 0),
    "A": (0, -1),
    "S": (1, 0),
    "D": (0, 1),
}
OPPOSITE = {
    "W": "S",
    "S": "W",
    "A": "D",
    "D": "A",
}


@dataclass
class Case:
    name: str
    n_value: int
    obstacle_cells: set[tuple[int, int]]
    initial_snake: list[tuple[int, int]]
    initial_food: tuple[int, int]
    food_sequence: list[tuple[int, int]]
    max_turns: int


def empty_map() -> list[list[str]]:
    grid = [["." for _ in range(COLS)] for _ in range(ROWS)]
    for row in range(ROWS):
        grid[row][0] = "#"
        grid[row][COLS - 1] = "#"
    for col in range(COLS):
        grid[0][col] = "#"
        grid[ROWS - 1][col] = "#"
    return grid


def build_lines(*segments: tuple[int, int, int, int]) -> set[tuple[int, int]]:
    cells: set[tuple[int, int]] = set()
    for r1, c1, r2, c2 in segments:
        if r1 == r2:
            start, end = sorted((c1, c2))
            for col in range(start, end + 1):
                cells.add((r1, col))
        elif c1 == c2:
            start, end = sorted((r1, r2))
            for row in range(start, end + 1):
                cells.add((row, c1))
        else:
            raise ValueError("only axis-aligned segments are supported")
    return cells


def sweep_foods(start_row: int, end_row: int, left: int, right: int) -> list[tuple[int, int]]:
    foods: list[tuple[int, int]] = []
    for row in range(start_row, end_row + 1):
        columns = range(left, right + 1) if row % 2 == 0 else range(right, left - 1, -1)
        for col in columns:
            foods.append((row, col))
    return foods


def filter_foods(
    foods: list[tuple[int, int]],
    blocked: set[tuple[int, int]],
    snake: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    snake_cells = set(snake)
    return [food for food in foods if food not in blocked and food not in snake_cells]


def ring_foods(top: int, left: int, bottom: int, right: int) -> list[tuple[int, int]]:
    foods: list[tuple[int, int]] = []
    for col in range(left, right + 1):
        foods.append((top, col))
    for row in range(top + 1, bottom + 1):
        foods.append((row, right))
    for col in range(right - 1, left - 1, -1):
        foods.append((bottom, col))
    for row in range(bottom - 1, top, -1):
        foods.append((row, left))
    return foods


def case_definitions() -> list[Case]:
    base_snake = [(10, 10), (11, 10), (12, 10)]

    cases: list[Case] = []

    foods = filter_foods(sweep_foods(2, 6, 2, 17), set(), base_snake)
    cases.append(
        Case(
            name="open-field-fast-growth",
            n_value=1,
            obstacle_cells=set(),
            initial_snake=base_snake,
            initial_food=foods[0],
            food_sequence=foods[1:21],
            max_turns=240,
        )
    )

    obstacles = build_lines((4, 4, 4, 15), (4, 15, 15, 15), (15, 4, 15, 15), (8, 8, 15, 8))
    foods = filter_foods(ring_foods(2, 2, 17, 17), obstacles, base_snake)
    cases.append(
        Case(
            name="outer-ring-detour",
            n_value=2,
            obstacle_cells=obstacles,
            initial_snake=base_snake,
            initial_food=foods[0],
            food_sequence=foods[1:21],
            max_turns=260,
        )
    )

    obstacles = build_lines((3, 6, 16, 6), (3, 13, 16, 13), (9, 6, 9, 13))
    foods = filter_foods(sweep_foods(2, 17, 2, 17), obstacles, base_snake)
    cases.append(
        Case(
            name="three-lane-maze",
            n_value=4,
            obstacle_cells=obstacles,
            initial_snake=base_snake,
            initial_food=foods[20],
            food_sequence=foods[21:41],
            max_turns=320,
        )
    )

    obstacles = build_lines(
        (2, 5, 14, 5),
        (5, 9, 17, 9),
        (2, 13, 14, 13),
        (6, 5, 6, 8),
        (10, 9, 10, 12),
        (14, 13, 14, 16),
    )
    foods = filter_foods(sweep_foods(2, 17, 2, 17), obstacles, base_snake)
    cases.append(
        Case(
            name="stair-corridors",
            n_value=8,
            obstacle_cells=obstacles,
            initial_snake=base_snake,
            initial_food=foods[8],
            food_sequence=foods[9:29],
            max_turns=360,
        )
    )

    obstacles = build_lines(
        (3, 3, 3, 16),
        (3, 3, 16, 3),
        (16, 3, 16, 16),
        (3, 16, 12, 16),
        (7, 7, 7, 16),
        (7, 7, 14, 7),
        (14, 7, 14, 14),
    )
    foods = filter_foods(ring_foods(4, 4, 15, 15) + ring_foods(8, 8, 13, 13), obstacles, base_snake)
    cases.append(
        Case(
            name="nested-u-turns",
            n_value=16,
            obstacle_cells=obstacles,
            initial_snake=base_snake,
            initial_food=foods[3],
            food_sequence=foods[4:24],
            max_turns=380,
        )
    )

    obstacles = build_lines(
        (2, 4, 17, 4),
        (2, 8, 17, 8),
        (2, 12, 17, 12),
        (2, 16, 17, 16),
        (5, 4, 5, 7),
        (9, 8, 9, 11),
        (13, 12, 13, 15),
    )
    foods = filter_foods(sweep_foods(2, 17, 2, 17), obstacles, base_snake)
    cases.append(
        Case(
            name="column-gates",
            n_value=32,
            obstacle_cells=obstacles,
            initial_snake=base_snake,
            initial_food=foods[30],
            food_sequence=foods[31:51],
            max_turns=420,
        )
    )

    obstacles = build_lines(
        (4, 4, 4, 15),
        (4, 15, 15, 15),
        (15, 4, 15, 15),
        (4, 4, 15, 4),
        (6, 6, 6, 13),
        (6, 13, 13, 13),
        (13, 6, 13, 13),
        (6, 6, 13, 6),
    )
    foods = filter_foods(ring_foods(5, 5, 14, 14) + ring_foods(7, 7, 12, 12), obstacles, base_snake)
    cases.append(
        Case(
            name="double-ring",
            n_value=64,
            obstacle_cells=obstacles,
            initial_snake=base_snake,
            initial_food=foods[0],
            food_sequence=foods[1:21],
            max_turns=420,
        )
    )

    snake = [(8, 8), (8, 7), (8, 6)]
    obstacles = build_lines((5, 5, 5, 14), (5, 14, 14, 14), (14, 5, 14, 14), (9, 5, 9, 12), (10, 7, 14, 7))
    foods = filter_foods(sweep_foods(6, 13, 6, 13), obstacles, snake)
    cases.append(
        Case(
            name="tail-follow-recovery",
            n_value=128,
            obstacle_cells=obstacles,
            initial_snake=snake,
            initial_food=foods[10],
            food_sequence=foods[11:31],
            max_turns=440,
        )
    )

    snake = [(10, 9), (10, 8), (10, 7)]
    obstacles = build_lines((6, 6, 6, 13), (6, 13, 13, 13), (13, 6, 13, 13), (8, 6, 8, 11), (11, 8, 13, 8))
    foods = [(9, 11), (10, 11), (11, 11), (12, 11), (12, 10), (12, 9), (11, 9), (10, 9), (9, 9), (9, 10)]
    foods = filter_foods(foods + sweep_foods(7, 12, 7, 12), obstacles, snake)
    cases.append(
        Case(
            name="growth-tail-conflict",
            n_value=256,
            obstacle_cells=obstacles,
            initial_snake=snake,
            initial_food=foods[0],
            food_sequence=foods[1:16],
            max_turns=260,
        )
    )

    snake = [(15, 10), (16, 10), (17, 10)]
    obstacles = build_lines(
        (2, 3, 17, 3),
        (2, 6, 17, 6),
        (2, 9, 17, 9),
        (2, 12, 17, 12),
        (2, 15, 17, 15),
        (4, 3, 4, 5),
        (7, 6, 7, 8),
        (10, 9, 10, 11),
        (13, 12, 13, 14),
    )
    foods = filter_foods(sweep_foods(2, 17, 2, 17), obstacles, snake)
    cases.append(
        Case(
            name="late-weight-navigation",
            n_value=512,
            obstacle_cells=obstacles,
            initial_snake=snake,
            initial_food=foods[18],
            food_sequence=foods[19:39],
            max_turns=480,
        )
    )

    return cases


def render_map(case: Case, snake: list[tuple[int, int]], food: tuple[int, int] | None) -> list[str]:
    grid = empty_map()
    for row, col in case.obstacle_cells:
        grid[row][col] = "O"
    for index, (row, col) in enumerate(snake):
        grid[row][col] = "H" if index == 0 else "B"
    if food is not None:
        row, col = food
        grid[row][col] = "F"
    return ["".join(line) for line in grid]


def parse_program_map(lines: list[str]) -> list[str]:
    return [line.rstrip("\r\n") for line in lines]


def run_case(executable: str, case: Case) -> dict[str, object]:
    snake = deque(case.initial_snake)
    current_food = case.initial_food
    pending_foods = deque(case.food_sequence)
    score = 0
    turns = 0
    growth_counter = 0
    previous_direction = "W"
    protocol_errors: list[str] = []

    process = subprocess.Popen(
        [executable],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )

    initial_map = render_map(case, list(snake), current_food)
    payload = "\n".join(initial_map + [str(case.n_value)]) + "\n"
    assert process.stdin is not None
    assert process.stdout is not None
    process.stdin.write(payload)
    process.stdin.flush()

    finished_normally = False
    final_snapshot_map: list[str] | None = None
    final_snapshot_score = score

    try:
        while turns < case.max_turns:
            direction_line = process.stdout.readline()
            score_line = process.stdout.readline()
            if not direction_line or not score_line:
                protocol_errors.append("程序提前结束，未按协议输出方向和得分")
                break

            direction = direction_line.strip()
            if direction not in DIRS:
                protocol_errors.append(f"输出了非法方向: {direction!r}")
                break

            try:
                reported_score = int(score_line.strip())
            except ValueError:
                protocol_errors.append(f"输出了非法得分: {score_line.strip()!r}")
                break

            if reported_score != score:
                protocol_errors.append(f"移动前得分错误，期望 {score}，实际 {reported_score}")
                break

            snapshot_map = render_map(case, list(snake), current_food)
            final_snapshot_map = snapshot_map
            final_snapshot_score = score

            head_row, head_col = snake[0]
            delta_row, delta_col = DIRS[direction]
            next_head = (head_row + delta_row, head_col + delta_col)
            ate_food = current_food is not None and next_head == current_food
            next_growth_counter = growth_counter + 1
            grows_by_n = next_growth_counter == case.n_value
            will_grow = ate_food or grows_by_n

            collision = False
            if direction == OPPOSITE[previous_direction]:
                collision = True
            else:
                row, col = next_head
                if row < 0 or row >= ROWS or col < 0 or col >= COLS:
                    collision = True
                else:
                    cell = snapshot_map[row][col]
                    if cell in {"#", "O"}:
                        collision = True
                    elif next_head in snake:
                        tail = snake[-1]
                        if next_head != tail or will_grow:
                            collision = True

            if collision:
                process.stdin.write("100 100\n")
                process.stdin.flush()
                returned_map = [process.stdout.readline() for _ in range(ROWS)]
                returned_score_line = process.stdout.readline()
                returned_map = parse_program_map(returned_map)
                if returned_map != snapshot_map:
                    protocol_errors.append("结束时输出的地图不是碰撞前一刻地图")
                try:
                    returned_score = int(returned_score_line.strip())
                except ValueError:
                    protocol_errors.append("结束时输出的最终得分格式错误")
                else:
                    if returned_score != score:
                        protocol_errors.append("结束时输出的最终得分错误")
                finished_normally = True
                break

            snake.appendleft(next_head)
            if will_grow:
                if ate_food:
                    score += 10
                if grows_by_n:
                    next_growth_counter = 0
            else:
                snake.pop()

            if will_grow and not ate_food:
                pass

            growth_counter = next_growth_counter
            previous_direction = direction
            turns += 1

            if ate_food:
                current_food = pending_foods.popleft() if pending_foods else None
                if current_food is not None:
                    process.stdin.write(f"{current_food[0]} {current_food[1]}\n")
                else:
                    process.stdin.write("20 20\n")
            else:
                process.stdin.write("20 20\n")
            process.stdin.flush()

            if current_food is None and not pending_foods:
                direction_line = process.stdout.readline()
                score_line = process.stdout.readline()
                if not direction_line or not score_line:
                    protocol_errors.append("食物耗尽后程序提前结束")
                    break
                direction = direction_line.strip()
                try:
                    reported_score = int(score_line.strip())
                except ValueError:
                    protocol_errors.append("食物耗尽后的得分格式错误")
                    break
                if direction not in DIRS or reported_score != score:
                    protocol_errors.append("食物耗尽后未按协议继续输出方向和得分")
                    break
                snapshot_map = render_map(case, list(snake), current_food)
                process.stdin.write("100 100\n")
                process.stdin.flush()
                returned_map = [process.stdout.readline() for _ in range(ROWS)]
                returned_score_line = process.stdout.readline()
                returned_map = parse_program_map(returned_map)
                if returned_map != snapshot_map:
                    protocol_errors.append("主动结束时输出的地图不正确")
                try:
                    returned_score = int(returned_score_line.strip())
                except ValueError:
                    protocol_errors.append("主动结束时输出的得分格式错误")
                else:
                    if returned_score != score:
                        protocol_errors.append("主动结束时输出的得分错误")
                finished_normally = True
                break

        if turns >= case.max_turns and not finished_normally:
            protocol_errors.append("达到最大回合数仍未结束，按超时处理")
    finally:
        try:
            stdout_data, stderr_data = process.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout_data, stderr_data = process.communicate()

    weight = 1 / (math.log2(case.n_value) + 1)
    weighted_score = score * weight
    return {
        "name": case.name,
        "n_value": case.n_value,
        "score": score,
        "weight": weight,
        "weighted_score": weighted_score,
        "turns": turns,
        "errors": protocol_errors,
        "stderr": stderr_data.strip(),
        "finished_normally": finished_normally,
    }


def main() -> int:
    executable = sys.argv[1] if len(sys.argv) > 1 else "game.exe"
    results = [run_case(executable, case) for case in case_definitions()]
    total = sum(result["weighted_score"] for result in results)

    print("自定义评测结果")
    print("=" * 60)
    for result in results:
        print(
            f"{result['name']}: N={result['n_value']}, 原始分={result['score']}, "
            f"权重={result['weight']:.6f}, 加权分={result['weighted_score']:.2f}, 回合={result['turns']}"
        )
        if result["errors"]:
            for error in result["errors"]:
                print(f"  错误: {error}")
        if result["stderr"]:
            print(f"  stderr: {result['stderr']}")

    print("=" * 60)
    print(f"总加权分: {total:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())