import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
import pymannkendall as mk
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.colors import LinearSegmentedColormap, LogNorm
from matplotlib.lines import Line2D
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# 🔧 全局字体设置为 Arial 8号
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['font.size'] = 6
plt.rcParams['axes.labelsize'] = 6
plt.rcParams['axes.titlesize'] = 6
plt.rcParams['xtick.labelsize'] = 6
plt.rcParams['ytick.labelsize'] = 6
plt.rcParams['legend.fontsize'] = 6
plt.rcParams['figure.titlesize'] = 6

# ==================== 1. 数据读取 ====================
print("=" * 80)
print("步骤 1: 读取保护区数据")
print("=" * 80)

# 定义损失年份列（2001-2024）
loss_years = list(range(2001, 2025))
loss_cols = [f'LY_{year}_Area_km2' for year in loss_years]

# 🔧 指定数据类型字典
dtype_dict = {col: float for col in loss_cols}

# 读取数据
print("正在读取Excel文件...")
df = pd.read_excel(
    r'H:\003 GPA数据\03 按lossyear统计\02GPA_LoseYear\06 绘图（分布图）\00 Updated_LossYear_LatLon_2001_2024.xlsx',
    header=0,
    dtype=dtype_dict
)

print(f"原始数据维度: {df.shape}")
print(f"原始保护区数量: {len(df):,}")

# 🔧 强制转换数据类型
print("\n强制转换数据类型...")
for col in loss_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0).astype(np.float64)

# 转换坐标和面积
df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
df['GIS_AREA'] = pd.to_numeric(df['GIS_AREA'], errors='coerce')

# 🔧 【关键修改】转换并筛选森林面积
print("\n" + "="*80)
print("🌲 森林面积筛选")
print("="*80)

if 'forestMask_Area_km2' in df.columns:
    df['forestMask_Area_km2'] = pd.to_numeric(df['forestMask_Area_km2'], errors='coerce')
    
    # 统计排除前的数量
    original_count = len(df)
    no_forest_count = (df['forestMask_Area_km2'].fillna(0) == 0).sum()
    
    # 排除森林面积为0的保护区
    df = df[df['forestMask_Area_km2'] > 0].copy()
    
    print(f"原始保护区总数: {original_count:,}")
    print(f"无森林保护区数量: {no_forest_count:,}")
    print(f"排除后保护区数量: {len(df):,}")
    print(f"排除比例: {no_forest_count/original_count*100:.2f}%")
    print(f"保留比例: {len(df)/original_count*100:.2f}%")
else:
    print("\n⚠️ 警告: 数据中没有 'forestMask_Area_km2' 列，无法进行森林面积筛选！")
    print("   将继续使用全部保护区进行分析...")

print("="*80)

# 删除坐标缺失的行
original_count_coord = len(df)
df = df.dropna(subset=['Longitude', 'Latitude'])
if len(df) < original_count_coord:
    print(f"\n⚠️ 删除了 {original_count_coord - len(df)} 个坐标缺失的保护区")

# 计算总损失
df['Total_Loss_2001_2024'] = df[loss_cols].sum(axis=1)

print(f"\n✓ 最终用于分析的保护区数量: {len(df):,}")

# 如果有森林面积列，在预览中显示
preview_cols = ['SITE_ID', 'NAME_ENG', 'Longitude', 'Latitude', 'GIS_AREA']
if 'forestMask_Area_km2' in df.columns:
    preview_cols.append('forestMask_Area_km2')
preview_cols.append('Total_Loss_2001_2024')

print(f"\n前3行数据预览:")
print(df[preview_cols].head(3))


# ==================== 2. 可视化：森林损失总量空间分布 ====================
print("\n" + "=" * 80)
print("步骤 2: 生成森林损失总量空间分布图")
print("=" * 80)

# 筛选有损失的保护区
loss_data = df[df['Total_Loss_2001_2024'] > 0].copy()
no_loss_data = df[df['Total_Loss_2001_2024'] == 0].copy()

print(f"\n有森林损失的保护区数量: {len(loss_data):,}")
print(f"无森林损失的保护区数量: {len(no_loss_data):,}")
print(f"总损失面积: {loss_data['Total_Loss_2001_2024'].sum():.2f} ha")
print(f"损失面积统计:")
print(f"  最小值: {loss_data['Total_Loss_2001_2024'].min():.4f} ha")
print(f"  最大值: {loss_data['Total_Loss_2001_2024'].max():.2f} ha")
print(f"  中位数: {loss_data['Total_Loss_2001_2024'].median():.4f} ha")
print(f"  平均值: {loss_data['Total_Loss_2001_2024'].mean():.4f} ha")

# 创建图形
fig_loss = plt.figure(figsize=(5.91, 3.94))
ax_loss = plt.axes(projection=ccrs.PlateCarree())
# ax_loss = plt.axes(projection=ccrs.Robinson())

ax_loss.add_feature(cfeature.LAND, facecolor='#FFFFFF', alpha=1.0)
ax_loss.add_feature(cfeature.COASTLINE, linewidth=0.2, edgecolor='#666666')
ax_loss.add_feature(cfeature.BORDERS, linewidth=0.2, edgecolor='#AAAAAA', alpha=0.5)
ax_loss.set_extent([-180, 180, -60, 90], crs=ccrs.PlateCarree())
# ax_loss.spines['geo'].set_visible(False)
# 加边框
ax_loss.spines['geo'].set_visible(True)
ax_loss.spines['geo'].set_edgecolor('#666666')  # 浅灰
ax_loss.spines['geo'].set_linewidth(0.25)        # 细线


# 🔧 新的连续配色方案：浅灰色(0) → 橙色 → 深红色
colors_continuous = ['#E8E8E8', '#FFA500', '#FF4500', '#8B0000']
# colors_continuous = ['#F0F0F0', '#90EE90', '#FFD700', '#8B0000']
# colors_continuous = ['#F0F0F0', '#90EE90', '#FFD700', '#8B0000']   ### 采用
# colors_continuous = ['#F0F0F0', '#90EE90', '#FFD700', '#FFA500', '#FF8C00', '#FF4500', '#DC143C']
# colors_continuous = ['#E8E8E8', '#C8E6C9', '#FFA500', '#FF4500', '#8B0000']
# colors_continuous = ['#E8E8E8', '#D3D3D3', '#FFA500', '#FF6347', '#DC143C']
# colors_continuous = ['#F0F0F0', '#E0E0E0', '#FFB84D', '#FF8C42', '#D2691E']
# colors_continuous = ['#EEEEEE', '#FFD580', '#FFA500', '#FF6347']

# 🔧 新的连续配色方案：浅灰色(0) → 绿色 → 橙色 → 深红色
# colors_continuous = ['#E8E8E8', '#90EE90', '#FFA500', '#FF6347', '#DC143C']
# 🔧 最小化红色的配色方案
# colors_continuous = ['#EEEEEE', '#A5D6A7', '#66BB6A', '#FFE57F', '#FFB74D', '#EF5350']  # 10
# # 或者完全去掉红色
# colors_continuous = ['#EEEEEE', '#A5D6A7', '#66BB6A', '#FFD54F', '#FF9800', '#FF6F00']
# # 🔧 优化配色：增加绿色和橙色的占比，减少红色
# colors_continuous = ['#F5F5F5', '#B8E6B8', '#90EE90', '#FFE082', '#FFB84D', '#FF7043']
# colors_continuous = ['#E8E8E8', '#C8E6C9', '#90EE90', '#FFD54F', '#FFA726', '#FF6347']

cmap = LinearSegmentedColormap.from_list('loss_cmap', colors_continuous, N=256)

# 设置尺寸（根据保护区面积）
def scale_size(area):
    return np.clip(np.sqrt(area/100) *0.05, 0.05, 12)


# 🔧 合并所有数据，使用连续颜色映射（包括0值）
all_data = df.copy()
sizes_all = scale_size(all_data['GIS_AREA'].values)

# 🔧 使用线性标准化（从0开始）
loss_values_all = all_data['Total_Loss_2001_2024'].values
# vmin = 0  # 从0开始
# vmax = loss_values_all.max()
## 将0值设为一个很小的正数以便对数处理
# loss_values_adjusted = np.where(loss_values_all == 0, 0.0001, loss_values_all)
# vmin = 0.0001
# vmax = loss_values_all.max()

non_zero_loss = loss_values_all[loss_values_all > 0]

if len(non_zero_loss) > 0:
    vmin_percentile = np.percentile(non_zero_loss, 2)
    vmax_percentile = np.percentile(non_zero_loss, 98)
    
    print(f"\n色度条范围（10-90%分位点）:")
    print(f"  10%分位点 (vmin): {vmin_percentile:.4f} ha")
    print(f"  90%分位点 (vmax): {vmax_percentile:.4f} ha")
    
    # 为了包含0值，将0值映射到一个很小的正数
    loss_values_adjusted = np.where(loss_values_all == 0, vmin_percentile * 0.01, loss_values_all)
    
    # 将超出范围的值裁剪到范围内
    loss_values_clipped = np.clip(loss_values_adjusted, vmin_percentile * 0.01, vmax_percentile)
    
    vmin = vmin_percentile * 0.01  # 从接近0的值开始
    vmax = vmax_percentile
else:
    # 如果没有非零值，使用默认范围
    vmin = 0.0001
    vmax = 1.0
    loss_values_clipped = loss_values_all


# 绘制所有保护区（包括无损失的）
scatter = ax_loss.scatter(
    all_data['Longitude'],
    all_data['Latitude'],
    s=sizes_all,
    c=loss_values_clipped,
    cmap=cmap,
    vmin=vmin,
    vmax=vmax,
    alpha=0.5,
    edgecolors='none',
    transform=ccrs.PlateCarree(),
    zorder=2
)

# 添加colorbar
cax = inset_axes(ax_loss,
                 width="20%",
                 height="4%",
                 loc='lower left',
                 bbox_to_anchor=(0.034, 0.10, 1, 1),
                 bbox_transform=ax_loss.transAxes,
                 borderpad=0)



cbar = plt.colorbar(scatter, cax=cax, orientation='horizontal')

cbar.ax.set_title('Forest loss (ha)', 
                  fontsize=6, 
                  family='Arial',
                  loc='left',
                  pad=6)

cbar.ax.tick_params(
    labelsize=6,
    size=2,
    width=0.4,
    pad=1,
    direction='out',
    length=5,
    colors='black'
)

cbar.outline.set_linewidth(0.4)

example_areas = [1000, 1000000]  # 10 ha 和 100,000 ha
example_sizes = scale_size(np.array(example_areas))

pa_legend_elements = [
    Line2D([0], [0], marker='o', color='w',
           markerfacecolor='none', markeredgecolor='#999999',
           markeredgewidth=0.5, markersize=example_sizes[0], linestyle='',
           label=r'$10^{3}$'),
    Line2D([0], [0], marker='o', color='w',
           markerfacecolor='none', markeredgecolor='#999999',
           markeredgewidth=0.5, markersize=example_sizes[1], linestyle='',
           label=r'$10^{6}$'),
]

legend_pa = ax_loss.legend(handles=pa_legend_elements,
                           loc='lower left',
                           bbox_to_anchor=(0.020, 0.25),
                           fontsize=6,
                           frameon=False,
                           ncol=2,
                           title='PA size (ha)',
                           title_fontsize=6,
                           columnspacing=0.8,
                           handletextpad=0.1,
                           labelspacing=1.0,
                           alignment='left',
                           prop={'family': 'Arial', 'size': 6})

# # PA area图例
# pa_legend_elements = [
#     Line2D([0], [0], marker='o', color='w',
#            markerfacecolor='none', markeredgecolor='#999999',
#            markeredgewidth=0.5, markersize=1.2, linestyle='',
#            label=r'$10^{-1}$ ha'),
#     Line2D([0], [0], marker='o', color='w',
#            markerfacecolor='none', markeredgecolor='#999999',
#            markeredgewidth=0.5, markersize=2.5, linestyle='',
#            label=r'$10^{5}$ ha'),
# ]

# legend_pa = ax_loss.legend(handles=pa_legend_elements,
#                            loc='lower left',
#                            bbox_to_anchor=(0.018, 0.01),
#                            fontsize=6,
#                            frameon=False,
#                            ncol=2,
#                            title='PA area',
#                            title_fontsize=6,
#                            columnspacing=0.8,
#                            handletextpad=0.1,
#                            labelspacing=1.0,
#                            alignment='left',
#                            prop={'family': 'Arial', 'size': 6})



plt.tight_layout()
plt.savefig(r'H:\003 GPA数据\03 按lossyear统计\02GPA_LoseYear\06 绘图（分布图）\04_pk_global_pa_total_loss_with_no_loss(18).png', 
            dpi=600, bbox_inches='tight')
print("\n✓ 森林损失总量空间分布图已保存（连续配色方案）")
plt.show()


# ==================== 3. 数据分类与综合统计 ====================
print("\n" + "=" * 80)
print("步骤 3: 生成综合统计表格")
print("=" * 80)

df_analysis = df.copy()

# 🔧 1. IUCN等级分类：I-II、III-IV、V-VI
print("\n1. 处理IUCN等级分类...")
def categorize_iucn(iucn_cat):
    if pd.isna(iucn_cat):
        return 'Unknown'
    iucn_str = str(iucn_cat).strip()
    if iucn_str in ['Ia', 'Ib']:
        return 'I'
    elif iucn_str in ['II']:
        return 'II'
    elif iucn_str in ['III']:
        return 'III'
    elif iucn_str in ['IV']:
        return 'IV'
    elif iucn_str in ['V']:
        return 'V'
    elif iucn_str in ['VI']:
        return 'VI'
    else:
        return 'Other'

if 'IUCN_CAT' in df_analysis.columns:
    df_analysis['IUCN_Group'] = df_analysis['IUCN_CAT'].apply(categorize_iucn)
else:
    print("⚠️ 数据中没有IUCN_CAT列")
    df_analysis['IUCN_Group'] = 'Unknown'

print(f"   IUCN等级分布:")
print(df_analysis['IUCN_Group'].value_counts().sort_index())

# 🔧 2. 建立年份分类：1990以前、1990-2010、2010以后
print("\n2. 处理建立年份分类...")
def categorize_year(year):
    if pd.isna(year):
        return 'Unknown'
    year = int(year)
    if year <= 1990:
        return 'Before 1990'
    elif 1990 < year <= 2000:
        return '1990-2000'
    elif 2000 < year <= 2010:
        return '2000-2010'
    else:
        return 'After 2010'

if 'STATUS_YR' in df_analysis.columns:
    df_analysis['STATUS_YR'] = pd.to_numeric(df_analysis['STATUS_YR'], errors='coerce')
    df_analysis['Year_Group'] = df_analysis['STATUS_YR'].apply(categorize_year)
else:
    print("⚠️ 数据中没有STATUS_YR列")
    df_analysis['Year_Group'] = 'Unknown'

print(f"   建立年份分布:")
print(df_analysis['Year_Group'].value_counts().sort_index())

# 🔧 3. PA面积分类：<5、5-100、>100
print("\n3. 处理PA面积分类...")
def categorize_pa_area(area):
    if pd.isna(area):
        return 'Unknown'
    elif area <= 1000:
        return '<1k ha'
    elif 1000 < area <= 10000:
        return '1k-10k ha'
    elif 10000 < area <= 100000:
        return '10k-100k ha'
    elif 100000 < area <= 1000000:
        return '100k-1M ha'
    else:
        return '>1M ha'

df_analysis['PA_Area_Group'] = df_analysis['GIS_AREA'].apply(categorize_pa_area)

print(f"   PA面积分布:")
print(df_analysis['PA_Area_Group'].value_counts())

# 🔧 4. 大洲分类
print("\n4. 处理大洲分类...")
valid_continents = ['Africa', 'Asia', 'Europe', 'North America', 'South America', 'Oceania']

if 'Continent' in df_analysis.columns:
    df_analysis['Continent_Group'] = df_analysis['Continent'].fillna('Unknown')
    # 标准化大洲名称
    df_analysis.loc[~df_analysis['Continent_Group'].isin(valid_continents), 'Continent_Group'] = 'Other'
else:
    print("⚠️ 数据中没有Continent列")
    df_analysis['Continent_Group'] = 'Unknown'

print(f"   大洲分布:")
print(df_analysis['Continent_Group'].value_counts())

# 🔧 5. 气候带分类：Tropical、Subtropical、Temperate、Boreal、Polar
print("\n5. 处理气候带分类...")
valid_climate_zones = ['Tropical', 'Subtropical', 'Temperate', 'Boreal', 'Polar']

if 'Climate_Zone_Name' in df_analysis.columns:
    df_analysis['Climate_Zone_Group'] = df_analysis['Climate_Zone_Name'].fillna('Unknown')
    # 标准化气候带名称
    df_analysis.loc[~df_analysis['Climate_Zone_Group'].isin(valid_climate_zones), 'Climate_Zone_Group'] = 'Other'
else:
    print("⚠️ 数据中没有Climate_Zone_Name列")
    df_analysis['Climate_Zone_Group'] = 'Unknown'

print(f"   气候带分布:")
print(df_analysis['Climate_Zone_Group'].value_counts())


# ==================== 4. 生成综合统计表格 ====================
print("\n" + "=" * 80)
print("步骤 4: 生成综合统计表格")
print("=" * 80)

# 定义分类配置
categories = {
    'IUCN_Group': {
        'name': 'IUCN Category',
        'order': ['I', 'II', 'III', 'IV', 'V', 'VI', 'Other', 'Unknown']
    },
    'Year_Group': {
        'name': 'Establishment Year',
        'order': ['Before 1990', '1990-2000', '2000-2010', 'After 2010', 'Unknown']
    },
    'PA_Area_Group': {
        'name': 'PA Area',
        'order': ['<1k ha', '1k-10k ha', '10k-100k ha', '100k-1M ha', '>1M ha', 'Unknown']
    },
    'Continent_Group': {
        'name': 'Continent',
        'order': ['Africa', 'Asia', 'Europe', 'North America', 'South America', 'Oceania', 'Other', 'Unknown']
    },
    'Climate_Zone_Group': {
        'name': 'Climate Zone',
        'order': ['Tropical', 'Subtropical', 'Temperate', 'Boreal', 'Polar', 'Other', 'Unknown']
    }
}

# 创建综合统计表
all_stats = []

for group_col, config in categories.items():
    print(f"\n处理 {config['name']}...")
    
    # 基础统计
    group_stats = df_analysis.groupby(group_col).agg({
        'SITE_ID': 'count',
        'GIS_AREA': 'sum',
        'Total_Loss_2001_2024': 'sum'
    }).reset_index()
    
    group_stats.columns = ['Category', 'PA_Count', 'Total_PA_Area_km2', 'Total_Forest_Loss_km2']
    
    # 添加分类类型列
    group_stats.insert(0, 'Category_Type', config['name'])
    
    # 添加每年的损失数据
    for year in loss_years:
        col = f'LY_{year}_Area_km2'
        group_stats[f'Loss_{year}'] = df_analysis.groupby(group_col)[col].sum().values
    
    # 按指定顺序排序
    group_stats['sort_key'] = group_stats['Category'].apply(
        lambda x: config['order'].index(x) if x in config['order'] else 999
    )
    group_stats = group_stats.sort_values('sort_key').drop('sort_key', axis=1)
    
    all_stats.append(group_stats)

# 合并所有统计
comprehensive_stats = pd.concat(all_stats, ignore_index=True)

# 添加百分比列
print("\n计算百分比...")
for category_type in comprehensive_stats['Category_Type'].unique():
    mask = comprehensive_stats['Category_Type'] == category_type
    total_pa = comprehensive_stats.loc[mask, 'PA_Count'].sum()
    total_area = comprehensive_stats.loc[mask, 'Total_PA_Area_km2'].sum()
    total_loss = comprehensive_stats.loc[mask, 'Total_Forest_Loss_km2'].sum()
    
    comprehensive_stats.loc[mask, 'PA_Count_Percentage'] = (
        comprehensive_stats.loc[mask, 'PA_Count'] / total_pa * 100
    )
    comprehensive_stats.loc[mask, 'Area_Percentage'] = (
        comprehensive_stats.loc[mask, 'Total_PA_Area_km2'] / total_area * 100
    )
    comprehensive_stats.loc[mask, 'Loss_Percentage'] = (
        comprehensive_stats.loc[mask, 'Total_Forest_Loss_km2'] / total_loss * 100
    )

# 重新排列列顺序
cols_order = ['Category_Type', 'Category', 
              'PA_Count', 'PA_Count_Percentage',
              'Total_PA_Area_km2', 'Area_Percentage',
              'Total_Forest_Loss_km2', 'Loss_Percentage']
cols_order += [f'Loss_{year}' for year in loss_years]
comprehensive_stats = comprehensive_stats[cols_order]

# 保存到Excel
output_file = r'H:\003 GPA数据\03 按lossyear统计\02GPA_LoseYear\06 绘图（分布图）\04_Comprehensive_Statistics.xlsx'

print(f"\n保存综合统计表格...")
with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    # 主表
    comprehensive_stats.to_excel(writer, sheet_name='Comprehensive Statistics', index=False, float_format='%.4f')
    
    # 为每个分类创建单独的工作表
    for category_type in comprehensive_stats['Category_Type'].unique():
        sheet_name = category_type.replace(' ', '_')[:31]  # Excel工作表名称限制
        category_data = comprehensive_stats[comprehensive_stats['Category_Type'] == category_type].copy()
        category_data = category_data.drop(columns=['Category_Type'])
        category_data.to_excel(writer, sheet_name=sheet_name, index=False, float_format='%.4f')
    
    # 总体摘要
    summary_data = pd.DataFrame({
        'Metric': [
            'Total Protected Areas',
            'Total PA Area (km²)',
            'Total Forest Loss 2001-2024 (km²)',
            'Average Loss per PA (km²)',
            'PAs with Forest Loss',
            'PAs without Forest Loss',
            'Loss Percentage of Total Area (%)'
        ],
        'Value': [
            len(df_analysis),
            df_analysis['GIS_AREA'].sum(),
            df_analysis['Total_Loss_2001_2024'].sum(),
            df_analysis['Total_Loss_2001_2024'].mean(),
            len(df_analysis[df_analysis['Total_Loss_2001_2024'] > 0]),
            len(df_analysis[df_analysis['Total_Loss_2001_2024'] == 0]),
            df_analysis['Total_Loss_2001_2024'].sum() / df_analysis['GIS_AREA'].sum() * 100
        ]
    })
    summary_data.to_excel(writer, sheet_name='Overall Summary', index=False)

print(f"✓ 综合统计表格已保存: {output_file}")


# ==================== 5. 打印统计预览 ====================
print("\n" + "="*80)
print("统计预览")
print("="*80)

for category_type in comprehensive_stats['Category_Type'].unique():
    print(f"\n【{category_type}】")
    category_data = comprehensive_stats[comprehensive_stats['Category_Type'] == category_type]
    display_cols = ['Category', 'PA_Count', 'PA_Count_Percentage', 
                   'Total_PA_Area_km2', 'Total_Forest_Loss_km2', 'Loss_Percentage']
    print(category_data[display_cols].to_string(index=False))

print("\n" + "="*80)
print("所有分析完成！")
print("="*80)
print(f"\n生成的文件:")
print(f"  1. 空间分布图: 03_pk_global_pa_total_loss_with_no_loss(2).png")
print(f"  2. 综合统计表: 03_Comprehensive_Statistics.xlsx")
print(f"     - 包含所有分类的统计数据")
print(f"     - 包含每个分类的单独工作表")
print(f"     - 包含总体摘要工作表")

plt.close('all')



# ==================== 3. 纬度梯度分析与绘图 ====================
print("\n" + "=" * 80)
print("步骤 3: 统计并绘制随纬度变化的森林总损失面积")
print("=" * 80)

# 1. 设置纬度区间
lat_step = 1.5  # 纬度步长
lat_bins = np.arange(-60, 90 + lat_step, lat_step)  # 生成纬度区间

# 2. 对纬度进行分箱
df['Lat_Bin'] = pd.cut(df['Latitude'], bins=lat_bins)

# 3. 分组计算平均值和标准差
lat_stats = df.groupby('Lat_Bin')['Total_Loss_2001_2024'].agg(['mean', 'std', 'count', 'sum']).reset_index()

# 4. 获取每个区间的中心纬度
lat_stats['Lat_Center'] = lat_stats['Lat_Bin'].apply(lambda x: x.mid).astype(float)

# 5. 过滤掉数据量过少的区间
min_count = 10
lat_stats_filtered = lat_stats[lat_stats['count'] >= min_count].copy()

print("\n纬度统计结果预览 (前5行):")
print(lat_stats_filtered[['Lat_Center', 'mean', 'std', 'sum', 'count']].head())

# 画布高度保持 3.09 以匹配地图文件的物理高度
fig_lat, ax_lat = plt.subplots(figsize=(0.8, 3.09))

# # 绘制均值曲线
# ax_lat.plot(lat_stats_filtered['mean'], lat_stats_filtered['Lat_Center'], 
#             color="#8B0000", linewidth=2.0, label='Mean') # 线宽稍微调细一点适配小图

# 绘制标准差范围
ax_lat.fill_betweenx(lat_stats_filtered['Lat_Center'], 
                     lat_stats_filtered['mean'] - lat_stats_filtered['std'], 
                     lat_stats_filtered['mean'] + lat_stats_filtered['std'], 
                     color="#D9DEE4", alpha=0.8, edgecolor='none')

# 绘制均值曲线
ax_lat.plot(lat_stats_filtered['sum'], lat_stats_filtered['Lat_Center'], 
            color="#8B0000", linewidth=1.0, label='Sum') # 线宽稍微调细一点适配小图

# ax_lat.plot(lat_stats_filtered['count'], lat_stats_filtered['Lat_Center'], 
#             color="#142B76", linewidth=1.0, label='count') # 线宽稍微调细一点适配小图

# # 绘制均值曲线
# ax_lat.plot(lat_stats_filtered['mean'], lat_stats_filtered['Lat_Center'], 
#             color="#8B0000", linewidth=2.0, label='Mean') # 线宽稍微调细一点适配小图


# 3. 设置 Y 轴 (纬度) - 关键修改
ax_lat.set_ylim(-60, 90)
ax_lat.set_yticks(np.arange(-60, 91, 30))

# 🔧 关键修改 1: 隐藏纵轴(Y)的刻度线和标签
ax_lat.tick_params(axis='y', which='both', left=False, labelleft=False)

# ax_lat.set_xlim(-1000, 30000000)

# 🔧 关键修改 2: 隐藏横轴(X)的标签，但保留刻度线
ax_lat.tick_params(axis='x', which='both', 
                   bottom=True,      # 显示刻度线
                   labelbottom=False,# 隐藏数字标签
                   length=2,         # 刻度线长度
                   color='#666666',
                   width=0.25)        # 刻度线宽度

# 移除轴标题
ax_lat.set_ylabel('')
ax_lat.set_title('')
# ax_lat.set_xlabel('Loss area (ha)', fontsize=6)

for spine in ax_lat.spines.values():
    spine.set_linewidth(0.25)
    spine.set_color('#666666')

# 保存
output_lat_png = r'H:\003 GPA数据\03 按lossyear统计\02GPA_LoseYear\06 绘图（分布图）\03_Latitude_Gradient_Curve_Formatted03.png'
plt.savefig(output_lat_png, dpi=600, bbox_inches='tight') # bbox_inches='tight' 会再次自动裁剪白边
print(f"\n✓ 纬度梯度曲线图已保存 (标签已修复): {output_lat_png}")
plt.show()

print("\n" + "="*80)
print("所有分析完成！")
print("="*80)



