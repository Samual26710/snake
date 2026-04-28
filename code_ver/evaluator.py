from __future__ import annotations

import argparse
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


@dataclass(frozen=True)
class ScoreSummary:
    raw_total: int
    base_score: int
    ranking_bonus: int
    submission_penalty: int
    final_score: int


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


def base_score_from_raw_total(raw_total: int) -> int:
    if raw_total >= 500:
        return 50
    if raw_total >= 400:
        return 45
    if raw_total >= 300:
        return 40
    if raw_total >= 200:
        return 35
    if raw_total >= 100:
        return 30
    return 0


def submission_penalty_from_count(submission_count: int) -> int:
    return max(0, submission_count - 10) * 10


def summarize_oj_like_score(
    raw_total: int,
    ranking_bonus: int,
    submission_count: int,
) -> ScoreSummary:
    base_score = base_score_from_raw_total(raw_total)
    submission_penalty = submission_penalty_from_count(submission_count)
    final_score = max(0, base_score + ranking_bonus - submission_penalty)
    return ScoreSummary(
        raw_total=raw_total,
        base_score=base_score,
        ranking_bonus=ranking_bonus,
        submission_penalty=submission_penalty,
        final_score=final_score,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="运行本地贪吃蛇评测，并按课程 OJ 规则近似计算成绩。",
    )
    parser.add_argument(
        "executable",
        nargs="?",
        default="game.exe",
        help="待评测可执行文件路径，默认是当前目录下的 game.exe",
    )
    parser.add_argument(
        "--ranking-bonus",
        type=int,
        default=0,
        choices=(0, 2, 4, 6, 8),
        help="排名分，按题面可选 0/2/4/6/8，默认 0。",
    )
    parser.add_argument(
        "--submission-count",
        type=int,
        default=1,
        help="提交次数。前 10 次不扣分，第 11 次起每次扣 10 分，默认 1。",
    )
    parser.add_argument(
        "--show-weighted-total",
        action="store_true",
        help="额外显示旧版自定义加权分，便于与历史本地 benchmark 对比。",
    )
    return parser.parse_args()


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


def base_cell(case: Case, row: int, col: int) -> str:
    if row in {0, ROWS - 1} or col in {0, COLS - 1}:
        return "#"
    if (row, col) in case.obstacle_cells:
        return "O"
    return "."


def with_restored_cell(
    map_lines: list[str],
    position: tuple[int, int] | None,
    replacement: str,
) -> list[str] | None:
    if position is None:
        return None
    row, col = position
    updated = list(map_lines)
    updated[row] = updated[row][:col] + replacement + updated[row][col + 1 :]
    return updated


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
    consumed_food: tuple[int, int] | None = None

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
                consumed_food = current_food
                current_food = pending_foods.popleft() if pending_foods else None
                if current_food is not None:
                    process.stdin.write(f"{current_food[0]} {current_food[1]}\n")
                else:
                    process.stdin.write("100 100\n")
            else:
                process.stdin.write("20 20\n")
            process.stdin.flush()

            if current_food is None and not pending_foods:
                current_snapshot_map = render_map(case, list(snake), current_food)
                returned_map = [process.stdout.readline() for _ in range(ROWS)]
                returned_score_line = process.stdout.readline()
                returned_map = parse_program_map(returned_map)
                try:
                    returned_score = int(returned_score_line.strip())
                except ValueError:
                    protocol_errors.append("主动结束时输出的得分格式错误")
                else:
                    restored_pending_map = with_restored_cell(
                        final_snapshot_map,
                        consumed_food,
                        base_cell(case, consumed_food[0], consumed_food[1]) if consumed_food is not None else ".",
                    )
                    current_state_ok = returned_map == current_snapshot_map and returned_score == score
                    pending_state_ok = (
                        final_snapshot_map is not None
                        and returned_map == final_snapshot_map
                        and returned_score == final_snapshot_score
                    )
                    restored_pending_state_ok = (
                        restored_pending_map is not None
                        and returned_map == restored_pending_map
                        and returned_score == final_snapshot_score
                    )
                    if not current_state_ok and not pending_state_ok and not restored_pending_state_ok:
                        protocol_errors.append("主动结束时输出的地图或得分不符合允许的结束语义")
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
    args = parse_args()
    results = [run_case(args.executable, case) for case in case_definitions()]
    weighted_total = sum(result["weighted_score"] for result in results)
    raw_total = sum(int(result["score"]) for result in results)
    score_summary = summarize_oj_like_score(
        raw_total=raw_total,
        ranking_bonus=args.ranking_bonus,
        submission_count=args.submission_count,
    )

    print("本地近似 OJ 评测结果")
    print("=" * 60)
    for result in results:
        line = (
            f"{result['name']}: N={result['n_value']}, 原始分={result['score']}, 回合={result['turns']}"
        )
        if args.show_weighted_total:
            line += (
                f", 权重={result['weight']:.6f}, 加权分={result['weighted_score']:.2f}"
            )
        print(line)
        if result["errors"]:
            for error in result["errors"]:
                print(f"  错误: {error}")
        if result["stderr"]:
            print(f"  stderr: {result['stderr']}")

    print("=" * 60)
    print(f"原始总分: {score_summary.raw_total}")
    print(f"基础分: {score_summary.base_score}")
    print(f"排名分: {score_summary.ranking_bonus}")
    print(f"提交扣分: {score_summary.submission_penalty}")
    print(f"近似 OJ 总分: {score_summary.final_score}")
    if args.show_weighted_total:
        print(f"旧版自定义总加权分: {weighted_total:.2f}")
    print("说明: 当前 case 集仍是本地 benchmark；这里只把最终成绩换成了更接近课程 OJ 的计分层。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())