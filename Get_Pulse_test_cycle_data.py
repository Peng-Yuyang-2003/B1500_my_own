# data_plotter.py
import pandas as pd
import matplotlib.pyplot as plt
import os

class DataPlotter:
    def __init__(self, max_col=10, x1_col=1, y1_col=2, x2_col=1, y2_col=3):
        """
        初始化绘图参数
        """
        self.max_col = max_col
        self.x1_col = x1_col
        self.y1_col = y1_col
        self.x2_col = x2_col
        self.y2_col = y2_col

        # 自动生成列名
        self.column_names = [f"col{i}" for i in range(max_col)]

    def plot_csv(self, filepath, show_plot=True, save_plot=True, out_dir=None):
        """
        绘制单个 CSV 文件并保存为 PNG 图片，同时输出 clean数据CSV
        """

        df = pd.read_csv(
            filepath,
            header=None,
            names=self.column_names,
            on_bad_lines='skip'
        )

        # 初始化数据列表
        x1_data, y1_data = [], []
        x2_data, y2_data = [], []

        ax1 = None

        # ------- Voltage 曲线 -------
        for _, row in df.iterrows():
            if row.iloc[0] == 'DataValue' and row.iloc[self.x1_col] != ' ':
                x1_data.append(float(row.iloc[self.x1_col]))
                y1_data.append(float(row.iloc[self.y1_col]))
            else:
                if x1_data:
                    fig, ax1 = plt.subplots()
                    ax1.plot(x1_data, y1_data, color='blue', label='Voltage (V)')
                    ax1.set_xlabel('Time (s)')
                    ax1.set_ylabel('Voltage (V)', color='blue')
                    ax1.tick_params(axis='y', labelcolor='blue')
                    break

        # ------- Current 曲线 -------
        for _, row in df.iterrows():
            if row.iloc[0] == 'DataValue' and row.iloc[self.x2_col] != ' ':
                x2_data.append(float(row.iloc[self.x2_col]))
                y2_data.append(-float(row.iloc[self.y2_col]))
            else:
                if x2_data:
                    ax2 = ax1.twinx()
                    ax2.plot(x2_data, y2_data, color='red', label='Current (A)')
                    ax2.set_ylabel('Current (A)', color='red')
                    ax2.tick_params(axis='y', labelcolor='red')
                    break

        # 合并图例
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='lower left')

        plt.title('Voltage & Current vs. Time')
        plt.tight_layout()

        # 输出目录
        if out_dir is None:
            out_dir = os.path.dirname(filepath)
        os.makedirs(out_dir, exist_ok=True)

        # 保存图像
        if save_plot:
            out_name = os.path.splitext(os.path.basename(filepath))[0] + ".png"
            out_path = os.path.join(out_dir, out_name)
            plt.savefig(out_path, dpi=300)
            print(f"[Saved figure] {out_path}")

        # 保存 clean 数据 CSV
        clean_df = pd.DataFrame({
            "x1_voltage_time": x1_data,
            "y1_voltage": y1_data,
            "x2_current_time": x2_data,
            "y2_current": y2_data
        })

        clean_name = "clean_" + os.path.splitext(os.path.basename(filepath))[0] + ".csv"
        clean_path = os.path.join(out_dir, clean_name)
        clean_df.to_csv(clean_path, index=False)
        print(f"[Saved clean CSV] {clean_path}")

        # 显示图像
        if show_plot:
            plt.show()
        else:
            plt.close()

        return True

    
# -------------------------------
# 直接运行 data_plotter.py 时自动绘图
# -------------------------------
if __name__ == "__main__":
    test_file = r"E:\\融合2\\实验数据\\2025-11-27\SW_1T1R_READ [(10) ; 11_27_2025 5_05_53 PM].csv"
    print(f"Running standalone mode, plotting: {test_file}")

    plotter = DataPlotter()
    plotter.plot_csv(test_file, show_plot=True, save_plot=True)
