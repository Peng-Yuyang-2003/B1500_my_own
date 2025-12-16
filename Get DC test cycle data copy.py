import pandas as pd
import matplotlib.pyplot as plt
# 指令
importfile = "E:\融合2\实验数据\SET_0-2.5-0 [(162) ; 2025_3_18 11_39_25]_good31_17_15.csv" #读取文件路径
export_flag = True # 是否执行导出代码的旗帜
exportfile = 'E:/python/B1500_data_processor/export_temp.xlsx' #导出文件路径
max_col = 4 # 最大列数
x_col = 1 # x轴数据所在列
y_col = 3 # y轴数据所在列
min_xlim = -1 # x轴最小值
max_xlim = 2 # x轴最大值
min_ylim = 1e-7 # y轴最小值
max_ylim = 1e-2 # y轴最大值
# 读文件

# 定义与最大列数匹配的列名（例如 col0 到 col3，共4列），也就意味着哪些列数不为4列的行将被跳过
column_names = [f"col{i}" for i in range(max_col)]

df = pd.read_csv(
    importfile,
    header=None,        # 假设原始文件无列名
    names=column_names, # 匹配最大列数的列名
    on_bad_lines='skip' # 跳过无法解析的行（可选）
)
# print(df) # 调试专用：打印 DataFrame
# 初始化列表
x_data = []
y_data = []
cycle_num = 0
# 遍历 DataFrame 的行
for index, row in df.iterrows():
    if row[0] == 'DataValue':
        # 把数据添加到列表
        x_data.append(float(row[x_col])/2)
        y_data.append(float(row[y_col]))
    else:
        # 如果这是一个新的循环，绘制上一个循环的数据
        if x_data and y_data:
            plt.semilogy(x_data, y_data)
            # 把画出的数据导出到excel，打开xlsx时不要删掉之前已经写了的数据，从第0列开始写入，每一个循环占用两列
            if export_flag:
                export_df = pd.DataFrame({'V': x_data, 'A': y_data})
                with pd.ExcelWriter(exportfile, mode="a", if_sheet_exists="overlay", engine="openpyxl") as writer:export_df.to_excel(writer, index=False, header=False, startrow=0, startcol=cycle_num*2)
            x_data = []
            y_data = []
            cycle_num += 1

# 别忘了画出最后一组数据
if x_data and y_data:
    plt.semilogy(x_data, y_data)

print('cycle_number:',(cycle_num+1)/2)
# 画出图案的要求
#plt.xlim(min_xlim, max_xlim)  # 设置x轴范围
plt.ylim(min_ylim, max_ylim)  # 设置y轴范围
plt.xlabel('V')  # Set x-axis label
plt.ylabel('A')  # Set y-axis label
plt.show()