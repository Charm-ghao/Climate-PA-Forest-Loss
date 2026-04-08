import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import warnings
import os

# 忽略警告
warnings.filterwarnings('ignore')

# =================配置区域=================
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['font.size'] = 7
plt.rcParams['axes.titlesize'] = 8

class CorrelationAnalyzer:
    def __init__(self, filepath):
        print(f"正在读取数据: {filepath} ...")
        self.df = pd.read_excel(filepath)
        self.output_dir = os.path.dirname(filepath)

    def process_data(self):
        df = self.df.copy()
        
        # 1. 数据清洗
        df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
        df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
        df['GIS_AREA'] = pd.to_numeric(df['GIS_AREA'], errors='coerce').replace(0, np.nan)
        df = df.dropna(subset=['Longitude', 'Latitude', 'GIS_AREA'])
        
        # 2. 计算变量
        # Total Loss (2001-2024)
        loss_cols = [c for c in df.columns if c.startswith('LY_')]
        df[loss_cols] = df[loss_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
        df['Total_Loss'] = df[loss_cols].sum(axis=1)
        
        # Relative Ratio
        df['Relative_Ratio'] = df['Total_Loss'] / df['GIS_AREA']
        
        # 3. 过滤有效数据 (Log变换前处理)
        # 过滤掉 Total_Loss 为 0 的数据，以免干扰相关性计算（或者保留，视研究目的而定）
        # 这里建议保留，但在Log变换时使用 log1p
        self.data = df
        print(f"有效数据量: {len(self.data)}")
        
        return df

    def calc_global_correlation(self):
        """计算全球整体相关性"""
        df = self.data
        
        # 使用 Spearman 秩相关 (鲁棒，适合非正态分布)
        corr, p_value = stats.spearmanr(df['Total_Loss'], df['Relative_Ratio'])
        
        print("\n=== 全球统计相关性 ===")
        print(f"Spearman Correlation (r): {corr:.4f}")
        print(f"P-value: {p_value:.4e}")
        
        return corr, p_value

    def plot_scatter(self):
        """绘制散点图 (统计空间)"""
        df = self.data
        
        # Log变换用于绘图展示
        x = np.log1p(df['Total_Loss'])
        y = np.log1p(df['Relative_Ratio'])
        
        fig, ax = plt.subplots(figsize=(5, 4))
        
        # 绘制Hexbin密度图 (比单纯Scatter更清晰显示密集区)
        hb = ax.hexbin(x, y, gridsize=50, cmap='Spectral_r', mincnt=1, bins='log')
        cb = plt.colorbar(hb, ax=ax)
        cb.set_label('Count (log scale)')
        
        # 添加拟合线
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        ax.plot(x, slope*x + intercept, color='black', lw=1, linestyle='--')
        
        corr, _ = self.calc_global_correlation()
        
        ax.set_xlabel('Log(Total Loss Area + 1)')
        ax.set_ylabel('Log(Relative Ratio + 1)')
        ax.set_title(f'Global Correlation: Total Loss vs. Relative Ratio\nSpearman r = {corr:.2f}')
        
        out_path = os.path.join(self.output_dir, "02_Correlation_Scatter_Plot.png")
        plt.tight_layout()
        plt.savefig(out_path, dpi=600)
        print(f"散点图已保存: {out_path}")
        plt.show()

    def plot_spatial_grid_correlation(self, grid_size=10, min_samples=15):
        """
        绘制空间网格相关性地图 (地理空间)
        grid_size: 网格大小 (度)，默认 10x10 度
        min_samples: 每个网格内计算相关性所需的最小保护区数量
        """
        print(f"\n正在计算空间网格相关性 (Grid Size: {grid_size}°)...")
        
        # 1. 创建网格
        lon_bins = np.arange(-180, 181, grid_size)
        lat_bins = np.arange(-90, 91, grid_size)
        
        grid_lons = []
        grid_lats = []
        grid_corrs = []
        grid_counts = []
        
        # 2. 遍历网格计算局部相关性
        for i in range(len(lon_bins)-1):
            for j in range(len(lat_bins)-1):
                lon_min, lon_max = lon_bins[i], lon_bins[i+1]
                lat_min, lat_max = lat_bins[j], lat_bins[j+1]
                
                # 筛选网格内的点
                mask = (self.data['Longitude'] >= lon_min) & (self.data['Longitude'] < lon_max) & \
                       (self.data['Latitude'] >= lat_min) & (self.data['Latitude'] < lat_max)
                sub_df = self.data[mask]
                
                # 只有样本量足够才计算
                if len(sub_df) >= min_samples:
                    # 计算 Spearman 相关
                    # 如果数据全是一样的(方差为0)，spearmanr会返回nan
                    if sub_df['Total_Loss'].nunique() > 1 and sub_df['Relative_Ratio'].nunique() > 1:
                        r, p = stats.spearmanr(sub_df['Total_Loss'], sub_df['Relative_Ratio'])
                    else:
                        r = np.nan
                    
                    if not np.isnan(r):
                        grid_lons.append(lon_min) # 记录网格左下角
                        grid_lats.append(lat_min)
                        grid_corrs.append(r)
                        grid_counts.append(len(sub_df))
        
        # 3. 绘图
        fig = plt.figure(figsize=(8, 4.5))
        ax = plt.axes(projection=ccrs.PlateCarree())
        
        ax.add_feature(cfeature.LAND, facecolor='#f0f0f0')
        ax.add_feature(cfeature.COASTLINE, linewidth=0.3)
        ax.set_extent([-180, 180, -60, 90], crs=ccrs.PlateCarree())
        
        # 绘制网格
        # 使用 scatter 绘制方块，或者使用 pcolormesh (需要整理成网格矩阵)
        # 这里用 marker='s' (正方形) 模拟网格，简单直观
        # 调整 s (size) 以匹配 grid_size。经验值：对于 figsize(8,4)，s~=130 对应 10度
        
        sc = ax.scatter(np.array(grid_lons) + grid_size/2, # 中心点
                        np.array(grid_lats) + grid_size/2, 
                        c=grid_corrs, 
                        cmap='RdBu_r', # 红=正相关，蓝=负相关
                        vmin=-1, vmax=1,
                        s=110, # 此数值可能需要微调以填满缝隙，或者改用 pcolormesh
                        marker='s',
                        transform=ccrs.PlateCarree(),
                        edgecolor='none',
                        alpha=0.9)
        
        # 添加 Colorbar
        cbar = plt.colorbar(sc, ax=ax, orientation='horizontal', pad=0.05, fraction=0.03, aspect=30)
        cbar.set_label(f'Spearman Correlation (Total vs. Relative)\nGrid Size: {grid_size}° x {grid_size}° (Min Samples: {min_samples})')
        
        ax.set_title("Spatial Pattern of Correlation: Total Loss vs. Relative Ratio", fontsize=9, fontweight='bold')
        
        out_path = os.path.join(self.output_dir, "02_Spatial_Grid_Correlation_Map.png")
        plt.savefig(out_path, dpi=600, bbox_inches='tight')
        print(f"空间相关性地图已保存: {out_path}")
        plt.show()

# =================执行程序=================
if __name__ == "__main__":
    file_path = r"H:\003 GPA数据\06 驱动因素\002 数据合并\002 WRI合并（各大洲）\01 WRI_2001_2024_经纬度_无森林与气候.xlsx"
    
    try:
        analyzer = CorrelationAnalyzer(file_path)
        analyzer.process_data()
        
        # 1. 计算并打印全球数值
        analyzer.calc_global_correlation()
        
        # 2. 绘制散点图 (统计分布)
        analyzer.plot_scatter()
        
        # 3. 绘制空间网格图 (地理分布)
        # grid_size=10度 (全球概览), min_samples=15 (保证统计显著性)
        analyzer.plot_spatial_grid_correlation(grid_size=10, min_samples=15)
        
    except FileNotFoundError:
        print("错误: 找不到文件")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"发生错误: {e}")
        
        
