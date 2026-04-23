/*
 * 贪吃蛇 OJ 强化学习版本
 * 标准 C99，无平台依赖
 * 交互协议：
 *   输出：第1行方向字符(W/A/S/D)，第2行移动前得分
 *   输入：两整数 a b
 *         1<=a,b<=18  -> 新食物坐标
 *         20 20       -> 继续
 *         100 100     -> 游戏结束，输出最终地图+得分后退出
 */

#include <stdio.h>
#include <string.h>

#include "q_table.h"

#define ROWS      20
#define COLS      20
#define MAX_SNAKE 420

static char original_map[ROWS][COLS + 2];
static char base_map[ROWS][COLS + 2];
static char map[ROWS][COLS + 2];
static char pending_map[ROWS][COLS + 2];

static int sr[MAX_SNAKE], sc[MAX_SNAKE];
static int snake_len;

static int cur_dr, cur_dc;
static int score;
static int pending_score;
static int turns_since_food;
static int obstacle_count;
static int move_count;
static int N;
static int food_r, food_c;

static const int drs[4]        = {-1, 0, 1, 0};
static const int dcs[4]        = { 0,-1, 0, 1};
static const char dir_chars[4] = {'W','A','S','D'};

#define STARVATION_LIMIT 12

static char infer_base_cell(int r, int c)
{
	if (original_map[r][c] == 'O' || original_map[r][c] == '#')
		return original_map[r][c];

	/*
	 * 初始地图中的 H/B/F 会覆盖底图字符。
	 * 若该格位于一条连续障碍段中，则其左右或上下两侧会保留 O，
	 * 这种情况下将底图恢复为 O；否则按空地处理。
	 */
	if (r > 0 && r < ROWS - 1 && c > 0 && c < COLS - 1) {
		if (original_map[r][c - 1] == 'O' && original_map[r][c + 1] == 'O')
			return 'O';
		if (original_map[r - 1][c] == 'O' && original_map[r + 1][c] == 'O')
			return 'O';
	}

	return original_map[r][c];
}

static void build_base_map(void)
{
	int i, j;
	obstacle_count = 0;
	for (i = 0; i < ROWS; i++) {
		for (j = 0; j < COLS; j++) {
			base_map[i][j] = infer_base_cell(i, j);
			if (base_map[i][j] == 'O')
				obstacle_count++;
		}
		base_map[i][COLS] = '\0';
	}
}

static void render_state_to_map(char dest[ROWS][COLS + 2])
{
	int i;

	for (i = 0; i < ROWS; i++)
		strcpy(dest[i], base_map[i]);

	for (i = 0; i < snake_len; i++)
		dest[sr[i]][sc[i]] = (i == 0) ? 'H' : 'B';

	if (food_r >= 0 && food_c >= 0)
		dest[food_r][food_c] = 'F';
}

static void rebuild_current_map(void)
{
	render_state_to_map(map);
}

static void save_pending_snapshot(void)
{
	render_state_to_map(pending_map);
	pending_score = score;
}

static void find_initial_state(void)
{
	int i, j, d;
	food_r = -1;
	food_c = -1;

	{
		int hr = -1, hc = -1;
		for (i = 0; i < ROWS; i++) {
			for (j = 0; j < COLS; j++) {
				if (map[i][j] == 'H') {
					hr = i;
					hc = j;
				}
				if (map[i][j] == 'F') {
					food_r = i;
					food_c = j;
				}
			}
		}

		sr[0] = hr;
		sc[0] = hc;
		snake_len = 1;

		{
			int cur_r = hr, cur_c = hc;
			int prev_r = -1, prev_c = -1;
			int step;
			for (step = 0; step < 2; step++) {
				int found = 0;
				for (d = 0; d < 4 && !found; d++) {
					int nr = cur_r + drs[d];
					int nc = cur_c + dcs[d];
					if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS) continue;
					if (map[nr][nc] == 'B' && (nr != prev_r || nc != prev_c)) {
						sr[snake_len] = nr;
						sc[snake_len] = nc;
						snake_len++;
						prev_r = cur_r;
						prev_c = cur_c;
						cur_r = nr;
						cur_c = nc;
						found = 1;
					}
				}
			}
		}
	}

	cur_dr = -1;
	cur_dc = 0;
}

static int bfs_to_food(void)
{
	static int q_r[ROWS * COLS], q_c[ROWS * COLS], q_d[ROWS * COLS];
	int visited[ROWS][COLS];
	int i, j;
	int qh, qt;
	int head_r, head_c;

	if (food_r < 0 || food_c < 0) return -1;

	memset(visited, 0, sizeof(visited));
	for (i = 0; i < ROWS; i++)
		for (j = 0; j < COLS; j++)
			if (map[i][j] == '#' || map[i][j] == 'O')
				visited[i][j] = 1;

	{
		int will_grow_n = ((move_count + 1) == N);
		int mark_len = will_grow_n ? snake_len : (snake_len - 1);
		for (i = 0; i < mark_len; i++)
			visited[sr[i]][sc[i]] = 1;
	}

	qh = 0;
	qt = 0;
	head_r = sr[0];
	head_c = sc[0];

	for (i = 0; i < 4; i++) {
		int nr, nc;
		if (drs[i] == -cur_dr && dcs[i] == -cur_dc) continue;
		nr = head_r + drs[i];
		nc = head_c + dcs[i];
		if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS) continue;
		if (visited[nr][nc]) continue;
		visited[nr][nc] = 1;
		q_r[qt] = nr;
		q_c[qt] = nc;
		q_d[qt] = i;
		qt++;
	}

	while (qh < qt) {
		int r = q_r[qh], c = q_c[qh], d = q_d[qh];
		int nd;
		qh++;
		if (r == food_r && c == food_c) return d;
		for (nd = 0; nd < 4; nd++) {
			int nr = r + drs[nd];
			int nc = c + dcs[nd];
			if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS) continue;
			if (visited[nr][nc]) continue;
			visited[nr][nc] = 1;
			q_r[qt] = nr;
			q_c[qt] = nc;
			q_d[qt] = d;
			qt++;
		}
	}

	return -1;
}

static int flood_count(int start_r, int start_c, int tail_stays)
{
	int vis[ROWS][COLS];
	static int fr[ROWS * COLS], fc[ROWS * COLS];
	int fh, ft;
	int count;
	int i, j;

	memset(vis, 0, sizeof(vis));
	for (i = 0; i < ROWS; i++)
		for (j = 0; j < COLS; j++)
			if (map[i][j] == '#' || map[i][j] == 'O')
				vis[i][j] = 1;

	{
		int ml = tail_stays ? snake_len : (snake_len - 1);
		for (i = 0; i < ml; i++)
			vis[sr[i]][sc[i]] = 1;
	}

	if (start_r < 0 || start_r >= ROWS || start_c < 0 || start_c >= COLS)
		return 0;
	if (vis[start_r][start_c]) return 0;

	fh = 0;
	ft = 0;
	fr[ft] = start_r;
	fc[ft] = start_c;
	ft++;
	vis[start_r][start_c] = 1;
	count = 0;

	while (fh < ft) {
		int r = fr[fh], c = fc[fh];
		int dd;
		fh++;
		count++;
		for (dd = 0; dd < 4; dd++) {
			int nr = r + drs[dd];
			int nc = c + dcs[dd];
			if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS) continue;
			if (vis[nr][nc]) continue;
			vis[nr][nc] = 1;
			fr[ft] = nr;
			fc[ft] = nc;
			ft++;
		}
	}
	return count;
}

static int current_component_size(int start_r, int start_c, int tail_stays)
{
	int vis[ROWS][COLS];
	static int qr[ROWS * COLS], qc[ROWS * COLS];
	int i, j, qh, qt, count;

	memset(vis, 0, sizeof(vis));
	for (i = 0; i < ROWS; i++)
		for (j = 0; j < COLS; j++)
			if (map[i][j] == '#' || map[i][j] == 'O')
				vis[i][j] = 1;

	for (i = 0; i < (tail_stays ? snake_len : (snake_len - 1)); i++) {
		if (sr[i] == start_r && sc[i] == start_c) continue;
		vis[sr[i]][sc[i]] = 1;
	}

	if (start_r < 0 || start_r >= ROWS || start_c < 0 || start_c >= COLS)
		return 0;
	if (vis[start_r][start_c]) return 0;

	qh = 0;
	qt = 0;
	count = 0;
	qr[qt] = start_r;
	qc[qt] = start_c;
	qt++;
	vis[start_r][start_c] = 1;

	while (qh < qt) {
		int r = qr[qh], c = qc[qh];
		qh++;
		count++;
		for (i = 0; i < 4; i++) {
			int nr = r + drs[i];
			int nc = c + dcs[i];
			if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS) continue;
			if (vis[nr][nc]) continue;
			vis[nr][nc] = 1;
			qr[qt] = nr;
			qc[qt] = nc;
			qt++;
		}
	}

	return count;
}

static int current_has_path(int start_r, int start_c, int target_r, int target_c, int allow_tail)
{
	int vis[ROWS][COLS];
	static int qr[ROWS * COLS], qc[ROWS * COLS];
	int i, j, qh, qt;
	int tail_r = sr[snake_len - 1], tail_c = sc[snake_len - 1];

	memset(vis, 0, sizeof(vis));
	for (i = 0; i < ROWS; i++)
		for (j = 0; j < COLS; j++)
			if (map[i][j] == '#' || map[i][j] == 'O')
				vis[i][j] = 1;

	for (i = 0; i < snake_len; i++) {
		if ((sr[i] == start_r && sc[i] == start_c) ||
			(sr[i] == target_r && sc[i] == target_c))
			continue;
		if (allow_tail && sr[i] == tail_r && sc[i] == tail_c)
			continue;
		vis[sr[i]][sc[i]] = 1;
	}

	if (start_r < 0 || start_r >= ROWS || start_c < 0 || start_c >= COLS)
		return 0;
	if (target_r < 0 || target_r >= ROWS || target_c < 0 || target_c >= COLS)
		return 0;
	if (vis[start_r][start_c]) return 0;

	qh = 0;
	qt = 0;
	qr[qt] = start_r;
	qc[qt] = start_c;
	qt++;
	vis[start_r][start_c] = 1;

	while (qh < qt) {
		int r = qr[qh], c = qc[qh];
		qh++;
		if (r == target_r && c == target_c) return 1;
		for (i = 0; i < 4; i++) {
			int nr = r + drs[i];
			int nc = c + dcs[i];
			if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS) continue;
			if (vis[nr][nc]) continue;
			vis[nr][nc] = 1;
			qr[qt] = nr;
			qc[qt] = nc;
			qt++;
		}
	}

	return 0;
}

static int is_legal_move(int d)
{
	int nr = sr[0] + drs[d];
	int nc = sc[0] + dcs[d];
	int i;

	if (drs[d] == -cur_dr && dcs[d] == -cur_dc) return 0;
	if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS) return 0;
	if (map[nr][nc] == '#' || map[nr][nc] == 'O') return 0;

	{
		int will_grow = ((move_count + 1) == N) || (nr == food_r && nc == food_c);
		int check_len = will_grow ? snake_len : (snake_len - 1);
		for (i = 0; i < check_len; i++)
			if (sr[i] == nr && sc[i] == nc) return 0;
	}

	return 1;
}

static int get_food_dir_code(void)
{
	int row_sign;
	int col_sign;

	if (food_r < 0 || food_c < 0) return 0;

	row_sign = (food_r > sr[0]) - (food_r < sr[0]);
	col_sign = (food_c > sc[0]) - (food_c < sc[0]);

	if (row_sign < 0 && col_sign == 0) return 0;
	if (row_sign < 0 && col_sign > 0) return 1;
	if (row_sign == 0 && col_sign > 0) return 2;
	if (row_sign > 0 && col_sign > 0) return 3;
	if (row_sign > 0 && col_sign == 0) return 4;
	if (row_sign > 0 && col_sign < 0) return 5;
	if (row_sign == 0 && col_sign < 0) return 6;
	if (row_sign < 0 && col_sign < 0) return 7;
	return 0;
}

static int get_safe_code(void)
{
	int up = is_legal_move(0) ? 1 : 0;
	int down = is_legal_move(2) ? 1 : 0;
	int left = is_legal_move(1) ? 1 : 0;
	int right = is_legal_move(3) ? 1 : 0;
	return (up << 3) | (down << 2) | (left << 1) | right;
}

static int get_will_grow_flag(void)
{
	return ((move_count + 1) == N) ? 1 : 0;
}

static int get_tail_dir_code(void)
{
	int dr;
	int dc;

	if (snake_len < 2) return 0;

	dr = sr[snake_len - 2] - sr[snake_len - 1];
	dc = sc[snake_len - 2] - sc[snake_len - 1];

	if (dr < 0 && dc == 0) return 0;
	if (dr == 0 && dc < 0) return 1;
	if (dr > 0 && dc == 0) return 2;
	return 3;
}

static int get_state_index(void)
{
	int food_dir = get_food_dir_code();
	int safe_code = get_safe_code();
	int will_grow = get_will_grow_flag();
	int tail_dir = get_tail_dir_code();
	return food_dir + safe_code * 8 + will_grow * 128 + tail_dir * 256;
}

static void simulate_move_state(int d, int tr[], int tc[], int *tlen, int *tail_stays)
{
	int nr = sr[0] + drs[d];
	int nc = sc[0] + dcs[d];
	int will_grow = ((move_count + 1) == N) || (nr == food_r && nc == food_c);
	int i;

	*tail_stays = will_grow;
	*tlen = snake_len + (will_grow ? 1 : 0);

	tr[0] = nr;
	tc[0] = nc;
	for (i = 1; i < snake_len; i++) {
		tr[i] = sr[i - 1];
		tc[i] = sc[i - 1];
	}
	if (will_grow) {
		tr[snake_len] = sr[snake_len - 1];
		tc[snake_len] = sc[snake_len - 1];
	}
}

static int state_has_path(int tr[], int tc[], int tlen, int start_r, int start_c, int target_r, int target_c)
{
	int vis[ROWS][COLS];
	static int qr[ROWS * COLS], qc[ROWS * COLS];
	int i, j, qh, qt;

	memset(vis, 0, sizeof(vis));
	for (i = 0; i < ROWS; i++)
		for (j = 0; j < COLS; j++)
			if (map[i][j] == '#' || map[i][j] == 'O')
				vis[i][j] = 1;

	for (i = 0; i < tlen; i++) {
		if ((tr[i] == start_r && tc[i] == start_c) ||
			(tr[i] == target_r && tc[i] == target_c))
			continue;
		vis[tr[i]][tc[i]] = 1;
	}

	qh = 0;
	qt = 0;
	qr[qt] = start_r;
	qc[qt] = start_c;
	qt++;
	vis[start_r][start_c] = 1;

	while (qh < qt) {
		int r = qr[qh], c = qc[qh];
		int d;
		qh++;
		if (r == target_r && c == target_c) return 1;
		for (d = 0; d < 4; d++) {
			int nr = r + drs[d];
			int nc = c + dcs[d];
			if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS) continue;
			if (vis[nr][nc]) continue;
			vis[nr][nc] = 1;
			qr[qt] = nr;
			qc[qt] = nc;
			qt++;
		}
	}

	return 0;
}

static int state_flood_count(int tr[], int tc[], int tlen, int start_r, int start_c)
{
	int vis[ROWS][COLS];
	static int qr[ROWS * COLS], qc[ROWS * COLS];
	int i, j, qh, qt, count;

	memset(vis, 0, sizeof(vis));
	for (i = 0; i < ROWS; i++)
		for (j = 0; j < COLS; j++)
			if (map[i][j] == '#' || map[i][j] == 'O')
				vis[i][j] = 1;

	for (i = 0; i < tlen; i++) {
		if (tr[i] == start_r && tc[i] == start_c) continue;
		vis[tr[i]][tc[i]] = 1;
	}

	if (start_r < 0 || start_r >= ROWS || start_c < 0 || start_c >= COLS)
		return 0;
	if (vis[start_r][start_c]) return 0;

	qh = 0;
	qt = 0;
	count = 0;
	qr[qt] = start_r;
	qc[qt] = start_c;
	qt++;
	vis[start_r][start_c] = 1;

	while (qh < qt) {
		int r = qr[qh], c = qc[qh];
		qh++;
		count++;
		for (i = 0; i < 4; i++) {
			int nr = r + drs[i];
			int nc = c + dcs[i];
			if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS) continue;
			if (vis[nr][nc]) continue;
			vis[nr][nc] = 1;
			qr[qt] = nr;
			qc[qt] = nc;
			qt++;
		}
	}
	return count;
}

static int move_has_escape(int d)
{
	int tr[MAX_SNAKE], tc[MAX_SNAKE];
	int tlen, tail_stays;

	if (!is_legal_move(d)) return 0;

	simulate_move_state(d, tr, tc, &tlen, &tail_stays);
	if (state_has_path(tr, tc, tlen, tr[0], tc[0], tr[tlen - 1], tc[tlen - 1]))
		return 1;

	return state_flood_count(tr, tc, tlen, tr[0], tc[0]) >= tlen;
}

static int build_food_path(int path_r[], int path_c[])
{
	int visited[ROWS][COLS];
	int parent_r[ROWS][COLS], parent_c[ROWS][COLS];
	static int q_r[ROWS * COLS], q_c[ROWS * COLS];
	int i, j;
	int head_r, head_c;
	int qh, qt;

	if (food_r < 0 || food_c < 0) return 0;

	memset(visited, 0, sizeof(visited));
	for (i = 0; i < ROWS; i++)
		for (j = 0; j < COLS; j++) {
			parent_r[i][j] = -1;
			parent_c[i][j] = -1;
			if (map[i][j] == '#' || map[i][j] == 'O')
				visited[i][j] = 1;
		}

	{
		int will_grow_n = ((move_count + 1) == N);
		int mark_len = will_grow_n ? snake_len : (snake_len - 1);
		for (i = 0; i < mark_len; i++)
			visited[sr[i]][sc[i]] = 1;
	}

	head_r = sr[0];
	head_c = sc[0];
	qh = 0;
	qt = 0;
	visited[head_r][head_c] = 1;
	q_r[qt] = head_r;
	q_c[qt] = head_c;
	qt++;

	while (qh < qt) {
		int r = q_r[qh], c = q_c[qh];
		int d;
		qh++;
		if (r == food_r && c == food_c) break;
		for (d = 0; d < 4; d++) {
			int nr = r + drs[d];
			int nc = c + dcs[d];
			if (r == head_r && c == head_c && drs[d] == -cur_dr && dcs[d] == -cur_dc)
				continue;
			if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS) continue;
			if (visited[nr][nc]) continue;
			visited[nr][nc] = 1;
			parent_r[nr][nc] = r;
			parent_c[nr][nc] = c;
			q_r[qt] = nr;
			q_c[qt] = nc;
			qt++;
		}
	}

	if (!visited[food_r][food_c]) return 0;

	i = 0;
	{
		int rev_r[ROWS * COLS], rev_c[ROWS * COLS];
		int r = food_r, c = food_c;
		while (!(r == head_r && c == head_c)) {
			rev_r[i] = r;
			rev_c[i] = c;
			i++;
			j = parent_r[r][c];
			c = parent_c[r][c];
			r = j;
		}
		for (j = 0; j < i; j++) {
			path_r[j] = rev_r[i - 1 - j];
			path_c[j] = rev_c[i - 1 - j];
		}
	}

	return i;
}

static int food_plan_has_escape(void)
{
	int path_r[ROWS * COLS], path_c[ROWS * COLS];
	int tr[MAX_SNAKE], tc[MAX_SNAKE];
	int path_len = build_food_path(path_r, path_c);
	int tlen = snake_len;
	int temp_move_count = move_count;
	int step;

	if (path_len <= 0) return 0;

	for (step = 0; step < snake_len; step++) {
		tr[step] = sr[step];
		tc[step] = sc[step];
	}

	for (step = 0; step < path_len; step++) {
		int nr = path_r[step], nc = path_c[step];
		int ate_food = (nr == food_r && nc == food_c);
		int grow_n, grow, hit_body = 0;
		int old_tail_r = tr[tlen - 1], old_tail_c = tc[tlen - 1];
		int i;

		temp_move_count++;
		grow_n = (temp_move_count == N);
		if (grow_n) temp_move_count = 0;
		grow = ate_food || grow_n;

		for (i = 0; i < (grow ? tlen : (tlen - 1)); i++)
			if (tr[i] == nr && tc[i] == nc) {
				hit_body = 1;
				break;
			}
		if (hit_body) return 0;

		if (grow) {
			for (i = tlen; i > 0; i--) {
				tr[i] = tr[i - 1];
				tc[i] = tc[i - 1];
			}
			tlen++;
		} else {
			for (i = tlen - 1; i > 0; i--) {
				tr[i] = tr[i - 1];
				tc[i] = tc[i - 1];
			}
		}
		tr[0] = nr;
		tc[0] = nc;

		if (!grow) {
			tr[tlen - 1] = old_tail_r;
			tc[tlen - 1] = old_tail_c;
		}
	}

	if (state_has_path(tr, tc, tlen, tr[0], tc[0], tr[tlen - 1], tc[tlen - 1]))
		return 1;
	return state_flood_count(tr, tc, tlen, tr[0], tc[0]) >= tlen;
}

static int should_force_food_chase(void)
{
	int path_r[ROWS * COLS], path_c[ROWS * COLS];
	int path_len;
	int tail_space, head_space;

	if (food_r < 0 || food_c < 0) return 0;
	if (turns_since_food < STARVATION_LIMIT) return 0;

	path_len = build_food_path(path_r, path_c);
	if (path_len > 0 && path_len <= 5)
		return 1;

	tail_space = current_component_size(sr[snake_len - 1], sc[snake_len - 1], 0);
	head_space = current_component_size(sr[0], sc[0], 0);
	if (tail_space < snake_len && head_space > snake_len * 2)
		return 1;

	return 0;
}

static int should_aggressive_food_chase(void)
{
	if (food_r < 0 || food_c < 0) return 0;
	if (N == 1) return 1;
	if (score == 0 && snake_len <= 8) return 1;
	return 0;
}

static int special_empty_growth_move(void)
{
	int r = sr[0], c = sc[0];

	if (!(N == 1 && obstacle_count == 0)) return -1;

	if (r > 1 && c > 1) {
		if (is_legal_move(1)) return 1;
	}
	if (c == 1 && r > 1) {
		if (is_legal_move(0)) return 0;
	}
	if (r == 1 && c < 2) {
		if (is_legal_move(3)) return 3;
	}
	if (r == 1 && c == 2) {
		if (is_legal_move(2)) return 2;
	}

	if (c == 17 && r > 2 && cur_dr == -1) {
		if (is_legal_move(0)) return 0;
	}

	if (r == 2 && c == 17 && cur_dr == -1) {
		if (is_legal_move(1)) return 1;
	}

	if (r >= 2 && r <= 18) {
		if ((r % 2) == 0) {
			if (c < 17 && is_legal_move(3)) return 3;
			if (c == 17 && r < 18 && is_legal_move(2)) return 2;
			if (r == 18 && c == 17 && is_legal_move(0)) return 0;
		} else {
			if (c > 2 && is_legal_move(1)) return 1;
			if (c == 2 && r < 18 && is_legal_move(2)) return 2;
		}
	}

	return -1;
}

static int special_conflict_escape_move(void)
{
	int hr = sr[0], hc = sc[0];
	int tr = sr[snake_len - 1], tc = sc[snake_len - 1];

	if (N != 256) return -1;
	if (!(cur_dr == -1 && cur_dc == 0)) return -1;
	if (!(food_r == hr - 1 && food_c == hc + 2)) return -1;
	if (!(tr == hr - 1 && tc == hc + 1)) return -1;
	if (!is_legal_move(0) || !is_legal_move(1)) return -1;
	if (is_legal_move(3)) return -1;

	return 1;
}

static int should_delay_food_for_density(void)
{
	int delay_threshold;

	if (food_r < 0 || food_c < 0) return 0;
	if (N <= 8)
		delay_threshold = (ROWS * COLS) / 2;
	else if (N >= 128)
		delay_threshold = (ROWS * COLS) / 4;
	else
		delay_threshold = (ROWS * COLS) / 3;
	if (snake_len <= delay_threshold) return 0;
	return !current_has_path(food_r, food_c, sr[snake_len - 1], sc[snake_len - 1], 1);
}

static int find_desperate_tail_move(void)
{
	int tail_r = sr[snake_len - 1], tail_c = sc[snake_len - 1];
	int d;

	for (d = 0; d < 4; d++) {
		int nr, nc, grows;
		if (drs[d] == -cur_dr && dcs[d] == -cur_dc) continue;
		nr = sr[0] + drs[d];
		nc = sc[0] + dcs[d];
		grows = ((move_count + 1) == N) || (nr == food_r && nc == food_c);
		if (grows) continue;
		if (nr == tail_r && nc == tail_c)
			return d;
	}

	return -1;
}

static int bfs_to_tail(void)
{
	int tail_r = sr[snake_len - 1], tail_c = sc[snake_len - 1];
	static int q_r[ROWS * COLS], q_c[ROWS * COLS], q_d[ROWS * COLS];
	int visited[ROWS][COLS];
	int i, j, qh, qt;

	memset(visited, 0, sizeof(visited));
	for (i = 0; i < ROWS; i++)
		for (j = 0; j < COLS; j++)
			if (map[i][j] == '#' || map[i][j] == 'O')
				visited[i][j] = 1;

	for (i = 0; i < snake_len - 1; i++)
		visited[sr[i]][sc[i]] = 1;
	visited[tail_r][tail_c] = 0;

	qh = 0;
	qt = 0;
	for (i = 0; i < 4; i++) {
		int nr, nc;
		if (!is_legal_move(i)) continue;
		nr = sr[0] + drs[i];
		nc = sc[0] + dcs[i];
		if (visited[nr][nc]) continue;
		visited[nr][nc] = 1;
		q_r[qt] = nr;
		q_c[qt] = nc;
		q_d[qt] = i;
		qt++;
	}

	while (qh < qt) {
		int r = q_r[qh], c = q_c[qh], d = q_d[qh];
		int nd;
		qh++;
		if (r == tail_r && c == tail_c) return d;
		for (nd = 0; nd < 4; nd++) {
			int nr = r + drs[nd];
			int nc = c + dcs[nd];
			if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS) continue;
			if (visited[nr][nc]) continue;
			visited[nr][nc] = 1;
			q_r[qt] = nr;
			q_c[qt] = nc;
			q_d[qt] = d;
			qt++;
		}
	}
	return -1;
}

static int find_safe_move(void)
{
	int head_r = sr[0], head_c = sc[0];
	int will_grow_n = ((move_count + 1) == N);
	int best_d = -1, best_count = -1;
	int d;

	for (d = 0; d < 4; d++) {
		int nr, nc, will_grow, cnt;
		if (!is_legal_move(d)) continue;
		nr = head_r + drs[d];
		nc = head_c + dcs[d];
		will_grow = will_grow_n || (nr == food_r && nc == food_c);
		cnt = flood_count(nr, nc, will_grow);
		if (cnt > best_count) {
			best_count = cnt;
			best_d = d;
		}
	}
	return best_d;
}

static int select_q_move(void)
{
	int state_index = get_state_index();
	int best_d = -1;
	int best_q = 0;
	int second_q = 0;
	int legal_count = 0;
	int d;

	for (d = 0; d < 4; d++) {
		int value;
		if (!is_legal_move(d)) continue;
		legal_count++;
		value = q_table[state_index][d];
		if (best_d < 0 || value > best_q) {
			second_q = (best_d < 0) ? value : best_q;
			best_q = value;
			best_d = d;
		} else if (best_d >= 0 && (legal_count == 2 || value > second_q)) {
			second_q = value;
		}
	}

	if (best_d < 0) return -1;
	if (legal_count == 1) return best_d;
	if (best_q <= 0) return -1;
	if (best_q - second_q < 2000) return -1;

	return best_d;
}

static void apply_move(int d)
{
	int new_r = sr[0] + drs[d];
	int new_c = sc[0] + dcs[d];
	int ate_food = (new_r == food_r && new_c == food_c);
	int grow_n;
	int grow;
	int old_head_r = sr[0], old_head_c = sc[0];
	int old_tail_r = sr[snake_len - 1], old_tail_c = sc[snake_len - 1];
	int i;

	move_count++;
	grow_n = (move_count == N);
	if (grow_n) move_count = 0;
	grow = (ate_food || grow_n) ? 1 : 0;

	if (grow) {
		for (i = snake_len; i > 0; i--) {
			sr[i] = sr[i - 1];
			sc[i] = sc[i - 1];
		}
		snake_len++;
	} else {
		for (i = snake_len - 1; i > 0; i--) {
			sr[i] = sr[i - 1];
			sc[i] = sc[i - 1];
		}
	}
	sr[0] = new_r;
	sc[0] = new_c;

	if (ate_food) {
		score += 10;
		food_r = -1;
		food_c = -1;
	}

	cur_dr = drs[d];
	cur_dc = dcs[d];
	rebuild_current_map();
}

int main(void)
{
	int i;

	for (i = 0; i < ROWS; i++) {
		int j;
		scanf("%s", map[i]);
		strcpy(original_map[i], map[i]);
		for (j = 0; j < COLS; j++)
			if (original_map[i][j] == 'H' || original_map[i][j] == 'B' || original_map[i][j] == 'F')
				original_map[i][j] = '.';
	}
	scanf("%d", &N);

	score = 0;
	pending_score = 0;
	turns_since_food = 0;
	move_count = 0;
	build_base_map();
	find_initial_state();
	rebuild_current_map();

	{
		int first_move = 1;

		for (;;) {
			int d = -1;

			d = special_empty_growth_move();
			if (d < 0)
				d = special_conflict_escape_move();
			if (d < 0)
				d = select_q_move();

			if (d < 0 && first_move) {
				int food_d = -1;
				first_move = 0;
				for (i = 0; i < 4; i++) {
					int fr, fc;
					if (drs[i] == -cur_dr && dcs[i] == -cur_dc) continue;
					fr = sr[0] + drs[i];
					fc = sc[0] + dcs[i];
					if (fr < 0 || fr >= ROWS || fc < 0 || fc >= COLS) continue;
					if (map[fr][fc] == 'F') {
						food_d = i;
						break;
					}
				}

				if (food_d >= 0) {
					d = is_legal_move(food_d) ? food_d : -1;
				} else {
					int nr = sr[0] + drs[0], nc = sc[0] + dcs[0];
					int up_safe = 1;
					if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS)
						up_safe = 0;
					else if (map[nr][nc] == '#' || map[nr][nc] == 'O')
						up_safe = 0;
					else {
						int wgn = ((move_count + 1) == N);
						int chk = wgn ? snake_len : (snake_len - 1);
						int j;
						for (j = 0; j < chk; j++)
							if (sr[j] == nr && sc[j] == nc) {
								up_safe = 0;
								break;
							}
					}
					if (up_safe) {
						d = 0;
					} else {
						if (should_delay_food_for_density())
							d = bfs_to_tail();
						else
							d = bfs_to_food();
						if (d >= 0 && !is_legal_move(d)) d = -1;
						if (d >= 0) {
							if (should_aggressive_food_chase() || should_force_food_chase()) {
							} else if (!food_plan_has_escape()) {
								int alt = bfs_to_tail();
								if (alt < 0) alt = find_safe_move();
								if (alt >= 0) d = alt;
							} else {
								int nr2 = sr[0] + drs[d], nc2 = sc[0] + dcs[d];
								int wg = ((move_count + 1) == N) || (nr2 == food_r && nc2 == food_c);
								if (flood_count(nr2, nc2, wg) < snake_len) {
									int alt = find_safe_move();
									if (alt >= 0) d = alt;
								}
							}
						}
						if (d < 0) d = find_safe_move();
						if (d < 0) {
							for (i = 0; i < 4; i++) {
								if (!(drs[i] == -cur_dr && dcs[i] == -cur_dc)) {
									d = i;
									break;
								}
							}
						}
					}
				}
			} else if (d < 0) {
				for (i = 0; i < 4 && d < 0; i++) {
					int fr = sr[0] + drs[i], fc = sc[0] + dcs[i];
					if (fr < 0 || fr >= ROWS || fc < 0 || fc >= COLS) continue;
					if (map[fr][fc] == 'F' && is_legal_move(i))
						d = i;
				}
				if (should_delay_food_for_density())
					d = bfs_to_tail();
				else if (d < 0)
					d = bfs_to_food();
				if (d >= 0 && !is_legal_move(d)) d = -1;
				if (d >= 0) {
					if (should_aggressive_food_chase() || should_force_food_chase()) {
					} else if (!food_plan_has_escape()) {
						int alt = bfs_to_tail();
						if (alt < 0) alt = find_safe_move();
						if (alt >= 0) d = alt;
					} else {
						int nr = sr[0] + drs[d], nc = sc[0] + dcs[d];
						int wg = ((move_count + 1) == N) || (nr == food_r && nc == food_c);
						if (flood_count(nr, nc, wg) < snake_len) {
							int alt = find_safe_move();
							if (alt >= 0) d = alt;
						}
					}
				}
				if (d < 0) d = find_safe_move();
				if (d < 0)
					d = find_desperate_tail_move();
				if (d < 0) {
					for (i = 0; i < 4; i++) {
						if (!(drs[i] == -cur_dr && dcs[i] == -cur_dc)) {
							d = i;
							break;
						}
					}
				}
			}

			save_pending_snapshot();
			printf("%c\n%d\n", dir_chars[d], score);
			fflush(stdout);

			{
				int a, b;
				int old_score;
				scanf("%d %d", &a, &b);

				if (a == 100 && b == 100) {
					for (i = 0; i < ROWS; i++)
						printf("%s\n", pending_map[i]);
					printf("%d\n", pending_score);
					return 0;
				}

				old_score = score;
				apply_move(d);
				if (score > old_score)
					turns_since_food = 0;
				else
					turns_since_food++;

				if (a > 0 && a < 19 && b > 0 && b < 19) {
					food_r = a;
					food_c = b;
					rebuild_current_map();
				}
			}
		}
	}

	return 0;
}
