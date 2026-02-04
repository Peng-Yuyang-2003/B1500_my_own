import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import matplotlib
import os
from datetime import datetime
import tkinter as tk
from tkinter import simpledialog
from matplotlib.ticker import FuncFormatter, ScalarFormatter
import warnings
#用于读取矩阵csv然后生成新数据保存矩阵csv
#重要参数
noise_level = 1E-11
smooth_level = 1E-10
ICC = 1E-5
# ----------------------------
# 基本设置（字体/忽略特定警告）
# ----------------------------
warnings.filterwarnings("ignore", message=".*glyph for.*")
matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei']  # 微软雅黑
matplotlib.rcParams['axes.unicode_minus'] = True

# ----------------------------
# 科学计数格式（避免 U+2212 问题）
# ----------------------------
def sci_notation(y, pos):
    if y == 0:
        return "0"
    return "{:.3e}".format(y)

# ----------------------------
# 1. 从CSV提取矩阵
# ----------------------------
importfile = r"E:\融合2\实验数据\2025-12-13\1-25-7_merged_clean.csv"
# 读取CSV并强制转换为数值类型，无法转换的值会变为NaN
matrix_df = pd.read_csv(importfile, header=None, low_memory=False)
matrix = matrix_df.apply(pd.to_numeric, errors='coerce').to_numpy()

groups = matrix.shape[1] // 2
print(f"读取到 {groups} 条曲线，矩阵 shape = {matrix.shape}")

# ----------------------------
# 2. 绘图初始化
# ----------------------------
fig, ax = plt.subplots()
plt.subplots_adjust(right=0.75, bottom=0.22)

lines = []

def plot_all():
    """画所有曲线并返回 lines 列表"""
    new_lines = []
    # 设置坐标轴标签及单位
    ax.set_xlabel("Voltage (V)")
    ax.set_ylabel("Current (A)")
    ncols = matrix.shape[1]
    for i in range(ncols // 2):
        x = matrix[:, 2*i]
        y = matrix[:, 2*i+1]
        if pd.isna(x).all() and pd.isna(y).all():
            continue
        line, = ax.plot(x, y, picker=5, label=f"曲线{i}", linewidth=1.0, color="blue")
        new_lines.append(line)
    return new_lines

lines = plot_all()
ax.set_title("点击曲线高亮（再点一次取消） /撤销 / 保存 / 切换 Y 轴")
ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))

ax.yaxis.set_major_formatter(ScalarFormatter())
ax.ticklabel_format(style='plain', axis='y')

# ----------------------------
# 3. 撤销历史
# ----------------------------
history = []

def backup_state():
    history.append(matrix.copy())

def restore_state():
    global matrix
    if history:
        matrix = history.pop()
        redraw()
    else:
        print("没有历史可以撤销")

# ----------------------------
# 4. 点击曲线 → 高亮/取消高亮
# ----------------------------
def on_pick(event):
    thisline = event.artist
    if thisline not in lines:
        return
    lw = thisline.get_linewidth()
    if lw == 1.0:  # 默认
        thisline.set_linewidth(3.0)
        thisline.set_color("red")
        print("高亮曲线")
    else:
        thisline.set_linewidth(1.0)
        thisline.set_color("blue")
        print("取消高亮")
    fig.canvas.draw_idle()

# ----------------------------
# 5. 重绘函数
# ----------------------------
def redraw():
    global lines
    current_scale = ax.get_yscale()
    current_formatter = ax.yaxis.get_major_formatter()

    ax.clear()
    lines = plot_all()
    ax.set_title(f"点击曲线高亮 / 剩余 {matrix.shape[1]//2} 条")
    ax.set_yscale(current_scale)
    ax.yaxis.set_major_formatter(current_formatter)

    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    fig.canvas.draw_idle()


# ----------------------------
# 7. 按钮功能
# ----------------------------
def undo(event):
    print("撤销上一步操作")
    restore_state()

def save(event):
    n_curves = matrix.shape[1] // 2
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    folder = "B1500_data_storage"
    os.makedirs(folder, exist_ok=True)  # 如果文件夹不存在则创建
    fname = os.path.join(folder, f"filtered_matrix_{n_curves}curves_generated_{timestamp}.csv")
    np.savetxt(fname, matrix, delimiter=",", fmt='%s')
    print(f"已保存到 {fname}")

def toggle_scale(event):
    if ax.get_yscale() == "linear":
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(FuncFormatter(sci_notation))
        print("切换到对数坐标")
    else:
        ax.set_yscale("linear")
        ax.yaxis.set_major_formatter(ScalarFormatter())
        ax.ticklabel_format(style='plain', axis='y')
        print("切换到普通坐标")
    fig.canvas.draw_idle()


# ----------------------------
# 8. 按钮放置
# ----------------------------
def delete_selected(event):
    """删除当前高亮（linewidth>1.5）的曲线对应的 X/Y 列，并压缩矩阵避免空列"""
    global matrix, lines
    # 找到被高亮的曲线索引（lines 中的位置）
    highlighted = [i for i, ln in enumerate(lines) if ln.get_linewidth() > 1.5]
    if not highlighted:
        print("未选中任何曲线以删除")
        return

    # 备份以便撤销
    backup_state()

    num_pairs = matrix.shape[1] // 2
    # 生成保留的列索引（按原顺序保留未删除的对）
    keep_cols = []
    for p in range(num_pairs):
        if p not in highlighted:
            keep_cols.extend([2 * p, 2 * p + 1])

    if len(keep_cols) == 0:
        # 如果全部删除，变为空矩阵（保持行数）
        matrix = np.empty((matrix.shape[0], 0))
    else:
        matrix = matrix[:, keep_cols]

    # 重新绘制以反映删除结果
    redraw()
    print(f"已删除曲线索引: {highlighted}，矩阵更新为 {matrix.shape}")

# 按钮放置（位于撤销按钮下方）
ax_delete = plt.axes([0.90, 0.03, 0.10, 0.07])
btn_delete = Button(ax_delete, '删除选中曲线')
btn_delete.on_clicked(delete_selected)
# ----------------------------
ax_undo = plt.axes([0.02, 0.03, 0.12, 0.07])
btn_undo = Button(ax_undo, '撤销')
btn_undo.on_clicked(undo)


ax_save = plt.axes([0.54, 0.03, 0.18, 0.07])
btn_save = Button(ax_save, '保存矩阵')
btn_save.on_clicked(save)

ax_toggle = plt.axes([0.72, 0.03, 0.18, 0.07])
btn_toggle = Button(ax_toggle, '切换纵坐标')
btn_toggle.on_clicked(toggle_scale)

# ----------------------------
# 9. 事件绑定
# ----------------------------
fig.canvas.mpl_connect('pick_event', on_pick)

plt.show()
