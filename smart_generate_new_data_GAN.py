import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import warnings
import matplotlib
#用于读取矩阵csv然后生成新数据保存矩阵csv
# ----------------------------
# 基本设置（字体/忽略特定警告）
# ----------------------------
warnings.filterwarnings("ignore", message=".*glyph for.*")
matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei']  # 微软雅黑
matplotlib.rcParams['axes.unicode_minus'] = True

# ===============================
# 数据读取函数（使用你原来的）
# ===============================
def read_csv_convert_to_martix(importfile, log_even=False, only_even=False):
    matrix = pd.read_csv(importfile, header=None).to_numpy()
    nan_columns = np.any(np.isnan(matrix), axis=0)
    for i in range(len(nan_columns)):
        if nan_columns[i]:
            if i % 2 == 0 and i + 1 < len(nan_columns):
                nan_columns[i + 1] = True
            elif i % 2 == 1 and i - 1 >= 0:
                nan_columns[i - 1] = True
    matrix = matrix[:, ~nan_columns]
    groups = matrix.shape[1] // 2
    if log_even:
        matrix[:, ::2] = np.log1p(matrix[:, ::2])
    if only_even:
        matrix = matrix[:, 1::2]
    print(f"读取到 {groups} 条曲线，矩阵 shape = {matrix.shape}")
    return matrix

# ===============================
# 1. 读取并准备数据
# ===============================
importfile = r"E:\python\B1500_data_storage\filtered_matrix_35curves_20250905-100848.csv"  # <- 改成你的路径
matrix = read_csv_convert_to_martix(importfile, log_even=False, only_even=True)
