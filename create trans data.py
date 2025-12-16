import pandas as pd
import matplotlib.pyplot as plt
import random
# 指令
importfile = "E:\融合2\实验数据\晶体管钝化前\Trans [(7) ; 2025_3_31 18_00_42].csv" #读取文件路径
export_flag = True # 是否执行导出代码的旗帜
exportfile = 'E:/python/B1500_data_processor/export_temp.xlsx' #导出文件路径
max_col = 6 # 最大列数
x_col = 1 # x轴数据所在列
y_col = 5 # y轴数据所在列
# min_xlim = -1 # x轴最小值
# max_xlim = 2 # x轴最大值
# min_ylim = 1e-14 # y轴最小值
# max_ylim = 1e-3 # y轴最大值
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
y_new_data = []
cycle_num = 0
# 遍历 DataFrame 的行
for index, row in df.iterrows():
    if row[0] == 'DataValue':
        # 把数据添加到列表
        x_data.append(float(row[x_col]))
        y_data.append(float(row[y_col]))
    else:
        # 如果这是一个新的循环，绘制上一个循环的数据
        if x_data and y_data:
            plt.semilogy(x_data, y_data)
            for i in range(10):
                #为y_data数据中的前103个数据添加绝对值小于10e-10的随机噪声，产生新的y_data，但是当y_data小于1e-6时不添加噪声
                y_new_data[0:140] = [y + random.uniform(-1e-7, 1e-7) if y > 1e-7 else y for y in y_data[0:140]]
                y_new_data[0:140] = [y + random.uniform(-1e-8, 1e-8) if y > 1e-8 else y for y in y_data[0:140]]
                y_new_data[0:140] = [y + random.uniform(-1e-9, 1e-9) if y > 1e-9 else y for y in y_data[0:140]]
                y_new_data[0:140] = [y + random.uniform(-1e-10, 1e-10) if y > 1e-10 else y for y in y_data[0:140]]
                #把y_data中的后103个数据添加到y_new_data中
                y_new_data[140:206] = y_data[140:206]
                #为y_data中每一个数乘以一个相同的0.1到10之间的随机数，产生新的y_data
                s = random.uniform(0.5, 1)
                y_new_data = [y * s for y in y_new_data]

                plt.semilogy(x_data, y_new_data)
                # 把画出的数据导出到excel，打开xlsx时不要删掉之前已经写了的数据，从第0列开始写入，每一个循环占用两列
                if export_flag:
                    export_df = pd.DataFrame({'V': x_data, 'A': y_data})
                    with pd.ExcelWriter(exportfile, mode="a", if_sheet_exists="overlay", engine="openpyxl") as writer:export_df.to_excel(writer, index=False, header=False, startrow=0, startcol=cycle_num*2)
                    cycle_num += 1
            x_data = []
            y_data = []
            

# 别忘了画出最后一组数据
#if x_data and y_data:
    #plt.semilogy(x_data, y_data)

print('cycle_number:',(cycle_num))
# 画出图案的要求
#plt.xlim(min_xlim, max_xlim)  # 设置x轴范围
#plt.ylim(min_ylim, max_ylim)  # 设置y轴范围
plt.xlabel('V')  # Set x-axis label
plt.ylabel('A')  # Set y-axis label
plt.show()