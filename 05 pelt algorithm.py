import numpy as np
import pandas as pd
import scipy.signal.signaltools

# ==========================================
# 补丁区：修复 statsmodels 与新版库的冲突 (保持不变)
# ==========================================
if not hasattr(np, 'MachAr'):
    class MachAr:
        def __init__(self, float_conv_type=float, int_conv_type=int,
                     float_to_float=float, int_to_float=float,
                     title='Python floating point number'):
            finfo = np.finfo(float)
            self.eps = finfo.eps
            self.tiny = finfo.tiny
            self.huge = finfo.max
            self.precision = finfo.precision
            self.resolution = finfo.resolution
    np.MachAr = MachAr

if not hasattr(pd, 'Int64Index'):
    pd.Int64Index = pd.Index
if not hasattr(pd, 'Float64Index'):
    pd.Float64Index = pd.Index

def _centered(arr, newsize):
    newsize = np.asarray(newsize)
    currsize = np.array(arr.shape)
    startind = (currsize - newsize) // 2
    endind = startind + newsize
    myslice = [slice(startind[k], endind[k]) for k in range(len(endind))]
    return arr[tuple(myslice)]

if not hasattr(scipy.signal.signaltools, '_centered'):
    scipy.signal.signaltools._centered = _centered

# ==========================================

import ruptures as rpt
import statsmodels.api as sm
from scipy import stats
import os
from collections import Counter

# ================= 1. 全局配置 =================
file_path = r'H:\003 GPA数据\03 按lossyear统计\02GPA_LoseYear\08 绘图（断点）\004 Summary_Result_GlobalConClim_20260208.xlsx'
output_file = os.path.join(os.path.dirname(file_path), '005_断点检测与验证表格（补充材料）_min3.xlsx')

# 敏感性分析扫描范围 (恢复为完整的范围)
PENALTY_RANGE = np.arange(0.5, 5.5, 0.5) 

# ================= 2. 核心算法 =================

def run_pelt_rbf_detection(signal, pen):
    """ 使用 Ruptures-Pelt (RBF Kernel) 检测断点 (保持不变) """
    try:
        signal_reshaped = np.array(signal).reshape(-1, 1)
        algo = rpt.Pelt(model="rbf", min_size=3, jump=1).fit(signal_reshaped)
        breakpoints = algo.predict(pen=pen)
        valid_bps = [bp for bp in breakpoints if 0 < bp < len(signal)]
        return valid_bps[0] if valid_bps else None
    except:
        return None

def calculate_slope_r2(y):
    """ 计算一段数据的斜率和 R2 (保持不变) """
    n = len(y)
    if n < 3: return np.nan, np.nan
    x = np.arange(n)
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    return slope, r_value**2

def compare_global_vs_segmented(y, break_index):
    """ 对比全局模型 vs 分段模型 (保持不变) """
    n = len(y)
    x = np.arange(n)
    
    # 全局模型
    slope_g, intercept_g, r_val_g, _, _ = stats.linregress(x, y)
    y_pred_g = slope_g * x + intercept_g
    rss_g = np.sum((y - y_pred_g)**2)
    rmse_g = np.sqrt(rss_g / n)
    r2_g = r_val_g**2
    
    # 分段模型
    y1 = y[:break_index]
    x1 = np.arange(len(y1))
    if len(y1) >= 2:
        s1, i1, _, _, _ = stats.linregress(x1, y1)
        rss1 = np.sum((y1 - (s1*x1 + i1))**2)
    else: rss1 = 0
    
    y2 = y[break_index:]
    x2 = np.arange(len(y2))
    if len(y2) >= 2:
        s2, i2, _, _, _ = stats.linregress(x2, y2)
        rss2 = np.sum((y2 - (s2*x2 + i2))**2)
    else: rss2 = 0
    
    rss_seg = rss1 + rss2
    rmse_seg = np.sqrt(rss_seg / n)
    tss = np.sum((y - np.mean(y))**2)
    r2_seg = 1 - (rss_seg / tss) if tss != 0 else 0
        
    return {
        'Global R2': r2_g,
        'Segmented R2': r2_seg,
        'Delta R2': r2_seg - r2_g,
        'Global RMSE': rmse_g,
        'Segmented RMSE': rmse_seg,
        'RMSE Reduction': rmse_g - rmse_seg
    }

def calculate_chow_test(y, break_index):
    """ 计算 Chow Test (保持不变) """
    if break_index < 3 or (len(y) - break_index) < 3:
        return np.nan, np.nan, 0
    X = sm.add_constant(np.arange(len(y)))
    try:
        rss_global = sm.OLS(y, X).fit().ssr
        k = 2 
        y1, y2 = y[:break_index], y[break_index:]
        X1 = sm.add_constant(np.arange(len(y1)))
        X2 = sm.add_constant(np.arange(len(y2)))
        rss1 = sm.OLS(y1, X1).fit().ssr
        rss2 = sm.OLS(y2, X2).fit().ssr
        n1, n2 = len(y1), len(y2)
        numerator = (rss_global - (rss1 + rss2)) / k
        denominator = (rss1 + rss2) / (n1 + n2 - 2 * k)
        if denominator == 0: return np.nan, np.nan, 0
        f_stat = numerator / denominator
        p_value = 1 - stats.f.cdf(f_stat, k, n1 + n2 - 2 * k)
        n = len(y)
        rss_global = max(rss_global, 1e-10)
        rss_split = max(rss1 + rss2, 1e-10)
        bic_global = n * np.log(rss_global/n) + k * np.log(n)
        bic_break = n * np.log(rss_split/n) + 2*k * np.log(n)
        return f_stat, p_value, (bic_global - bic_break)
    except:
        return np.nan, np.nan, 0

# ================= 3. 主程序逻辑 =================

if not os.path.exists(file_path):
    print(f"错误：文件不存在 {file_path}")
    exit()

print("正在读取数据...")
df = pd.read_excel(file_path)
years = df['Year'].values
regions = df.columns[1:]

summary_data = []
sensitivity_matrix_list = []

print(f"开始处理 {len(regions)} 个区域...")

for region in regions:
    print(f"  -> 分析: {region}")
    signal = df[region].values
    
    # --- A. 敏感性分析 (保持不变) ---
    sensitivity_row = {'Region': region}
    detected_years_scan = []
    
    for p in PENALTY_RANGE:
        b_idx_scan = run_pelt_rbf_detection(signal, pen=p)
        if b_idx_scan is not None:
            yr = years[b_idx_scan-1]
            detected_years_scan.append(yr)
            sensitivity_row[f"Pen={p}"] = yr
        else:
            detected_years_scan.append(np.nan)
            sensitivity_row[f"Pen={p}"] = "None"
    sensitivity_matrix_list.append(sensitivity_row)
    
    # --- B. 核心断点检测 (pen=3) ---
    target_pen = 3
    bk_idx = run_pelt_rbf_detection(signal, pen=target_pen)
    
    # --- C. 统计计算 ---
    if bk_idx is not None:
        bk_year = years[bk_idx-1]
        
        # 1. 稳定性 & Range (保持不变)
        freq = detected_years_scan.count(bk_year)
        stability = (freq / len(PENALTY_RANGE)) * 100
        matching_indices = [i for i, yr in enumerate(detected_years_scan) if yr == bk_year]
        if matching_indices:
            pen_range_str = f"{PENALTY_RANGE[min(matching_indices)]}-{PENALTY_RANGE[max(matching_indices)]}"
        else:
            pen_range_str = "-"
            
        # 2. 斜率 (保持不变)
        p1_data = signal[:bk_idx]
        p2_data = signal[bk_idx:]
        slope_p1, r2_p1 = calculate_slope_r2(p1_data)
        slope_p2, r2_p2 = calculate_slope_r2(p2_data)
        
        # 3. 统计检验 (Chow Test + 【新增】Mann-Whitney)
        chow_f, chow_p, delta_bic = calculate_chow_test(signal, bk_idx)
        
        # 【此处为新增修改】：计算并保存 U 统计量
        u_stat, u_p = stats.mannwhitneyu(p1_data, p2_data, alternative='two-sided')
        
        # 4. 模型对比 (保持不变)
        model_comp = compare_global_vs_segmented(signal, bk_idx)
        
        if slope_p2 > slope_p1: status = 'Accelerated'
        elif slope_p2 < slope_p1: status = 'Decelerated'
        else: status = 'Stable'
            
        record = {
            'Region': region,
            'Breakpoint Year': int(bk_year),
            'Algorithm': 'PELT-RBF (Pen=3)',
            'Stability (%)': f"{stability:.1f}%",
            'Stable Penalty Range': pen_range_str,
            # 模型对比指标
            'Global R2': model_comp['Global R2'],
            'Segmented R2': model_comp['Segmented R2'],
            'Delta R2': model_comp['Delta R2'],
            'Global RMSE': model_comp['Global RMSE'],
            'Segmented RMSE': model_comp['Segmented RMSE'],
            'RMSE Reduction': model_comp['RMSE Reduction'],
            # 基础信息
            'P1 Slope': slope_p1,
            'P2 Slope': slope_p2,
            'Slope Status': status,
            'P1 R2': r2_p1,
            'P2 R2': r2_p2,
            'Chow Test (P)': chow_p,
            'Delta BIC': delta_bic,
            # 【新增】Mann-Whitney 统计量
            'Mann-Whitney (P)': u_p,
            'Mann-Whitney (U)': u_stat
        }
    else:
        # 无断点情况
        global_slope, global_r2 = calculate_slope_r2(signal)
        n = len(signal)
        x = np.arange(n)
        s, i, _, _, _ = stats.linregress(x, signal)
        rss = np.sum((signal - (s*x + i))**2)
        rmse = np.sqrt(rss/n)
        
        record = {
            'Region': region,
            'Breakpoint Year': 'Not Detected',
            'Algorithm': 'PELT-RBF (Pen=3)',
            'Stability (%)': f"{stability:.1f}%" if 'stability' in locals() else "0%",
            'Stable Penalty Range': '-',
            'Global R2': global_r2,
            'Segmented R2': '-',
            'Delta R2': '-',
            'Global RMSE': rmse,
            'Segmented RMSE': '-',
            'RMSE Reduction': '-',
            'P1 Slope': global_slope,
            'P2 Slope': '-',
            'Slope Status': 'Stable',
            'P1 R2': '-',
            'P2 R2': '-',
            'Chow Test (P)': '-',
            'Delta BIC': '-',
            'Mann-Whitney (P)': '-',
            'Mann-Whitney (U)': '-'
        }
        
    summary_data.append(record)

# ================= 4. 导出 =================
df_summary = pd.DataFrame(summary_data)
df_sensitivity = pd.DataFrame(sensitivity_matrix_list)

try:
    with pd.ExcelWriter(output_file) as writer:
        df_summary.to_excel(writer, sheet_name='Validation_Summary', index=False)
        df_sensitivity.to_excel(writer, sheet_name='Sensitivity_Matrix', index=False)
        
    print("\n" + "="*60)
    print("【处理完成】")
    print(f"已增加 Mann-Whitney (U Statistic & P Value) 统计量。")
    print(f"输出文件: {output_file}")
    print("="*60)
    
    # 预览
    print("\n[关键检验指标预览]:")
    cols_preview = ['Region', 'Breakpoint Year', 'Chow Test (P)', 'Mann-Whitney (P)', 'Mann-Whitney (U)']
    print(df_summary[cols_preview].to_string())
    
except Exception as e:
    print(f"保存失败: {e}")


