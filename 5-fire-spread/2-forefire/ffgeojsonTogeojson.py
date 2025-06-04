import json
import os
from pyproj import Transformer


def load_json(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
        return data

def reproject(xy, inEpsg, outEpsg='epsg:4326'):
    x1, y1 = xy
    transformer = Transformer.from_crs(inEpsg, outEpsg, always_xy=True)
    x2, y2 = transformer.transform(x1, y1)
    return [x2, y2]

def ffjson2geojson(filepath):
    ff_geojson = load_json(filepath)
    
    # Reproject coordinates
    inEpsg = ff_geojson['projection'].lower()
    for feature in ff_geojson["features"]:
        reproj = [reproject(xy, inEpsg) for xy in feature['geometry']['coordinates'][0]]
        reproj.append(reproj[0])  # Ensure the polygon is closed
        feature['geometry']['coordinates'][0] = reproj
    ff_geojson['projection'] = 'epsg:4326'

    # Save the converted file
    fileextension = filepath.split('.')[-1]
    savePath = filepath.replace(f'.{fileextension}', '.geojson')
    with open(savePath, 'w', encoding='utf-8') as f:
        json.dump(ff_geojson, f, ensure_ascii=False, indent=4)
    
    return savePath

def process_ffgeojson_files():
    current_dir = os.getcwd()
    ffgeojson_files = [f for f in os.listdir(current_dir) if f.endswith('.ffgeojson')]
    
    for ffgeojson_file in ffgeojson_files:
        filepath = os.path.join(current_dir, ffgeojson_file)
        geojson_path = ffjson2geojson(filepath)
        print(f"Converted GeoJSON file saved to: {geojson_path}")

if __name__ == "__main__":
    process_ffgeojson_files()
