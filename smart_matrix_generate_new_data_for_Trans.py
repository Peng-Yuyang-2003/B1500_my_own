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
importfile = r"E:\融合2\实验数据\2026-1-29-mostuihuobyothers\Trans [(25) ; 2026_1_29 10_28_40]-multidevice_clean.csv"
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
ax.set_title("点击曲线高亮（再点一次取消） / 新增 / 批量生成 / 撤销 / 保存 / 切换 Y 轴")
ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))

ax.yaxis.set_major_formatter(ScalarFormatter())
ax.ticklabel_format(style='plain', axis='y')

# ----------------------------
# 2. 计算关键值
# ----------------------------
def cal(event):
    # =========================
    # 可调物理参数（建议不要乱改）
    # =========================
    I_REF = 1e-9          # 固定电流法 Vth
    I_SS_LOW = 1e-11      # SS 下限
    I_SS_HIGH = 3e-9      # SS 上限
    VG_WINDOW = 0.05      # Ion/Ioff 取值窗口 (V)
    W   = 40e-6        # m
    L   = 2e-6        # m
    Vd  = 1         # V
    Cox = 1.5e-2     # F/m^2  (例：12 nm HfO2 Cox = ε0*εr/tox 20*8.85e-12/12e-9)
    gm_win  = 5       # gm 滑动窗口点数

    ncols = matrix.shape[1]
    ncurves = ncols // 2

    print("=" * 110)
    print("Curve | Vth@1e-9A(V) | SS(mV/dec) | Ion/Ioff | Imax(A) | mu_FE,max (cm^2/Vs)")
    print("=" * 110)

    for i in range(ncurves):
        Vg = matrix[:, 2*i]
        Id = matrix[:, 2*i + 1]

        # ---------- 清洗数据 ----------
        mask = (~pd.isna(Vg)) & (~pd.isna(Id))
        Vg = np.asarray(Vg[mask], dtype=float)
        Id = np.abs(np.asarray(Id[mask], dtype=float))

        if len(Vg) < 20:
            continue

        # 排序（防止反向扫描造成插值错误）
        idx = np.argsort(Vg)
        Vg = Vg[idx]
        Id = Id[idx]

        # =========================
        # 1. Vth —— 固定电流法
        # =========================
        Vth = np.nan
        for k in range(len(Id) - 1):
            if Id[k] < I_REF <= Id[k + 1]:
                # 线性插值
                Vth = Vg[k] + (I_REF - Id[k]) * \
                      (Vg[k + 1] - Vg[k]) / (Id[k + 1] - Id[k])
                break

        # =========================
        # 2. SS —— 受限亚阈值区
        # =========================
        SS = extract_SS_adaptive(Vg, Id,
                                 I_noise=I_SS_LOW,
                                 window=6,
                                 r2_threshold=0.98)

        # =========================
        # 3. Ion / Ioff —— 固定 Vg
        # =========================
        Vg_on = np.max(Vg)
        Vg_off = np.min(Vg)

        Ion_mask = np.abs(Vg - Vg_on) < VG_WINDOW
        Ioff_mask = np.abs(Vg - Vg_off) < VG_WINDOW

        if np.any(Ion_mask) and np.any(Ioff_mask):
            Ion = np.median(Id[Ion_mask])
            Ioff = np.median(Id[Ioff_mask])
            Ion_Ioff = Ion / Ioff if Ioff > 0 else np.nan
        else:
            Ion_Ioff = np.nan
        # =========================
        # 3. Imax —— 求最大电流
        # =========================
        Imax = np.max(Id)
        # =========================
        # 3. μFE_max —— 滑动窗口 Vg
        # =========================
        mu_FE_max = np.nan
        valid = (Id > I_REF) & (Vg > Vth)

        Vg_lin = Vg[valid]
        Id_lin = Id[valid]

        if len(Vg_lin) > gm_win:
            gm_list = []
            for k in range(len(Vg_lin) - gm_win):
                dId = Id_lin[k+gm_win] - Id_lin[k]
                dVg = Vg_lin[k+gm_win] - Vg_lin[k]
                if dVg > 0:
                    gm_list.append(dId / dVg)

            if gm_list:
                gm_max = np.max(gm_list)
                mu_FE_max = gm_max * L / (W * Cox * Vd) * 1e4  # → cm^2/Vs

        print(f"{i:5d} | {Vth:12.4f} | {SS:11.1f} | {Ion_Ioff:9.2e} | "
              f"{Imax:8.2e} | {mu_FE_max:10.2f}")


        # =========================
        # 输出
        # =========================
        print(f"{i:5d} | {Vth:12.4f} | {SS:11.1f} | {Ion_Ioff:9.2e} | "
        f"{Imax:8.2e} | {mu_FE_max:10.2f}")

    print("=" * 110)

def extract_SS_adaptive(Vg, Id,
                        I_noise=5e-11,
                        window=6,
                        r2_threshold=0.98):
    """
    自适应亚阈值摆幅提取
    返回 SS (mV/dec)，若无有效指数区则返回 np.nan
    """
    # 把Id整个向量前后颠倒，颠倒顺序对SS没有影响，因为扫描方向是双向的
    #Id = Id[::-1]
    #Vg = Vg[::-1]
    #print(Id)
    # 排除噪声区
    mask = Id > I_noise
    Vg = Vg[mask]
    Id = Id[mask]

    if len(Vg) < window + 2:
        return np.nan

    logId = np.log10(Id)

    best_slope = None
    best_r2 = 0

    for i in range(len(Vg) - window + 1):
        x = Vg[i:i + window]
        y = logId[i:i + window]

        # 线性拟合
        coef = np.polyfit(x, y, 1)
        y_fit = np.polyval(coef, x)

        # R^2
        ss_res = np.sum((y - y_fit) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        slope = coef[0]

        # 只接受“足够线性 + 正斜率”
        if r2 > r2_threshold and slope > 0:
            # 选斜率最大的指数区
            if best_slope is None or slope > best_slope:
                best_slope = slope
                best_r2 = r2

    if best_slope is None:
        return np.nan

    SS = 1 / best_slope * 1e3  # mV/dec
    return SS

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

def select_valid_pair(matrix, max_trials=50, threshold=0.01, factor=100):
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
    Y_new = f * np.where((Y1 < Y2)&(Y2 < smooth_level), Y1*np.exp(jump_magnitude), Y1)+ np.where((Y2 < Y1)&(Y1 < smooth_level), Y2*np.exp(jump_magnitude), Y2) * (1 - f) + noise

    matrix = np.column_stack([matrix, X, Y_new])
    line, = ax.plot(X, Y_new, linestyle="--", picker=5, label=f"新曲线({kind})", color="blue")
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
ax_undo = plt.axes([0.00, 0.03, 0.08, 0.07])
btn_undo = Button(ax_undo, '撤销')
btn_undo.on_clicked(undo)

ax_new = plt.axes([0.08, 0.03, 0.16, 0.07])
btn_new = Button(ax_new, '新增曲线')
btn_new.on_clicked(augment_curve)

ax_batch = plt.axes([0.24, 0.03, 0.16, 0.07])
btn_batch = Button(ax_batch, '批量生成')
btn_batch.on_clicked(augment_multiple)

ax_save = plt.axes([0.40, 0.03, 0.16, 0.07])
btn_save = Button(ax_save, '保存矩阵')
btn_save.on_clicked(save)

ax_toggle = plt.axes([0.56, 0.03, 0.20, 0.07])
btn_toggle = Button(ax_toggle, '切换纵坐标')
btn_toggle.on_clicked(toggle_scale)

ax_cal = plt.axes([0.76, 0.03, 0.20, 0.07])
btn_cal = Button(ax_cal, '计算关键值')
btn_cal.on_clicked(cal)

# ----------------------------
# 9. 事件绑定
# ----------------------------
fig.canvas.mpl_connect('pick_event', on_pick)

plt.show()
