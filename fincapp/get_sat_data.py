import json
import folium
import ee
import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import geemap

json_data = st.secrets["json_data"]

json_object = json.loads(json_data, strict=False)
service_account = json_object['client_email']
json_object = json.dumps(json_object)
credentials = ee.ServiceAccountCredentials(service_account, key_data=json_object)
ee.Initialize(credentials)

# Retrieve cloud-free satellite images from the Sentinel-2 collection
@st.cache_data()
def get_cloud_free_images(aoi, start, end):
    """
    Retrieves cloud-free images from the Sentinel-2 collection for a given area and time range.

    Args:
    aoi (ee.Geometry): Area of interest.
    start (str): Start date for the image collection (format: 'YYYY-MM-DD').
    end (str): End date for the image collection (format: 'YYYY-MM-DD').

    Returns:
    ee.ImageCollection: Cloud-free Sentinel-2 images with selected bands.
    """
    
    aoi = geemap.shp_to_ee(aoi).geometry()

    s2_sr = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(aoi).filterDate(start, end)
    s2_cloud_prob = ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY').filterBounds(aoi).filterDate(start, end).map(lambda image: image.clip(aoi))

    def add_cloud_prob(image):
        cloud_prob = s2_cloud_prob.filter(ee.Filter.equals('system:index', image.get('system:index')))
        has_cloud_prob = cloud_prob.size().gt(0)
        default_cloud_prob = ee.Image.constant(100).rename('cloud_prob')
        cloud_prob_image = ee.Algorithms.If(has_cloud_prob, cloud_prob.first().select('probability').rename('cloud_prob'), default_cloud_prob)
        image = image.addBands(cloud_prob_image)
        return image

    s2_sr_with_cloud = s2_sr.map(add_cloud_prob)

    def compute_aoi_cloud_prob(image):
        cloud_prob = image.select('cloud_prob')
        mean_cloud_prob = cloud_prob.reduceRegion(reducer=ee.Reducer.mean(), geometry=aoi, scale=10).get('cloud_prob')
        return image.set('mean_cloud_prob', mean_cloud_prob)

    s2_sr_with_aoi_cloud_prob = s2_sr_with_cloud.map(compute_aoi_cloud_prob)
    filtered_images = s2_sr_with_aoi_cloud_prob.filter(ee.Filter.lt('mean_cloud_prob', 5)).map(lambda image: image.clip(aoi)).select(['B8', 'B4'])

    return filtered_images

# Generate an NDVI layer for the latest image and add it to a Folium map
@st.cache_data()
def add_latest_ndvi_layer(aoi, centroid, start, end):
    """
    Generates and adds an NDVI layer from the latest image to a Folium map.

    Args:
    aoi (ee.Geometry): Area of interest.
    centroid (list): Coordinates [latitude, longitude] to center the map.
    start (str): Start date for the image collection (format: 'YYYY-MM-DD').
    end (str): End date for the image collection (format: 'YYYY-MM-DD').

    Returns:
    folium.Map: Folium map with the NDVI layer.
    """
    filtered_images = get_cloud_free_images(aoi, start, end)
    latest_image = filtered_images.sort('system:time_start', False).first()
    ndvi = latest_image.normalizedDifference(['B8', 'B4']).rename('NDVI')

    ndvi_params = {'min': -0.75, 'max': 0.75, 'palette': ['red', 'yellow', 'green']}
    m = folium.Map(location=centroid, zoom_start=15)

    ndvi_map_id_dict = ee.Image(ndvi).getMapId(ndvi_params)
    ndvi_tile_url = ndvi_map_id_dict['tile_fetcher'].url_format

    folium.TileLayer(tiles=ndvi_tile_url, attr='Google Earth Engine', name='NDVI', overlay=True, control=True).add_to(m)
    folium.LayerControl().add_to(m)

    return m

# Generate an NDVI layer for the mean image and add it to a Folium map
@st.cache_data()
def add_mean_ndvi_layer(aoi, centroid, start, end):
    """
    Generates and adds an NDVI layer from the mean image to a Folium map.

    Args:
    aoi (ee.Geometry): Area of interest.
    centroid (list): Coordinates [latitude, longitude] to center the map.
    start (str): Start date for the image collection (format: 'YYYY-MM-DD').
    end (str): End date for the image collection (format: 'YYYY-MM-DD').

    Returns:
    folium.Map: Folium map with the NDVI layer.
    """
    filtered_images = get_cloud_free_images(aoi, start, end)
    mean_image = filtered_images.mean()
    ndvi = mean_image.normalizedDifference(['B8', 'B4']).rename('NDVI')

    ndvi_params = {'min': -0.75, 'max': 0.75, 'palette': ['red', 'yellow', 'green']}
    m = folium.Map(location=centroid, zoom_start=15)

    ndvi_map_id_dict = ee.Image(ndvi).getMapId(ndvi_params)
    ndvi_tile_url = ndvi_map_id_dict['tile_fetcher'].url_format

    folium.TileLayer(tiles=ndvi_tile_url, attr='Google Earth Engine', name='NDVI', overlay=True, control=True).add_to(m)
    folium.LayerControl().add_to(m)

    return m

# Generate a time series plot of NDVI for each polygon within the area of interest@st.cache_data()
@st.cache_data()
def ndvi_time_series(aoi, start, end):
    """
    Generates a time series plot of NDVI for each polygon within the area of interest.

    Args:
    aoi (ee.Geometry): Area of interest.
    start (str): Start date for the image collection (format: 'YYYY-MM-DD').
    end (str): End date for the image collection (format: 'YYYY-MM-DD').

    Returns:
    plotly.graph_objs._figure.Figure: Plotly figure containing the NDVI time series.
    """
    images = get_cloud_free_images(aoi, start, end)
    polygons = geemap.shp_to_ee(aoi).geometry().geometries()
    all_ndvi_results = []

    for i in range(polygons.length().getInfo()):
        polygon = ee.Geometry(polygons.get(i))

        def get_image_date_and_ndvi(image):
            ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
            mean_ndvi = ndvi.reduceRegion(reducer=ee.Reducer.mean(), geometry=polygon, scale=10).get('NDVI')
            date = image.date().format('YYYY-MM-dd')
            return ee.Feature(None, {'date': date, 'mean_ndvi': mean_ndvi, 'polygon': i})

        ndvi_info = images.map(get_image_date_and_ndvi).getInfo()['features']
        ndvi_results = [{'date': f['properties']['date'], 'mean_ndvi': f['properties']['mean_ndvi'], 'polygon': f['properties']['polygon']} for f in ndvi_info]
        all_ndvi_results.extend(ndvi_results)

    ndvi_df = pd.DataFrame(all_ndvi_results)
    num_polygons = polygons.length().getInfo()
    cmap = plt.get_cmap('rainbow')

    if num_polygons > 1:
        colors = [mcolors.rgb2hex(cmap(value)) for value in [i / (num_polygons - 1) for i in range(num_polygons)]]
    else:
        colors = [mcolors.rgb2hex(cmap(value)) for value in [i / (num_polygons) for i in range(num_polygons)]]

    fig = px.line(
        ndvi_df,
        x='date',
        y='mean_ndvi',
        color='polygon',
        title='NDVI Time Series for Each Polygon',
        labels={'mean_ndvi': 'Mean NDVI', 'date': 'Date', 'polygon': 'Polygon'},
        markers=True,
        color_discrete_sequence=colors
    )

    return fig
