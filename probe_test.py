import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
import sys
#用来处理E:\C&C++\test_gpib_probe\test_gpib_probe的C++程序中获取的数据
# ===================== 配置区域 =====================
DATA_DIR = r"E:\C&C++\probe_test_data"   # 数据所在文件夹
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


def plot_voltage_current(index):
    v_file, i_file = find_vi_files(index)

    print(f"使用电压文件: {v_file}")
    print(f"使用电流文件: {i_file}")

    # 读取 CSV
    v_data = pd.read_csv(v_file, header=None)
    i_data = pd.read_csv(i_file, header=None)

    time_v = v_data.iloc[:, 0]
    voltage = v_data.iloc[:, 1]

    time_i = i_data.iloc[:, 0]
    current = i_data.iloc[:, 1]

    # ===================== 画图 =====================
    fig, ax1 = plt.subplots(figsize=(7, 4))

    # 左轴：电压
    ax1.plot(time_v, voltage, label="Voltage (V)")
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Voltage (V)")
    ax1.tick_params(axis='y')

    # 右轴：电流
    ax2 = ax1.twinx()
    ax2.plot(time_i, 0-current, label="Current (A)", color='red')# 电流取负值以便更好地显示
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
    index = sys.argv[1] if len(sys.argv) > 1 else "0"###这里的数字0表示画出最后一组里的第一对数据
    plot_voltage_current(7)