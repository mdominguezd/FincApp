import streamlit as st
from streamlit_extras.switch_page_button import switch_page 
from PIL import Image

im = Image.open("images/logo.ico")

st.set_page_config(layout="wide",
                   initial_sidebar_state="collapsed",
                   page_title='FincApp',
                   page_icon = im)


# Set the title of the dashboard
st.title("FincApp :farmer:")

# Custom CSS for the button
st.markdown("""
            <style>
            div[data-testid="column"]
            {
                text-align: center;
            } 
            </style>

            <style>
            .stButton button {
                background-color: #4CAF50; /* Green background */
                color: white;
                font-size: 120px;
                padding: 30px 60px;
                border-radius: 10px;
            }

            .stButton button:hover {
                background-color: #45a049; /* Darker green on hover */
            }
            </style>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    montelibano = st.button("Montelibano")
    st.image('images/Montelibano.png')
    
    if montelibano:
        switch_page("Montelibano")
        
    lamaria = st.button("La Maria")
    st.image('images/LaMaria.png')

    if lamaria:
        switch_page("LaMaria")


with col2:
    triangulo = st.button("Triangulo Lucerna")
    st.image('images/Triangulo.png')

    if triangulo:
        switch_page("Triangulo")

    remansos = st.button("Remansos")
    st.image('images/Remansos.png')

    if remansos:
        switch_page("Remansos")
