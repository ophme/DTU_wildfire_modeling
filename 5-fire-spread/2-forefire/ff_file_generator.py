import os
import rasterio as rio
from datetime import datetime, timedelta
import geojson
from shapely.geometry import shape
from pyproj import Transformer

def create_ff_file(i, folderName, run_dir, initial_date, time_step, propagation_model="Rothermel"):
    fuel_table_file =  '/home/jsoma/europeData/fuels.ff'
    
   

    # Set the date for this time step and extract the ignition point
    date = initial_date
    elevation_file = run_dir + '/elevation.tif'
    with rio.open(elevation_file) as src:
        # Projection of the raster
        EPSG = src.crs
    if i == 0:
            # Get the coordinates of the center of the raster (fire ignition)   
            fire_ignition = src.xy(src.width // 2, src.height // 2)
            fire_ignition = (fire_ignition[0], fire_ignition[1], 0)
    else:
        # Increment the timestamp by the specified time step
        prev_timestamp = datetime.strptime(date.rstrip('Z'), "%Y-%m-%d_%H:%M:%S")
        new_timestamp = prev_timestamp + (time_step * i)
        date = new_timestamp.strftime("%Y-%m-%d_%H:%M:%S") + "Z"
    
    # create the tX.ff file
    t_ff_path = os.path.join(run_dir, folderName, f't{i}.ff')
    print(t_ff_path)

    with open(t_ff_path, 'w') as t_file:
        t_file.write('setParameter[dumpMode=geojson]\n')
        t_file.write('setParameter[caseDirectory=.]\n')
        t_file.write('setParameter[ForeFireDataDirectory=.]\n')
        t_file.write(f'setParameter[projection={EPSG}]\n')
        t_file.write(f'setParameter[fuelsTableFile={fuel_table_file}]\n')
        t_file.write(f'setParameter[propagationModel={propagation_model}]\n')
        t_file.write(f'loadData[landscape.nc;{date}]\n')

        if i == 0:
            # Initial fire ignition for t0
            t_file.write(f'startFire[loc={fire_ignition};t=0]\n')
        else:
            # Load GeoJSON from the previous time step to extract perimeter coordinates
            geojson_file = os.path.join(run_dir, f't{i-1}', f't{i-1}.geojson')
            with open(geojson_file) as f:
                gj = geojson.load(f)
            perimeter = shape(gj['features'][0]['geometry'])

            # Reproject and write the fire node locations
            t_file.write("FireFront[t=0.]\n")
            transformer = Transformer.from_crs("epsg:4326", EPSG.to_string(), always_xy=True)
            for coord in list(perimeter.exterior.coords):
                x, y = transformer.transform(coord[0], coord[1])
                t_file.write(f"\tFireNode[loc=({x},{y},0);;vel=(0.,0.,0.);;t=0.]\n")

        # Add remaining lines for fire propagation
        t_file.write('step[dt=10800s]\n')
        t_file.write(f'print[t{i}.ffgeojson]\n')
        t_file.write('print[]')

