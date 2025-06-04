from datetime import datetime, timedelta
import geojson
import geopandas as gpd
import numpy as np
import os
from pathlib import Path
import pandas as pd
from pyproj import Transformer, CRS
import rasterio as rio
from rasterio.mask import mask
import scipy.stats as stats
from shapely.geometry import Polygon
from shapely.geometry import shape
import shutil
import subprocess
import time

# IMPORT FUNCTIONS --------------------------------------------------------
from ff_file_generator_automatic import create_ff_file
from ffgeojsonTogeojson import process_ffgeojson_files

# Import the relevant functions from extend.py
from extend import get_utm_crs, process_raster_files

# Import the creation of the cfg file for windNinja
from genWindNinjaFile_automatic import create_config_file
# -------------------------------------------------------------------------

# .........................
start_time = time.time()# .
# .........................

# Load the historical size distribution -----------------------------
region = 'North'
print(f' > PROCESSING REGION: {region}')
parameters_distirbution = pd.read_csv('/home/jsoma/wildfire-repo/Fire-spread/historical-fires/lognormal_params_EFFIS_fires_{region}.csv')
sigma, loc, scale = parameters_distirbution.iloc[0] # extract the values
historical_distri_ha = stats.lognorm(s=sigma, loc=loc, scale=scale) # Fit the log-nromal distribution

 
# Directories -------------------------------------------------------
DEM_path = '/home/jsoma/europeData/EU-DEM.tif'
CLC_path = '/home/jsoma/europeData/EU-CLC_v2018.tif'
 
# Directory where all the different folders that we want to run are located
parent_dir = Path.cwd()

print(f' The parent directory is {parent_dir}...')

# Iterate through each subdirectory in the parent directory
for subdir in sorted(parent_dir.iterdir()):

    print(f"Processing folder: {subdir}")
    run_dir = str(subdir)

    # Change to the folder
    os.chdir(subdir)
    # Find the file that ends with '_data.csv'
    wind_data_file = next((file for file in os.listdir('.') if file.endswith('_data.csv')), None)
    wind_data = pd.read_csv(wind_data_file)
    num_steps = np.shape(wind_data)[0]

    # Parameters -------------------------------------------------------
    # Get the common data
    common_data = wind_data.iloc[[0]]
    lat = common_data['lat'].iloc[0]
    lon = common_data['lon'].iloc[0]
    size_km1 = 90  # Size of the square in kilometers
    size_km2 = 30

    # Get the UTM CRS
    dstCrs_UCTM = get_utm_crs(lon, lat)
    output_dir = os.getcwd()
    elevation_path, landcover_path = process_raster_files(lon, lat, size_km1, size_km2, DEM_path, CLC_path, output_dir, dstCrs_UCTM)
    
    # set randomly the maximun area of the fire
    area_max = historical_distri_ha.rvs()
    print(f'The maximum extension of this fire is: {area_max} ha')
    
    # loop over the rows of wind_data to run the simulation
    # for i in range(num_steps):
    for i, row in wind_data.iterrows():
        
        folderName = f't{i}'

        if not os.path.exists(folderName):
            os.mkdir(folderName)
            shutil.copy('elevation.tif', folderName)  # Copy elevation file for all folders

            if i == 0:
                shutil.copy('land_cover.tif', folderName)  # Copy land_cover.tif only for t0
            else: 
                # Modify land cover based on previous step's GeoJSON output
                print(f"Attempting to read file: {geojson_file}")
                land_cover = os.path.join(subdir, 'land_cover.tif')
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
        print('-------------------')
        print(folderName)
        print('-------------------')
        # Store teh variables for this time-step
        wind_speed =  round(wind_data['wind_speed'][i], 1)
        wind_direction = round(wind_data['wind_direction'][i])
        date =  wind_data['date'][i]

        # 3) WindNinja Simulation  --------------------
        # Gen cfg file
        create_config_file(wind_speed, wind_direction)
        # run WindNinja
        subprocess.run(['WindNinja_cli', 'wind_domain_avg.cfg'])

        # 4) Create landscape.nc file once WindNinja is done --------
        subprocess.run(['python3', '/home/jsoma/wildfire-repo/Fire-spread/all-together/createLandscape.py'], check=True)

                                   
        # 5) Create a tX.ff file -------------------------------------
        
        create_ff_file(i, folderName, run_dir, date)
        
        # 6) Run ForeFire -------------------------------------------
        subprocess.run(['forefire', '-i', f't{i}.ff'], check=True)

        # 7) Proccess the output of ForeFire -----------------------
        process_ffgeojson_files()
        geojson_file = os.path.join(run_dir, f't{i}', f't{i}.geojson')

        # 8) Prepare for the next iteration ---------------------------
        # Break if the geojson file is bigger than 2500 ha
        geojson_file_step = gpd.read_file(geojson_file)
        geojson_file_step = geojson_file_step.to_crs("EPSG:3857")  # Reproject to a projected CRS (e.g., Web Mercator)
        geojson_file_step['area_ha'] = geojson_file_step.geometry.area/10_000 #calculate the ha of the fire
        print(geojson_file_step['area_ha'])
        if (geojson_file_step['area_ha'] > area_max).any(): #------------------------------------------
            print(f"Stopping simulation at t{i} because an area exceeds {area_max} ha.")
            final_name = os.path.join(run_dir, f't{i}', f'final_t{i}.geojson')
            os.rename(geojson_file, final_name)
            for root, dirs, files in os.walk(parent_dir):
                for file in files:
                    if not (file.endswith('.ff') or file.endswith('.geojson') or file.endswith('.csv')):
                        file_path = os.path.join(root, file)
                        try:
                            os.remove(file_path)
                        except Exception as e:
                            print(f"Error removing {file_path}: {e}")
            # stop the code
            break

        # break if time is complete  ------------------------------------------
        os.chdir(subdir)
        if i == num_steps - 1:
            final_name = os.path.join(run_dir, f't{i}', f'final_t{i}.geojson')
            os.rename(geojson_file, final_name)
            
            for root, dirs, files in os.walk(parent_dir):
                for file in files:
                    if not (file.endswith('.ff') or file.endswith('.geojson') or file.endswith('.nc') or file.endswith('.csv')):
                        file_path = os.path.join(root, file)
                        try:
                            os.remove(file_path)
                        except Exception as e:
                            print(f"Error removing {file_path}: {e}")
            # stop the code
            break
    


    # Change back to the parent directory
    os.chdir(parent_dir)

# Record the end time
end_time = time.time()

# Calculate and print the elapsed time
elapsed_time = end_time - start_time
print(f"Total elapsed time: {elapsed_time / 60:.2f} minutes")