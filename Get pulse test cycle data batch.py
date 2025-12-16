# batch_plot.py
import os
from Get_Pulse_test_cycle_data import DataPlotter

def plot_all_csv_in_folder(folder_path, show_plot=False):
    """
    为文件夹中所有 CSV 文件绘图
    :param folder_path: CSV 所在目录
    :param show_plot: 是否显示图（一般批处理设为 False）
    """

    plotter = DataPlotter()  # 使用默认列

    for file in os.listdir(folder_path):
        if file.lower().endswith(".csv"):
            csv_path = os.path.join(folder_path, file)
            print(f"Processing: {csv_path}")
            plotter.plot_csv(csv_path, show_plot=True, save_plot=True)

    print("All CSV files have been processed.")

if __name__ == "__main__":
    # 你可以在这里直接填写路径，或者后续改成 argparse
    folder = r"E:\\融合2\\实验数据\\2025-11-27"
    plot_all_csv_in_folder(folder)
