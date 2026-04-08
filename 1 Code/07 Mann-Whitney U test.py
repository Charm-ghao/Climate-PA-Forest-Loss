import pandas as pd
import numpy as np
from scipy import stats
import os

# ==========================================
# 1. 配置参数
# ==========================================
input_path = r"H:\003 GPA数据\06 驱动因素\002 数据合并\004 绘图（图4）\04ClimData.xlsx"

# 定义每一列对应的 Period 1 结束年份
# 逻辑：P1 = [Start, End], P2 = [End+1, Final]
# 例如 Global: 2001-2016, 则 P1_End_Year = 2016
config_breakpoints = {
    'Global': 2016,         # 2001-2016 vs 2017-2024
    'South America': 2015,  # 2001-2015 vs 2016-2024
    'Africa': 2012,         # 2001-2012 vs 2013-2024
    'PA size': 2016,        # 2001-2016 vs 2017-2024
    'Temperate': 2018,      # 2001-2018 vs 2019-2024
    'Tropical': 2015,       # 2001-2015 vs 2016-2024
    'Boreal': 2012,         # 2001-2012 vs 2013-2024
    'Subtropical': 2015     # 2001-2015 vs 2016-2024
}

# ==========================================
# 2. 读取数据
# ==========================================
print(f"正在读取文件: {input_path}")
try:
    df = pd.read_excel(input_path)
except FileNotFoundError:
    print("错误：找不到文件，请检查路径。")
    exit()

# 检查 Year 列 (兼容大小写)
if 'Year' not in df.columns:
    # 尝试查找类似的列名
    for col in df.columns:
        if col.lower() == 'year':
            df.rename(columns={col: 'Year'}, inplace=True)
            break
    else:
        print("错误：表格中找不到 'Year' 列。")
        exit()

# ==========================================
# 3. 循环计算 Mann-Whitney U Test
# ==========================================
results = []

# 更新打印表头，增加 Std P1 和 Std P2
print("-" * 130)
print(f"{'Variable':<18} {'P1 Period':<12} {'Mean P1':<10} {'Std P1':<10} {'Mean P2':<10} {'Std P2':<10} {'Change%':<10} {'P-value':<10} {'Sig'}")
print("-" * 130)

for col_name, p1_end in config_breakpoints.items():
    if col_name not in df.columns:
        print(f"跳过: 列名 '{col_name}' 在 Excel 中未找到")
        continue

    # 1. 数据切片
    group_p1 = df[df['Year'] <= p1_end][col_name].dropna().values
    group_p2 = df[df['Year'] > p1_end][col_name].dropna().values

    if len(group_p1) < 2 or len(group_p2) < 2:
        print(f"跳过: '{col_name}' 数据量不足")
        continue

    # 2. 计算统计量：均值、标准差和变化率
    mean_p1 = np.mean(group_p1)
    std_p1 = np.std(group_p1, ddof=1) # ddof=1 表示样本标准差
    
    mean_p2 = np.mean(group_p2)
    std_p2 = np.std(group_p2, ddof=1)
    
    change_pct = (mean_p2 - mean_p1) / mean_p1 * 100

    # 3. 核心检验: Mann-Whitney U test (双尾)
    stat, p_val = stats.mannwhitneyu(group_p1, group_p2, alternative='two-sided')

    # 4. 显著性标记
    if p_val < 0.001: sig = "***"
    elif p_val < 0.01: sig = "**"
    elif p_val < 0.05: sig = "*"
    else: sig = "ns"

    # 5. 记录结果
    period_str = f"2001-{p1_end}"
    period_p2_str = f"{p1_end+1}-2024"
    
    results.append({
        'Variable': col_name,
        'P1_Period': period_str,
        'P2_Period': period_p2_str,
        'Mean_P1': mean_p1,
        'Std_P1': std_p1,
        'Mean_P2': mean_p2,
        'Std_P2': std_p2,
        'Change_Pct': round(change_pct, 2),
        'U_Statistic': stat,
        'P_value': p_val,
        'Significance': sig
    })

    # 格式化输出
    print(f"{col_name:<18} {period_str:<12} {mean_p1:<10.2f} {std_p1:<10.2f} {mean_p2:<10.2f} {std_p2:<10.2f} {change_pct:<10.1f} {p_val:<10.5f} {sig}")

# ==========================================
# 4. 保存结果
# ==========================================
file_dir, file_name = os.path.split(input_path)
file_base, file_ext = os.path.splitext(file_name)
output_name = f"{file_base}_统计分析结果{file_ext}"
output_path = os.path.join(file_dir, output_name)

if results:
    results_df = pd.DataFrame(results)
    # 调整列顺序，使输出更美观
    cols = ['Variable', 'P1_Period', 'P2_Period', 'Mean_P1', 'Std_P1', 'Mean_P2', 'Std_P2', 'Change_Pct', 'U_Statistic', 'P_value', 'Significance']
    results_df = results_df[cols]
    
    results_df.to_excel(output_path, index=False)
    print("-" * 130)
    print(f"处理完成！结果已包含均值和标准差，并保存至:\n{output_path}")
else:
    print("未生成任何结果，请检查列名是否匹配。")



