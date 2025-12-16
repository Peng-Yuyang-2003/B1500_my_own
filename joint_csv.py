import os
import pandas as pd
import glob

def merge_clean_csv_files():
    # 获取用户输入的文件夹路径
    folder_path = input("请输入包含CSV文件的文件夹路径: ")
    
    # 获取用户输入的文件名片段
    name_fragment = input("请输入要查找的文件名片段(如'11'): ")
    
    # 构造匹配模式：包含指定片段且以'_clean.csv'结尾
    pattern = f"*{name_fragment}*_clean.csv"
    search_path = os.path.join(folder_path, pattern)
    
    # 查找匹配的文件
    matched_files = glob.glob(search_path)
    
    if not matched_files:
        print(f"未找到包含'{name_fragment}'且以'_clean.csv'结尾的文件")
        return
    
    print(f"找到 {len(matched_files)} 个匹配文件:")
    for file in matched_files:
        print(f"- {os.path.basename(file)}")
    
    # 按文件名排序以保证顺序一致
    matched_files.sort()
    
    # 横向拼接所有CSV文件
    merged_df = pd.DataFrame()
    for file in matched_files:
        df = pd.read_csv(file, header=None, low_memory=False)
        merged_df = pd.concat([merged_df, df], axis=1)
    
    # 保存合并结果
    output_file = os.path.join(folder_path, f"{name_fragment}_merged_clean.csv")
    merged_df.to_csv(output_file, index=False, header=False)
    print(f"\n所有文件已横向拼接并保存至: {output_file}")

if __name__ == "__main__":
    merge_clean_csv_files()
