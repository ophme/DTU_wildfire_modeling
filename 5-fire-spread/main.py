from datetime import datetime, timedelta
import geojson
import geopandas as gpd
import numpy as np
import os
from pyproj import Transformer, CRS
import rasterio as rio
from rasterio.mask import mask
from shapely.geometry import Polygon
from shapely.geometry import shape
import shutil
import subprocess
import time

from ff_file_generator import create_ff_file
from ffgeojsonTogeojson import process_ffgeojson_files

# Import the relevant functions from extend.py
from extend import get_utm_crs, process_raster_files
# .........................
start_time = time.time()# .
# .........................


# Parameters -------------------------------------------------------
num_steps = 8
time_step = timedelta(hours=3)  # Time step between each iteration
DEM_path = '/home/jsoma/europeData/EU-DEM.tif'
CLC_path = '/home/jsoma/europeData/EU-CLC_v2018.tif'

# 1) Select Ignition point -------------------------------
lat = float(input("Enter latitude: "))  
lon = float(input("Enter longitude: "))
size_km1 = 90  # Size of the square in kilometers
size_km2 = 50

# Get the UTM CRS
dstCrs_UCTM = get_utm_crs(lon, lat)

# Use current directory as the output directory
output_dir = os.getcwd()

# Call the process_raster_files function
elevation_path, landcover_path = process_raster_files(lon, lat, size_km1, size_km2, DEM_path, CLC_path, output_dir, dstCrs_UCTM)

# prompt for the date
year = input("Enter the year (YYYY): ")
month = input("Enter the month (MM): ") 
day = input("Enter the day (DD): ")
initial_date = f"{year}-{month}-{day}_12:00:00Z"

# 2) Initialize the t0 folder -------------------------------
run_dir = os.getcwd()


for i in range(num_steps):
    os.chdir(run_dir)
    folderName = f't{i}'

    if not os.path.exists(folderName):
        os.mkdir(folderName)
        shutil.copy('elevation.tif', folderName)  # Copy elevation file for all folders

        if i == 0:
            shutil.copy('land_cover.tif', folderName)  # Copy land_cover.tif only for t0
        else: 
            # Modify land cover based on previous step's GeoJSON output
            print(f"Attempting to read file: {geojson_file}")
            land_cover = os.path.join(run_dir, 'land_cover.tif')
            out_forefire_geojson = gpd.read_file(geojson_file)

            with rio.open(land_cover) as src:
                land_cover_array = src.read(1)
                land_cover_array_copy = land_cover_array.copy()
                land_cover_crs = src.crs

                if out_forefire_geojson.crs != land_cover_crs:
                    out_forefire_geojson = out_forefire_geojson.to_crs(land_cover_crs)

                geometries = [geom for geom in out_forefire_geojson.geometry]
                out_image, out_transform = mask(src, geometries, crop=False, nodata=-1, filled=True)

                land_cover_array_copy[out_image[0] != -1] = 324  # Set burned areas to specific value
                land_cover_array_copy = land_cover_array_copy.astype(np.int16)

                out_meta = src.meta.copy()

                # Save modified land cover for the next iteration
                output_path = os.path.join(folderName, 'land_cover.tif')
                with rio.open(output_path, 'w', **out_meta) as dest:
                    dest.write(land_cover_array_copy, 1)

       
    
    os.chdir(folderName)
    
    # 3) WindNinja Simulation  --------------------
    # Gen cfg file
    subprocess.run(['python3', '/home/jsoma/scripts/scripts/allTogether/genWindNinjaFile.py'])
    
    # run WindNinja
    subprocess.run(['WindNinja_cli', 'wind_domain_avg.cfg'])

    # 4) Create landscape.nc file once WindNinja is done --------
    subprocess.run(['python3', '/home/jsoma/scripts/scripts/allTogether/createLandscape.py'])

    # 5) Create a tX.ff file -------------------------------------
    create_ff_file(i, folderName, run_dir, initial_date, time_step)

    # 6) Run ForeFire -------------------------------------------
    subprocess.run(['forefire', '-i', f't{i}.ff'], check=True)

    # 7) Proccess the output of ForeFire -----------------------
    process_ffgeojson_files()
    geojson_file = os.path.join(run_dir, f't{i}', f't{i}.geojson')

    # 8) Prepare for the next iteration ---------------------------
    os.chdir(run_dir)
    if i == num_steps - 1:
        break
    
    

# Record the end time
end_time = time.time()

# Calculate and print the elapsed time
elapsed_time = end_time - start_time
print(f"Total elapsed time: {elapsed_time / 60:.2f} minutes")