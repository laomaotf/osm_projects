import os
import folium
import geopandas as gpd
import osmium
from collections import defaultdict
from dataclasses import dataclass
import json
import warnings
from typing import Any, Union, Optional

osm_file = './data/planet_119.867_29.995_9f24ee25.osm'
cache_osm_file = "./entities.json"
lon, lat = 120.1417, 30.2458
region_size = 0.05

@dataclass
class OSMEntity:
    lon: float
    lat: float
    visible: bool
    type: str
    tags: dict[str, str]


##
#gdf = gpd.read_file(osm_file,
#                   bbox=(lon - region_size/2, lat - region_size/2, lon + region_size/2, lat+region_size/2), layer="points")
#folium.GeoJson(gdf).add_to(m)


class OSMEntityExtractor(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.entities_all: list[OSMEntity] = []

    def node(self, n):
        tags: dict[str, str] = defaultdict(str)
        for tag in n.tags:
            tags[tag.k] = tag.v
        entity = OSMEntity(lon=n.location.lon, lat=n.location.lat, visible=n.visible, tags=tags, type="node")
        self.entities_all.append(entity)

    def way(self, w):
        tags: dict[str, str] = defaultdict(str)
        for tag in w.tags:
            tags[tag.k] = tag.v
        entity = OSMEntity(lon=-1, lat=-1, visible=w.visible, tags=tags, type="way")
        self.entities_all.append(entity)

    def relation(self, r):
        tags: dict[str, str] = defaultdict(str)
        for tag in r.tags:
            tags[tag.k] = tag.v
        entity = OSMEntity(lon=-1, lat=-1, visible=r.visible, tags=tags, type="relation")
        self.entities_all.append(entity)


def get_all_entities(osm_file):
    handler = OSMEntityExtractor()
    handler.apply_file(osm_file)
    return handler.entities_all


if not os.path.exists(cache_osm_file):
    osm_entities_all = get_all_entities(osm_file)

    class OSMEntityEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, OSMEntity):
                return dict(lon=o.lon, lat=o.lat, tags=o.tags, type=o.type, visible=o.visible, __type__="OSMEntity")
            return super().default(o)
    with open(cache_osm_file, 'w', encoding='utf-8') as f:
        json.dump(osm_entities_all, f, indent=4, cls=OSMEntityEncoder, ensure_ascii=False)
else:
    warnings.warn(f"load entities from json file {cache_osm_file}")

    class OSMEntityDecoder(json.JSONDecoder):
        def __init__(self, *args, **kwargs):
            super().__init__(object_hook=self.object_hook, *args, **kwargs)

        def object_hook(self, obj: dict[str, Any]) -> Any:
            if "__type__" in obj and obj["__type__"] == "OSMEntity":
                return OSMEntity(lon=obj['lon'], lat=obj['lat'], type=obj['type'], tags=obj['tags'], visible=obj['visible'])
            return obj
    with open(cache_osm_file, "r", encoding='utf-8') as f:
        osm_entities_all = json.load(f, cls=OSMEntityDecoder)


def selection(entities_all: list[OSMEntity], 
              bbox: Optional[tuple[float, float, float, float]] = None, 
              tags: Optional[set[str]] = None) -> list[OSMEntity]:
    filtered_entities_all = entities_all
    if bbox is not None:
        lon_min, lat_min, lon_max, lat_max = bbox
        filtered_entities_all = [ent for ent in filtered_entities_all 
                                 if ent.lon >= lon_min and ent.lon <= lon_max and ent.lat >= lat_min and ent.lat <= lat_max]
    if tags is not None:
        filtered_entities_all = [ent for ent in filtered_entities_all if tags.intersection(set(ent.tags.keys()))]
    return filtered_entities_all


osm_entities_all = selection(osm_entities_all,
                             bbox=(lon - region_size/2, lat - region_size/2, lon + region_size/2, lat+region_size/2),
                             tags={"public_transport", "building"})

m = folium.Map(location=[lat, lon], zoom_start=15)
for ent in osm_entities_all:
    name = "lost name"
    icon_name, icon_color = 'question', "gray"
    if 'name' in ent.tags:
        name = ent.tags['name']
        if "building" in ent.tags:
            icon_name, icon_color = "building", "blue"
        if "public_transport" in ent.tags:
            icon_name, icon_color = "flag", "green"
    folium.Marker([ent.lat, ent.lon], popup=f'<i>{name}</i>', icon=folium.Icon(icon=icon_name, color=icon_color)).add_to(m)
folium.Marker([lat, lon], popup='<i>west lake</i>', icon=folium.Icon(icon='diamond', color="orange")).add_to(m)

m.save('map.html')

