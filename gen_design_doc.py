"""
生成贪吃蛇 OJ 版本 概要设计 Word 文档
"""
from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
import datetime

doc = Document()

# ── 全局样式设置 ──
style = doc.styles['Normal']
font = style.font
font.name = '宋体'
font.size = Pt(11)
style.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')

for level in range(1, 5):
    hs = doc.styles[f'Heading {level}']
    hf = hs.font
    hf.name = '黑体'
    hs.element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
    if level == 1:
        hf.size = Pt(16)
    elif level == 2:
        hf.size = Pt(14)
    elif level == 3:
        hf.size = Pt(12)
    else:
        hf.size = Pt(11)

def add_para(text, bold=False, align=None, size=None, font_name=None):
    p = doc.add_paragraph()
    run = p.add_run(text)
    if bold:
        run.bold = True
    if size:
        run.font.size = Pt(size)
    if font_name:
        run.font.name = font_name
        run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
    if align is not None:
        p.alignment = align
    return p

def add_table(headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = 'Light Grid Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            for r in p.runs:
                r.bold = True
                r.font.size = Pt(10)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = table.rows[ri + 1].cells[ci]
            cell.text = str(val)
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(10)
    return table

# ════════════════════════════════════════
# 封面
# ════════════════════════════════════════
add_para('概要设计', bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=22, font_name='黑体')
doc.add_paragraph()
add_para('贪吃蛇 — OJ 交互版本', bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=16, font_name='黑体')
doc.add_paragraph()

info_lines = [
    ('版本号', 'v2.0'),
    ('撰写时间', datetime.date.today().strftime('%Y年%m月%d日')),
    ('程序版本', 'OJ 版（单人独立完成）'),
    ('开发语言', 'C99，无平台依赖'),
    ('代码行数', '约 1060 行（单文件 game.c）'),
]
for label, value in info_lines:
    p = doc.add_paragraph()
    run_label = p.add_run(f'{label}：')
    run_label.bold = True
    p.add_run(value)

doc.add_page_break()

# ════════════════════════════════════════
# 1. 用户故事
# ════════════════════════════════════════
doc.add_heading('1. 用户故事', level=1)

doc.add_heading('1.1 游戏概述', level=2)
add_para(
    '贪吃蛇是一款经典的街机游戏，玩家操控蛇头在 20×20 的网格地图中移动，'
    '通过吃掉随机出现的食物来增长蛇身并获取分数。'
    '游戏终止条件是蛇头撞到墙壁、障碍物或自身身体，'
    '同时禁止蛇头直接向相反方向移动（如当前向右时不能直接向左）。'
)

doc.add_heading('1.2 OJ 交互流程', level=2)
add_para('本程序为在线评测（OJ）交互版本，通过标准输入输出与评测系统通信，交互协议如下：')

add_table(
    ['步骤', '方向', '说明'],
    [
        ['1', '输入', '读取 20×20 初始地图（每行 20 字符） + 第 21 行整数 N（N步增长参数）'],
        ['2', '输出', '输出一行方向字符（W/A/S/D）+ 一行移动前得分'],
        ['3', '输入', '读取两个整数 a b：1~18=新食物坐标，20 20=继续无食物，100 100=游戏结束'],
        ['4', '循环', '重复步骤 2-3，直到收到 100 100'],
        ['5', '结束', '收到 100 100 后，输出 20 行地图 + 1 行得分，然后退出'],
    ]
)

add_para('')
add_para('关键规则说明：', bold=True)
add_para('• 初始蛇长 3 格（1 头 + 2 身），默认方向向上')
add_para('• 每吃一个食物 +10 分，蛇身增长 1 节')
add_para('• 每经过 N 次移动，蛇身自动增长 1 节（N 步增长）')
add_para('• 若第 N 步恰好吃到食物，仍只增长 1 节（不叠加）')
add_para('• 增长时蛇尾不腾空（原地保留），非增长时蛇尾正常离开')
add_para('• 地图元素：#=墙 . =空地 H=蛇头 B=蛇身 F=食物 O=障碍(10个)')
add_para('• 游戏结束时须输出撞击前一时刻的地图状态')

doc.add_page_break()

# ════════════════════════════════════════
# 2. 状态与状态转换
# ════════════════════════════════════════
doc.add_heading('2. 状态与状态转换', level=1)

doc.add_heading('2.1 顶层状态图', level=2)
add_para('程序整体运行流程如下：')

p = doc.add_paragraph()
run = p.add_run(
    '初始化\n'
    '  ├─ 读取地图 + N\n'
    '  ├─ 构建 base_map/original_map\n'
    '  ├─ 解析初始蛇体坐标\n'
    '  └─ 初始化全局变量\n'
    '       ↓\n'
    '┌─────────────────────────────┐\n'
    '│        主 循 环              │\n'
    '│                              │\n'
    '│  ① 决策方向                  │\n'
    '│     ├─ 特化策略（N=1/冲突）   │\n'
    '│     └─ 常规决策引擎          │\n'
    '│          ↓                   │\n'
    '│  ② 保存 pending 快照         │\n'
    '│          ↓                   │\n'
    '│  ③ 输出方向 + 移动前得分      │\n'
    '│          ↓                   │\n'
    '│  ④ 读取 OJ 回应 (a, b)       │\n'
    '│     ├─ 100 100 → 游戏结束    │\n'
    '│     └─ 其他 → 继续           │\n'
    '│          ↓                   │\n'
    '│  ⑤ apply_move() 执行移动      │\n'
    '│          ↓                   │\n'
    '│  ⑥ 更新食物坐标              │\n'
    '│          ↓                   │\n'
    '│     循环 ←──────────────────┘ │\n'
    '└─────────────────────────────┘\n'
    '       ↓ (收到 100 100)\n'
    '输出 pending_map + pending_score\n'
    '       ↓\n'
    '     退出'
)
run.font.name = 'Consolas'
run.font.size = Pt(9)

doc.add_heading('2.2 决策子状态图', level=2)
add_para('决策引擎（decide_move）内部为多级优先级链，每一层失败后进入下一层：')

p = doc.add_paragraph()
run = p.add_run(
    '┌─ 特化策略（优先） ──────────────────────┐\n'
    '│ special_empty_growth_move()             │\n'
    '│   └─ N=1 且无障碍 → 蛇形扫描路线       │\n'
    '│ special_conflict_escape_move()          │\n'
    '│   └─ N=256 特定几何规避                 │\n'
    '└────────────────────────────────────────┘\n'
    '                ↓ (未命中)\n'
    '┌─ 首步前置（仅第1回合） ────────────────┐\n'
    '│ ① 相邻食物检测 find_adjacent_food_move │\n'
    '│ ② 默认向上 find_default_up_move        │\n'
    '└────────────────────────────────────────┘\n'
    '                ↓ (未命中 或 非首步)\n'
    '┌─ 常规决策 decide_regular_move() ───────┐\n'
    '│ ① 相邻食物检测                         │\n'
    '│ ② should_delay_food_for_density?       │\n'
    '│    → 是: bfs_to_tail (尾追)             │\n'
    '│    → 否: bfs_to_food (BFS最短到食物)    │\n'
    '│ ③ should_take_space_step?              │\n'
    '│    → 是: find_safe_move (最大空间方向)  │\n'
    '│ ④ 逃逸验证 + 空间阈值检查              │\n'
    '│    不通过 → 降级到 bfs_to_tail / safe   │\n'
    '│ ⑤ find_safe_move (兜底安全移动)        │\n'
    '│ ⑥ find_desperate_tail_move (绝望跟尾)  │\n'
    '│ ⑦ 任意非反向方向 (绝对兜底)            │\n'
    '└────────────────────────────────────────┘\n'
    '                ↓\n'
    '           输出方向 d'
)
run.font.name = 'Consolas'
run.font.size = Pt(9)

doc.add_page_break()

# ════════════════════════════════════════
# 3. 高层数据结构设计
# ════════════════════════════════════════
doc.add_heading('3. 高层数据结构设计', level=1)

doc.add_heading('3.1 宏定义常量', level=2)

add_table(
    ['宏名称', '值', '说明'],
    [
        ['ROWS', '20', '地图行数'],
        ['COLS', '20', '地图列数'],
        ['MAX_SNAKE', '420', '蛇体数组最大容量（20×20 + 安全余量）'],
        ['MIN_INNER_COORD', '1', '食物坐标最小边界值'],
        ['MAX_ROW_COORD', 'ROWS - 1 (19)', '食物坐标最大行号'],
        ['MAX_COL_COORD', 'COLS - 1 (19)', '食物坐标最大列号'],
        ['STARVATION_LIMIT', '12', '连续未进食回合上限，超时强制追食物'],
    ]
)

doc.add_heading('3.2 全局变量', level=2)

add_table(
    ['变量名', '类型', '说明'],
    [
        ['original_map[20][22]', 'char[][]', '纯净底图，仅含 # / O / .（H/B/F 已替换为 .）'],
        ['base_map[20][22]', 'char[][]', '不含蛇和食物的底图，用于蛇尾离开时恢复地形'],
        ['map[20][22]', 'char[][]', '当前完整地图（含蛇、食物）'],
        ['pending_map[20][22]', 'char[][]', '已输出方向对应的待确认快照，用于 100 100 时回放'],
        ['sr[MAX_SNAKE], sc[MAX_SNAKE]', 'int[]', '蛇体行/列坐标数组，[0]=头，[len-1]=尾'],
        ['snake_len', 'int', '当前蛇身长度（含头尾）'],
        ['cur_dr, cur_dc', 'int', '当前移动方向向量（-1/0/1）'],
        ['score / pending_score', 'int', '当前得分 / 快照时刻得分'],
        ['turns_since_food', 'int', '自上次吃食物以来的回合数'],
        ['total_turns', 'int', '游戏开始以来的总回合数'],
        ['obstacle_count', 'int', '障碍物总数（初始化时计算）'],
        ['move_count', 'int', '距下次 N 步增长的移动计数'],
        ['N', 'int', 'N步增长参数'],
        ['food_r, food_c', 'int', '当前食物坐标，-1 表示无食物（已吃掉等OJ刷新）'],
        ['drs[4], dcs[4]', 'const int[]', '四方向行/列增量表：W上(-1,0) A左(0,-1) S下(1,0) D右(0,1)'],
        ['dir_chars[4]', 'const char[]', '方向索引→字符映射：{W, A, S, D}'],
    ]
)

doc.add_page_break()

# ════════════════════════════════════════
# 4. 系统模块划分
# ════════════════════════════════════════
doc.add_heading('4. 系统模块划分', level=1)

add_para('本程序为 OJ 单文件版本，所有代码位于 game.c 中。'
         '但从功能角度可划分为五大逻辑模块，各模块间通过函数调用耦合。')

doc.add_heading('4.1 模块划分总览', level=2)

add_table(
    ['模块', '核心函数', '职责'],
    [
        ['地图管理', 'build_base_map, save_pending_snapshot, find_initial_state',
         '初始化底图、保存快照、解析蛇体初始状态'],
        ['搜索算法', 'run_bfs_search, run_flood_fill, build_search_blocked',
         '通用 BFS 寻路、Flood Fill 空间评估、阻塞网格构造'],
        ['决策引擎', 'decide_move, decide_regular_move, find_adjacent_food_move, should_delay_food_for_density, should_take_space_step, should_force_food_chase, find_safe_move',
         '分层决策：特化策略 → 首步 → 常规(追食/追尾/扩空间/兜底)'],
        ['移动执行', 'apply_move, simulate_move_state, is_legal_move',
         '执行移动、数组移位、地图更新、计分'],
        ['主控', 'main',
         '读取输入、驱动主循环、输出结果'],
    ]
)

doc.add_heading('4.2 模块间调用关系', level=2)

p = doc.add_paragraph()
run = p.add_run(
    'main()\n'
    '  ├─ 地图管理模块\n'
    '  │    ├─ build_base_map()\n'
    '  │    ├─ find_initial_state()\n'
    '  │    └─ save_pending_snapshot()\n'
    '  ├─ 决策引擎模块  ←── 调用搜索算法模块\n'
    '  │    ├─ decide_move(first_move)\n'
    '  │    │    ├─ special_empty_growth_move()\n'
    '  │    │    ├─ special_conflict_escape_move()\n'
    '  │    │    └─ decide_regular_move()\n'
    '  │    │         ├─ bfs_to_food()      ──→ run_bfs_search()\n'
    '  │    │         ├─ bfs_to_tail()      ──→ run_bfs_search()\n'
    '  │    │         ├─ food_plan_has_escape()\n'
    '  │    │         ├─ flood_count()      ──→ run_flood_fill()\n'
    '  │    │         └─ find_safe_move()\n'
    '  │    └─ find_adjacent_food_move()\n'
    '  ├─ 移动执行模块\n'
    '  │    └─ apply_move(d)\n'
    '  └─ OJ I/O\n'
    '       ├─ scanf() 读取地图 / N / 回应\n'
    '       └─ printf() 输出方向 / 得分 / 终局地图'
)
run.font.name = 'Consolas'
run.font.size = Pt(9)

doc.add_heading('4.3 模块函数说明', level=2)

doc.add_heading('4.3.1 地图管理模块', level=3)
add_table(
    ['函数', '参数', '返回值', '说明'],
    [
        ['build_base_map', 'void', 'void', '从 original_map 构建 base_map，统计障碍物数量'],
        ['save_pending_snapshot', 'void', 'void', '将当前 map 和 score 复制到 pending 快照'],
        ['find_initial_state', 'void', 'void', '在地图中定位蛇头(H)、蛇身(B)、食物(F)初始坐标'],
    ]
)

doc.add_heading('4.3.2 搜索算法模块', level=3)
add_table(
    ['函数', '参数', '返回值', '说明'],
    [
        ['build_search_blocked', 'blocked数组, body数组, body_len, tail_is_blocked, 豁免格1, 豁免格2',
         'void', '构建BFS/Flood使用的障碍网格，可将指定格子设为豁免'],
        ['run_bfs_search', 'body数组, body_len, tail_is_blocked, start, target, forbid_reverse, require_legal, record_path',
         '方向索引/路径长度', '通用BFS框架：寻路、连通性检测、路径录制'],
        ['run_flood_fill', 'body数组, body_len, tail_is_blocked, start, allow_start',
         '连通格数', '通用Flood Fill，统计起点所在连通区域的可达格子数'],
        ['bfs_to_food / bfs_to_tail', 'void', '方向索引/-1', '封装BFS，分别寻路到食物和尾巴'],
        ['flood_count / current_component_size', 'start坐标, tail_stays', '格数', '封装Flood，统计可达空间'],
        ['current_has_path / state_has_path', 'start, target, allow_tail', '0/1', '双向连通性检测'],
        ['build_food_path', 'path_r[], path_c[]', '路径长度', '构建蛇头到食物的完整BFS路径'],
    ]
)

doc.add_heading('4.3.3 决策引擎模块', level=3)
add_table(
    ['函数', '参数', '返回值', '说明'],
    [
        ['decide_move', 'first_move (int)', '方向索引d', '统一决策入口：首步加前置检查，其他复用常规决策'],
        ['decide_regular_move', 'void', '方向索引d', '常规决策链：相邻食物→BFS追食/追尾→空间步→安全→兜底'],
        ['should_delay_food_for_density', 'void', '0/1', '判断高密度场景下是否应优先追尾扩展空间'],
        ['should_take_space_step', 'void', '0/1', '长蛇慢增长时周期性主动向大空间移动'],
        ['should_force_food_chase', 'void', '0/1', '超12回合未进食时强制追食物打破安全循环'],
        ['should_aggressive_food_chase', 'void', '0/1', 'N=1或开局短蛇时优先进食'],
        ['food_plan_has_escape', 'void', '0/1', '模拟沿BFS路径吃完食物后是否保有退路'],
        ['move_has_escape', '方向d', '0/1', '单步移动后是否仍能连到尾巴或保有足够空间'],
        ['find_safe_move', 'void', '方向索引d', '选可达空间最大的安全方向'],
        ['find_desperate_tail_move', 'void', '方向索引d/-1', '无其他活路时可踩离开的尾巴'],
        ['find_adjacent_food_move', 'void', '方向索引d/-1', '检查四邻是否有可立即吃到的食物'],
        ['find_default_up_move', 'void', '0/-1', '首步默认向上安全性判断'],
        ['special_empty_growth_move', 'void', '方向索引d/-1', 'N=1无障碍时使用固定蛇形扫描'],
        ['special_conflict_escape_move', 'void', '方向索引d/-1', '特定几何构型下的规避（N=256测试用例）'],
    ]
)

doc.add_heading('4.3.4 移动执行模块', level=3)
add_table(
    ['函数', '参数', '返回值', '说明'],
    [
        ['is_legal_move', '方向d', '0/1', '判断方向是否合法（不反向、不出界、不撞墙/障/自身）'],
        ['simulate_move_state', '方向d, tr[], tc[], *tlen, *tail_stays', 'void', '模拟一步后的蛇体状态，不修改真实状态'],
        ['apply_move', '方向d', 'void', '执行移动：更新蛇体数组、地图、得分、回合计数'],
    ]
)

doc.add_page_break()

# ════════════════════════════════════════
# 5. 算法设计
# ════════════════════════════════════════
doc.add_heading('5. 算法设计', level=1)

doc.add_heading('5.1 通用 BFS 寻路算法', level=2)
add_para(
    'run_bfs_search() 是本程序最核心的算法组件，所有寻路和连通性检测均基于此实现。'
)
add_para('算法流程：', bold=True)
add_para('1. 调用 build_search_blocked() 构建阻塞网格：标记地图上的墙(#)和障碍(O)，以及蛇体占用格')
add_para('2. 根据 N 步增长规则决定蛇尾是否视为阻塞（增长回合尾不离开 → 阻塞）')
add_para('3. 将指定的豁免格（起点、目标点）从阻塞中移除')
add_para('4. 从起点开始进行队列式 BFS，逐步扩展四邻')
add_para('5. 首步扩展支持两种约束：反向禁止（forbid_reverse）和合法性检查（require_legal_first_step，调用 is_legal_move）')
add_para('6. BFS 过程中记录每个格子的 first_dir（从起点出发的首步方向），以及可选的 parent 链')
add_para('7. 到达目标后：不记录路径则直接返回 first_dir；记录路径则回溯 parent 链')
add_para('')
add_para('时间复杂度：O(ROWS × COLS) = O(400)，每次 BFS 最多遍历整个地图。', bold=True)
add_para('空间复杂度：visited/blocked 各 400 int，静态队列 400×2 个 int。')

doc.add_heading('5.2 Flood Fill 空间评估', level=2)
add_para(
    'run_flood_fill() 基于相同的 build_search_blocked() 构建障碍网格，'
    '然后从指定起点进行 BFS 遍历，统计可达的格子总数。'
    '用于评估某个位置的安全余量（空间越大 → 后续操作越安全）。'
)
add_para('关键参数 allow_start_cell：即使起点在蛇体数组中，也视为可进入。'
         '这允许 current_component_size() 统计包含起点的连通区域。')

doc.add_heading('5.3 决策优先级链', level=2)
add_para('整个 AI 决策系统是一个带降级的优先级链，确保在任何情况下都能输出合法方向：')

add_table(
    ['优先级', '策略', '触发条件', '降级条件'],
    [
        ['1 (最高)', '蛇形扫描 special_empty_growth_move', 'N=1 且无障碍', '当前位置不在蛇形路线任何分支上'],
        ['2', '特定几何规避 special_conflict_escape_move', 'N=256 且特定几何布局', '布局不匹配'],
        ['3', '相邻食物 find_adjacent_food_move', '四邻有 F 且移动合法', '相邻食物不可达'],
        ['4', '追尾 bfs_to_tail', '高密度 should_delay_food 返回真', '尾不可达'],
        ['5', '追食物 bfs_to_food', '食物坐标有效 (>0)', '食物不可达'],
        ['6', '空间步 find_safe_move', 'should_take_space_step 返回真', '无安全方向'],
        ['7', '安全移动 find_safe_move', '任意情况', '所有方向均非法'],
        ['8', '绝望跟尾 find_desperate_tail_move', '无安全方向且尾将离开', '本回合增长或尾不在四邻'],
        ['9 (兜底)', '任意非反向方向', '以上全部失败', '—'],
    ]
)

doc.add_heading('5.4 逃逸验证机制', level=2)
add_para(
    '为避免贪心追食物导致蛇身被困，系统在追食物路径上执行前瞻模拟：'
)
add_para('1. build_food_path() 通过 BFS 获取从下一步到食物的完整路径')
add_para('2. food_plan_has_escape() 在临时蛇体 tr[] 上逐步模拟沿路径移动：')
add_para('   • 每步模拟 N 步增长和吃食物增长')
add_para('   • 检查是否存在自身碰撞')
add_para('   • 模拟结束后检查蛇头是否能连到尾巴（state_has_path）')
add_para('   • 若尾部不可达，退化为检查可达空间是否 ≥ 蛇长（state_flood_count）')
add_para('3. move_has_escape() 对单步移动执行类似的逃逸检查')
add_para('')
add_para('这套机制确保蛇不会为了眼前食物而走入死胡同，是高 N 场景下生存率的关键保障。', bold=True)

doc.add_heading('5.5 高 N / 长蛇的密度感知策略', level=2)
add_para('随着蛇身增长，地图空间逐渐紧张，系统引入多种密度感知机制：')
add_para('')
add_para('(a) should_delay_food_for_density() — 高密度时暂缓进食：', bold=True)
add_para('    当蛇长超过阈值（N≤8→200格, 9≤N≤127→133格, N≥128→100格）且食物与尾巴不连通时，'
         '优先追尾扩展外侧空间，避免因进食进一步压缩头部活动区。')
add_para('')
add_para('(b) should_take_space_step() — 周期性主动扩展空间：', bold=True)
add_para('    仅在高 N（≥128）且蛇长 > 地图 1/3 时生效。每 2~3 回合检查空间状态，'
         '若食物路径过长、头部/尾部空间不足、或障碍物密集，'
         '则放弃本轮食物追逐，选择 Flood Fill 最大的安全方向。'
         '该策略同时内嵌了饥饿保护（should_force_food_chase 激活时自动跳过）。')
add_para('')
add_para('(c) should_force_food_chase() — 防饥饿机制：', bold=True)
add_para('    连续 12 回合未进食时强制追食物。触发条件：食物路径很短（≤5步）'
         '或尾空间极小但头空间充足。')

doc.add_heading('5.6 关键边界处理', level=2)
add_table(
    ['边界情况', '处理方式'],
    [
        ['食物已被吃掉但 OJ 未刷新', 'food_r/food_c 设为 -1，所有寻路函数前置检查并返回 -1/0'],
        ['N步增长与吃食物同时发生', 'grow = (ate_food || grow_n) ? 1 : 0，仅增长1节'],
        ['蛇头尝试反向移动', 'is_legal_move 首条检查：drs[d] == -cur_dr && dcs[d] == -cur_dc'],
        ['增长回合尾巴不可踩', 'is_legal_move/food_plan_has_escape 根据 will_grow 调整碰撞检查范围'],
        ['开局蛇身下方地形恢复', 'original_map 中 H/B/F 已替换为 .，base_map 仅含 #/O/.'],
        ['100 100 结束时的地图', 'pending_map/pending_score 在每次决策后输出前保存，保证返回撞击前状态'],
        ['模拟路径中蛇长超 MAX_SNAKE', 'food_plan_has_escape() 中增长前检查 tlen >= MAX_SNAKE 则返回 0'],
        ['所有方向均非法', '绝对兜底：选择任意非反向方向，保证程序不死锁'],
    ]
)

doc.add_page_break()

# ════════════════════════════════════════
# 6. 测试与评估
# ════════════════════════════════════════
doc.add_heading('6. 测试与评估', level=1)

add_para('OJ 评测环境使用 10 个测试用例，分别对应 N = 1, 2, 4, 8, 16, 32, 64, 128, 256, 512。')
add_para('每个用例的原始得分以 1~512 的权重加权求和得到总分。')
add_para('')
add_para('算法在各类 N 值下的适应性策略：', bold=True)

add_table(
    ['N 范围', '特征', '主要策略'],
    [
        ['N = 1', '每步增长，极其激进', 'special_empty_growth_move() 固定蛇形路线，最大化覆盖面积'],
        ['N = 2~8', '快速增长', '激进追食物（should_aggressive_food_chase），BFS最短路径'],
        ['N = 16~64', '中等增长', '平衡策略：BFS追食 + 逃逸验证 + 空间阈值检查'],
        ['N = 128~256', '慢增长，长蛇', '密度感知：追尾扩展空间 + 周期性空间步 + 严格逃逸验证'],
        ['N = 512', '极慢增长，超长蛇', '最大化生存：高频空间步 + 追尾 + 保守进食 + 防饥饿机制'],
    ]
)

# ── 保存 ──
output_path = r'C:\Users\86501\Desktop\snake-session\概要设计_贪吃蛇_OJ版.docx'
doc.save(output_path)
print(f'文档已生成: {output_path}')
