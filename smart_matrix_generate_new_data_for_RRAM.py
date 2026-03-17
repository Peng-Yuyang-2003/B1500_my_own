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
#importfile = r"E:\融合2\实验数据\2025-12-13\1-25-7_merged_clean.csv"
importfile = r"E:\融合2\实验数据\2026-02-03-Graphene\1T1R_reset [(3) ; 2_2_2026 11_12_23 AM]-d4middle_clean.csv"
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
        line, = ax.plot(x, y, picker=5, linewidth=1.0, color="blue")
        new_lines.append(line)
    return new_lines

lines = plot_all()
ax.set_title("点击曲线高亮（再点一次取消） / 新增 / 批量生成 / 撤销 / 保存 / 切换 Y 轴")
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
# 6. 随机混合函数
# ----------------------------
def folding(values):
    """把数值翻折到 [0,1] 区间"""
    folded = np.array(values, dtype=float)
    while True:
        mask_high = folded > 1
        if not mask_high.any():
            break
        folded[mask_high] = 2 - folded[mask_high]

    while True:
        mask_low = folded < 0
        if not mask_low.any():
            break
        folded[mask_low] = -folded[mask_low]

    return folded

def random_function(n, kind="quadratic"):
    t = np.linspace(0, 1, n)
    if kind == "linear":
        a = np.random.uniform(0.5, 2)
        f = a*t
    elif kind == "quadratic":
        a, b, c = np.random.uniform(-1, 1), np.random.uniform(-1, 1), np.random.uniform(0, 1)
        f = a*t**2 + b*t + c
    elif kind == "bezier":
        p0, p1, p2 = np.random.rand(), np.random.rand(), np.random.rand()
        f = (1-t)**2 * p0 + 2*(1-t)*t*p1 + t**2*p2
    else:
        raise ValueError("未知函数类型")
    return folding(f)

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
    np.savetxt(fname, matrix, delimiter=",", fmt="%.6e")
    print(f"矩阵数据已保存到 {fname}")

def save_resistance(event):
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    folder = "B1500_data_storage"
    os.makedirs(folder, exist_ok=True)

    resistances = []

    n_cols = matrix.shape[1]

    for col in range(0, n_cols, 2):
        V = matrix[:, col]
        I = matrix[:, col + 1]

        # 1. 如果电压列中大部分为负数，跳过
        if np.sum(V < 0) > len(V) / 2:
            continue

        # 2. 找到最接近 +0.1 V 的前两个索引
        # 2. 找到最接近 +0.1 V 的前两个索引（排除 NaN / Inf）
        mask = np.isfinite(V)
        V_valid = V[mask]

        if V_valid.size < 2:
            continue  # 有效点不足两个，跳过该曲线

        # 与 0.1 V 的差值
        diff = np.abs(V_valid - 0.1)

        # 取差值最小的两个
        idx_valid_2 = np.argsort(diff)[:2]

        # 映射回原始 V 的索引
        idx_2 = np.where(mask)[0][idx_valid_2]
        I_at_01 = I[idx_2[0]]

        # 3. 电流为 0 或异常，跳过
        if I_at_01 == 0 or np.isnan(I_at_01) or np.isinf(I_at_01):
            continue

        # 4. 计算电阻
        R = 0.1 / I_at_01
        resistances.append(R)
        I_at_01 = I[idx_2[1]]

        # 3. 电流为 0 或异常，跳过
        if I_at_01 == 0 or np.isnan(I_at_01) or np.isinf(I_at_01):
            continue

        # 4. 计算电阻
        R = 0.1 / I_at_01
        resistances.append(R)

    resistances = np.array(resistances)

    # ===============================
    # 保存电阻 CSV
    # ===============================
    csv_name = os.path.join(
        folder, f"resistance_values_{timestamp}.csv"
    )
    np.savetxt(
        csv_name,
        resistances.reshape(-1, 1),
        delimiter=",",
        header="Resistance(Ohm)",
        comments="",
        fmt="%.6e"
    )

    print(f"电阻数据已保存到 {csv_name}")

    # ===============================
    # 绘制柱状分布图（Histogram）
    # ===============================
    # 先清洗数据（必须）
    resistances = np.array(resistances)
    resistances = resistances[np.isfinite(resistances) & (resistances > 0)]
    #计算中位数，并把大于中位数的所有数求平均，把小于中位数的所有数求平均，这三个数都打印出来
    median_R = np.median(resistances)
    mean_R_above_median = np.mean(resistances[resistances > median_R])
    mean_R_below_median = np.mean(resistances[resistances < median_R])
    print(f"电阻中位数: {median_R:.3e} Ohm")
    print(f"电阻大于中位数的平均值: {mean_R_above_median:.3e} Ohm")
    print(f"电阻小于中位数的平均值: {mean_R_below_median:.3e} Ohm") 

    logR = np.log10(resistances)

    plt.figure(figsize=(6, 4))
    plt.hist(logR, bins=100)
    plt.xlabel("log10(Resistance / Ohm)")
    plt.ylabel("Count")
    plt.title("Resistance Distribution at 0.1 V")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.show()
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime

def save_setvoltage(event):
    """
    功能：
    1. 遍历矩阵的列（假设电压列在偶数索引，电流列在奇数索引）。
    2. 对于大部分为正数的电压列，找到对应电流列中第一个到达电流最大值的位置。
    3. 记录该位置的电压值，保存到 CSV 文件。
    4. 计算电压值的平均值。
    5. 绘制正常坐标轴的柱状图。
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    folder = "B1500_data_storage"
    os.makedirs(folder, exist_ok=True)

    setvoltages = []  # 存储找到的电压值

    n_cols = matrix.shape[1]

    for col in range(0, n_cols, 2):
        V = matrix[:, col]
        I = matrix[:, col + 1]

        # 1. 如果电压列中大部分为负数，跳过
        if np.sum(V < 0) > len(V) / 2:
            continue

        # 2. 找到电流列的最大值（排除 NaN/Inf）
        mask = np.isfinite(I)
        I_valid = I[mask]
        if I_valid.size == 0:
            continue  # 没有有效电流数据，跳过

        I_max = np.max(I_valid)
        if np.isnan(I_max) or np.isinf(I_max):
            continue

        # 3. 找到第一个到达电流最大值的位置（在原始 I 中）
        # 注意：由于可能存在多个点等于最大值，取第一个
        idx_max = np.argmax(I == I_max)
        if idx_max >= len(V):
            continue  # 索引越界保护

        V_at_I_max = V[idx_max]

        # 4. 检查电压值是否有效
        if np.isnan(V_at_I_max) or np.isinf(V_at_I_max):
            continue

        setvoltages.append(V_at_I_max)

    setvoltages = np.array(setvoltages)

    # ===============================
    # 保存电压 CSV
    # ===============================
    csv_name = os.path.join(
        folder, f"setvoltage_values_{timestamp}.csv"
    )
    np.savetxt(
        csv_name,
        setvoltages.reshape(-1, 1),
        delimiter=",",
        header="SetVoltage(V)",
        comments="",
        fmt="%.6e"
    )
    print(f"电压数据已保存到 {csv_name}")

    # ===============================
    # 计算平均值
    # ===============================
    if len(setvoltages) > 0:
        avg_voltage = np.mean(setvoltages)
        print(f"电压平均值: {avg_voltage:.6f} V")
    else:
        avg_voltage = np.nan
        print("未找到有效的电压数据，无法计算平均值")

    # ===============================
    # 绘制柱状图（正常坐标轴）
    # ===============================
    if len(setvoltages) > 0:
        plt.figure(figsize=(6, 4))
        plt.hist(setvoltages, bins=20)
        plt.xlabel("Set Voltage (V)")
        plt.ylabel("Count")
        plt.title("Set Voltage Distribution at First Current Maximum")
        plt.grid(True, linestyle="--", alpha=0.5)
        plt.tight_layout()
        plt.show()
    else:
        print("没有有效数据可绘制柱状图")

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

def select_valid_pair(matrix, max_trials=50, threshold=0.1, factor=100):
    """
    选择一对合格的曲线索引 (idx1, idx2)，最多尝试 max_trials 次
    threshold: 允许不符合的比例 (默认 0.1 = 10%)
    factor: 判断倍数 (默认 10 倍)
    """
    num_curves = matrix.shape[1] // 2

    for _ in range(max_trials):
        idx1, idx2 = np.random.choice(num_curves, 2, replace=False)
        Y1 = matrix[:, 2*idx1+1]
        Y2 = matrix[:, 2*idx2+1]

        # 取非 NaN 的位置
        mask = ~np.isnan(Y1) & ~np.isnan(Y2)
        Y1_valid, Y2_valid = Y1[mask], Y2[mask]

        if len(Y1_valid) == 0:
            continue  # 没有有效点，跳过

        # 逐点计算是否超过 factor 倍
        ratio = np.maximum(np.abs(Y1_valid), np.abs(Y2_valid)) / np.minimum(np.abs(Y1_valid), np.abs(Y2_valid))
        invalid_ratio = np.mean(ratio > factor)  # 不符合的比例

        if invalid_ratio <= threshold:
            return idx1, idx2
        else:
            print(f"尝试 {idx1}, {idx2} 不合格 (不符合比例 {invalid_ratio:.2%})，继续尝试...")

    raise ValueError("在给定的尝试次数内，没有找到符合条件的曲线对")

def augment_curve(event):
    global matrix, lines
    num_curves = matrix.shape[1] // 2
    if num_curves < 2:
        print("不足两条曲线，无法生成")
        return

    idx1, idx2 = select_valid_pair(matrix)
    X = matrix[:, 2*idx1]
    Y1 = matrix[:, 2*idx1+1]
    Y2 = matrix[:, 2*idx2+1]

    kind = np.random.choice(["linear", "quadratic", "bezier"])
    f = random_function(len(X), kind)
    noise = np.random.uniform(0, noise_level, size=Y1.shape)
    #检查Y1和Y2相差多少倍，将倍数设为jump
    jump = np.maximum(np.abs(Y1), np.abs(Y2)) / np.minimum(np.abs(Y1), np.abs(Y2))
    #计算jump的数量级
    jump_magnitude = np.floor(np.log(jump))
    #在jump>1时，给Y1、Y2中小的那个数乘上jump_magnitude的10次方
    adjustment = np.where(Y1 < Y2, np.exp(jump_magnitude), 1) * np.where(Y2 < Y1, np.exp(jump_magnitude), 1)
    #Y_new = f * Y1+ Y2 * (1 - f) + noise
    term1 = f * np.where((Y1 < Y2) & (Y2 < smooth_level), Y1 * np.exp(jump_magnitude), Y1)
    term2 = (1 - f) * np.where((Y2 < Y1) & (Y1 < smooth_level), Y2 * np.exp(jump_magnitude), Y2)
    Y_new_candidate = term1 + term2 + noise
    mask_icc = np.isclose(Y1, ICC) | np.isclose(Y2, ICC)
    Y_new = np.where(mask_icc, ICC, Y_new_candidate)

    matrix = np.column_stack([matrix, X, Y_new])
    line, = ax.plot(X, Y_new, linestyle="--", picker=5, label=f"新曲线({kind})", color="red")
    lines.append(line)
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    fig.canvas.draw_idle()
    print(f"新增曲线: 由 {idx1} 和 {idx2} 混合，函数={kind}")

def augment_multiple(event):
    global matrix, lines
    root = tk.Tk()
    root.withdraw()
    n = simpledialog.askinteger("批量生成", "请输入要生成的曲线数量:")
    if not n or n <= 0:
        print("无效输入")
        return

    for _ in range(n):
        num_curves = matrix.shape[1] // 2
        idx1, idx2 = select_valid_pair(matrix)
        X = matrix[:, 2*idx1]
        Y1 = matrix[:, 2*idx1+1]
        Y2 = matrix[:, 2*idx2+1]
        kind = np.random.choice(["linear", "quadratic", "bezier"])
        f = random_function(len(X), kind)
        Y_new = Y1 * f + Y2 * (1 - f)
        matrix = np.column_stack([matrix, X, Y_new])
        line, = ax.plot(X, Y_new, linestyle="--", picker=5, label=f"新曲线({kind})", color="blue")
        lines.append(line)

    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    fig.canvas.draw_idle()
    print(f"批量生成 {n} 条曲线完成")

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
ax_delete = plt.axes([0.90, 0.04, 0.10, 0.08])
btn_delete = Button(ax_delete, '删除选中曲线')
btn_delete.on_clicked(delete_selected)
# ----------------------------
ax_undo = plt.axes([0.02, 0.04, 0.12, 0.08])
btn_undo = Button(ax_undo, '撤销')
btn_undo.on_clicked(undo)

ax_new = plt.axes([0.14, 0.04, 0.18, 0.08])
btn_new = Button(ax_new, '新增曲线')
btn_new.on_clicked(augment_curve)

ax_batch = plt.axes([0.32, 0.04, 0.22, 0.08])
btn_batch = Button(ax_batch, '批量生成')
btn_batch.on_clicked(augment_multiple)

ax_save = plt.axes([0.54, 0.04, 0.18, 0.08])
btn_save = Button(ax_save, '保存矩阵')
btn_save.on_clicked(save)

ax_toggle = plt.axes([0.72, 0.04, 0.18, 0.08])
btn_toggle = Button(ax_toggle, '切换纵坐标')
btn_toggle.on_clicked(toggle_scale)

ax_save_re = plt.axes([0.72, 0.00, 0.18, 0.04])
btn_save_re = Button(ax_save_re, '保存电阻值')
btn_save_re.on_clicked(save_resistance)


ax_save_set = plt.axes([0.54, 0.00, 0.18, 0.04])
btn_save_set = Button(ax_save_set, '保存set电压')
btn_save_set.on_clicked(save_setvoltage)


# ----------------------------
# 9. 事件绑定
# ----------------------------
fig.canvas.mpl_connect('pick_event', on_pick)

plt.show()
