
// --------------------------- Inputs ----------------------------------
var GLO = ee.FeatureCollection("projects/ee-chuanwu/assets/Global_Natural_Earth");
var WDPA = ee.FeatureCollection("WCMC/WDPA/current/polygons");
var IUCN_KEEP = ['Ia','Ib','II','III','IV','V','VI'];


var wdpa_land = WDPA.filter(
  ee.Filter.or(
    ee.Filter.eq('MARINE', 0),
    ee.Filter.eq('MARINE', '0')
  )
);


print('最终 GPA 数:', wdpa_land.size());

var wdpa_iucn = wdpa_land
  .filter(ee.Filter.notNull(['IUCN_CAT']))
  .filter(ee.Filter.inList('IUCN_CAT', IUCN_KEEP));


var wdpa_year = wdpa_iucn
  .filter(ee.Filter.notNull(['STATUS_YR']))
  .filter(ee.Filter.gt('STATUS_YR', 0))
  .filter(ee.Filter.lte('STATUS_YR', 2025));

var GPA_0001 = wdpa_year
  .filter(ee.Filter.notNull(['GIS_AREA', 'REP_AREA']))
  .filter(ee.Filter.and(
    ee.Filter.gte('GIS_AREA', 0.0036),
    ee.Filter.gte('REP_AREA', 0.0036)
  ));

var Continents01 = ee.FeatureCollection('projects/ee-chuanwu/assets/World_Continents');

var GPA_0002 = GPA_0001.map(function(f) {
  var pt = f.geometry().centroid(10);
  var cont = Continents01.filterBounds(pt).first();
  var name = ee.String(ee.Algorithms.If(cont, cont.get('CONTINENT'), 'Unknown'));
  return f.set('Continent', name);
});

var GPA = GPA_0002.select([
  'WDPAID',
  'NAME',
  'MARINE',
  'DESIG_ENG',
  'DESIG_TYPE',
  'GOV_TYPE',
  'REP_AREA',
  'GIS_AREA',
  'IUCN_CAT',
  'STATUS_YR',
  'Continent'
]);

print('========== GPA 数据验证 ==========');
print('保护区总数:', GPA_0001.size());

// ======================== 数据加载与重采样 ========================

// Hansen GFC v1.12 (30m)
var gfc = ee.Image('UMD/hansen/global_forest_change_2024_v1_12');
var LY00   = gfc.select('lossyear').toByte();
var TC2000 = gfc.select('treecover2000').toByte(); 

// ESSD-GFD (30m)
var image1 = ee.Image('projects/ee-chuanwu/assets/ESSD_GFC001').toByte();
var image2 = ee.Image('projects/ee-chuanwu/assets/ESSD_GFC002').toByte();
var image3 = ee.Image('projects/ee-chuanwu/assets/ESSD_GFC003').toByte();
var image4 = ee.Image('projects/ee-chuanwu/assets/ESSD_GFC004').toByte();
var image5 = ee.Image('projects/ee-chuanwu/assets/ESSD_GFC03').toByte();
var GFD = ee.ImageCollection([image1, image2, image3, image4, image5])
  .mosaic()
  .rename('gfd');

// ✅ WRI (1km → 30m) - reproject重采样
var WRI = ee.Image("projects/landandcarbon/assets/wri_gdm_drivers_forest_loss_1km/v1_2_2001_2024")
  .select('classification')
  .toByte()
  .rename('wri')
  .reproject({
    crs: 'EPSG:4326',
    scale: 30,
  });

// ✅ SCI (20km → 30m) - reproject重采样
var SCI = ee.Image('projects/ee-chuanwu/assets/Science_2018_rep')
  .toByte()
  .rename('sci')
  .reproject({
    crs: 'EPSG:4326',
    scale: 30,
  });

print('✅ 所有数据已加载并重采样到30m分辨率');

// ======================== Map visualization ========================
var glo_Outline = GLO.style({ color: 'yellow', width: 2, fillColor: '00000000' });
var gpa_Outline = GPA.style({ color: 'red', width: 1, fillColor: '00000000' });


var treeCoverVisParam = {
  min: 0,
  max: 100,
  palette: ['black', 'green']
};

var treeLossVisParam = {
  min: 0,
  max: 24,
  palette: ['yellow', 'red']
};

Map.addLayer(glo_Outline, {}, 'Globe_Boundary');
Map.addLayer(gpa_Outline, {}, 'Protected_Area');
Map.addLayer(LY00, treeLossVisParam, '30m_LossYear');
Map.addLayer(TC2000, treeCoverVisParam, '30m_TreeCover');


// ======================== Masking ========================
var FOREST_TH = 0;
var forestMask = TC2000.gte(FOREST_TH).updateMask(TC2000.gt(FOREST_TH));

var LY_2001_2020 = LY00.updateMask(LY00.gte(1).and(LY00.lte(20))).updateMask(forestMask);
var LY_2001_2024 = LY00.updateMask(LY00.gte(1).and(LY00.lte(24))).updateMask(forestMask);
var LY_2001_2015 = LY00.updateMask(LY00.gte(1).and(LY00.lte(15))).updateMask(forestMask);

// var LY_2001_2020 = LY00.updateMask(LY00.gte(1).and(LY00.lte(20)));
// var LY_2001_2024 = LY00.updateMask(LY00.gte(1).and(LY00.lte(24)));
// var LY_2001_2015 = LY00.updateMask(LY00.gte(1).and(LY00.lte(15)));

var GFD_m = GFD.updateMask(GFD.gte(1).and(GFD.lte(22)));
var WRI_m = WRI.updateMask(WRI.gte(1).and(WRI.lte(7)));
var SCI_m = SCI.updateMask(SCI.gte(1).and(SCI.lte(5)));

var cm_GFD = LY_2001_2020.mask().and(GFD_m.mask());
var cm_WRI = LY_2001_2024.mask().and(WRI_m.mask());
var cm_SCI = LY_2001_2015.mask().and(SCI_m.mask());

var LY_GFD  = LY_2001_2020.updateMask(cm_GFD);
var GFD_use = GFD_m.updateMask(cm_GFD);

var LY_WRI  = LY_2001_2024.updateMask(cm_WRI);
var WRI_use = WRI_m.updateMask(cm_WRI);

var LY_SCI  = LY_2001_2015.updateMask(cm_SCI);
var SCI_use = SCI_m.updateMask(cm_SCI);

print('✅ Masking完成');

// ======================== 参数配置 ========================
var SCALE_MAIN = 30;
var MAX_PIXELS_PER_REGION = 1e11;

// ======================== 统计函数 ========================




//为每个保护区统计各数据集的面积

function computeDatasetStats(paCollection, scale) {
  return paCollection.map(function(feature) {
    var geometry = feature.geometry();
    var stats = feature;
    
    // ============ TC2000 树冠覆盖 ============
    var tc2000_stats = TC2000.reduceRegion({
      reducer: ee.Reducer.count(),
      geometry: geometry,
      scale: scale,
      maxPixels: MAX_PIXELS_PER_REGION
    });
    var tc2000_count = ee.Number(tc2000_stats.get('treecover2000'));
    tc2000_count = ee.Algorithms.If(tc2000_count, tc2000_count, 0);
    var tc2000_area = ee.Number(tc2000_count).multiply(scale).multiply(scale).divide(1e6);
    
    stats = stats.set('TC2000_Area_km2', tc2000_area);
    
    // ============ forestMask 森林掩膜 ============
    var forestmask_stats = forestMask.reduceRegion({
      reducer: ee.Reducer.count(),
      geometry: geometry,
      scale: scale,
      maxPixels: MAX_PIXELS_PER_REGION
    });
    var forestmask_count = ee.Number(forestmask_stats.get('treecover2000'));
    forestmask_count = ee.Algorithms.If(forestmask_count, forestmask_count, 0);
    var forestmask_area = ee.Number(forestmask_count).multiply(scale).multiply(scale).divide(1e6);
    
    stats = stats.set('forestMask_Area_km2', forestmask_area);
    
    // ============ LY_2001_2020 Hansen森林损失 (2001-2020) ============
    var ly_2001_2020_stats = LY_2001_2020.reduceRegion({
      reducer: ee.Reducer.count(),
      geometry: geometry,
      scale: scale,
      maxPixels: MAX_PIXELS_PER_REGION
    });
    var ly_2001_2020_count = ee.Number(ly_2001_2020_stats.get('lossyear'));
    ly_2001_2020_count = ee.Algorithms.If(ly_2001_2020_count, ly_2001_2020_count, 0);
    var ly_2001_2020_area = ee.Number(ly_2001_2020_count).multiply(scale).multiply(scale).divide(1e6);
    
    stats = stats.set('LY_2001_2020_Area_km2', ly_2001_2020_area);
    
    // ============ GFD_use 驱动因素 ============
    var gfd_use_stats = GFD_use.reduceRegion({
      reducer: ee.Reducer.count(),
      geometry: geometry,
      scale: scale,
      maxPixels: MAX_PIXELS_PER_REGION
    });
    var gfd_use_count = ee.Number(gfd_use_stats.get('gfd'));
    gfd_use_count = ee.Algorithms.If(gfd_use_count, gfd_use_count, 0);
    var gfd_use_area = ee.Number(gfd_use_count).multiply(scale).multiply(scale).divide(1e6);
    
    stats = stats.set('GFD_use_Area_km2', gfd_use_area);
    
    // ============ LY_2001_2024 Hansen森林损失 (2001-2024) ============
    var ly_2001_2024_stats = LY_2001_2024.reduceRegion({
      reducer: ee.Reducer.count(),
      geometry: geometry,
      scale: scale,
      maxPixels: MAX_PIXELS_PER_REGION
    });
    var ly_2001_2024_count = ee.Number(ly_2001_2024_stats.get('lossyear'));
    ly_2001_2024_count = ee.Algorithms.If(ly_2001_2024_count, ly_2001_2024_count, 0);
    var ly_2001_2024_area = ee.Number(ly_2001_2024_count).multiply(scale).multiply(scale).divide(1e6);
    
    stats = stats.set('LY_2001_2024_Area_km2', ly_2001_2024_area);
    
    // ============ WRI_use 驱动因素 ============
    var wri_use_stats = WRI_use.reduceRegion({
      reducer: ee.Reducer.count(),
      geometry: geometry,
      scale: scale,
      maxPixels: MAX_PIXELS_PER_REGION
    });
    var wri_use_count = ee.Number(wri_use_stats.get('wri'));
    wri_use_count = ee.Algorithms.If(wri_use_count, wri_use_count, 0);
    var wri_use_area = ee.Number(wri_use_count).multiply(scale).multiply(scale).divide(1e6);
    
    stats = stats.set('WRI_use_Area_km2', wri_use_area);
    
    // ============ LY_2001_2015 Hansen森林损失 (2001-2015) ============
    var ly_2001_2015_stats = LY_2001_2015.reduceRegion({
      reducer: ee.Reducer.count(),
      geometry: geometry,
      scale: scale,
      maxPixels: MAX_PIXELS_PER_REGION
    });
    var ly_2001_2015_count = ee.Number(ly_2001_2015_stats.get('lossyear'));
    ly_2001_2015_count = ee.Algorithms.If(ly_2001_2015_count, ly_2001_2015_count, 0);
    var ly_2001_2015_area = ee.Number(ly_2001_2015_count).multiply(scale).multiply(scale).divide(1e6);
    
    stats = stats.set('LY_2001_2015_Area_km2', ly_2001_2015_area);
    
    // ============ SCI_use 驱动因素 ============
    var sci_use_stats = SCI_use.reduceRegion({
      reducer: ee.Reducer.count(),
      geometry: geometry,
      scale: scale,
      maxPixels: MAX_PIXELS_PER_REGION
    });
    var sci_use_count = ee.Number(sci_use_stats.get('sci'));
    sci_use_count = ee.Algorithms.If(sci_use_count, sci_use_count, 0);
    var sci_use_area = ee.Number(sci_use_count).multiply(scale).multiply(scale).divide(1e6);
    
    stats = stats.set('SCI_use_Area_km2', sci_use_area);
    
    return stats;
  });
}
