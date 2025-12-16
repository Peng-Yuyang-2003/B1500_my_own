import pandas as pd
import numpy as np
import os

def process_csv(importfile):
    """
    从B1500导出的CSV文件中提取数据矩阵. 

    :param importfile: 输入的CSV文件路径
    :return: 处理后的数据保存的文件路径
    """
    max_col = 7  # 最大列数
    #x_col = 1    # x轴数据所在列
    #y_col = 5    # y轴数据所在列

    column_names = [f"col{i}" for i in range(max_col)]
    try:
        df = pd.read_csv(
            importfile,
            header=None,
            names=column_names,
            on_bad_lines='skip',
            encoding='utf-8'
        )
    except UnicodeDecodeError:
        df = pd.read_csv(
            importfile,
            header=None,
            names=column_names,
            on_bad_lines='skip',
            encoding='latin1'
        )


    # 提取 DataValue 段落
    groups = []
    current_x, current_y = [], []

    for _, row in df.iterrows():
        if row['col0'] == 'DataValue':
            try:
                x = float(row[f"col{x_col}"])
                y = float(row[f"col{y_col}"])
                current_x.append(x)
                current_y.append(y)
            except (ValueError, TypeError):
                continue
        else:
            if current_x:  # 遇到分隔，存一组
                groups.append((np.array(current_x), np.array(current_y)))
                current_x, current_y = [], []

    # 最后如果有数据也加进去
    if current_x:
        groups.append((np.array(current_x), np.array(current_y)))

    if not groups:
        print(f"在 {importfile} 中没有找到有效数据.")
        return None

    # 转为矩阵 (m, 2n)
    max_len = max(len(g[0]) for g in groups)
    matrix = np.zeros((max_len, 2 * len(groups)))
    for i, (x, y) in enumerate(groups):
        matrix[:len(x), 2*i] = x
        matrix[:len(y), 2*i+1] = y
        if len(x) < max_len:  # 对齐时，后面补NaN
            matrix[len(x):, 2*i] = np.nan
            matrix[len(y):, 2*i+1] = np.nan

    print(f"在 {importfile} 中读取到 {len(groups)} 条曲线，矩阵 shape = {matrix.shape}")

    # 保存矩阵为CSV文件
    outputfile = importfile.replace(".csv", "_clean.csv")
    pd.DataFrame(matrix).to_csv(outputfile, index=False, header=False)
    print(f"清理后的数据已保存到 {outputfile}")
    return outputfile

if __name__ == "__main__":
    # 保留单个文件处理功能
    importfile = r"E:\融合2\实验数据\2025-12-13\1-25-7-240cycle-not-end-third-group.csv"
    if os.path.exists(importfile):
        process_csv(importfile)
    else:
        print(f"文件不存在: {importfile}")
