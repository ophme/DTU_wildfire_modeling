# Fire Spread Simulation Workflow

This workflow simulates fire spread using historical fire data, wind forecasts, WindNinja, and ForeFire. It is organized into three main steps:

---

##  1. `1-pre-process/`

In this step, we prepare inputs for the simulation:

- **Extract Wind Forecasts:**  
  We extract 3-hourly wind forecasts for the fire location for the next 24 hours. These will be used to drive the fire spread simulation.

- **Historical Fire Data:**  
  We gather historical fire distributions (burned area and timing). This data is used to:
  - Define the **temporal duration** of the fire simulations.
  - Limit the **maximum spread** based on realistic fire sizes.

Outputs from this step are used to initialize and constrain the fire simulation.

---

##  2. `2-forefire/`

This is the core simulation step:

- **Wind Downscaling (WindNinja):**  
  Wind forecasts are downscaled to high-resolution terrain using WindNinja for better accuracy in local wind conditions.

- **Fire Spread Simulation (ForeFire):**  
  ForeFire is run using the downscaled wind and constraints from the pre-processing step. It models how the fire spreads through space and time.

---

##  3. `3-process-results/`

In the final step, we collect and annotate the simulation results:

- **Merge Simulation Outputs:**  
  All fire spread simulation outputs are merged into a single shapefile.

- **Add Event Metadata:**  
  Each fire polygon is annotated with the date of the event, representing when the fire occurred.

---


---

##  Notes

- Ensure all dependencies for WindNinja and ForeFire are installed and available in your environment.
- Wind data input and historical fire data must be correctly formatted before starting the simulation.




