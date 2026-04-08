import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import os
import warnings

# 忽略 Pandas 的性能警告
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)
warnings.filterwarnings('ignore')

# ==========================================
# 0. Global Style Settings
# ==========================================
# 1) 强制设置全局字体为 Arial 6pt
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['font.size'] = 6
plt.rcParams['axes.labelsize'] = 6
plt.rcParams['axes.titlesize'] = 6
plt.rcParams['xtick.labelsize'] = 6
plt.rcParams['ytick.labelsize'] = 6
plt.rcParams['legend.fontsize'] = 6
plt.rcParams['figure.titlesize'] = 6
# 设置全局线宽默认值
plt.rcParams['axes.linewidth'] = 0.5
plt.rcParams['xtick.major.width'] = 0.5
plt.rcParams['ytick.major.width'] = 0.5
plt.rcParams['xtick.major.size'] = 2
plt.rcParams['ytick.major.size'] = 2
plt.rcParams['xtick.direction'] = 'out'
plt.rcParams['ytick.direction'] = 'out'
plt.rcParams['mathtext.default'] = 'regular'

cm_to_inc = 1 / 2.54

# ==========================================
# 1. Data Processing Logic
# ==========================================

class DriverAnalyzer:
    def __init__(self, filepath):
        print(f"Reading data: {filepath} ...")
        self.df = pd.read_excel(filepath) 
        
        # --- 替换为 GFD 数据配置 ---
        self.years = list(range(2001, 2021)) 
        self.anthro_codes = ['GFD_11', 'GFD_12', 'GFD_13', 'GFD_14', 'GFD_18', 'GFD_19', 'GFD_21', 'GFD_22']
        self.natural_codes = ['GFD_15', 'GFD_20']

    def _clean_geo_data(self):
        df = self.df.copy()
        df['GIS_AREA'] = pd.to_numeric(df['GIS_AREA'], errors='coerce')
        df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
        df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
        return df.dropna(subset=['Longitude', 'Latitude'])

    def process_hovmoller_data(self, lat_bin_size=1.5):
        print(f"Calculating Hovmöller Matrix (Bin size: {lat_bin_size} deg)...")
        df = self._clean_geo_data()
        lat_bins = np.arange(-60, 90 + lat_bin_size, lat_bin_size)
        df['Lat_Bin'] = pd.cut(df['Latitude'], bins=lat_bins, labels=lat_bins[:-1])
        matrix = np.zeros((len(lat_bins)-1, len(self.years)))
        matrix[:] = np.nan 
        
        for i, yr in enumerate(self.years):
            a_cols = [f"LY_{yr}_{c}" for c in self.anthro_codes]
            n_cols = [f"LY_{yr}_{c}" for c in self.natural_codes]
            df['Temp_Anthro'] = df[a_cols].sum(axis=1)
            df['Temp_Natural'] = df[n_cols].sum(axis=1)
            grouped = df.groupby('Lat_Bin')[['Temp_Anthro', 'Temp_Natural']].sum()
            total = grouped['Temp_Natural'] + grouped['Temp_Anthro']
            ratio = grouped['Temp_Natural'] / total
            for lat_label, r_val in ratio.items():
                if pd.isna(lat_label) or pd.isna(r_val): continue
                row_idx = np.where(lat_bins[:-1] == lat_label)[0][0]
                matrix[row_idx, i] = r_val
        return matrix, lat_bins


# ==========================================
# 2. Visualization Logic
# ==========================================

def plot_hovmoller_diagram(matrix, years, lat_bins, output_name="hovmoller.png"):
    fig, ax = plt.subplots(figsize=(2.5 * cm_to_inc, 5.965 * cm_to_inc)) 
    cmap = plt.get_cmap('RdYlBu_r')

    # 严格按照代码 1：使用连续渐变模式
    im = ax.imshow(matrix, aspect='auto', cmap=cmap, vmin=0, vmax=1,
                   extent=[years[0], years[-1]+1, lat_bins[0], lat_bins[-1]],
                   origin='lower', interpolation='nearest')
    
    ax.set_ylabel("", fontsize=6) 
    ax.set_ylim(-60, 90)
    yticks_locs = np.arange(-20, 91, 40)
    ax.set_yticks(yticks_locs)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{int(x)}°N" if x > 0 else (f"{int(abs(x))}°S" if x < 0 else "0°")))
    ax.tick_params(axis='y', which='both', left=True, labelleft=True, length=2, width=0.5, colors='black', direction='out', pad=2)
    plt.setp(ax.get_yticklabels(), rotation=90, va='center')

    ax.set_xticks([2001, 2010, 2020]) 
    ax.tick_params(axis='x', which='major', labelsize=6, width=0.5, length=2, color='black', direction='out', pad=2)
    
    for spine in ax.spines.values():
        spine.set_linewidth(0.5); spine.set_edgecolor('black')
    ax.axhline(0, color='black', linestyle='--', linewidth=0.5, alpha=0.5)
    
    cbar = plt.colorbar(im, ax=ax, orientation='vertical', shrink=0.7, pad=0.12, fraction=0.08, drawedges=False)
    cbar.set_label("Climate-related loss ratio", fontsize=6, labelpad=2)
    
    ticks = [0, 0.5, 1.0]
    cbar.set_ticks(ticks) # 代码 1 原始设置
    cbar.ax.set_yticklabels(['0', '0.5', '1'], rotation=90, va='center')
    cbar.ax.tick_params(width=0.5, length=2, color='black', labelsize=6, direction='out', pad=0.12)
    cbar.outline.set_linewidth(0.5)

    plt.savefig(output_name, dpi=600, bbox_inches='tight', pad_inches=0.05)
    plt.close()


# ==========================================
# Main Execution
# ==========================================
if __name__ == "__main__":
    file_path = r"H:\003 GPA数据\06 驱动因素\002 数据合并\001 GFD合并（各大洲）\01 GFD_2001_2020_经纬度_无森林与气候.xlsx"
    output_dir = r"H:\003 GPA数据\06 驱动因素\002 数据合并\001 GFD合并（各大洲）\01 绘图结果（驱动因素与二元图）"
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    
    try:
        analyzer = DriverAnalyzer(file_path)
        matrix, lat_bins = analyzer.process_hovmoller_data(lat_bin_size=1.5)
        plot_hovmoller_diagram(matrix, analyzer.years, lat_bins, os.path.join(output_dir, "02Figure_1b_Hovmoller_GFD03.png"))
        print("\nProcess completed successfully.")
    except Exception as e:
        import traceback; traceback.print_exc()



