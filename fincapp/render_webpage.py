import streamlit as st
from streamlit_folium import st_folium
import geopandas as gpd
from datetime import datetime, timedelta

from fincapp.get_weather import get_weather_data
from fincapp.get_sat_data import add_latest_ndvi_layer, ndvi_time_series, add_mean_ndvi_layer
from fincapp.get_commodity_price_data import get_sugar_price_data
from fincapp.get_plot_data import map_plots

def render_page(slider_value):
    st.markdown(f'# {slider_value}')

    coordinates_farms = {'Montelibano': 'vector/Montelibano.shp',
                        'La María' : 'vector/LaMaria.shp',
                        'Triangulo' : 'vector/Triangulo.shp',
                        'Los Remansos': 'vector/Remansos.shp'}

    gdf = gpd.read_file(coordinates_farms[slider_value]).to_crs(3116)
    gdf['id'] = gdf.index

    coordinates = (gdf.dissolve().centroid.to_crs(4236)[0].y, gdf.dissolve().centroid.to_crs(4236)[0].x)

    # Show weather metrics
    col1, col2, col3 = st.columns(3)

    col1.metric("Temperatura actual", f'{get_weather_data(*coordinates)['temperature']} ºC')
    col2.metric("Precipitación acumulada último día", f'{get_weather_data(*coordinates)['rainfall']} mm')
    col3.metric("Humedad actual", f'{get_weather_data(*coordinates)['humidity']} %')

    dates = st.date_input(
            "Selecciona el periodo de monitoreo",
            (datetime.today() - timedelta(days=90), datetime.today()),
            datetime.today() - timedelta(days=6*365),
            datetime.today(),
            format="MM.DD.YYYY",
        )

    if len(dates) > 1:

        ndvi = st.toggle("Calcular serie de tiempo de NDVI")

        col1, col2, col3 = st.columns(3)

        aoi = coordinates_farms[slider_value]

        if ndvi:

            with col1:
                st.header('Serie de tiempo de índice de Vegetación (NDVI)')
                st.plotly_chart(ndvi_time_series(aoi, dates[0].strftime("%Y-%m-%d"), dates[1].strftime("%Y-%m-%d")))


            with col2:
                st.header('Polígonos de la finca')
                map = map_plots(gdf, coordinates)
                st_folium(map, width = '100%', height = 450)

            with col3:
                st.header('Índice de vegetación promedio')
                map = add_mean_ndvi_layer(aoi, coordinates, dates[0].strftime("%Y-%m-%d"), dates[1].strftime("%Y-%m-%d"))
                st_folium(map, width = '100%', height = 450)

        else:
            st.header('Indice de Vegetación (NDVI) más reciente')
            map = add_latest_ndvi_layer(aoi, coordinates, (datetime.today() - timedelta(days=90)).strftime("%Y-%m-%d"), datetime.today().strftime("%Y-%m-%d"))
            st_folium(map, width = '100%', height = 450)

    else:
        st.write('Selecciona fechas a monitorear')
        
        
    fig = get_sugar_price_data()
    st.header('Precio del Azucar')
    st.plotly_chart(fig)