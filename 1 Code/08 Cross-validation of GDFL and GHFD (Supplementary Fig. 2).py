import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import os
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

# ================= 1. 参数配置 =================
file_gdfl = r'H:\003 GPA数据\08 数据集之间的一致性比较\01 WRI_2001_2024_经纬度_无森林与气候.xlsx'
file_ghfd = r'H:\003 GPA数据\08 数据集之间的一致性比较\01 GFD_2001_2020_经纬度_无森林与气候.xlsx'
output_dir = os.path.dirname(file_gdfl)
years = range(2001, 2021)
MIN_AREA_KM2 = 0.01 
gdfl_natural_codes = ['05', '07']
ghfd_natural_codes = ['15', '20']

# ================= 2. 数据处理函数 =================
def get_climate_area(filepath, dataset_name, natural_codes, years):
    try:
        df = pd.read_excel(filepath)
    except Exception as e:
        print(f"读取失败 {filepath}: {e}")
        return None
    df['SITE_PID'] = df['SITE_PID'].astype(str)
    col_name = f'{dataset_name}_Climate_km2'
    df[col_name] = 0.0
    prefix_mid = "WRI" if dataset_name == "GDFL" else "GFD"
    for yr in years:
        for code in natural_codes:
            c = f'LY_{yr}_{prefix_mid}_{code}'
            if c in df.columns:
                df[col_name] += df[c].fillna(0)
    cols_to_keep = ['SITE_PID', col_name]
    if 'Continent' in df.columns:
        cols_to_keep.append('Continent')
    return df[cols_to_keep]

# ================= 3. 数据准备 =================
print("正在读取数据...")
df_gdfl = get_climate_area(file_gdfl, "GDFL", gdfl_natural_codes, years)
df_ghfd = get_climate_area(file_ghfd, "GHFD", ghfd_natural_codes, years)

if 'Continent' in df_ghfd.columns and 'Continent' in df_gdfl.columns:
    df_ghfd = df_ghfd.drop(columns=['Continent'])

print("正在合并数据集...")
df_merged = pd.merge(df_gdfl, df_ghfd, on='SITE_PID', how='inner')

df_valid = df_merged[
    (df_merged['GDFL_Climate_km2'] > MIN_AREA_KM2) & 
    (df_merged['GHFD_Climate_km2'] > MIN_AREA_KM2)
].copy()

# 准备绘图列表：Global + 排序后的各大洲
regions = ['Global'] + sorted(df_valid['Continent'].unique().tolist())

# ================= 4. 组合绘图逻辑 (Nature 2行4列布局) =================

print(f"开始绘制组合图，共 {len(regions)} 个区域...")

# Nature 双栏宽度约 183mm (7.2 inches)
# 设置 2 行 4 列，figsize=(宽, 高)
fig, axes = plt.subplots(nrows=2, ncols=4, figsize=(7.2, 3.4), dpi=600)
axes = axes.flatten() # 展平为 1D 数组方便索引

# 全局样式
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['axes.linewidth'] = 0.5
plt.rcParams['xtick.direction'] = 'out'
plt.rcParams['ytick.direction'] = 'out'

# 遍历每个区域进行绘图
for i, ax in enumerate(axes):
    # 如果索引超出了区域数量（例如第8个格），隐藏该坐标轴
    if i >= len(regions):
        ax.axis('off')
        continue

    region_name = regions[i]
    print(f"  - 处理: {region_name}")

    # 获取子数据
    if region_name == 'Global':
        sub_df = df_valid
    else:
        sub_df = df_valid[df_valid['Continent'] == region_name]

    if len(sub_df) < 5:
        ax.text(0.5, 0.5, "Insufficient Data", ha='center', va='center', fontsize=6)
        continue

    # 数据准备
    x_raw = sub_df['GDFL_Climate_km2']
    y_raw = sub_df['GHFD_Climate_km2']
    x_log = np.log10(x_raw).values 
    y_log = np.log10(y_raw).values

    # 线性回归
    slope, intercept, r_value, p_value, std_err = stats.linregress(x_log, y_log)

    # 计算密度 KDE
    xy = np.vstack([x_log, y_log])
    z = stats.gaussian_kde(xy)(xy)
    idx = z.argsort()
    x_plot, y_plot, z_plot = x_log[idx], y_log[idx], z[idx]

    # --- 绘图 ---
    # 散点
    sc = ax.scatter(x_plot, y_plot, c=z_plot, s=0.5, cmap='seismic', edgecolors='none', alpha=0.9)

    # 线条
    min_val = min(x_log.min(), y_log.min())
    max_val = max(x_log.max(), y_log.max())
    # 统一坐标轴范围，美观
    ax.set_xlim(min_val - 0.2, max_val + 0.2)
    ax.set_ylim(min_val - 0.2, max_val + 0.2)
    
    # 1:1 参考线
    ax.plot([min_val, max_val], [min_val, max_val], 'k--', linewidth=1.0, alpha=0.8)
    # 拟合线
    x_fit = np.linspace(min_val, max_val, 100)
    y_fit = slope * x_fit + intercept
    ax.plot(x_fit, y_fit, color='limegreen', linestyle='-', linewidth=1.2, alpha=0.9)

    # 右上角区域名称 (7号, Arial, Bold)
    # fix: horizontalalignment='right' 确保文字在框内
    ax.text(0.05, 0.90, region_name, 
            transform=ax.transAxes, 
            fontsize=7, 
            fontweight='bold', 
            verticalalignment='top', 
            horizontalalignment='left', 
            color='black')

    # --- 坐标轴格式化 ---
    def format_func(value, tick_number):
        return f'$10^{{{int(value)}}}$'
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(format_func))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_func))
    
    # 刻度设置
    ax.tick_params(axis='both', colors='black', labelsize=6, direction='out', width=0.5, length=2)

    # --- 智能标签显示 (Shared Labels Logic) ---
    # 只有最左侧的一列显示 Y 轴标题
    if i % 4 == 0: 
        ax.set_ylabel('Climate-driven loss (GHFD 30m)', fontsize=6, labelpad=1)
    else:
        # ax.set_yticklabels([]) # 可选：如果想隐藏内侧刻度数值
        ax.set_ylabel('')

    # 只有最下面的一行 (或第7张图) 显示 X 轴标题
    # 第一行索引 0,1,2,3; 第二行 4,5,6,7. 
    # 我们希望 4,5,6 以及 3(因为3下面没有图了，如果它是最后一张) 显示
    # 简单策略：所有图都显示刻度，但Label只给底部
    if i >= 4 or (i == 3 and len(regions) <= 4): 
        ax.set_xlabel('Climate-driven loss (GDFL 1km)', fontsize=6, labelpad=1)
    else:
        # ax.set_xticklabels([]) # 可选：如果想隐藏内侧刻度数值
        ax.set_xlabel('')

    # --- Inset Colorbar ---
    # 放在右下角
    cax = inset_axes(ax, width="5%", height="30%", loc='lower right',
                     bbox_to_anchor=(-0.30, 0.10, 1, 1), 
                     bbox_transform=ax.transAxes, borderpad=0)
    cb = plt.colorbar(sc, cax=cax, orientation='vertical')
    cb.set_ticks([z_plot.min(), z_plot.max()])
    cb.ax.set_yticklabels(['Low', 'High'], fontsize=5, va='center')
    cb.outline.set_linewidth(0.5)
    cb.ax.tick_params(width=0.5, length=1.5, direction='out', color='black')

# 5. 调整布局
plt.tight_layout()
plt.subplots_adjust(wspace=0.30, hspace=0.20) # 增加子图间距，防止标签重叠

# 6. 保存
out_file = os.path.join(output_dir, '05Fig_S1_Combined_Panel.png')
plt.savefig(out_file, dpi=600, bbox_inches='tight')
print(f"\n组合图已生成: {out_file}")
plt.show()
