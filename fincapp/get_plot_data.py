import folium
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt

import streamlit as st

def map_plots(gdf, coordinates):
    # Determine the number of polygons (features) in the GeoDataFrame
    num_polygons = len(gdf)
        
    # Get the rainbow colormap
    cmap = plt.get_cmap('rainbow')

    # Generate the colors corresponding to the values
    if num_polygons > 1:
        hex_colors = [mcolors.rgb2hex(cmap(value)) for value in [i / (num_polygons - 1) for i in range(num_polygons)]]
    else:
        hex_colors = [mcolors.rgb2hex(cmap(value)) for value in [i / (num_polygons) for i in range(num_polygons)]]


    # Create a Folium map
    map = folium.Map(location=coordinates, zoom_start=16)

    # Define a function to match polygon IDs with their corresponding colors
    def style_function(feature):
        polygon_id = feature['properties']['id']
        color = hex_colors[polygon_id % num_polygons]  # Ensure that the ID maps to a color index

        return {
            "fillColor": color,
            "color": color,
            "weight": 2,
            "fillOpacity": 0.6
        }

    # Add the polygons to the map with the corresponding colors
    folium.GeoJson(
        gdf,
        style_function=style_function,
        popup=folium.GeoJsonPopup(fields=["id"])
    ).add_to(map)

    return map