import os
import rasterio as rio
import geojson
from shapely.geometry import shape
from pathlib import Path
from pyproj import Transformer
import textwrap

def create_ff_file(i, folder_name, run_dir, date, propagation_model="Rothermel"):
    #
    print(propagation_model)
    # Define file paths
    run_dir = Path(run_dir)  # Ensure run_dir is a Path object
    fuel_table_file = '/home/jsoma/europeData/fuels.ff'
    elevation_file = run_dir / 'elevation.tif'
    t_ff_path = run_dir / folder_name / f't{i}.ff'
    
    # Read raster projection and get fire ignition point for the first time step
    with rio.open(elevation_file) as src:
        EPSG = src.crs
        if i == 0:
            fire_ignition = (*src.xy(src.width // 2, src.height // 2), 0)

    # Prepare the content of the file
    content = textwrap.dedent(f"""\
        setParameter[dumpMode=geojson]
        setParameter[caseDirectory=.]
        setParameter[ForeFireDataDirectory=.]
        setParameter[projection={EPSG}]
        setParameter[fuelsTableFile={fuel_table_file}]
        setParameter[propagationModel={propagation_model}]
        loadData[landscape.nc;{date}]
    """)

    # Add fire ignition or perimeter for subsequent steps
    if i == 0:
        content += f"startFire[loc={fire_ignition};t=0]\n"
    else:
        geojson_file = run_dir / f't{i-1}' / f't{i-1}.geojson'
        with open(geojson_file) as f:
            perimeter = shape(geojson.load(f)['features'][0]['geometry'])
        
        transformer = Transformer.from_crs("epsg:4326", EPSG.to_string(), always_xy=True)
        fire_nodes = "\n".join(
            f"\tFireNode[loc=({x},{y},0);;vel=(0.,0.,0.);;t=0.]"
            for x, y in (transformer.transform(*coord) for coord in perimeter.exterior.coords)
        )
        content += f"FireFront[t=0.]\n{fire_nodes}\n"

    # Add propagation steps and output
    content += textwrap.dedent(f"""\
        step[dt=10800s]
        print[t{i}.ffgeojson]
        print[]
    """)

    # Write the content to the file
    with open(t_ff_path, 'w') as t_file:
        t_file.write(content)
