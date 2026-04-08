import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter
from matplotlib.lines import Line2D
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import os
import warnings

plt.rcParams['mathtext.default'] = 'regular'

# 忽略警告
warnings.filterwarnings('ignore')

# ==========================================
# 0. 全局绘图风格设置 (对齐代码 1)
# ==========================================
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['font.size'] = 6
plt.rcParams['axes.labelsize'] = 6
plt.rcParams['axes.titlesize'] = 6
plt.rcParams['xtick.labelsize'] = 6
plt.rcParams['ytick.labelsize'] = 6
plt.rcParams['legend.fontsize'] = 6
plt.rcParams['figure.titlesize'] = 6

# 🔧 新增：全局刻度线设置 (对齐代码 1)
plt.rcParams['xtick.major.size'] = 2
plt.rcParams['ytick.major.size'] = 2
plt.rcParams['xtick.direction'] = 'out'
plt.rcParams['ytick.direction'] = 'out'

cm_to_inc = 1 / 2.54

# ==========================================
# 1. 数据处理类
# ==========================================
class BivariateMapGenerator:
    def __init__(self, filepath):
        print(f"正在读取数据: {filepath} ...")
        self.df = pd.read_excel(filepath) 
        self.years = range(2001, 2024) # 修正为2001-2023，或根据实际情况调整
        
        # 定义列名
        self.anthro_codes = ['WRI_01', 'WRI_02', 'WRI_03', 'WRI_04', 'WRI_06'] 
        self.natural_codes = ['WRI_05', 'WRI_07'] 

        # 3x3 双变量配色方案
        self.color_matrix = {
            '0-0': '#e8e8e8', '0-1': '#b0d5df', '0-2': '#64acbe',  # Na Low
            '1-0': '#e4acac', '1-1': '#ad9ea5', '1-2': '#627f8c',  # Na Med
            '2-0': '#c85a5a', '2-1': '#985356', '2-2': '#574249'   # Na High
        }

    def process_data(self):
        df = self.df.copy()
        df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
        df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
        df['GIS_AREA'] = pd.to_numeric(df['GIS_AREA'], errors='coerce')
        
        df = df.dropna(subset=['Longitude', 'Latitude'])
        
        print("正在聚合驱动因素数据...")
        anthro_cols = [f"LY_{yr}_{c}" for yr in self.years for c in self.anthro_codes]
        natural_cols = [f"LY_{yr}_{c}" for yr in self.years for c in self.natural_codes]
        
        for col in anthro_cols + natural_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            else:
                df[col] = 0.0

        df['Loss_Anthro_Total'] = df[anthro_cols].sum(axis=1)
        df['Loss_Natural_Total'] = df[natural_cols].sum(axis=1)
        df['Total_Loss_Sum'] = df['Loss_Anthro_Total'] + df['Loss_Natural_Total']

        df['GIS_AREA'] = df['GIS_AREA'].replace(0, np.nan)
        df['Anthro_Density'] = df['Loss_Anthro_Total'] / df['GIS_AREA']
        df['Natural_Density'] = df['Loss_Natural_Total'] / df['GIS_AREA']

        df = df.dropna(subset=['Anthro_Density', 'Natural_Density']).copy()

        def get_quantile_class(series):
            nonzero = series[series > 0]
            if len(nonzero) == 0:
                return pd.Series(0, index=series.index)
            q33 = nonzero.quantile(0.33)
            q66 = nonzero.quantile(0.66)
            def categorize(val):
                if val <= 0: return 0
                if val <= q33: return 0
                elif val <= q66: return 1
                else: return 2
            return series.apply(categorize)

        df['An_Class'] = get_quantile_class(df['Anthro_Density'])
        df['Na_Class'] = get_quantile_class(df['Natural_Density'])
        df['Bivariate_Color'] = df.apply(lambda row: self.color_matrix[f"{int(row['Na_Class'])}-{int(row['An_Class'])}"], axis=1)
        df['Draw_Order'] = df['An_Class'] + df['Na_Class']
        
        return df

    def export_statistics(self, df, output_path):
        total_pas = len(df)
        crosstab_count = pd.crosstab(df['Na_Class'], df['An_Class'])
        crosstab_pct = (crosstab_count / total_pas) * 100
        labels = {0: 'Low', 1: 'Med', 2: 'High'}
        crosstab_count.rename(index=labels, columns=labels, inplace=True)
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            pd.DataFrame({'Metric': ['Total'], 'Count': [total_pas]}).to_excel(writer, sheet_name='Summary', index=False)
            crosstab_count.to_excel(writer, sheet_name='Matrix', startrow=2)
        print(f"统计数据已保存至: {output_path}")

# 🔧 尺寸缩放函数 (对齐代码 1 的参数 0.03)
def scale_size(area_ha):
    return np.clip(np.sqrt(area_ha/100) * 0.03, 0.05, 8)

# ==========================================
# 2. 绘图函数 (核心修改部分)
# ==========================================
def plot_bivariate_map(df, generator_instance, output_file):
    df_sorted = df.sort_values('Draw_Order', ascending=True)
    
    # 🔧 1. 画布设置 (对齐代码 1: 12cm x 5.5cm)
    fig = plt.figure(figsize=(12 * cm_to_inc, 5.5 * cm_to_inc))
    ax = plt.axes(projection=ccrs.PlateCarree())
    
    # 🔧 2. 地图要素与范围 (对齐代码 1)
    ax.add_feature(cfeature.LAND, facecolor='#FFFFFF', alpha=1.0)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.2, edgecolor='#666666')
    ax.set_extent([-180, 180, -60, 90], crs=ccrs.PlateCarree())
    
    # 🔧 3. 边框设置 (对齐代码 1: 黑色，0.5线粗)
    ax.spines['geo'].set_visible(True)
    ax.spines['geo'].set_edgecolor('black') 
    ax.spines['geo'].set_linewidth(0.5)

    # 🔧 4. 经纬度刻度设置 (对齐代码 1)
    ax.set_xticks(np.arange(-180, 181, 60), crs=ccrs.PlateCarree())
    ax.set_yticks(np.arange(-20, 91, 40), crs=ccrs.PlateCarree())   

    lon_formatter = LongitudeFormatter(zero_direction_label=True)
    lat_formatter = LatitudeFormatter()
    ax.xaxis.set_major_formatter(lon_formatter)
    ax.yaxis.set_major_formatter(lat_formatter)

    # 🔧 5. 刻度参数设置 (对齐代码 1: 显示四周标签，线长2)
    ax.tick_params(
        axis='both', which='major', labelsize=6, color='black',
        length=2, width=0.5,
        top=True, labeltop=True,      
        bottom=True, labelbottom=True,
        left=True, labelleft=True,    
        direction='out', pad=2
    )
    plt.setp(ax.get_yticklabels(), rotation=90, va='center')

    # 🔧 6. 绘制散点
    area_ha = df_sorted['GIS_AREA'].values * 100
    sizes = scale_size(area_ha)
    
    ax.scatter(
        x=df_sorted['Longitude'], 
        y=df_sorted['Latitude'],
        c=df_sorted['Bivariate_Color'],
        s=sizes,
        alpha=0.6, # 统一透明度
        edgecolors='none',
        transform=ccrs.PlateCarree(),
        zorder=2
    )

    # 🔧 7. 双变量图例 (位置微调以对齐风格)
    ax_legend = inset_axes(ax, width="13%", height="28%", loc='lower left',
                           bbox_to_anchor=(0.06, 0.14, 1, 1), 
                           bbox_transform=ax.transAxes, borderpad=0)
    
    matrix = generator_instance.color_matrix
    for n in [0, 1, 2]:
        for a in [0, 1, 2]:
            color = matrix[f"{n}-{a}"]
            rect = mpatches.Rectangle((a, n), 1, 1, facecolor=color, edgecolor='white', linewidth=0.2) 
            ax_legend.add_patch(rect)
            
    ax_legend.set_xlim(0, 3)
    ax_legend.set_ylim(0, 3)
    ax_legend.tick_params(left=False, bottom=False)
    
    ax_legend.set_xticks([0.5, 1.5, 2.5])
    ax_legend.set_xticklabels(['Low', 'Med', 'High'], fontsize=4, color='#555555')
    ax_legend.set_yticks([0.5, 1.5, 2.5])
    ax_legend.set_yticklabels(['Low', 'Med', 'High'], fontsize=4, rotation=90, va='center', color='#555555')
    
    # 调整 X 轴（Anthropogenic 轴）标签距离
    ax_legend.tick_params(axis='x', pad=0.05)

    # 调整 Y 轴（Climate-related 轴）标签距离
    ax_legend.tick_params(axis='y', pad=0.05)    
    
    ax_legend.set_xlabel(r"Anthropogenic $\rightarrow$", fontsize=5, labelpad=1)
    ax_legend.set_ylabel(r"Climate-related $\rightarrow$", fontsize=5, labelpad=1)
    ax_legend.set_facecolor('none')
    for spine in ax_legend.spines.values():
        spine.set_visible(False)
        
    ax_legend.text(3.1, 2.5, "Double\nJeopardy", fontsize=5, color='#574249', fontweight='bold', va='center')

    # 🔧 8. 保护区面积图例 (位置放在双变量图例上方)
    example_areas_ha = np.array([1000, 1000000]) 
    example_sizes = scale_size(example_areas_ha)
    pa_legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='none', 
               markeredgecolor='#999999', markeredgewidth=0.4, markersize=example_sizes[0], 
               linestyle='', label=r'$10^{3}$'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='none', 
               markeredgecolor='#999999', markeredgewidth=0.4, markersize=example_sizes[1], 
               linestyle='', label=r'$10^{6}$'),
    ]
    ax.legend(handles=pa_legend_elements, loc='lower left', bbox_to_anchor=(0.035, 0.44),
              fontsize=5, frameon=False, ncol=2, title='PA size (ha)', title_fontsize=5,
              columnspacing=0.5, handletextpad=0.1)

    # 🔧 9. 保存设置 (对齐代码 1)
    plt.tight_layout()
    plt.savefig(output_file, dpi=600, bbox_inches='tight')
    print(f"\n绘图完成！图片已保存至: {output_file}")
    plt.close()

# ==========================================
# 3. 程序入口
# ==========================================
if __name__ == "__main__":
    file_path = r"H:\003 GPA数据\06 驱动因素\002 数据合并\002 WRI合并（各大洲）\01 WRI_2001_2024_经纬度_无森林与气候.xlsx"
    output_dir = r"H:\003 GPA数据\06 驱动因素\002 数据合并\002 WRI合并（各大洲）\01 绘图结果（驱动因素与二元图）"
    output_png_path = os.path.join(output_dir, "01Bivariate_Map_气候与人为双变量03.png")
    output_xlsx_path = os.path.join(output_dir, "01 九宫格双重压力统计结果02.xlsx")
    
    if not os.path.exists(output_dir): os.makedirs(output_dir)

    try:
        generator = BivariateMapGenerator(file_path)
        df_processed = generator.process_data()
        generator.export_statistics(df_processed, output_xlsx_path)
        plot_bivariate_map(df_processed, generator, output_file=output_png_path)
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        
