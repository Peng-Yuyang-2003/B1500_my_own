import os
from smart_b1500_csv_to_clean_csv import process_csv
import matplotlib.pyplot as plt
import pandas as pd

def process_directory(directory_path):
    """
    处理目录中的所有B1500 CSV文件并为每个文件生成图像.

    :param directory_path: 包含CSV文件的目录
    """
    for filename in os.listdir(directory_path):
        if filename.endswith(".csv") and not filename.endswith("_clean.csv"):
            file_path = os.path.join(directory_path, filename)
            
            # 1. 清理CSV并获取清理后文件的路径
            cleaned_csv_path = process_csv(file_path)

if __name__ == "__main__":
    # 在这里设置你要处理的文件夹路径
    target_directory = r"E:\融合2\实验数据\2025-12-05(1)"
    
    if os.path.isdir(target_directory):
        process_directory(target_directory)
    else:
        print(f"错误: 目录 '{target_directory}' 不存在.")
