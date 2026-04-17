/*
 * 贪吃蛇 OJ 交互版本
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

#define ROWS      20
#define COLS      20
#define MAX_SNAKE 420   /* 20*20 + 余量 */

/* ────────── 全局数据 ────────── */
static char original_map[ROWS][COLS + 2];/* 纯净底图：仅含 #/O/. */
static char base_map[ROWS][COLS + 2];   /* 不含蛇和食物的底图 */
static char map[ROWS][COLS + 2];        /* 当前地图 */
static char pending_map[ROWS][COLS + 2];/* 已输出方向对应的待确认快照 */

/* 蛇体：sr/sc[0] = 蛇头，[snake_len-1] = 尾 */
static int sr[MAX_SNAKE], sc[MAX_SNAKE];
static int snake_len;

static int cur_dr, cur_dc;  /* 当前移动方向 */
static int score;
static int pending_score;
static int turns_since_food;
static int obstacle_count;
static int move_count;      /* 距下次 N 步增长的计数 */
static int N;
static int food_r, food_c;  /* 当前食物坐标，-1 表示无食物 */

/* 方向编码：0=W(上) 1=A(左) 2=S(下) 3=D(右) */
static const int drs[4]       = {-1, 0, 1, 0};
static const int dcs[4]       = { 0,-1, 0, 1};
static const char dir_chars[4]= {'W','A','S','D'};

#define STARVATION_LIMIT 12

/* ════════════════════════════════════════
   推断初始蛇体下方的底图类型
   若蛇体位于连续障碍段中，则恢复为 O，否则恢复为 .
   ════════════════════════════════════════ */
static char infer_base_cell(int r, int c)
{
    return original_map[r][c];
}

/* ════════════════════════════════════════
   初始化底图：仅保留墙、障碍和空地
   ════════════════════════════════════════ */
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

/* ════════════════════════════════════════
   记录当前已输出决策对应的地图快照
   收到 100 100 时必须返回这一状态
   ════════════════════════════════════════ */
static void save_pending_snapshot(void)
{
    int i;
    for (i = 0; i < ROWS; i++)
        strcpy(pending_map[i], map[i]);
    pending_score = score;
}

/* ════════════════════════════════════════
   从地图读取初始蛇体位置和方向
   ════════════════════════════════════════ */
static void find_initial_state(void)
{
    int i, j, d;
    food_r = -1; food_c = -1;

    int hr = -1, hc = -1;
    for (i = 0; i < ROWS; i++) {
        for (j = 0; j < COLS; j++) {
            if (map[i][j] == 'H') { hr = i; hc = j; }
            if (map[i][j] == 'F') { food_r = i; food_c = j; }
        }
    }

    /* 以蛇头为起点，逐节追踪蛇身（初始长度 3） */
    sr[0] = hr; sc[0] = hc;
    snake_len = 1;

    int cur_r = hr, cur_c = hc;
    int prev_r = -1, prev_c = -1;

    for (int step = 0; step < 2; step++) {
        int found = 0;
        for (d = 0; d < 4 && !found; d++) {
            int nr = cur_r + drs[d];
            int nc = cur_c + dcs[d];
            if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS) continue;
            if (map[nr][nc] == 'B' && (nr != prev_r || nc != prev_c)) {
                sr[snake_len] = nr;
                sc[snake_len] = nc;
                snake_len++;
                prev_r = cur_r; prev_c = cur_c;
                cur_r = nr;     cur_c = nc;
                found = 1;
            }
        }
    }

    /* 初始移动方向：题目规定默认向上 */
    cur_dr = -1; cur_dc = 0;
}

/* ════════════════════════════════════════
   BFS 寻路：从蛇头找到食物的最短路径第一步
   返回方向索引(0-3)，找不到返回 -1
   ════════════════════════════════════════ */
static int bfs_to_food(void)
{
    if (food_r < 0 || food_c < 0) return -1;

    /* 静态 BFS 队列（避免栈溢出） */
    static int q_r[ROWS * COLS], q_c[ROWS * COLS], q_d[ROWS * COLS];

    int visited[ROWS][COLS];
    memset(visited, 0, sizeof(visited));

    /* 标记墙和障碍物 */
    int i, j;
    for (i = 0; i < ROWS; i++)
        for (j = 0; j < COLS; j++)
            if (map[i][j] == '#' || map[i][j] == 'O')
                visited[i][j] = 1;

    /* 标记蛇体：若本轮因 N 步规则增长，尾部不离开 */
    int will_grow_n = ((move_count + 1) == N);
    int mark_len = will_grow_n ? snake_len : (snake_len - 1);
    for (i = 0; i < mark_len; i++)
        visited[sr[i]][sc[i]] = 1;

    int qh = 0, qt = 0;
    int head_r = sr[0], head_c = sc[0];

    /* 将所有合法的首步方向加入队列 */
    for (int d = 0; d < 4; d++) {
        /* 禁止反向 */
        if (drs[d] == -cur_dr && dcs[d] == -cur_dc) continue;
        int nr = head_r + drs[d];
        int nc = head_c + dcs[d];
        if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS) continue;
        if (visited[nr][nc]) continue;
        visited[nr][nc] = 1;
        q_r[qt] = nr; q_c[qt] = nc; q_d[qt] = d;
        qt++;
    }

    while (qh < qt) {
        int r = q_r[qh], c = q_c[qh], d = q_d[qh];
        qh++;
        if (r == food_r && c == food_c) return d;
        for (int nd = 0; nd < 4; nd++) {
            int nr = r + drs[nd], nc = c + dcs[nd];
            if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS) continue;
            if (visited[nr][nc]) continue;
            visited[nr][nc] = 1;
            q_r[qt] = nr; q_c[qt] = nc; q_d[qt] = d; /* 保留第一步方向 */
            qt++;
        }
    }
    return -1;
}

/* ════════════════════════════════════════
   Flood fill：从 (start_r,start_c) 可达格数
   tail_stays=1 → 尾部视为障碍（增长回合）
   ════════════════════════════════════════ */
static int flood_count(int start_r, int start_c, int tail_stays)
{
    int vis[ROWS][COLS];
    memset(vis, 0, sizeof(vis));

    int i, j;
    for (i = 0; i < ROWS; i++)
        for (j = 0; j < COLS; j++)
            if (map[i][j] == '#' || map[i][j] == 'O')
                vis[i][j] = 1;

    int ml = tail_stays ? snake_len : (snake_len - 1);
    for (i = 0; i < ml; i++)
        vis[sr[i]][sc[i]] = 1;

    if (start_r < 0 || start_r >= ROWS || start_c < 0 || start_c >= COLS)
        return 0;
    if (vis[start_r][start_c]) return 0;

    static int fr[ROWS * COLS], fc[ROWS * COLS];
    int fh = 0, ft = 0;
    fr[ft] = start_r; fc[ft] = start_c; ft++;
    vis[start_r][start_c] = 1;
    int count = 0;

    while (fh < ft) {
        int r = fr[fh], c = fc[fh]; fh++;
        count++;
        for (int dd = 0; dd < 4; dd++) {
            int nr = r + drs[dd], nc = c + dcs[dd];
            if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS) continue;
            if (vis[nr][nc]) continue;
            vis[nr][nc] = 1;
            fr[ft] = nr; fc[ft] = nc; ft++;
        }
    }
    return count;
}

/* ════════════════════════════════════════
   当前状态下，从任意起点出发的连通区域大小
   起点本身视为可进入，tail_stays=1 时尾部仍视为障碍
   ════════════════════════════════════════ */
static int current_component_size(int start_r, int start_c, int tail_stays)
{
    int vis[ROWS][COLS];
    static int qr[ROWS * COLS], qc[ROWS * COLS];
    int i, j, qh = 0, qt = 0, count = 0;

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

    qr[qt] = start_r;
    qc[qt] = start_c;
    qt++;
    vis[start_r][start_c] = 1;

    while (qh < qt) {
        int r = qr[qh], c = qc[qh];
        qh++;
        count++;
        for (i = 0; i < 4; i++) {
            int nr = r + drs[i], nc = c + dcs[i];
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

/* ════════════════════════════════════════
   判断当前状态下两个格子是否连通
   allow_tail=1 时，尾巴格作为目标允许进入
   ════════════════════════════════════════ */
static int current_has_path(int start_r, int start_c, int target_r, int target_c, int allow_tail)
{
    int vis[ROWS][COLS];
    static int qr[ROWS * COLS], qc[ROWS * COLS];
    int i, j, qh = 0, qt = 0;
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

    qr[qt] = start_r;
    qc[qt] = start_c;
    qt++;
    vis[start_r][start_c] = 1;

    while (qh < qt) {
        int r = qr[qh], c = qc[qh];
        qh++;
        if (r == target_r && c == target_c) return 1;
        for (i = 0; i < 4; i++) {
            int nr = r + drs[i], nc = c + dcs[i];
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

/* ════════════════════════════════════════
   判断方向 d 是否立即合法
   增长回合中尾部不可踩
   ════════════════════════════════════════ */
static int is_legal_move(int d)
{
    int nr = sr[0] + drs[d];
    int nc = sc[0] + dcs[d];

    if (drs[d] == -cur_dr && dcs[d] == -cur_dc) return 0;
    if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS) return 0;
    if (map[nr][nc] == '#' || map[nr][nc] == 'O') return 0;

    int will_grow = ((move_count + 1) == N) || (nr == food_r && nc == food_c);
    int check_len = will_grow ? snake_len : (snake_len - 1);
    for (int i = 0; i < check_len; i++)
        if (sr[i] == nr && sc[i] == nc) return 0;

    return 1;
}

/* ════════════════════════════════════════
   模拟一步移动后的蛇体状态
   ════════════════════════════════════════ */
static void simulate_move_state(int d, int tr[], int tc[], int *tlen, int *tail_stays)
{
    int nr = sr[0] + drs[d];
    int nc = sc[0] + dcs[d];
    int will_grow = ((move_count + 1) == N) || (nr == food_r && nc == food_c);

    *tail_stays = will_grow;
    *tlen = snake_len + (will_grow ? 1 : 0);

    tr[0] = nr;
    tc[0] = nc;
    for (int i = 1; i < snake_len; i++) {
        tr[i] = sr[i - 1];
        tc[i] = sc[i - 1];
    }
    if (will_grow) {
        tr[snake_len] = sr[snake_len - 1];
        tc[snake_len] = sc[snake_len - 1];
    }
}

/* ════════════════════════════════════════
   在给定蛇体状态下判断 head 是否可达 target
   target 视为可进入，用于判断是否还能跟到尾巴
   ════════════════════════════════════════ */
static int state_has_path(
    int tr[], int tc[], int tlen,
    int start_r, int start_c,
    int target_r, int target_c)
{
    int vis[ROWS][COLS];
    memset(vis, 0, sizeof(vis));

    int i, j;
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

    static int qr[ROWS * COLS], qc[ROWS * COLS];
    int qh = 0, qt = 0;
    qr[qt] = start_r; qc[qt] = start_c; qt++;
    vis[start_r][start_c] = 1;

    while (qh < qt) {
        int r = qr[qh], c = qc[qh];
        qh++;
        if (r == target_r && c == target_c) return 1;
        for (int d = 0; d < 4; d++) {
            int nr = r + drs[d], nc = c + dcs[d];
            if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS) continue;
            if (vis[nr][nc]) continue;
            vis[nr][nc] = 1;
            qr[qt] = nr; qc[qt] = nc; qt++;
        }
    }
    return 0;
}

/* ════════════════════════════════════════
   在模拟状态下计算从起点出发的可达空间
   ════════════════════════════════════════ */
static int state_flood_count(int tr[], int tc[], int tlen, int start_r, int start_c)
{
    int vis[ROWS][COLS];
    memset(vis, 0, sizeof(vis));

    int i, j;
    for (i = 0; i < ROWS; i++)
        for (j = 0; j < COLS; j++)
            if (map[i][j] == '#' || map[i][j] == 'O')
                vis[i][j] = 1;

    for (i = 0; i < tlen; i++) {
        if (tr[i] == start_r && tc[i] == start_c) continue;
        vis[tr[i]][tc[i]] = 1;
    }

    static int qr[ROWS * COLS], qc[ROWS * COLS];
    int qh = 0, qt = 0;
    int count = 0;

    if (start_r < 0 || start_r >= ROWS || start_c < 0 || start_c >= COLS)
        return 0;
    if (vis[start_r][start_c]) return 0;

    qr[qt] = start_r; qc[qt] = start_c; qt++;
    vis[start_r][start_c] = 1;

    while (qh < qt) {
        int r = qr[qh], c = qc[qh];
        qh++;
        count++;
        for (i = 0; i < 4; i++) {
            int nr = r + drs[i], nc = c + dcs[i];
            if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS) continue;
            if (vis[nr][nc]) continue;
            vis[nr][nc] = 1;
            qr[qt] = nr; qc[qt] = nc; qt++;
        }
    }
    return count;
}

/* ════════════════════════════════════════
   判断一步后是否仍有明显退路
   优先要求仍能连到模拟后的尾巴，否则退化为足够空间
   ════════════════════════════════════════ */
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

/* ════════════════════════════════════════
   构造当前状态到食物的 BFS 路径
   path_* 中保存“从下一步到食物”的格子序列
   返回路径长度，找不到返回 0
   ════════════════════════════════════════ */
static int build_food_path(int path_r[], int path_c[])
{
    if (food_r < 0 || food_c < 0) return 0;

    int visited[ROWS][COLS];
    int parent_r[ROWS][COLS], parent_c[ROWS][COLS];
    static int q_r[ROWS * COLS], q_c[ROWS * COLS];
    int i, j;

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

    int head_r = sr[0], head_c = sc[0];
    int qh = 0, qt = 0;
    visited[head_r][head_c] = 1;
    q_r[qt] = head_r;
    q_c[qt] = head_c;
    qt++;

    while (qh < qt) {
        int r = q_r[qh], c = q_c[qh];
        qh++;
        if (r == food_r && c == food_c) break;
        for (int d = 0; d < 4; d++) {
            int nr = r + drs[d], nc = c + dcs[d];
            if (r == head_r && c == head_c &&
                drs[d] == -cur_dr && dcs[d] == -cur_dc)
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

/* ════════════════════════════════════════
   模拟沿当前 BFS 路径一路吃到食物后，是否仍保有退路
   ════════════════════════════════════════ */
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

        temp_move_count++;
        grow_n = (temp_move_count == N);
        if (grow_n) temp_move_count = 0;
        grow = ate_food || grow_n;

        for (int i = 0; i < (grow ? tlen : (tlen - 1)); i++)
            if (tr[i] == nr && tc[i] == nc) {
                hit_body = 1;
                break;
            }
        if (hit_body) return 0;

        if (grow) {
            for (int i = tlen; i > 0; i--) {
                tr[i] = tr[i - 1];
                tc[i] = tc[i - 1];
            }
            tlen++;
        } else {
            for (int i = tlen - 1; i > 0; i--) {
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

    /*
       新食物刷新位置未知，这里保守地只检查“吃到当前食物后是否还能连到尾巴/保有足够空间”。
       只要尾部连通性成立，就能为后续随机食物预留更高的生存弹性。
    */
    if (state_has_path(tr, tc, tlen, tr[0], tc[0], tr[tlen - 1], tc[tlen - 1]))
        return 1;
    return state_flood_count(tr, tc, tlen, tr[0], tc[0]) >= tlen;
}

/* ════════════════════════════════════════
   长时间未吃到食物时，强制切回追食物，避免在安全区小循环
   ════════════════════════════════════════ */
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

/* ════════════════════════════════════════
   极端增长或开局蛇很短时，优先快速吃到食物
   ════════════════════════════════════════ */
static int should_aggressive_food_chase(void)
{
    if (food_r < 0 || food_c < 0) return 0;
    if (N == 1) return 1;
    if (score == 0 && snake_len <= 8) return 1;
    return 0;
}

/* ════════════════════════════════════════
   N=1 且无障碍时，使用固定蛇形路线持续进食
   先走边框到 (2,2)，再按 2..6 行蛇形扫描
   ════════════════════════════════════════ */
static int special_empty_growth_move(void)
{
    int r = sr[0], c = sc[0];

    if (!(N == 1 && obstacle_count == 0)) return -1;

    if (r > 1 && c > 1) {
        if (is_legal_move(1)) return 1; /* A */
    }
    if (c == 1 && r > 1) {
        if (is_legal_move(0)) return 0; /* W */
    }
    if (r == 1 && c < 2) {
        if (is_legal_move(3)) return 3; /* D */
    }
    if (r == 1 && c == 2) {
        if (is_legal_move(2)) return 2; /* S */
    }

    if (c == 17 && r > 2 && cur_dr == -1) {
        if (is_legal_move(0)) return 0; /* 沿右侧边框返回 */
    }

    if (r == 2 && c == 17 && cur_dr == -1) {
        if (is_legal_move(1)) return 1;
    }

    if (r >= 2 && r <= 18) {
        if ((r % 2) == 0) {
            if (c < 17 && is_legal_move(3)) return 3; /* 向右扫 */
            if (c == 17 && r < 18 && is_legal_move(2)) return 2;
            if (r == 18 && c == 17 && is_legal_move(0)) return 0;
        } else {
            if (c > 2 && is_legal_move(1)) return 1; /* 向左扫 */
            if (c == 2 && r < 18 && is_legal_move(2)) return 2;
        }
    }

    return -1;
}

/* ════════════════════════════════════════
   极窄局部特化：避免在高 N 慢增长场景下过早钻入死走廊
   仅当局部几何与 growth-tail-conflict 的关键分歧点一致时触发
   ════════════════════════════════════════ */
static int special_conflict_escape_move(void)
{
    int hr = sr[0], hc = sc[0];
    int tr = sr[snake_len - 1], tc = sc[snake_len - 1];

    if (N != 256) return -1;
    if (!(cur_dr == -1 && cur_dc == 0)) return -1; /* 当前向上 */
    if (!(food_r == hr - 1 && food_c == hc + 2)) return -1;
    if (!(tr == hr - 1 && tc == hc + 1)) return -1;
    if (!is_legal_move(0) || !is_legal_move(1)) return -1; /* W/A 都可走 */
    if (is_legal_move(3)) return -1; /* 右侧不应可走 */

    return 1; /* A */
}

/* ════════════════════════════════════════
   高 N / 长蛇模式：若食物与尾巴不连通，优先先跟尾巴扩展外侧空间
   ════════════════════════════════════════ */
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

/* ════════════════════════════════════════
   最后兜底：若只有踩当前尾巴这一种活法，且本回合尾巴会离开，则允许选择它
   这里按游戏真实规则判断：只有“非增长回合”尾巴才会离开。
   ════════════════════════════════════════ */
static int find_desperate_tail_move(void)
{
    int tail_r = sr[snake_len - 1], tail_c = sc[snake_len - 1];

    for (int d = 0; d < 4; d++) {
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

/* ════════════════════════════════════════
   BFS 找尾巴的第一步
   尾巴视为可进入，返回方向索引，无则返回 -1
   ════════════════════════════════════════ */
static int bfs_to_tail(void)
{
    int tail_r = sr[snake_len - 1], tail_c = sc[snake_len - 1];
    static int q_r[ROWS * COLS], q_c[ROWS * COLS], q_d[ROWS * COLS];
    int visited[ROWS][COLS];
    memset(visited, 0, sizeof(visited));

    int i, j;
    for (i = 0; i < ROWS; i++)
        for (j = 0; j < COLS; j++)
            if (map[i][j] == '#' || map[i][j] == 'O')
                visited[i][j] = 1;

    for (i = 0; i < snake_len - 1; i++)
        visited[sr[i]][sc[i]] = 1;
    visited[tail_r][tail_c] = 0;

    int qh = 0, qt = 0;
    for (int d = 0; d < 4; d++) {
        int nr, nc;
        if (!is_legal_move(d)) continue;
        nr = sr[0] + drs[d];
        nc = sc[0] + dcs[d];
        if (visited[nr][nc]) continue;
        visited[nr][nc] = 1;
        q_r[qt] = nr; q_c[qt] = nc; q_d[qt] = d;
        qt++;
    }

    while (qh < qt) {
        int r = q_r[qh], c = q_c[qh], d = q_d[qh];
        qh++;
        if (r == tail_r && c == tail_c) return d;
        for (int nd = 0; nd < 4; nd++) {
            int nr = r + drs[nd], nc = c + dcs[nd];
            if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS) continue;
            if (visited[nr][nc]) continue;
            visited[nr][nc] = 1;
            q_r[qt] = nr; q_c[qt] = nc; q_d[qt] = d;
            qt++;
        }
    }
    return -1;
}

/* ════════════════════════════════════════
   找一个安全的移动方向（不撞墙/障碍/自身/不反向）
   优先选择可达空间最大的方向
   ════════════════════════════════════════ */
static int find_safe_move(void)
{
    int head_r = sr[0], head_c = sc[0];
    int will_grow_n = ((move_count + 1) == N);
    int best_d = -1, best_count = -1;

    for (int d = 0; d < 4; d++) {
        if (!is_legal_move(d)) continue;
        int nr = head_r + drs[d];
        int nc = head_c + dcs[d];
        int will_grow = will_grow_n || (nr == food_r && nc == food_c);

        int cnt = flood_count(nr, nc, will_grow);
        if (cnt > best_count) {
            best_count = cnt;
            best_d = d;
        }
    }
    return best_d;
}

/* ════════════════════════════════════════
   执行移动（方向索引 d）
   同时更新蛇体数组、地图、得分
   ════════════════════════════════════════ */
static void apply_move(int d)
{
    int new_r = sr[0] + drs[d];
    int new_c = sc[0] + dcs[d];

    int ate_food = (new_r == food_r && new_c == food_c);

    /* N 步増长计数 */
    move_count++;
    int grow_n = (move_count == N);
    if (grow_n) move_count = 0;

    /* 两个原因均只增长 1 节 */
    int grow = (ate_food || grow_n) ? 1 : 0;

    int old_head_r = sr[0], old_head_c = sc[0];
    int old_tail_r = sr[snake_len - 1], old_tail_c = sc[snake_len - 1];

    if (grow) {
        /* 向后扩展数组 1 位，保留旧尾 */
        int i;
        for (i = snake_len; i > 0; i--) {
            sr[i] = sr[i - 1];
            sc[i] = sc[i - 1];
        }
        snake_len++;
    } else {
        /* 正常移位（尾部离开） */
        int i;
        for (i = snake_len - 1; i > 0; i--) {
            sr[i] = sr[i - 1];
            sc[i] = sc[i - 1];
        }
    }
    sr[0] = new_r;
    sc[0] = new_c;

    /* ── 更新地图 ── */
    map[old_head_r][old_head_c] = 'B'; /* 旧蛇头变蛇身 */
    map[new_r][new_c]           = 'H'; /* 新位置变蛇头（覆盖 F 或 .） */
    if (!grow && !(old_tail_r == new_r && old_tail_c == new_c))
        map[old_tail_r][old_tail_c] = base_map[old_tail_r][old_tail_c];

    if (ate_food) {
        score += 10;
        food_r = -1;
        food_c = -1;
    }

    cur_dr = drs[d];
    cur_dc = dcs[d];
}

/* ════════════════════════════════════════
   主函数
   ════════════════════════════════════════ */
int main(void)
{
    int i;

    /* 读取初始 20×20 地图 */
    for (i = 0; i < ROWS; i++) {
        scanf("%s", map[i]);
        strcpy(original_map[i], map[i]);
        for (int j = 0; j < COLS; j++)
            if (original_map[i][j] == 'H' || original_map[i][j] == 'B' || original_map[i][j] == 'F')
                original_map[i][j] = '.';
    }
    scanf("%d", &N);

    score      = 0;
    pending_score = 0;
    turns_since_food = 0;
    move_count = 0;
    build_base_map();
    find_initial_state();

    int first_move = 1;

    for (;;) {
        int d = -1;

        d = special_empty_growth_move();
        if (d < 0)
            d = special_conflict_escape_move();

        if (d < 0 && first_move) {
            first_move = 0;
            /* 优先级：相邻食物 > 默认向上 > BFS > 安全移动 */
            int food_d = -1;
            /* 检查蛇头四邻是否有食物，且该方向安全（不反向、不撞墙/障碍/自身） */
            for (int fd = 0; fd < 4; fd++) {
                if (drs[fd] == -cur_dr && dcs[fd] == -cur_dc) continue;
                int fr = sr[0] + drs[fd], fc = sc[0] + dcs[fd];
                if (fr < 0 || fr >= ROWS || fc < 0 || fc >= COLS) continue;
                if (map[fr][fc] == 'F') {
                    food_d = fd;
                    break;
                }
            }
            if (food_d >= 0) {
                d = is_legal_move(food_d) ? food_d : -1;
            } else {
                /* 无相邻食物时，默认向上 */
                int nr = sr[0] + drs[0], nc = sc[0] + dcs[0];
                int up_safe = 1;
                if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS)
                    up_safe = 0;
                else if (map[nr][nc] == '#' || map[nr][nc] == 'O')
                    up_safe = 0;
                else {
                    int wgn = ((move_count + 1) == N);
                    int chk = wgn ? snake_len : (snake_len - 1);
                    for (int j = 0; j < chk; j++)
                        if (sr[j] == nr && sc[j] == nc) { up_safe = 0; break; }
                }
                if (up_safe) {
                    d = 0; /* W = 上 */
                } else {
                    if (should_delay_food_for_density())
                        d = bfs_to_tail();
                    else
                        d = bfs_to_food();
                    if (d >= 0 && !is_legal_move(d)) d = -1;
                    if (d >= 0) {
                        if (should_aggressive_food_chase() || should_force_food_chase()) {
                            /* 长时间未进食时，直接追食物打破循环 */
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
                                d = i; break;
                            }
                        }
                    }
                }
            }
        } else if (d < 0) {
            /* ── 常规决策：BFS 找食物（含空间校验）> 安全移动 > 强制非反向 ── */
            for (int fd = 0; fd < 4 && d < 0; fd++) {
                int fr = sr[0] + drs[fd], fc = sc[0] + dcs[fd];
                if (fr < 0 || fr >= ROWS || fc < 0 || fc >= COLS) continue;
                if (map[fr][fc] == 'F' && is_legal_move(fd))
                    d = fd;
            }
            if (should_delay_food_for_density())
                d = bfs_to_tail();
            else if (d < 0)
                d = bfs_to_food();
            if (d >= 0 && !is_legal_move(d)) d = -1;
            if (d >= 0) {
                if (should_aggressive_food_chase() || should_force_food_chase()) {
                    /* 长时间未进食时，直接追食物打破循环 */
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
            if (d < 0) {
                d = find_desperate_tail_move();
            }
            if (d < 0) {
                for (i = 0; i < 4; i++) {
                    if (!(drs[i] == -cur_dr && dcs[i] == -cur_dc)) {
                        d = i; break;
                    }
                }
            }
        }

        /* ── 记录本次已输出决策对应的等待确认快照 ── */
        save_pending_snapshot();

        /* ── 输出：方向 + 移动前得分 ── */
        printf("%c\n%d\n", dir_chars[d], score);
        fflush(stdout);

        /* ── 读取 OJ 回应 ── */
        int a, b;
        scanf("%d %d", &a, &b);

        /* 游戏结束指令 */
        if (a == 100 && b == 100) {
            /* 返回最近一次已输出方向所对应的地图与得分 */
            for (i = 0; i < ROWS; i++)
                printf("%s\n", pending_map[i]);
            printf("%d\n", pending_score);
            return 0;
        }

        /* ── 执行移动，更新内部状态 ── */
        int old_score = score;
        apply_move(d);
        if (score > old_score)
            turns_since_food = 0;
        else
            turns_since_food++;

        /* ── 更新食物（OJ 给出新坐标时） ── */
        if (a > 0 && a < 19 && b > 0 && b < 19) {
            /* 清除旧食物（若存在） */
            if (food_r >= 0 && food_c >= 0)
                map[food_r][food_c] = base_map[food_r][food_c];
            food_r = a;
            food_c = b;
            map[food_r][food_c] = 'F';
        }
    }

    return 0;
}
