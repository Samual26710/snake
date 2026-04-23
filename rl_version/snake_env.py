from __future__ import annotations

import random
from collections import deque
from typing import Iterable, Sequence


ROWS = 20
COLS = 20
INTERIOR_ROWS = range(1, ROWS - 1)
INTERIOR_COLS = range(1, COLS - 1)

ACTION_TO_DIR = {
	0: "W",
	1: "A",
	2: "S",
	3: "D",
}
DIR_TO_ACTION = {value: key for key, value in ACTION_TO_DIR.items()}
DIR_VECTORS = {
	"W": (-1, 0),
	"A": (0, -1),
	"S": (1, 0),
	"D": (0, 1),
}
OPPOSITE_DIR = {
	"W": "S",
	"A": "D",
	"S": "W",
	"D": "A",
}
TAIL_DIR_CODE = {
	(-1, 0): 0,
	(0, -1): 1,
	(1, 0): 2,
	(0, 1): 3,
}


class SnakeEnv:
	def __init__(self, N: int, initial_map: Sequence[str] | Sequence[Sequence[str]] | None = None):
		if N <= 0:
			raise ValueError("N must be a positive integer")

		self.N = int(N)
		self._fixed_initial_map = self._normalize_map(initial_map) if initial_map is not None else None

		self.base_map: list[list[str]] = []
		self.map: list[list[str]] = []
		self.sr: list[tuple[int, int]] = []
		self.direction = "W"
		self.score = 0
		self.move_count = 0
		self.done = False
		self.food_pos: tuple[int, int] | None = None

		self.reset(initial_map=initial_map)

	def reset(self, initial_map: Sequence[str] | Sequence[Sequence[str]] | None = None):
		normalized_map = self._normalize_map(initial_map) if initial_map is not None else self._fixed_initial_map
		if normalized_map is None:
			normalized_map = self._generate_random_map()

		self._load_from_map(normalized_map)
		return self._encode_state()

	def step(self, action: int):
		if self.done:
			raise RuntimeError("Cannot call step() after the episode has ended. Call reset() first.")
		if action not in ACTION_TO_DIR:
			raise ValueError("action must be one of 0, 1, 2, 3")

		chosen_dir = ACTION_TO_DIR[action]
		if chosen_dir == OPPOSITE_DIR[self.direction]:
			self.done = True
			return self._encode_state(), -100, True

		head_row, head_col = self.sr[0]
		delta_row, delta_col = DIR_VECTORS[chosen_dir]
		next_head = (head_row + delta_row, head_col + delta_col)

		periodic_grow = (self.move_count + 1) == self.N
		ate_food = next_head == self.food_pos
		will_grow = periodic_grow or ate_food

		if not self._is_target_cell_safe(next_head, chosen_dir, will_grow):
			self.done = True
			return self._encode_state(), -100, True

		self.direction = chosen_dir
		self.move_count += 1
		if self.move_count == self.N:
			self.move_count = 0

		self.sr.insert(0, next_head)
		if not will_grow:
			self.sr.pop()

		reward = -1
		if ate_food:
			self.score += 10
			reward = 100
			if self._head_tail_connected():
				reward += 50
			self.food_pos = self._spawn_food()

		self._rebuild_map()
		return self._encode_state(), reward, False

	def render(self):
		board = "\n".join("".join(row) for row in self.map)
		print(board)
		return board

	def _load_from_map(self, map_lines: Sequence[str]):
		self.base_map = []
		snake_cells: set[tuple[int, int]] = set()
		head_pos: tuple[int, int] | None = None
		food_pos: tuple[int, int] | None = None

		for row_index, line in enumerate(map_lines):
			base_row: list[str] = []
			for col_index, cell in enumerate(line):
				if row_index in (0, ROWS - 1) or col_index in (0, COLS - 1):
					if cell != "#":
						raise ValueError("Map borders must be '#'")
					base_row.append("#")
					continue

				if cell not in {".", "O", "H", "B", "F"}:
					raise ValueError(f"Unsupported map cell: {cell}")

				if cell == "H":
					if head_pos is not None:
						raise ValueError("Map must contain exactly one snake head")
					head_pos = (row_index, col_index)
					snake_cells.add((row_index, col_index))
					base_row.append(".")
				elif cell == "B":
					snake_cells.add((row_index, col_index))
					base_row.append(".")
				elif cell == "F":
					if food_pos is not None:
						raise ValueError("Map must contain at most one food cell")
					food_pos = (row_index, col_index)
					base_row.append(".")
				else:
					base_row.append(cell)
			self.base_map.append(base_row)

		if head_pos is None:
			raise ValueError("Map must contain one snake head")

		self.sr = self._trace_snake(head_pos, snake_cells)
		if len(self.sr) < 3:
			raise ValueError("Initial snake length must be at least 3")
		if self.sr[1] != (self.sr[0][0] + 1, self.sr[0][1]):
			raise ValueError("Initial snake must match the OJ default upward direction")

		self.direction = "W"
		self.score = 0
		self.move_count = 0
		self.done = False
		self.food_pos = food_pos if food_pos is not None else self._spawn_food()
		self._rebuild_map()

	def _trace_snake(self, head_pos: tuple[int, int], snake_cells: set[tuple[int, int]]):
		ordered = [head_pos]
		previous = None
		current = head_pos

		while True:
			candidates = []
			for delta_row, delta_col in DIR_VECTORS.values():
				neighbor = (current[0] + delta_row, current[1] + delta_col)
				if neighbor in snake_cells and neighbor != previous:
					candidates.append(neighbor)

			if len(ordered) == 1:
				body_candidates = [cell for cell in candidates if cell != head_pos]
				if len(body_candidates) != 1:
					raise ValueError("Snake body must form a single chain from the head")
				next_cell = body_candidates[0]
			else:
				if len(candidates) > 1:
					raise ValueError("Snake body must not branch")
				if not candidates:
					break
				next_cell = candidates[0]

			ordered.append(next_cell)
			previous, current = current, next_cell

		if len(ordered) != len(snake_cells):
			raise ValueError("Snake cells must form one continuous chain")
		return ordered

	def _rebuild_map(self):
		self.map = [row[:] for row in self.base_map]
		for index, (row, col) in enumerate(self.sr):
			self.map[row][col] = "H" if index == 0 else "B"
		if self.food_pos is not None:
			food_row, food_col = self.food_pos
			self.map[food_row][food_col] = "F"

	def _spawn_food(self):
		empty_cells = []
		snake_cells = set(self.sr)
		for row in INTERIOR_ROWS:
			for col in INTERIOR_COLS:
				if self.base_map[row][col] != ".":
					continue
				if (row, col) in snake_cells:
					continue
				empty_cells.append((row, col))
		if not empty_cells:
			return None
		return random.choice(empty_cells)

	def _generate_random_map(self):
		grid = [["." for _ in range(COLS)] for _ in range(ROWS)]
		for row in range(ROWS):
			grid[row][0] = "#"
			grid[row][COLS - 1] = "#"
		for col in range(COLS):
			grid[0][col] = "#"
			grid[ROWS - 1][col] = "#"

		head_row = random.randint(1, ROWS - 4)
		head_col = random.randint(1, COLS - 2)
		snake = [
			(head_row, head_col),
			(head_row + 1, head_col),
			(head_row + 2, head_col),
		]
		occupied = set(snake)

		candidates = [(row, col) for row in INTERIOR_ROWS for col in INTERIOR_COLS if (row, col) not in occupied]
		obstacle_cells = random.sample(candidates, 10)
		for row, col in obstacle_cells:
			grid[row][col] = "O"
			occupied.add((row, col))

		food_candidates = [(row, col) for row in INTERIOR_ROWS for col in INTERIOR_COLS if (row, col) not in occupied]
		food_row, food_col = random.choice(food_candidates)

		grid[snake[0][0]][snake[0][1]] = "H"
		for row, col in snake[1:]:
			grid[row][col] = "B"
		grid[food_row][food_col] = "F"
		return ["".join(row) for row in grid]

	def _normalize_map(self, initial_map: Sequence[str] | Sequence[Sequence[str]] | None):
		if initial_map is None:
			return None
		if len(initial_map) != ROWS:
			raise ValueError("Map must have exactly 20 rows")

		normalized = []
		for line in initial_map:
			row = "".join(line) if not isinstance(line, str) else line
			if len(row) != COLS:
				raise ValueError("Each map row must have exactly 20 columns")
			normalized.append(row)
		return tuple(normalized)

	def _is_target_cell_safe(self, target: tuple[int, int], chosen_dir: str, will_grow: bool):
		target_row, target_col = target
		if chosen_dir == OPPOSITE_DIR[self.direction]:
			return False
		if not (0 <= target_row < ROWS and 0 <= target_col < COLS):
			return False
		if self.base_map[target_row][target_col] in {"#", "O"}:
			return False

		blocked_length = len(self.sr) if will_grow else len(self.sr) - 1
		for row, col in self.sr[:blocked_length]:
			if (row, col) == target:
				return False
		return True

	def _is_safe_action(self, action_dir: str):
		head_row, head_col = self.sr[0]
		delta_row, delta_col = DIR_VECTORS[action_dir]
		target = (head_row + delta_row, head_col + delta_col)
		periodic_grow = (self.move_count + 1) == self.N
		will_grow = periodic_grow or target == self.food_pos
		return self._is_target_cell_safe(target, action_dir, will_grow)

	def _head_tail_connected(self):
		if len(self.sr) <= 1:
			return True

		head = self.sr[0]
		tail = self.sr[-1]
		blocked = set(self.sr[1:-1])
		queue = deque([head])
		visited = {head}

		while queue:
			row, col = queue.popleft()
			if (row, col) == tail:
				return True
			for delta_row, delta_col in DIR_VECTORS.values():
				next_row = row + delta_row
				next_col = col + delta_col
				next_cell = (next_row, next_col)
				if next_cell in visited or next_cell in blocked:
					continue
				if not (0 <= next_row < ROWS and 0 <= next_col < COLS):
					continue
				if self.base_map[next_row][next_col] in {"#", "O"}:
					continue
				visited.add(next_cell)
				queue.append(next_cell)
		return False

	def _encode_state(self):
		return (
			self._food_direction_code(),
			self._safe_code(),
			self._next_move_periodic_growth_flag(),
			self._tail_direction_code(),
		)

	def _food_direction_code(self):
		if self.food_pos is None:
			return 0

		head_row, head_col = self.sr[0]
		food_row, food_col = self.food_pos
		row_sign = self._sign(food_row - head_row)
		col_sign = self._sign(food_col - head_col)

		direction_map = {
			(-1, 0): 0,
			(-1, 1): 1,
			(0, 1): 2,
			(1, 1): 3,
			(1, 0): 4,
			(1, -1): 5,
			(0, -1): 6,
			(-1, -1): 7,
			(0, 0): 0,
		}
		return direction_map[(row_sign, col_sign)]

	def _safe_code(self):
		up = 1 if self._is_safe_action("W") else 0
		down = 1 if self._is_safe_action("S") else 0
		left = 1 if self._is_safe_action("A") else 0
		right = 1 if self._is_safe_action("D") else 0
		return (up << 3) | (down << 2) | (left << 1) | right

	def _next_move_periodic_growth_flag(self):
		return 1 if (self.move_count + 1) == self.N else 0

	def _tail_direction_code(self):
		if len(self.sr) < 2:
			return 0
		tail_row, tail_col = self.sr[-1]
		prev_row, prev_col = self.sr[-2]
		return TAIL_DIR_CODE[(prev_row - tail_row, prev_col - tail_col)]

	@staticmethod
	def _sign(value: int):
		if value > 0:
			return 1
		if value < 0:
			return -1
		return 0


__all__ = ["SnakeEnv"]
