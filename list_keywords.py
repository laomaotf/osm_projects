import sys
import osmium
from collections import defaultdict
import json
class OSMKeywordExtractor(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.keywords = defaultdict(set)

    def node(self, n):
        for tag in n.tags:
            self.keywords[tag.k].add(tag.v)

    def way(self, w):
        for tag in w.tags:
            self.keywords[tag.k].add(tag.v)

    def relation(self, r):
        for tag in r.tags:
            self.keywords[tag.k].add(tag.v)


def extract_keywords(osm_file):
    handler = OSMKeywordExtractor()
    handler.apply_file(osm_file)
    return handler.keywords

class SetEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, set):
            return list(o)
        return super().default(o)



if __name__ == "__main__":
    osm_file = sys.argv[1]
    keywords = extract_keywords(osm_file)
    with open("./keywords.json", 'w', encoding='utf-8') as f:
        json.dump(keywords, f, indent=4, cls=SetEncoder, ensure_ascii=False)
    print("提取的关键词：", keywords)