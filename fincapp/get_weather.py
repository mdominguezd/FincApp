import requests

from datetime import datetime, timedelta

import numpy as np
import streamlit as st

@st.cache_data()
def get_weather_data(lat, lon):
    """
        Function to get 
    """
    # Calculate the current time and 24 hours ago
    now = datetime.utcnow() - timedelta(hours=24)
    past_24_hours = now - timedelta(hours=24)
    
    # Format the dates for the API
    start_time = past_24_hours.strftime('%Y-%m-%d')
    end_time = now.strftime('%Y-%m-%d')
    
    # API endpoint
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relative_humidity_2m"
    
    url_p = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start_time}&end_date={end_time}&hourly=precipitation"

    # Sending the request to the API
    response = requests.get(url)
    response_p = requests.get(url_p)
    
    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()

        precipitacion = [i if i is not None else 0 for i in response_p.json()['hourly']['precipitation']]

        # Extract the latest temperature, humidity, and rainfall
        temperature = round(data['hourly']['temperature_2m'][0], 2)
        humidity = round(data['hourly']['relative_humidity_2m'][0], 2)
        rainfall = round(sum(precipitacion), 2)
        
        return {
            "temperature": temperature,
            "humidity": humidity,
            "rainfall": rainfall
        }
    else:
        return {"error": f"Failed to get data, status code: {response.status_code}"}

