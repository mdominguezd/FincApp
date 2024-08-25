import yfinance as yf
import datetime
import plotly.graph_objects as go
import streamlit as st

def get_sugar_price_data():
    # Define the ticker symbol for sugar futures
    ticker = "SB=F"

    # Calculate the date three months ago from today
    end_date = datetime.datetime.today()
    start_date = end_date - datetime.timedelta(days=90)

    # Download historical data for sugar prices
    sugar_data = yf.download(ticker, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))

    # Create an interactive plot with Plotly
    fig = go.Figure()

    # Add the 'Close' price data to the plot
    fig.add_trace(go.Scatter(x=sugar_data.index, y=sugar_data['Close'],
                            mode='lines+markers',
                            name='Sugar Price',
                            line=dict(color='lightgreen'),
                            marker=dict(size=5, color='brown')))

    # Update layout with title and labels
    fig.update_layout(
        title='Precio histórico del Azucar (Últimos 3 meses)',
        xaxis_title='Fecha',
        yaxis_title='Precio (USD)',
        xaxis_rangeslider_visible=True,  # Add a range slider for the x-axis
        template='plotly_dark'  # Choose a dark theme for the plot
    )

    # Show the plot
    return fig