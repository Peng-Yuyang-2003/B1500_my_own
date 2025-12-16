import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import matplotlib
import copy
import os
from datetime import datetime

# ----------------------------
# 设置中文字体（避免方框问题）
# ----------------------------
matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei']  # 微软雅黑
matplotlib.rcParams['axes.unicode_minus'] = True              # 允许使用 Unicode 负号

# ----------------------------
# 1. 从CSV提取矩阵
# ----------------------------
max_col = 7  # 最大列数
x_col = 1    # x轴数据所在列
y_col = 6    # y轴数据所在列
importfile = r"E:\融合2\实验数据\2025-08-20\01\01-键合后 -1-3.csv"

column_names = [f"col{i}" for i in range(max_col)]
df = pd.read_csv(
    importfile,
    header=None,
    names=column_names,
    on_bad_lines='skip'
)

# 提取 DataValue 段落
groups = []
current_x, current_y = [], []

for _, row in df.iterrows():
    if row['col0'] == 'DataValue':
        try:
            x = float(row[f"col{x_col}"])
            y = float(row[f"col{y_col}"])
            current_x.append(x)
            current_y.append(y)
        except ValueError:
            continue
    else:
        if current_x:  # 遇到分隔，存一组
            groups.append((np.array(current_x), np.array(current_y)))
            current_x, current_y = [], []

# 最后如果有数据也加进去
if current_x:
    groups.append((np.array(current_x), np.array(current_y)))

# 转为矩阵 (m, 2n)
max_len = max(len(g[0]) for g in groups)
matrix = np.zeros((max_len, 2 * len(groups)))
for i, (x, y) in enumerate(groups):
    matrix[:len(x), 2*i] = x
    matrix[:len(y), 2*i+1] = y
    if len(x) < max_len:  # 对齐时，后面补NaN
        matrix[len(x):, 2*i] = np.nan
        matrix[len(y):, 2*i+1] = np.nan

print(f"读取到 {len(groups)} 条曲线，矩阵 shape = {matrix.shape}")

# ----------------------------
# 2. 绘图初始化
# ----------------------------
fig, ax = plt.subplots()
plt.subplots_adjust(right=0.75, bottom=0.2)

lines = []

def plot_all():
    """画所有曲线并返回 lines 列表"""
    new_lines = []
    for i in range(matrix.shape[1] // 2):
        line, = ax.plot(matrix[:, 2*i], matrix[:, 2*i+1], picker=5, label=f"曲线{i}")
        new_lines.append(line)
    return new_lines

lines = plot_all()
ax.set_title("点击曲线删除 (支持多次删除/撤销/保存)")
ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))

# ----------------------------
# 3. 撤销历史
# ----------------------------
history = []

def backup_state():
    history.append((matrix.copy(), lines.copy()))

def restore_state():
    global matrix, lines
    if history:
        matrix, _ = history.pop()
        redraw()

# ----------------------------
# 4. 删除逻辑
# ----------------------------
def on_pick(event):
    global matrix, lines
    thisline = event.artist
    if thisline in lines:
        idx = lines.index(thisline)
        print(f"删除 曲线 {idx}")
        backup_state()
        matrix = np.delete(matrix, [2*idx, 2*idx+1], axis=1)
        redraw()

# ----------------------------
# 5. 重绘函数
# ----------------------------
def redraw():
    global lines
    # 先保存当前 y 轴坐标类型（'linear' 或 'log'）
    current_scale = ax.get_yscale()
    current_formatter = ax.yaxis.get_major_formatter()

    ax.clear()
    lines = plot_all()
    ax.set_title(f"点击曲线删除 (剩余 {matrix.shape[1]//2} 条)")

    # 恢复之前的坐标类型
    ax.set_yscale(current_scale)
    ax.yaxis.set_major_formatter(current_formatter)

    # 图例放在外面
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    fig.canvas.draw_idle()


# ----------------------------
# 6. 按钮功能
# ----------------------------
def undo(event):
    print("撤销上一步操作")
    restore_state()

def save(event):
    # 自动生成文件名
    n_curves = matrix.shape[1] // 2
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    fname = f"filtered_matrix_{n_curves}curves_{timestamp}.csv"
    np.savetxt(fname, matrix, delimiter=",")
    print(f"已保存到 {fname}")

def toggle_scale(event):
    if ax.get_yscale() == "linear":
        ax.set_yscale("log")
        print("切换到对数坐标")
    else:
        ax.set_yscale("linear")
        print("切换到普通坐标")
    fig.canvas.draw()


# 在图下方放置按钮
ax_undo = plt.axes([0.1, 0.05, 0.15, 0.075])
btn_undo = Button(ax_undo, '撤销')
btn_undo.on_clicked(undo)

ax_save = plt.axes([0.3, 0.05, 0.25, 0.075])
btn_save = Button(ax_save, '保存矩阵')
btn_save.on_clicked(save)

ax_toggle = plt.axes([0.6, 0.05, 0.25, 0.075])
btn_toggle = Button(ax_toggle, '切换纵坐标')
btn_toggle.on_clicked(toggle_scale)


# ----------------------------
# 7. 事件绑定
# ----------------------------
fig.canvas.mpl_connect('pick_event', on_pick)

plt.show()
