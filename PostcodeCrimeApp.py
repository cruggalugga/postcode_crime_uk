import requests
import json
import streamlit as st
import pandas as pd
import math
import re
import pydeck as pdk
import plotly.express as px

# Take user postcode for API request to return lat, lng
def get_lat_long(postcode):
    base_url = "https://api.postcodes.io/postcodes/"
    url = base_url + postcode
    try:
        response = requests.get(url)
        data =  json.loads(response.content)
        if response.status_code == 200 and data['status'] == 200:
            lat = data['result']['latitude']
            lng = data['result']['longitude']
            return lat, lng
        else:
            return None, None
    except requests.exceptions.RequestException as e:
        print("Error:", e)
        return None, None
    
# Function for parsing the data
def parse_crime_event(cr):
    cr_parsed = pd.Series({
        'ID': cr['crime']['id'],
        'Crime Category': cr['crime']['category'],
        'Date': cr['crime']['month'],
        'Category Code': cr['category']['code'],
        'Cetegory Name': cr['category']['name'],
        'Longitude': float(cr['crime']['location']['longitude']),
        'Latitude': float(cr['crime']['location']['latitude']),
        'Crime Location Type': cr['crime']['location_type'],
        'Crime Location Sub-type': cr['crime']['location_subtype']
    })
    return cr_parsed

# Function to get crime data for a given latitude and longitude
def get_crime_data(lat, lng):
    url = f'https://data.police.uk/api/outcomes-at-location?lat={lat}&lng={lng}'
    r = requests.get(url)
    crimes = json.loads(r.content)
    
    # Empty list
    parsed = []
    # For each entry parse through the pd.series and then append to the list. 
    for cr in crimes:
        pc = parse_crime_event(cr)
        parsed.append(pc)
   
    # Convert the list to a DataFrame
    crime_parsed_df = pd.DataFrame(parsed)
    # Convert the 'Date' column to datetime format
    crime_parsed_df['Date'] = pd.to_datetime(crime_parsed_df['Date'], format='%Y %m')
    return crime_parsed_df


# Clean category text for the KPI box's
def clean_category(category):
    # Remove special characters and capitalise
    cleaned_category = re.sub(r'\W+', ' ', category).capitalize()
    return cleaned_category


def total_crimes(crime_parsed_data):
    crime_count = crime_parsed_data['ID'].nunique()
    return crime_count

def count_crimes_by_category(crime_parsed_data):
    crime_category_counts = crime_parsed_data.groupby('Crime Category')['ID'].nunique().reset_index(name='Count')
    crimes_by_category = crime_category_counts.sort_values(by='Count', ascending=True)
    return crimes_by_category

def get_insight_txt(crime_parsed_data):
    crime_counts = crime_parsed_data.groupby('Crime Category')['ID'].nunique()
    most_popular_crime = crime_counts.idxmax()
    count_of_most_popular_crime = crime_counts.max()

    # Calculate the percentage of the most popular crime
    total_crimes = crime_counts.sum()
    percent_of_most_popular_crime = (count_of_most_popular_crime / total_crimes) * 100

    # Create the sentence
    # Extract the minimum and maximum dates
    min_date = crime_parsed_data['Date'].min()
    max_date = crime_parsed_data['Date'].max()
    date_text = f"Time Period :blue[{min_date.strftime('%Y-%m')}] to :blue[{max_date.strftime('%Y-%m')}]"
    insights_sentence = (   f"In :blue[{postcode.upper()}], the crime reported the most is "
                            f":blue[{most_popular_crime}] with :blue[{count_of_most_popular_crime}] "
                            f"recorded. That accounts for :blue[{percent_of_most_popular_crime:.2f}%] "
                            "of all crimes in the area.")
    return date_text, insights_sentence


def draw_bar_chart(crime_parsed_data):
    crimes_by_cateogry = count_crimes_by_category(crime_parsed_data)
    fig = px.bar(crimes_by_cateogry, y='Crime Category', x='Count', text='Count')
    fig.update_traces(textfont_size=13) 
    fig.update_layout(
        xaxis=dict(
            title=None,
            showticklabels=False  # Remove x-axis tick labels
        ),
        yaxis=dict(title=None),
        autosize=False,
        dragmode=False
    )
    config = {'displayModeBar': False}
    return fig, config

def draw_map(crime_parsed_data):
    # Calculate the mean latitude and mean longitude
    mean_latitude = crime_parsed_data['Latitude'].mean()
    mean_longitude = crime_parsed_data['Longitude'].mean()

    built_map = st.pydeck_chart(pdk.Deck(
        map_style=None,
        initial_view_state=pdk.ViewState(
            latitude=mean_latitude,
            longitude=mean_longitude,
            zoom=13,
            pitch=0,
        ),
        layers=[
            pdk.Layer(
                'ScatterplotLayer',
                data=crime_parsed_data,
                get_position='[Longitude, Latitude]',
                get_color='[200, 30, 0, 160]',
                get_radius=30,
            ),
        ],
        tooltip=True
    ))
    return built_map

def draw_line_chart(crime_parsed_data):
    # Calculate the count of unique IDs for each date
    data = crime_parsed_data.groupby(crime_parsed_data['Date'].dt.strftime('%Y %m'))['ID'].nunique().reset_index(name='Count')

    # Create a DataFrame with all the required dates
    all_dates = pd.DataFrame({'Date': pd.date_range(start=data['Date'].min(), end=data['Date'].max(), freq='MS')})
    all_dates['FormattedDate'] = all_dates['Date'].dt.strftime('%Y %m')

    # Merge the actual data with the DataFrame containing all dates
    merged_data = pd.merge(all_dates, data, left_on='FormattedDate', right_on='Date', how='left').fillna(0)

    # Sort the data by 'Date'
    merged_data = merged_data.sort_values(by='FormattedDate', ascending=True)

    # Plot the line chart
    line_chart = st.line_chart(merged_data, x='FormattedDate', y='Count')
    return merged_data 


# Main Section
if __name__ == "__main__":
    st.title(f":cop: Crime by Postcode")
    postcode = st.text_input("Enter a UK postcode:") # Text input for postcode

    if postcode:
        lat, lng = get_lat_long(postcode)
        if lat and lng:
            pass
        else:
            st.write("Invalid postcode or unable to retrieve location information.")

        if lat and lng:
            crime_parsed_data = get_crime_data(lat, lng) # Use returned lat & lng to fetch crime data as a DataFrame
            st.title(f'Total Crimes :blue[{total_crimes(crime_parsed_data)}]')

            date_text, insights_sentence = get_insight_txt(crime_parsed_data) # Get insights for display
            st.caption(date_text)
            st.caption(insights_sentence)

            fig, config =  draw_bar_chart(crime_parsed_data) # Build bar chart by aggregating dataframe
            st.plotly_chart(fig, theme="streamlit", config=config)

            draw_line_chart(crime_parsed_data)

            st.subheader("Map")
            draw_map(crime_parsed_data) # Function to draw the map

            st.subheader("Table") 
            st.write(crime_parsed_data) # Write out the df in a table



            

            
            

        
                
           
