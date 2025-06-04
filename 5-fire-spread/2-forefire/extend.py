import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import os
from pyproj import Transformer, CRS
import rasterio
from rasterio.enums import Resampling
from shapely.geometry import box, Point
from rasterio.transform import from_origin
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.windows import from_bounds
import warnings

warnings.filterwarnings("ignore", category=FutureWarning, module="pyproj")

def get_utm_crs(lon, lat):
    """Determine UTM CRS based on longitude and latitude."""
    utm_zone = int((lon + 180) / 6) + 1
    hemisphere = 'N' if lat >= 0 else 'S'
    epsg_code = f'EPSG:326{utm_zone}' if hemisphere == 'N' else f'EPSG:327{utm_zone}'
    print(f"UTM Zone: {utm_zone}, Hemisphere: {hemisphere}, EPSG Code: {epsg_code}")
    return epsg_code  


def create_square(lon, lat, size_km, raster_path, output_path, resample_method):
    # Ensure the output directory exists
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Open the raster file to get metadata
    with rasterio.open(raster_path) as src:
        # Get the bounds of the raster
        bounds = src.bounds
        crs = src.crs
        transform = src.transform
        
        # Create a point from the given coordinates
        point = Point(lon, lat)
        
        # Convert size from kilometers to degrees (approximately)
        size_deg = size_km / 111.32  # Rough conversion, varies by latitude

        # Create a square around the point
        square = box(
            point.x - size_deg / 2, 
            point.y - size_deg / 2,
            point.x + size_deg / 2,
            point.y + size_deg / 2
        )

        # Check if the square is within the raster bounds
        square_bounds = square.bounds
        if (square_bounds[0] < bounds.left or square_bounds[2] > bounds.right or
            square_bounds[1] < bounds.bottom or square_bounds[3] > bounds.top):
            raise ValueError("The square is out of the raster bounds.")

        # Calculate the window for the square
        window = from_bounds(
            *square_bounds,
            transform=src.transform
        )
        
        # Read the data from the window
        data = src.read(1, window=window, resampling=resample_method)
        
        # Create a new transform for the output raster
        new_transform = from_origin(
            square_bounds[0],  # west
            square_bounds[3],  # north
            src.res[0],        # pixel width
            src.res[1]         # pixel height
        )
        
        # Check if the output file already exists and handle accordingly
        if os.path.exists(output_path):
            os.remove(output_path)  # Remove the file if it exists
        
        # Write the data to a new raster file
        with rasterio.open(output_path, 'w', driver='GTiff',
                           height=data.shape[0], width=data.shape[1],
                           count=1, dtype=data.dtype,
                           crs=crs,
                           transform=new_transform) as dst:
            dst.write(data, 1)
        
        # Return the output path directly
        return output_path

def reproject_raster(temp_elevation_path, output_dir, crsUCTM, resample_method):
    """
    Reproject a raster file to a UTM coordinate reference system based on longitude and latitude.

    Parameters:
    - temp_elevation_path: str, path to the temporary elevation raster file
    - output_dir: str, directory where the reprojected raster will be saved
    - crsUCTM: Coordinate reference system in UTM
    - resample_method: Rasterio resampling method
    """
    dstCrs = crsUCTM

    # Open the source raster
    with rasterio.open(temp_elevation_path) as srcRst:
        # Calculate transform and dimensions for the destination raster
        transform, width, height = calculate_default_transform(
            srcRst.crs, dstCrs, srcRst.width, srcRst.height, *srcRst.bounds
        )

        # Prepare metadata for the destination raster
        kwargs = srcRst.meta.copy()
        kwargs.update({
            'crs': dstCrs,
            'transform': transform,
            'width': width,
            'height': height
        })

        # Create the destination raster
        dst_path = output_dir
        with rasterio.open(dst_path, 'w', **kwargs) as dstRst:
            # Reproject and save each band
            for i in range(1, srcRst.count + 1):
                reproject(
                    source=rasterio.band(srcRst, i),
                    destination=rasterio.band(dstRst, i),
                    src_crs=srcRst.crs,
                    dst_crs=dstCrs,
                    resampling=resample_method
                )

    # Delete the temporary raster
    os.remove(temp_elevation_path)

def create_reprojected_square(lon, lat, size_km, reprojected_path, output_path, resample_method):
    """
    Create a square around a point in UTM projection and extract raster data.

    Parameters:
    - lon: float, longitude in degrees
    - lat: float, latitude in degrees
    - size_km: float, size of the square in kilometers
    - reprojected_path: str, path to the input raster file (assumed to be in UTM)
    - output_path: str, path to save the output raster file
    - resample_method: Rasterio resampling method
    """
    # Ensure the output directory exists
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Open the raster file to get metadata
    with rasterio.open(reprojected_path) as src:
        # Check if the raster CRS is UTM
        crs = src.crs
        if not crs.is_projected:
            raise ValueError("The input raster is not in a projected coordinate system.")

        transform = src.transform

        # Convert size from kilometers to meters
        size_m = size_km * 1000

        # Convert coordinates from lon/lat to UTM
        utm_crs = crs.to_proj4()  # UTM projection as PROJ string
        transformer = Transformer.from_crs("EPSG:4326", utm_crs, always_xy=True)
        easting, northing = transformer.transform(lon, lat)

        # Create a square around the point in UTM coordinates
        square = box(
            easting - size_m / 2,
            northing - size_m / 2,
            easting + size_m / 2,
            northing + size_m / 2
        )

        # Get raster bounds in UTM coordinates
        bounds = src.bounds

        # Check if the square is within the raster bounds
        square_bounds = square.bounds
        if (square_bounds[0] < bounds.left or square_bounds[2] > bounds.right or
            square_bounds[1] < bounds.bottom or square_bounds[3] > bounds.top):
            raise ValueError("The square is out of the raster bounds.")

        # Calculate the window for the square
        window = from_bounds(
            *square_bounds,
            transform=src.transform
        )

        # Read the data from the window
        data = src.read(1, window=window, resampling=resample_method)

        # Create a new transform for the output raster
        new_transform = from_origin(
            square_bounds[0],  # west
            square_bounds[3],  # north
            src.res[0],        # pixel width
            src.res[1]         # pixel height
        )

        # Check if the output file already exists and handle accordingly
        if os.path.exists(output_path):
            os.remove(output_path)  # Remove the file if it exists

        # Write the data to a new raster file
        with rasterio.open(output_path, 'w', driver='GTiff',
                           height=data.shape[0], width=data.shape[1],
                           count=1, dtype=data.dtype,
                           crs=crs,
                           transform=new_transform) as dst:
            dst.write(data, 1)

        # Delete the temporary raster
        os.remove(reprojected_path)

        # Return the output path directly
        return output_path

def process_raster_files(lon, lat, size_km1, size_km2, DEM_path, CLC_path, output_dir, dstCrs_UCTM):
    """
    Process both elevation and landcover files by creating squares and reprojecting.

    Parameters:
    - lon: float, longitude in degrees
    - lat: float, latitude in degrees
    - size_km1: float, size of the square in kilometers for the original projection
    - size_km2: float, size of the square in kilometers for the UTM projection
    - DEM_path: str, path to the DEM file
    - CLC_path: str, path to the landcover file
    - output_dir: str, directory to save the output files
    - dstCrs_UCTM: Coordinate reference system in UTM
    """
    # Elevation File -------------------------------------------
    temp_elevation_path = os.path.join(output_dir, 'elevation_temp.tif')
    resampling_method = Resampling.bilinear  # Use bilinear resampling for elevation

    # 1) Create the square for elevation in the DEM projection
    create_square(lon, lat, size_km1, DEM_path, temp_elevation_path, resampling_method)

    # 2) Reproject the elevation raster to UTM
    reproject_dir = os.path.join(output_dir, 'elevation_reproj.tif')
    reproject_raster(temp_elevation_path, reproject_dir, dstCrs_UCTM, resampling_method)

    # 3) Create the square for elevation in UTM
    elevation_path = os.path.join(output_dir, 'elevation.tif')
    create_reprojected_square(lon, lat, size_km2, reproject_dir, elevation_path, resampling_method)

    # Landcover File -------------------------------------------
    temp_landcover_path = os.path.join(output_dir, 'landcover_temp.tif')
    resampling_method = Resampling.nearest  # Use nearest neighbor resampling for landcover

    # 1) Create the square for landcover in the CLC projection
    create_square(lon, lat, size_km1, CLC_path, temp_landcover_path, resampling_method)

    # 2) Reproject the landcover raster to UTM
    reproject_dir = os.path.join(output_dir, 'landcover_reproj.tif')
    reproject_raster(temp_landcover_path, reproject_dir, dstCrs_UCTM, resampling_method)

    # 3) Create the square for landcover in UTM
    landcover_path = os.path.join(output_dir, 'land_cover.tif')
    create_reprojected_square(lon, lat, size_km2, reproject_dir, landcover_path, resampling_method)

    return elevation_path, landcover_path

if __name__ == "__main__":

    process_raster_files()
    # # Input parameters 
    # lat = float(input("Enter latitude: "))  
    # lon = float(input("Enter longitude: "))
    # size_km1 = 90  # Size of the square in kilometers
    # size_km2 = 50
    
    # # Get the corresponding UTM CRS
    # dstCrs_UCTM = get_utm_crs(lon, lat) 

    # # Use current directory as the output directory
    # output_dir = os.getcwd()

    # # Define file paths for input rasters
    # DEM_path = '/home/jsoma/europeData/EU-DEM.tif'
    # CLC_path = '/home/jsoma/europeData/EU-CLC_v2018.tif'

    # # ELEVATION FILE ------------------------------------------
    # #1) Define output file paths based on user-provided directory
    # temp_elevation_path = os.path.join(output_dir, 'elevation_temp.tif')
    # resampling_method = Resampling.bilinear  # or Resampling.nearest based on your need

   
    # #2) Create the square for elevation in the DEM Projection
    # create_square(lon, lat, size_km1, DEM_path, temp_elevation_path, resampling_method)

    # #3) Reproject the elevation raster to UTM
    # reproject_dir = os.path.join(output_dir, 'elevation_reproj.tif')
    # reproject_raster(temp_elevation_path, reproject_dir, dstCrs_UCTM, resampling_method)

    # #4) Create the square for elevation in UTM
    # elevation_path = os.path.join(output_dir, 'elevation.tif')
    # create_reprojected_square(lon, lat, size_km2, reproject_dir, elevation_path, resampling_method)
    
    # # LANDCOVER FILE ------------------------------------------
    # #1) Define output file paths based on user-provided directory
    # temp_landcover_path = os.path.join(output_dir, 'landcover_temp.tif')
    # resampling_method = Resampling.nearest  # or Resampling.nearest based on your need

   
    # #2) Create the square for elevation in the DEM Projection
    # create_square(lon, lat, size_km1, CLC_path, temp_landcover_path, resampling_method)

    # #3) Reproject the elevation raster to UTM
    # reproject_dir = os.path.join(output_dir, 'landcover_reproj.tif')
    # reproject_raster(temp_landcover_path, reproject_dir, dstCrs_UCTM, resampling_method)

    # #4) Create the square for elevation in UTM
    # landcover_path = os.path.join(output_dir, 'land_cover.tif')
    # create_reprojected_square(lon, lat, size_km2, reproject_dir, landcover_path, resampling_method)
