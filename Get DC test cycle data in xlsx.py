import pandas as pd

#文件地址"E:\融合\论文数据和图片收集\RRAM_sy\downleft_1.xlsx"

import matplotlib.pyplot as plt
min_xlim = -5 # x轴最小值
max_xlim = 6 # x轴最大值
min_ylim = 1e-15 # y轴最小值
max_ylim = 1e-2 # y轴最大值
# 读取Excel文件
file_path = r"E:\\融合2\\实验数据\\2025-12-13\\1-25-7-240cycle-not-end-third-group.csv"
data = pd.read_csv(file_path, header=None)

# 初始化图表
plt.figure()
plt.yscale('log')  # 设置纵轴为对数坐标

# 遍历列数据并绘制曲线
for i in range(0, data.shape[1], 2):
    if i + 1 < data.shape[1]:
        x = data.iloc[:, i]
        y = data.iloc[:, i + 1]
        if (y < 1e-15).any() or (y > 1e-3).any():
            continue
        # 将0替换为一个非常小的正数 
        plt.plot(x, y, label=f'Curve {i//2 + 1}', color='blue', linewidth=0.5)

# 画出图案的要求
plt.xlim(min_xlim, max_xlim)  # 设置x轴范围
plt.ylim(min_ylim, max_ylim)  # 设置y轴范围
plt.xlabel('V')  # Set x-axis label
plt.ylabel('A')  # Set y-axis label
plt.show()