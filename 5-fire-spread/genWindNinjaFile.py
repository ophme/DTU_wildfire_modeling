def create_config_file():
    # Function to get user input with validation for vegetation choice
    def get_vegetation_choice():
        vegetation_options = ['grass', 'brush', 'trees']
        while True:
            vegetation = input("Enter vegetation type (grass, brush, trees): ").strip().lower()
            if vegetation in vegetation_options:
                return vegetation
            else:
                print(f"Invalid choice. Please choose from {vegetation_options}.")

    # Get user inputs
    input_speed = input("Enter input speed (m/s): ").strip()
    input_direction = input("Enter input direction (º): ").strip()
    vegetation = get_vegetation_choice()

    # File content template
    file_content = f"""#
#    This is an example command line interface (cli) configuration file.
#    
#    This particular file illustrates the necessary options settings to
#    do a simple domain average initialization run without diurnal
#    winds.  The mesh resolution is chosen as 'coarse'.  The output file
#    resolution is defaulted to the mesh resolution (no value specified),
#    except for the ASCII output files which are set to 200 meters.
#          

num_threads                = 5
momentum_flag              = true
number_of_iterations       = 100
elevation_file             = ./elevation.tif
initialization_method      = domainAverageInitialization
input_speed                = {input_speed}
input_speed_units          = mps
input_direction            = {input_direction}
input_wind_height          = 10.0
units_input_wind_height    = m
output_speed_units         = mps
output_wind_height         = 10.0
units_output_wind_height   = m
vegetation                 = {vegetation}
# mesh_choice              = fine
mesh_resolution            = 200.0
units_mesh_resolution      = m
write_goog_output          = false
write_shapefile_output     = false
write_ascii_output         = true
units_ascii_out_resolution = m
write_farsite_atm          = false
"""

    # Write to the cfg file
    with open("wind_domain_avg.cfg", "w") as file:
        file.write(file_content)

    print("Configuration file 'wind_domain_avg.cfg' has been created successfully.")

# Call the function
create_config_file()
