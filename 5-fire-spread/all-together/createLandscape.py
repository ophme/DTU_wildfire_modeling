import os
import sys
import glob
import argparse
import rasterio as rio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
import numpy as np
from datetime import datetime
import netCDF4 as netcdf
from pyproj import Transformer
import affine
from math import floor

def prop_vrt_Warp(src_path, epsg):
    src = rio.open(src_path)
    bbox = src.bounds

    min_long, min_lat = (bbox[0], bbox[1])
    max_long, max_lat = (bbox[2], bbox[3])

    transformer = Transformer.from_crs(src.crs, f'epsg:{epsg}', always_xy=True)
    min_x, min_y = transformer.transform(min_long, min_lat)
    max_x, max_y = transformer.transform(max_long, max_lat)
    
    right = max_x
    bottom = min_y
    left = min_x
    top = max_y
    
    dst_crs = CRS.from_epsg(epsg)
    resolution = 45

    dst_width = floor((right - left) / resolution)
    dst_height = floor((top - bottom) / resolution)

    xres = (right - left) / dst_width
    yres = (top - bottom) / dst_height

    dst_transform = affine.Affine(xres, 0.0, left, 0.0, -yres, top)
   
    vrt_options = {
        'resampling': Resampling.nearest,
        'crs': dst_crs,
        'transform': dst_transform,
        'height': dst_height,
        'width': dst_width,
    }

    with rio.open(src_path) as src:
        with WarpedVRT(src, **vrt_options) as vrt:
            data = vrt.read(1)

    return vrt, data

def elevation_generator(elevation_filepath, epsg):
    elevation_ds = prop_vrt_Warp(elevation_filepath, epsg)
    elevation_map = elevation_ds[1]
    return elevation_map

def fuel_model_map_generator(fuel_filepath, epsg):
    fuel_ds = prop_vrt_Warp(fuel_filepath, epsg)
    fuel_model_map = fuel_ds[1]
    return fuel_model_map

def default_wind_generator(common_path):
    vel_files = glob.glob(os.path.join(common_path, '*_vel.asc'))
    ang_files = glob.glob(os.path.join(common_path, '*_ang.asc'))
    
    if not vel_files:
        print(f"Error: No velocity files ending with '_vel.asc' found in {common_path}.")
        sys.exit(1)
    if not ang_files:
        print(f"Error: No angle files ending with '_ang.asc' found in {common_path}.")
        sys.exit(1)
    
    vel_path = vel_files[0]
    ang_path = ang_files[0]
    
    vel = np.loadtxt(vel_path, skiprows=6)
    ang = np.loadtxt(ang_path, skiprows=6)
    
    wind_dict = {}
    wind_dict['wind_u'] = []    
    wind_dict['wind_v'] = []
    wind_dict['wind_shape'] = vel.shape
    
    directions = [0, 45, 90, 135, 180, 225, 270, 315, 360]
    math_ang = 270 - ang

    for i in range(len(directions)):
        u = vel * np.cos(np.radians(math_ang))
        v = vel * np.sin(np.radians(math_ang))
        wind_dict['wind_u'].append(u)
        wind_dict['wind_v'].append(v)
        
    return wind_dict

def domainGenerator(fuelModelMap):
    
    meta = fuelModelMap[0].meta['transform']
    res_y = meta[0]
    res_x = meta[4]

    shp_y = fuelModelMap[0].shape[0]
    shp_x = fuelModelMap[0].shape[1]
    
    x = meta[2] #+ res_x*shp_x
    y = meta[5] - res_y*shp_y
    
    Lx = shp_x*res_x
    Ly = shp_y*res_y
   
    domainProperties= {}
    domainProperties['SWx']  = np.float32(x)
    domainProperties['SWy']  = np.float32(y)
    domainProperties['SWz']  = np.float32(0.)
    domainProperties['Lx']   = np.float32(-Lx)
    domainProperties['Ly']   = np.float32(Ly)
    domainProperties['Lz']   = np.float32(0)
    domainProperties['t0']   = np.float32(0)
    domainProperties['Lt']   = np.float32(np.Inf)

    return domainProperties

def parameter_generator(projection):
    today = datetime.now()
    year = today.year
    day = today.day
    iso_today = today.isoformat(sep='_', timespec="seconds")
    
    parameters_properties= {}
    parameters_properties['date']  = f"{iso_today}"
    parameters_properties['duration']  = np.int32(3600)
    parameters_properties['projection']  = f"EPSG:{projection}"
    parameters_properties['refYear']  = np.int32(year)
    parameters_properties['refDay']  = np.int32(day)
    return parameters_properties

def landscape_generator(filename, domain_properties, parameters_properties, projection, fuel_model_map, wind_dict, elevation=None):
    ncfile = netcdf.Dataset(filename, 'w', format='NETCDF3_CLASSIC')
    
    # Dimensions
    ncfile.createDimension('nx', elevation.shape[1])
    ncfile.createDimension('ny', elevation.shape[0])
    ncfile.createDimension('nz', 1)
    ncfile.createDimension('nt', 1)
    ncfile.createDimension('fx', fuel_model_map.shape[1])
    ncfile.createDimension('fy', fuel_model_map.shape[0])
    ncfile.createDimension('fz', 1)
    ncfile.createDimension('ft', 1)
    ncfile.createDimension('wind_directions', 8)
    ncfile.createDimension('wind_dimensions', 2)
    ncfile.createDimension('wind_rows', wind_dict['wind_shape'][0])
    ncfile.createDimension('wind_columns', wind_dict['wind_shape'][1])

    ncfile.projection = str(projection)

    # Variables
    parameters = ncfile.createVariable('parameters', 'S1', ())
    parameters.type = "parameters"  
    if parameters_properties is not None:
        parameters.projection = parameters_properties['projection'] 
    
    domain = ncfile.createVariable('domain', 'S1', ())
    domain.Lz =  domain_properties['Lz']  
    domain.t0 =  domain_properties['t0']  
    domain.SWy = domain_properties['SWy'] 
    domain.SWx = domain_properties['SWx'] 
    domain.Lt =  domain_properties['Lt'] 
    domain.SWz = domain_properties['SWz']
    domain.type = "domain"  
    domain.Lx =  domain_properties['Lx']  
    domain.Ly =  domain_properties['Ly']  
    
    wind = ncfile.createVariable('wind', 'f4', ('wind_dimensions', 'wind_directions', 'wind_rows', 'wind_columns'))
    wind.type = "wind"          
        
    for i in range(8):           
        wind[0,i,:,:] = np.flip(wind_dict['wind_u'][i], axis=0)
        wind[1,i,:,:] = np.flip(wind_dict['wind_v'][i], axis=0)

    fuel = ncfile.createVariable('fuel', 'i4', ('ft', 'fz', 'fy', 'fx'))
    fuel[0,0,:,:] = np.flip(fuel_model_map, axis=0)
    fuel.type = "fuel"
    
    if elevation is not None:
        altitude = ncfile.createVariable('altitude', 'f8', ('nt', 'nz', 'ny', 'nx'))
        altitude[0,0,:,:] = np.flip(elevation, axis=0)
        altitude.type = "data" 
    
    print(f"writing {filename}")
    ncfile.sync()
    ncfile.close()
    return ncfile

def main():
    parser = argparse.ArgumentParser(description='Generate landscape.nc file.')
    # parser.add_argument('output_name', type=str, help='Output filename for the landscape.nc')
    # args = parser.parse_args()

    fixed_output_name = 'landscape.nc'
    elevation_filepath = 'elevation.tif'
    fuel_filepath = 'land_cover.tif'
    common_path_wind = '.'

    if not os.path.exists(elevation_filepath):
        print(f"Error: {elevation_filepath} does not exist.")
        sys.exit(1)
    
    if not os.path.exists(fuel_filepath):
        print(f"Error: {fuel_filepath} does not exist.")
        sys.exit(1)
    
    
    with rio.open(elevation_filepath) as src:
        epsg = src.crs.to_epsg()
        print(f"EPSG: {epsg}")

    elevation_map = elevation_generator(elevation_filepath, epsg)
    fuel_model_map = fuel_model_map_generator(fuel_filepath, epsg)
    wind_dict = default_wind_generator(common_path_wind)
    src = prop_vrt_Warp(fuel_filepath, epsg)
    domain = domainGenerator(src)
    parameters = parameter_generator(epsg)
    landscape = landscape_generator(fixed_output_name, domain, parameters, epsg, fuel_model_map, wind_dict, elevation_map)

if __name__ == "__main__":
    main()
