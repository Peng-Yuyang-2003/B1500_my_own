import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
import sys
import numpy as np
#用来处理E:\C&C++\test_gpib_probe\test_gpib_probe的C++程序中获取的数据
# ===================== 配置区域 =====================
DATA_DIR = r"E:\C&C++\probe_test_data"   # 数据所在文件夹
# ===================================================
# ===================== 行为配置 =====================

ENABLE_FAILURE = True          # 是否允许SET/RESET失败
FAIL_PROB = 0.5                # 失败概率

ENABLE_MULTI_SWITCH = True     # 一个波形内允许多次SET/RESET

ENABLE_STATE_CARRY = True      # 是否把上一组的最终状态传递到下一组


DEVICE_STATE = {
    "R": None,      # 当前电阻
    "mode": "HRS"   # HRS or LRS
}
# ===================================================
def find_vi_files(index):
    """
    根据序号查找 V 和 I 文件
    """
    v_pattern = os.path.join(DATA_DIR, f"V{index}_*.csv")
    i_pattern = os.path.join(DATA_DIR, f"I{index}_*.csv")

    v_files = glob.glob(v_pattern)
    i_files = glob.glob(i_pattern)

    if not v_files or not i_files:
        raise FileNotFoundError(f"未找到序号 {index} 对应的 V 或 I 文件")
    file_time = -1
    # 默认取最后一个file_time = -1（同一次测试时间戳应一致）
    return v_files[file_time], i_files[file_time]

def tail_resistance(mean, sigma):
    """
    生成带拖尾的电阻（lognormal）
    mean: 目标均值
    sigma: 拖尾强度
    """
    return np.random.lognormal(np.log(mean), sigma)

def generate_memristor_current(time, voltage, current_true):

    R1 = tail_resistance(1e4, 0.1)
    R2 = tail_resistance(1e7, 0.1)

    current_limit = 1.13865e-4

    # ---------------------------
    # 初始状态
    # ---------------------------
    if ENABLE_STATE_CARRY and DEVICE_STATE["R"] is not None:
        R_state = DEVICE_STATE["R"]
    else:
        R_state = R2

    current = voltage / R_state

    # ---------------------------
    # 找脉冲
    # ---------------------------
    pos_idx = np.where(voltage > 2)[0]
    neg_idx = np.where(voltage < -2)[0]

    pos_groups = np.split(pos_idx, np.where(np.diff(pos_idx) != 1)[0] + 1)
    neg_groups = np.split(neg_idx, np.where(np.diff(neg_idx) != 1)[0] + 1)

    events = []

    for g in pos_groups:
        events.append(("SET", g))

    for g in neg_groups:
        events.append(("RESET", g))

    # 按时间排序
    events.sort(key=lambda x: x[1][0])

    # ---------------------------
    # switching循环
    # ---------------------------
    for event_type, pulse in events:

        if len(pulse) == 0:
            continue

        t = np.random.choice(pulse)

        # 是否失败
        fail = ENABLE_FAILURE and (np.random.rand() < FAIL_PROB)

        if event_type == "SET":

            if DEVICE_STATE["mode"] == "HRS":

                if not fail:
                    R_state = R1
                    DEVICE_STATE["mode"] = "LRS"

        elif event_type == "RESET":

            if DEVICE_STATE["mode"] == "LRS":

                if not fail:
                    R_state = R2
                    DEVICE_STATE["mode"] = "HRS"

        current[t:] = voltage[t:] / R_state

        if not ENABLE_MULTI_SWITCH:
            break

    # 保存状态
    DEVICE_STATE["R"] = R_state

    # 限流
    current = np.clip(current + current_true, -current_limit, current_limit)

    return current, R1, R2

def plot_voltage_current(index, show_plot=True):
    v_file, i_file = find_vi_files(index)

    print(f"使用电压文件: {v_file}")
    print(f"使用电流文件: {i_file}")

    # 读取 CSV
    v_data = pd.read_csv(v_file, header=None)
    i_data = pd.read_csv(i_file, header=None)

    time_v = v_data.iloc[:, 0]
    voltage = v_data.iloc[:, 1]

    time_i = i_data.iloc[:, 0]
    current_true = i_data.iloc[:, 1]
    # ===================== 把数据写回 =====================
    current_mem, R1, R2 = generate_memristor_current(time_v.values, voltage.values, current_true)
    i_data.iloc[:,1] = current_mem
    backup_dir = os.path.join(DATA_DIR, "backup")
    os.makedirs(backup_dir, exist_ok=True)
    backup = os.path.join(backup_dir, os.path.basename(i_file).replace(".csv", "_raw.csv"))
    i_data.to_csv(backup, header=False, index=False)
    # ===================== 画图 =====================
    if show_plot:
        fig, ax1 = plt.subplots(figsize=(7, 4))

        # 左轴：电压
        ax1.plot(time_v, voltage, label="Voltage (V)")
        ax1.set_xlabel("Time (s)")
        ax1.set_ylabel("Voltage (V)")
        ax1.tick_params(axis='y')

        # 右轴：电流
        ax2 = ax1.twinx()
        ax2.plot(time_i, current_mem, label="Current (A)", color='red')
        ax2.set_ylabel("Current (A)")
        ax2.tick_params(axis='y')

        # 合并图例
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="best")

        plt.title(f"Voltage & Current vs Time (Index {index})")
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    # 默认 index = 0
    index_range = int(sys.argv[1]) if len(sys.argv) > 1 else 0###这里的数字0表示画出I0\V0开头的最新一对数据,如果想画出多组数据，可以在命令行输入一个范围，例如 "5" 表示画出 index 0 到 5 的数据
    print(f"将尝试绘制 index 从 0 到 {index_range} 的数据")
    for index in range(index_range + 1):  # 假设最多有10组数据，实际可根据需要调整
        plot_voltage_current(index, show_plot=True)