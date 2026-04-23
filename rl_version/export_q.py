from __future__ import annotations

from pathlib import Path

import numpy as np


STATE_COUNT = 1024
ACTION_COUNT = 4
SCALE = 1000
Q_TABLE_PATH = Path(__file__).with_name("q_table.npy")
HEADER_PATH = Path(__file__).with_name("q_table.h")


def load_q_table() -> np.ndarray:
	if not Q_TABLE_PATH.exists():
		raise FileNotFoundError(f"Q-table file not found: {Q_TABLE_PATH}")

	q_table = np.load(Q_TABLE_PATH)
	if q_table.shape != (STATE_COUNT, ACTION_COUNT):
		raise ValueError(f"Expected q_table shape {(STATE_COUNT, ACTION_COUNT)}, got {q_table.shape}")
	return q_table


def quantize_q_table(q_table: np.ndarray) -> np.ndarray:
	return np.rint(q_table * SCALE).astype(np.int32)


def build_header_content(q_table: np.ndarray) -> str:
	lines = [
		"#ifndef Q_TABLE_H",
		"#define Q_TABLE_H",
		"",
		"/* Trained Q-table: 1024 states x 4 actions */",
		"static const int q_table[1024][4] = {",
	]

	for state_index, row in enumerate(q_table):
		values = ", ".join(str(int(value)) for value in row)
		trailing_comma = "," if state_index < STATE_COUNT - 1 else ""
		lines.append(f"    {{{values}}}{trailing_comma}  /* 状态{state_index}的4个动作Q值 */")

	lines.extend(
		[
			"};",
			"",
			"#endif /* Q_TABLE_H */",
		]
	)
	return "\n".join(lines) + "\n"


def export_q_table() -> Path:
	q_table = load_q_table()
	quantized_q_table = quantize_q_table(q_table)
	header_content = build_header_content(quantized_q_table)
	HEADER_PATH.write_text(header_content, encoding="utf-8", newline="\n")
	return HEADER_PATH


def main():
	header_path = export_q_table()
	print(f"Export complete: {header_path}")


if __name__ == "__main__":
	main()
