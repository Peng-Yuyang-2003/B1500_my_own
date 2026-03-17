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
plt.subplots_adjust(right=0.85, bottom=0.12)

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

def calculate_Vth(Vg, Id, I_REF=1e-9):
    """
    计算阈值电压（固定电流法）
    返回 Vth，如果无法计算则返回 np.max(Vg)
    """
    # 清洗数据
    mask = (~pd.isna(Vg)) & (~pd.isna(Id))
    Vg = np.asarray(Vg[mask], dtype=float)
    Id = np.asarray(Id[mask], dtype=float)

    if len(Vg) < 2:
        return np.nan

    # 排序
    idx = np.argsort(Vg)
    Vg = Vg[idx]
    Id = Id[idx]

    # 固定电流法计算 Vth
    for k in range(len(Id) - 1):
        if Id[k] < I_REF <= Id[k + 1]:
            Vth = Vg[k] + (I_REF - Id[k]) * (Vg[k + 1] - Vg[k]) / (Id[k + 1] - Id[k])
            return Vth

    # 如果找不到，返回最大值
    return np.max(Vg)

def enhance_current(event):
    """
    分段线性放大电流
    - Vth 左侧：保持不变
    - Vth 到 1V：从 1 到 a 线性放大
    - 1V 右侧：直接放大 a 倍
    """
    global matrix, lines

    # 备份以便撤销
    backup_state()

    # 获取放大系数
    root = tk.Tk()
    root.withdraw()
    a = simpledialog.askfloat("放大电流", "请输入放大系数 a (例如 10):", minvalue=1.0, maxvalue=1000.0)
    if not a or a <= 0:
        print("无效输入，取消操作")
        return

    num_curves = matrix.shape[1] // 2

    for i in range(num_curves):
        Vg = matrix[:, 2*i]
        Id = matrix[:, 2*i+1]

        # 计算 Vth
        Vth = calculate_Vth(Vg, Id)

        if pd.isna(Vth):
            print(f"曲线 {i} 无法计算 Vth，跳过")
            continue

        # 创建缩放系数数组
        scale_factors = np.ones_like(Vg)

        for j in range(len(Vg)):
            if pd.isna(Vg[j]) or pd.isna(Id[j]):
                continue

            if Vg[j] <= Vth:
                # Vth 左侧：保持不变
                scale_factors[j] = 1.0
            elif Vg[j] >= Vth + 1.0:
                # 1V 右侧：直接放大 a 倍
                scale_factors[j] = a
            else:
                # Vth 到 Vth + 1V：线性插值从 1 到 a
                scale_factors[j] = 1.0 + (a - 1.0) * (Vg[j] - Vth) / (1.0)

        # 应用缩放
        matrix[:, 2*i+1] = Id * scale_factors

        print(f"曲线 {i}: Vth = {Vth:.4f}V, 放大系数 a = {a:.2f}")

    # 重新绘制
    redraw()
    print(f"所有曲线电流已分段放大，系数 a = {a}")

def shift_vth(event):
    """
    右移阈值电压功能（支持双向扫描）
    - 把正向扫描所有点的电流值向电压更大的方向填充，也就是电流数据全部向后移动n个位置，前面补0，
    - 把反向扫描所有点的电流值向电压更大的方向填充，也就是电流数据全部向前移动n个位置，后面补0，
    - 保持扫描方向不变（双向扫描特性）
    - 在4V到5V区间使用加权插值让双向扫描曲线逐渐逼近
    - 保持整体电压范围不变
    """
    global matrix, lines

    # 备份以便撤销
    backup_state()

    # 获取移动点数
    root = tk.Tk()
    root.withdraw()
    n = simpledialog.askinteger("右移阈值电压", "请输入移动的点数 n (例如 5):", minvalue=1, maxvalue=100)
    if not n or n <= 0:
        print("无效输入，取消操作")
        return

    num_curves = matrix.shape[1] // 2
    
    # 用于标识是否处理过正向/反向扫描的标记
    has_forward = False
    has_reverse = False

    for i in range(num_curves):
        Vg = matrix[:, 2*i]
        Id = matrix[:, 2*i+1]
        
        # 跳过空数据
        if np.all(np.isnan(Id)):
            continue

        # 简单判断扫描方向：第一个有效电压点与最后一个有效电压点的差值
        # 如果差值 > 0，则为正向扫描；否则为反向扫描
        valid_indices = np.where(~np.isnan(Vg))[0]
        if len(valid_indices) < 2:
            continue
            
        start_idx, end_idx = valid_indices[0], valid_indices[-1]
        direction = Vg[end_idx] - Vg[start_idx] # 正向 > 0, 反向 < 0
        
        # 复制一份数据进行操作，避免覆盖问题
        new_Id = Id.copy()
        
        if direction > 0:
            # 正向扫描：电流数据向后移动 n 个位置，前面补 0
            # Python切片: [n:] 取后段，[:-n] 取前段
            # new_Id[n:] = Id[:-n] 意味着 Id[0] 移动到了 new_Id[n]
            if n < len(Id):
                # 只有当 n 小于数据长度时才移动，否则全部置0
                new_Id[n:] = Id[:-n]
                new_Id[:n] = 0.0
            else:
                new_Id[:] = 0.0
            
            has_forward = True
            print(f"曲线 {i}: 正向扫描，数据向后移动 {n} 个点")
            
        else:
            # 反向扫描：电流数据向前移动 n 个位置，后面补 0
            # 向电压更大方向移动 = 数组索引变小 = 向前移
            # new_Id[:-n] = Id[n:] 意味着 Id[-1] 移动到了 new_Id[-1-n]
            if n < len(Id):
                new_Id[:-n] = Id[n:]
                new_Id[-n:] = 0.0
            else:
                new_Id[:] = 0.0
            
            has_reverse = True
            print(f"曲线 {i}: 反向扫描，数据向前移动 {n} 个点")

        # 应用修改
        matrix[:, 2*i+1] = new_Id

    # --- 处理 4V 到 5V 区间的加权插值 ---
    # 此逻辑假设正向扫描电压由低到高（0->5V），反向扫描电压由高到低（5V->0V）
    # 目标：在此区间内让两条曲线逐渐逼近（融合）
    
    # 仅当同时存在正向和反向扫描时才执行插值融合
    if has_forward and has_reverse:
        # 查找正向和反向扫描的曲线索引（这里简化逻辑，假设前半部分是正向，后半部分是反向，或者遍历查找）
        # 实际应用中可能需要更复杂的逻辑来配对同一器件的正反向扫描
        # 这里我们遍历所有曲线对进行尝试
        
        for i in range(num_curves):
            for j in range(i + 1, num_curves):
                Vg_i = matrix[:, 2*i]
                Id_i = matrix[:, 2*i+1]
                Vg_j = matrix[:, 2*j]
                Id_j = matrix[:, 2*j+1]
                
                # 判断是否为正反扫描对
                valid_i = np.where(~np.isnan(Vg_i))[0]
                valid_j = np.where(~np.isnan(Vg_j))[0]
                
                if len(valid_i) < 2 or len(valid_j) < 2:
                    continue
                    
                dir_i = Vg_i[valid_i[-1]] - Vg_i[valid_i[0]]
                dir_j = Vg_j[valid_j[-1]] - Vg_j[valid_j[0]]
                
                # 如果 i 是正向，j 是反向
                if dir_i > 0 and dir_j < 0:
                    # 在 4V 到 5V 区间进行加权插值
                    # 遍历该电压区间内的点
                    for k in range(len(Vg_i)):
                        v = Vg_i[k]
                        # 检查电压是否在 4V 到 5V 之间
                        if 4.0 <= v <= 5.0:
                            # 计算权重：(v - 4) / 1
                            # 4V时权重0，5V时权重1
                            # 此时我们让两条曲线的电流值取平均，并根据电压加权
                            # 权重 w 代表趋向程度
                            w = (v - 4.0) / 1.0
                            
                            # 找到另一条曲线上对应的电压点（反向扫描的电压与正向是对应的）
                            # 由于电压网格可能不完全对齐，使用最近的索引或插值
                            # 这里简化：假设电压点是对齐的（即同一行 k）
                            # 若不对齐，需使用 np.interp 或查找最近点，这里假设对齐
                            
                            if not (np.isnan(Id_i[k]) or np.isnan(Id_j[k])):
                                # 计算融合后的电流值
                                # 这里设计一种“逼近”逻辑：计算两者的加权平均
                                # 随着 V 升高，正向曲线权重降低，反向曲线权重升高？或反之？
                                # 题目要求“逐渐逼近”，通常意味着减少差异
                                # 这里采用简单的加权平均使它们趋于一致
                                avg_id = Id_i[k] * (1 - w) + Id_j[k] * w # 示例权重分配
                                
                                # 更新两条曲线
                                matrix[k, 2*i+1] = avg_id
                                matrix[k, 2*j+1] = avg_id

                    print(f"曲线 {i} 和 {j} 在 4V-5V 区间进行了加权融合")

    # 重新绘制
    redraw()
    print(f"所有曲线阈值电压已移动 {n} 个点")


# ----------------------------
# 8. 按钮放置
# ----------------------------
ax_undo = plt.axes([0.01, 0, 0.1, 0.07])#前两个是坐标，后两个是宽高
btn_undo = Button(ax_undo, '撤销')
btn_undo.on_clicked(undo)

ax_new = plt.axes([0.12, 0, 0.1, 0.07])
btn_new = Button(ax_new, '新增曲线')
btn_new.on_clicked(augment_curve)

ax_batch = plt.axes([0.23, 0, 0.1, 0.07])
btn_batch = Button(ax_batch, '批量生成')
btn_batch.on_clicked(augment_multiple)

ax_delete = plt.axes([0.34, 0, 0.1, 0.07])
btn_delete = Button(ax_delete, '删除选中曲线')
btn_delete.on_clicked(delete_selected)

ax_save = plt.axes([0.45, 0, 0.1, 0.07])
btn_save = Button(ax_save, '保存矩阵')
btn_save.on_clicked(save)

ax_toggle = plt.axes([0.56, 0, 0.1, 0.07])
btn_toggle = Button(ax_toggle, '切换纵坐标')
btn_toggle.on_clicked(toggle_scale)

ax_cal = plt.axes([0.67, 0, 0.1, 0.07])
btn_cal = Button(ax_cal, '计算关键值')
btn_cal.on_clicked(cal)

ax_enhance = plt.axes([0.78, 0, 0.1, 0.07])
btn_enhance = Button(ax_enhance, '放大电流')
btn_enhance.on_clicked(enhance_current)

ax_shift = plt.axes([0.89, 0, 0.1, 0.07])
btn_shift = Button(ax_shift, '右移阈值电压')
btn_shift.on_clicked(shift_vth)

# ----------------------------
# 9. 事件绑定
# ----------------------------
fig.canvas.mpl_connect('pick_event', on_pick)

plt.show()
