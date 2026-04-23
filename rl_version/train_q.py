from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np

from snake_env import SnakeEnv


STATE_COUNT = 1024
ACTIONS_COUNT = 4
ALPHA = 0.1
GAMMA = 0.9
EPSILON_START = 0.1
EPSILON_DECAY = 0.001
EPSILON_MIN = 0.01
EPISODES = 100000
AVERAGE_WINDOW = 1000
MAX_STEPS_PER_EPISODE = 2000
N_VALUES = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]
Q_TABLE_PATH = Path(__file__).with_name("q_table.npy")
CHECKPOINT_PATH = Path(__file__).with_name("q_checkpoint.json")
AUTOSAVE_INTERVAL = 1000


def state_to_index(state: tuple[int, int, int, int]) -> int:
	food_dir, safe_code, will_grow, tail_dir = state
	return food_dir + safe_code * 8 + will_grow * 128 + tail_dir * 256


def legal_actions_from_state(state: tuple[int, int, int, int]) -> list[int]:
	safe_code = state[1]
	legal_actions = []

	if safe_code & 0b1000:
		legal_actions.append(0)
	if safe_code & 0b0010:
		legal_actions.append(1)
	if safe_code & 0b0100:
		legal_actions.append(2)
	if safe_code & 0b0001:
		legal_actions.append(3)

	return legal_actions


def choose_action(q_table: np.ndarray, state: tuple[int, int, int, int], epsilon: float) -> int:
	legal_actions = legal_actions_from_state(state)
	if not legal_actions:
		return random.randrange(ACTIONS_COUNT)

	if random.random() < epsilon:
		return random.choice(legal_actions)

	state_index = state_to_index(state)
	best_value = max(q_table[state_index, action] for action in legal_actions)
	best_actions = [action for action in legal_actions if q_table[state_index, action] == best_value]
	return random.choice(best_actions)


def epsilon_for_episode(episode: int) -> float:
	decay_steps = episode // AVERAGE_WINDOW
	return max(EPSILON_MIN, EPSILON_START - decay_steps * EPSILON_DECAY)


def n_value_for_episode(episode: int) -> int:
	return N_VALUES[(episode - 1) // 10000]


def load_checkpoint() -> tuple[np.ndarray, int]:
	if not Q_TABLE_PATH.exists():
		return np.zeros((STATE_COUNT, ACTIONS_COUNT), dtype=np.float32), 0

	q_table = np.load(Q_TABLE_PATH)
	if q_table.shape != (STATE_COUNT, ACTIONS_COUNT):
		raise ValueError(f"Invalid q_table shape: {q_table.shape}")

	completed_episodes = 0
	if CHECKPOINT_PATH.exists():
		with CHECKPOINT_PATH.open("r", encoding="utf-8") as checkpoint_file:
			checkpoint = json.load(checkpoint_file)
		completed_episodes = int(checkpoint.get("completed_episodes", 0))

	return q_table.astype(np.float32, copy=False), completed_episodes


def save_checkpoint(q_table: np.ndarray, completed_episodes: int):
	np.save(Q_TABLE_PATH, q_table)
	checkpoint = {
		"completed_episodes": completed_episodes,
		"epsilon": epsilon_for_episode(completed_episodes),
		"next_n": n_value_for_episode(completed_episodes + 1) if completed_episodes < EPISODES else None,
	}
	with CHECKPOINT_PATH.open("w", encoding="utf-8") as checkpoint_file:
		json.dump(checkpoint, checkpoint_file, ensure_ascii=True, indent=2)


def train_q_learning(num_episodes: int = EPISODES, resume: bool = True) -> np.ndarray:
	if resume:
		q_table, completed_episodes = load_checkpoint()
	else:
		q_table = np.zeros((STATE_COUNT, ACTIONS_COUNT), dtype=np.float32)
		completed_episodes = 0

	if completed_episodes >= num_episodes:
		print(f"Checkpoint already reached {completed_episodes} episodes; target is {num_episodes}.")
		return q_table

	recent_scores: list[int] = []

	for episode in range(completed_episodes + 1, num_episodes + 1):
		n_value = n_value_for_episode(episode)
		env = SnakeEnv(n_value)
		state = env.reset()
		state_index = state_to_index(state)
		epsilon = epsilon_for_episode(episode - 1)

		for _ in range(MAX_STEPS_PER_EPISODE):
			action = choose_action(q_table, state, epsilon)
			next_state, reward, done = env.step(action)
			next_index = state_to_index(next_state)

			best_next_q = 0.0 if done else float(np.max(q_table[next_index]))
			current_q = q_table[state_index, action]
			q_table[state_index, action] = current_q + ALPHA * (reward + GAMMA * best_next_q - current_q)

			state = next_state
			state_index = next_index
			if done:
				break

		recent_scores.append(env.score)
		if episode % AVERAGE_WINDOW == 0:
			average_score = sum(recent_scores) / len(recent_scores)
			print(f"Episode {episode}: N={n_value}, epsilon={epsilon:.3f}, avg_score={average_score:.2f}")
			recent_scores.clear()

		if episode % AUTOSAVE_INTERVAL == 0:
			save_checkpoint(q_table, episode)
			print(f"Autosaved checkpoint at episode {episode}.")

	save_checkpoint(q_table, num_episodes)
	return q_table


def main():
	q_table = train_q_learning()
	print(f"Training complete. Q-table saved to {Q_TABLE_PATH}. shape={q_table.shape}")


if __name__ == "__main__":
	main()
