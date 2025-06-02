# Wildfire Simulation Repository

This repository contains a set of scripts designed to run ForeFire simulations iteratively. The main script `main.py` coordinates the execution of all the scripts, simulating fire spread over eight iterations (3h time steps over a day).

## Files

### 1. **main.py**
   - This is the main script integrating all the other functions.
   - It runs eight different fire simulations iteratively (from `t0` to `t7`).
   - **User Input**: The script prompts for wind speed, wind direction, and roughness type (as defined in WindNinja).
   - **Process**:
     - For each iteration, the landcover (fuel map) is updated to reflect the burned area.
     - The updated landcover is used for the following simulation.

### 2. **extend.py**
   - Generates the `elevation.tif` and `land_cover.tif` center in the lat/lon introduced by the user.


### 3. **ff_file_generator.py**
   - Creates a `.ff` file required for running each ForeFire simulation.
  

### 4. **genWindNinjaFile.py**
   - Generates the `.cfg` file required to run WindNinja.
   - The `.cfg` file contains configuration parameters such as wind speed, direction, and roughness type.

### 5. **ffgeojsonTojson.py**
   - Converts the output from ForeFire (a `.ffgeojson` format) into a simpler `.geojson` format.

## Workflow
1. The user runs `main.py` and inputs the required parameters.
2. The script iterates through eight simulations, updating the fuel map with each iteration.
3. During each simulation:
   - `genWindNinjaFile.py` generates the configuration file for WindNinja.
   - `ff_file_generator.py` creates the `.ff` file for the current iteration.
4. After each simulation, the output is processed using `ffgeojsonTojson.py`.
5. The cycle repeats for each of the eight time steps, producing a complete set of results.

## Requirements
- **Python 3.6+**
- **WindNinja** installed and configured.
- **ForeFire** installed and configured.
