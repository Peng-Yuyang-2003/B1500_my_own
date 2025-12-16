import pandas as pd
import matplotlib.pyplot as plt
# 指令
importfile = "E:\融合2\实验数据\SW_1T1R_forming [(1) ; 11_27_2025 4_04_05 PM].csv"#读取文件路径
export_flag = 0 # 是否执行导出代码的旗帜
exportfile = 'E:/python/B1500_data_processor/export_temp.xlsx' #导出文件路径
max_col = 10 # 存有数据的地方的列数
x1_col = 4 # x轴数据所在列
y1_col = 5 # y轴数据所在列
x2_col = 1 # x2轴数据所在列
y2_col = 3 # y2轴数据所在列
# 读文件

# 定义与最大列数匹配的列名（例如 col0 到 col3，共4列），也就意味着哪些列数不为4列的行将被跳过
column_names = [f"col{i}" for i in range(max_col)]

df = pd.read_csv(
    importfile,
    header=None,        # 假设原始文件无列名
    names=column_names, # 匹配最大列数的列名
    on_bad_lines='skip' # 跳过无法解析的行（可选）
)
# 初始化列表
x1_data = []
y1_data = []
x2_data = []
y2_data = []
# 遍历 DataFrame 的行获取电压数据
for index, row in df.iterrows():
    if row[0] == 'DataValue'and row[x1_col] != ' ':
        # 把数据添加到列表
        x1_data.append(float(row[x1_col]))
        y1_data.append(float(row[y1_col]))
    else:
        # 如果这是一个新的循环，绘制上一个循环的数据
        if x1_data:
            fig, ax1 = plt.subplots()
            ax1.plot(x1_data, y1_data, color='blue', label='Voltage (V)')
            ax1.set_xlabel('Time (s)')
            ax1.set_ylabel('Voltage (V)', color='blue')
            ax1.tick_params(axis='y', labelcolor='blue')
            #ax1.set_xlim(2.14, 2.3)
            # 把画出的数据导出到excel，打开xlsx时不要删掉之前已经写了的数据，从第0列开始写入，每一个循环占用两列
            if export_flag:
                export_df = pd.DataFrame({'T1': x1_data, 'A1': y1_data})
                with pd.ExcelWriter(exportfile, mode="a", if_sheet_exists="overlay", engine="openpyxl") as writer:export_df.to_excel(writer, index=False, header=False, startrow=0, startcol=cycle_num*2)
            x1_data = []
            y1_data = []
            break # 仅绘制第一个循环的数据

# 遍历 DataFrame 的行获取电流数据
for index, row in df.iterrows():
    if row[0] == 'DataValue' and row[x2_col] != ' ': # 有些数据是空的，这里要排除掉
        # 把数据添加到列表
        x2_data.append(float(row[x2_col]))
        y2_data.append(-float(row[y2_col]))
    else:
        # 如果这是一个新的循环，绘制上一个循环的数据
        if x2_data:
            #对y2_data做排序处理
            # 将 y2_data 切分为 50 段，每段 153 个数
            segments = [y2_data[i:i + 153] for i in range(0, len(y2_data), 153) if len(y2_data[i:i + 153]) == 153]

            # 按每段的平均值从大到小排序
            segments_sorted = sorted(segments, key=lambda segment: sum(segment) / len(segment), reverse=False)

            # 将排序后的段拼接为一个新的列表
            y2_data_sorted = [value for segment in segments_sorted for value in segment]

            # 更新 y2_data 为排序后的数据
            y2_data = y2_data_sorted
            ax2 = ax1.twinx()
            ax2.plot(x2_data, y2_data, color='red', label='Current (A)')
            ax2.set_ylabel('Current (A)', color='red')
            ax2.tick_params(axis='y', labelcolor='red')
            #ax2.set_xlim(2.14, 2.3)
            # 把画出的数据导出到excel，打开xlsx时不要删掉之前已经写了的数据，从第0列开始写入，每一个循环占用两列
            if export_flag:
                export_df = pd.DataFrame({'T1': x2_data, 'A1': y2_data})
                with pd.ExcelWriter(exportfile, mode="a", if_sheet_exists="overlay", engine="openpyxl") as writer:export_df.to_excel(writer, index=False, header=False, startrow=0, startcol=cycle_num*2)
            x2_data = []
            y2_data = []
            break # 仅绘制第一个循环的数据

# 合并图例并显示
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='lower left')

plt.title('Voltage & Current vs. Time')
plt.tight_layout()
plt.show()