import os
import geopandas as gpd
import json

# Directory path
simulation_dir = '/home/jsoma/runs/mediterranean'
save_dir = '/home/jsoma/results/mediterranean'

# List to store GeoDataFrames
gdf_list = []

# Walk through the root directory to find the GeoJSON files
for root, dirs, files in os.walk(simulation_dir):
    for file in files:
        if file.startswith('final_'):
            # Extract the date from the folder name (YYYY-MM-DD_lon_lat)
            folder_name = os.path.basename(os.path.dirname(root))
            date_str = folder_name.split('_')[0]  # YYYY-MM-DD
            
            # Full path to the GeoJSON file
            geojson_path = os.path.join(root, file)
            
            # Read the GeoJSON file into a GeoDataFrame
            gdf = gpd.read_file(geojson_path)
            
            gdf['date'] = date_str
            
            # Append the GeoDataFrame to the list
            gdf_list.append(gdf)
            
# Concatenate all GeoDataFrames into a single GeoDataFrame
combined_gdf = gpd.pd.concat(gdf_list, ignore_index=True)

#save thw GeoDataFrame
save_name = save_dir + '/mediterraneaFires_2010_2019.shp'
combined_gdf.to_file(save_name)
