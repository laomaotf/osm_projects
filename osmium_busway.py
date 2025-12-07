import os
import folium
import geopandas as gpd
import osmium
from collections import defaultdict
from dataclasses import dataclass,field
import json
import warnings
from typing import Any, Union, Optional
import numpy as np
import random



osm_file = './data/planet_119.867_29.995_9f24ee25.osm'
cache_osm_file = "./busway.json"
lon, lat = 120.1417, 30.2458
region_size = 0.05
flag_save_node = True
flag_save_way = True
flag_save_relation = True


type Member = dict(ref = 0, type ="", role ="")

@dataclass
class OSMEntity:
    id: np.int64 = 0
    lon: float = -1
    lat: float = -1
    visible: bool = True
    type: str = ""
    tags: dict[str, str] = field(default_factory=dict[str,str])
    refs: Optional[list[np.int64]] = None
    members: Optional[list[Member]] = None

##
#gdf = gpd.read_file(osm_file,
#                   bbox=(lon - region_size/2, lat - region_size/2, lon + region_size/2, lat+region_size/2), layer="points")
#folium.GeoJson(gdf).add_to(m)

class OSMEntityExtractor(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.entities_all: list[OSMEntity] = []

    def node(self, n):
        if not flag_save_node:
            return
        if ("highway" in n.tags and n.tags['highway'] == 'bus_stop'):
            tags: dict[str, str] = defaultdict(str)
            for tag in n.tags:
                tags[tag.k] = tag.v
            entity = OSMEntity(id=n.id, lon=n.location.lon, lat=n.location.lat, visible=n.visible, tags=tags, type="node")
            self.entities_all.append(entity)
        return

    def way(self, w):  #way: contours of building or vertex of bus line
        if not flag_save_way:
            return 
        tags: dict[str, str] = defaultdict(str)
        for tag in w.tags:
            tags[tag.k] = tag.v
        entity = OSMEntity(id=w.id, lon=-1, lat=-1, visible=w.visible, tags=tags, type="way", refs=[n.ref for n in w.nodes])
        self.entities_all.append(entity)
        return

    def relation(self, r): 
        if not flag_save_relation:
            return
        if 'route' in r.tags and r.tags['route'] == 'bus': #all bus lines. stations's ids are stored in r.tags.members
            tags: dict[str, str] = defaultdict(str)
            for tag in r.tags:
                tags[tag.k] = tag.v
            entity = OSMEntity(id=r.id, lon=-1, lat=-1, visible=r.visible, tags=tags, type="relation",
                            members=[dict(ref=m.ref, type=m.type, role=m.role) for m in r.members])
            self.entities_all.append(entity)
        return

def get_all_entities(osm_file):
    handler = OSMEntityExtractor()
    handler.apply_file(osm_file)
    return handler.entities_all


if not os.path.exists(cache_osm_file):
    osm_entities_all = get_all_entities(osm_file)

    class OSMEntityEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, OSMEntity):
                return dict(id=o.id, lon=o.lon, lat=o.lat, tags=o.tags, type=o.type, visible=o.visible, __type__="OSMEntity", refs=o.refs, members=o.members)
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
                return OSMEntity(id=obj['id'], lon=obj['lon'], lat=obj['lat'], type=obj['type'], tags=obj['tags'],
                                 visible=obj['visible'], refs=obj['refs'],
                                 members=[dict(ref=m['ref'],type=m['type'],role=m['role']) for m in obj['members']] if obj['members'] is not None else None)
            return obj
    with open(cache_osm_file, "r", encoding='utf-8') as f:
        osm_entities_all = json.load(f, cls=OSMEntityDecoder)


@dataclass 
class BusLine:
    name: str = ""
    stations: Optional[list[OSMEntity]] = None

def selection(entities_all: list[OSMEntity],bbox: tuple[float, float, float, float], max_busline_count: int=-1) -> list[BusLine]:
    lon_min, lat_min, lon_max, lat_max = bbox
    entities_id2ent: dict[np.int64, OSMEntity] = dict([(ent.id,ent) for ent in entities_all])
    buslines_all: list[BusLine] = []
    for line in filter(lambda ent: ent.type == 'relation', entities_all):
        if line.members is None:
            continue
        stations: list[OSMEntity] = []
        for member in line.members:
            if member['ref'] not in entities_id2ent:
                continue
            stations.append(entities_id2ent[member['ref']])
        stations = [ent for ent in stations 
                                 if ent.lon >= lon_min and ent.lon <= lon_max and ent.lat >= lat_min and ent.lat <= lat_max]
        if len(stations) > 1:
            buslines_all.append(BusLine(name=line.tags['name'],stations=stations))
    if max_busline_count > 0 and max_busline_count < len(buslines_all):
        random.shuffle(buslines_all)
        buslines_all = buslines_all[0:max_busline_count]
    return buslines_all


bus_lines_all = selection(osm_entities_all, bbox=(lon - region_size/2, lat - region_size/2, lon + region_size/2, lat+region_size/2), max_busline_count=10)

m = folium.Map(location=[lat, lon], zoom_start=15)
icon_name, icon_color = 'star', "green"
for line in bus_lines_all:
    if line.stations is None:
        continue
    polylines: list[tuple[float,float]] = []
    for station in line.stations:
        name = f"{line.name}-{station.tags['name']}"
        folium.Marker([station.lat, station.lon], popup=f'<i>{name}</i>', icon=folium.Icon(icon=icon_name, color=icon_color)).add_to(m)
        polylines.append((station.lat, station.lon))
    if polylines != []:
        pl = folium.PolyLine(locations = polylines,color='blue')
        pl.add_to(m)
folium.Marker([lat, lon], popup='<i>west lake</i>', icon=folium.Icon(icon='diamond', color="orange")).add_to(m)

m.save('map.html')

