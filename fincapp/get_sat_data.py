import json
import folium
import ee
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt

json_data = st.secrets["json_data"]

# Preparing values
json_object = json.loads(json_data, strict=False)
service_account = json_object['client_email']
json_object = json.dumps(json_object)

# Authorising the app
credentials = ee.ServiceAccountCredentials(service_account, key_data=json_object)
ee.Initialize(credentials)

def get_cloud_free_images(aoi, start, end):
    # Load the S2_SR_HARMONIZED and S2_CLOUD_PROBABILITY image collections
    s2_sr = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterBounds(aoi) \
            .filterDate(start, end)

    s2_cloud_prob = ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY') \
                    .filterBounds(aoi) \
                    .filterDate(start, end) \
                    .map(lambda image: image.clip(aoi))
        
    # Function to add cloud probability band to S2_SR images
    def add_cloud_prob(image):
        # Filter cloud probability images based on the 'system:index' property
        cloud_prob = s2_cloud_prob.filter(ee.Filter.equals('system:index', image.get('system:index')))

        # Check if there is at least one cloud probability image
        has_cloud_prob = cloud_prob.size().gt(0)
        
        # Define a default cloud probability image with all values set to 100
        default_cloud_prob = ee.Image.constant(100).rename('cloud_prob')

        # If there is a cloud probability image, use it; otherwise, use the default
        cloud_prob_image = ee.Algorithms.If(has_cloud_prob, cloud_prob.first().select('probability').rename('cloud_prob'), default_cloud_prob)

        # Add the cloud probability band to the original image
        image = image.addBands(cloud_prob_image)
        
        return image

    # Add the cloud probability band to the S2_SR images
    s2_sr_with_cloud = s2_sr.map(add_cloud_prob)

    # Function to compute mean cloud probability within the AOI
    def compute_aoi_cloud_prob(image):
        cloud_prob = image.select('cloud_prob')
        mean_cloud_prob = cloud_prob.reduceRegion(reducer=ee.Reducer.mean(), geometry=aoi, scale=10).get('cloud_prob')
        return image.set('mean_cloud_prob', mean_cloud_prob)

    # Compute the mean cloud probability for each image
    s2_sr_with_aoi_cloud_prob = s2_sr_with_cloud.map(compute_aoi_cloud_prob)

    # Filter images based on mean cloud probability within the AOI
    filtered_images = s2_sr_with_aoi_cloud_prob.filter(ee.Filter.lt('mean_cloud_prob', 5)).map(lambda image: image.clip(aoi)).select(['B8','B4'])

    return filtered_images

@st.cache_data
def add_ndvi_layer(_aoi, centroid, start, end):
    """
    Generates an NDVI layer for the given GeoDataFrame polygon and displays it on a Folium map.

    Args:
    gdf (geopandas.GeoDataFrame): GeoDataFrame containing a polygon for the area of interest.

    Returns:
    folium.Map: Folium map with the NDVI layer.
    """
    
    filtered_image_mean = get_cloud_free_images(_aoi, start, end).mean()
    
    # Calculate NDVI
    ndvi = filtered_image_mean.normalizedDifference(['B8', 'B4']).rename('NDVI')
    
    # Define visualization parameters for NDVI
    ndvi_params = {
        'min': -0.75,
        'max': 0.75,
        'palette': ['red', 'yellow', 'green']
    }
    
    # Create a map centered at the polygon's centroid
    m = folium.Map(location=centroid, zoom_start=15)
    
    # Get the URL for the NDVI tile layer
    ndvi_map_id_dict = ee.Image(ndvi).getMapId(ndvi_params)
    ndvi_tile_url = ndvi_map_id_dict['tile_fetcher'].url_format

    # Add the NDVI layer to the folium map
    folium.TileLayer(
        tiles=ndvi_tile_url,
        attr='Google Earth Engine',
        name='NDVI',
        overlay=True,
        control=True
    ).add_to(m)

    # Add layer control to toggle the NDVI layer
    folium.LayerControl().add_to(m)

    # Display the map
    return m

@st.cache_data()
def ndvi_time_series(_aoi, start, end):

    # Get cloud-free images
    images = get_cloud_free_images(_aoi, start, end)

    # Get each individual polygon from the AOI
    polygons = _aoi.geometries()

    all_ndvi_results = []

    # Loop through each polygon
    for i in range(polygons.length().getInfo()):
        polygon = ee.Geometry(polygons.get(i))
        
        def get_image_date_and_ndvi(image):
            # Calculate NDVI
            ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')

            # Compute the mean NDVI for this specific polygon
            mean_ndvi = ndvi.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=polygon,
                scale=10
            ).get('NDVI')

            # Get the acquisition date of the image
            date = image.date().format('YYYY-MM-dd')

            # Return a dictionary with the date, mean NDVI, and polygon index
            return ee.Feature(None, {'date': date, 'mean_ndvi': mean_ndvi, 'polygon': i})
        
        # Get NDVI information for the current polygon
        ndvi_info = images.map(get_image_date_and_ndvi).getInfo()['features']
        
        # Store results for this polygon
        ndvi_results = [{'date': f['properties']['date'], 
                         'mean_ndvi': f['properties']['mean_ndvi'], 
                         'polygon': f['properties']['polygon']} for f in ndvi_info]
        all_ndvi_results.extend(ndvi_results)
    
    # Convert the list of dictionaries to a Pandas DataFrame
    ndvi_df = pd.DataFrame(all_ndvi_results)

    # Generate a rainbow color map based on the number of polygons
    num_polygons = polygons.length().getInfo()

    # Get the rainbow colormap
    cmap = plt.get_cmap('rainbow')

    # Generate the colors corresponding to the values
    colors = [mcolors.rgb2hex(cmap(value)) for value in [i/(num_polygons-1) for i in range(num_polygons)]]


    # Create a Plotly graph, using 'polygon' to distinguish between different polygons and color them using the rainbow colormap
    fig = px.line(
        ndvi_df,
        x='date',
        y='mean_ndvi',
        color='polygon',
        title='serie de tiempo de NDVI para cada polígono',
        labels={'mean_ndvi': 'NDVI promedio', 'date': 'Fecha', 'polygon': 'Polígono'},
        markers=True,
        color_discrete_sequence=colors
    )

    return fig