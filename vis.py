import folium
import geopandas as gpd

longit, lati = 120.1417, 30.2458  
region_size = 0.05
# 创建底图
m = folium.Map(location=[lati, longit], zoom_start=10)

# 添加OSM数据
gdf = gpd.read_file('./data/planet_119.867_29.995_9f24ee25.osm',
                    bbox=(longit - region_size/2, lati - region_size/2, longit + region_size/2, lati+region_size/2), layer="points")
folium.GeoJson(gdf).add_to(m)
m.save('map.html')

