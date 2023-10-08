import requests
import json
import streamlit as st
import pandas as pd
import math
import re
import pydeck as pdk
import plotly.express as px

# Use user postcode for API request to return latitude and longitude valuea
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

    parsed = []
    for cr in crimes:
        pc = parse_crime_event(cr)
        parsed.append(pc)
   
    crime_parsed_df = pd.DataFrame(parsed)
    # Convert the 'Date' column to datetime format
    crime_parsed_df['Date'] = pd.to_datetime(crime_parsed_df['Date'], format='%Y %m')

    
    return crime_parsed_df


# Clean category text for the KPI box's
def clean_category(category):
    cleaned_category = re.sub(r'\W+', ' ', category).capitalize()
    return cleaned_category

# function to generate a grid with a KPI for each category count in the data
def create_metric_boxes(category_counts, num_rows, num_columns, clean_category):
    for i in range(num_rows):
        columns = st.columns(num_columns)
        for j in range(num_columns):
            index = i * num_columns + j
            if index < len(category_counts):
                category = list(category_counts.keys())[index]
                cleaned_category = clean_category(category)
                count = category_counts[category]
                columns[j].metric(label=f"{cleaned_category}", value=count)

def total_crimes(crime_parsed_data):
    crime_count = crime_parsed_data['ID'].nunique()
    return crime_count

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
            crime_parsed_data = get_crime_data(lat, lng)
            # Aggregate count of rows for each crime category
            category_counts = crime_parsed_data['Crime Category'].value_counts()
            #crime_category_counts = crime_parsed_data.groupby('Crime Category').size().reset_index(name='Count')
            crime_category_counts = crime_parsed_data.groupby('Crime Category')['ID'].nunique().reset_index(name='Count')
            crime_category_counts_sorted = crime_category_counts.sort_values(by='Count', ascending=True)


            num_categories = len(category_counts)
            num_columns = 4
            num_rows = int(math.ceil(num_categories / num_columns))



        
            st.title(f'Total Crimes :blue[{total_crimes(crime_parsed_data)}]')
            

            # Calculate the most popular crime and its count based on distinct IDs
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
            insights_sentence = f"In :blue[{postcode.upper()}], the most reported crime was :blue[{most_popular_crime}] with :blue[{count_of_most_popular_crime}] recorded. That accounts for :blue[{percent_of_most_popular_crime:.2f}%] of all crimes in the area."
            st.caption(date_text)
            st.caption(insights_sentence)

            fig = px.bar(crime_category_counts_sorted, y='Crime Category', x='Count', text='Count')
            fig.update_traces(textfont_size=13) 
            fig.update_layout(
                xaxis=dict(
                    title=None,
                    showticklabels=False  # Remove x-axis tick labels
                ),
                yaxis=dict(title=None),
                #bargap=0.2,         # Adjust the gap between bars within a group
                #bargroupgap=0.1     # Adjust the gap between groups of bars
                autosize=False
            )
            
            config = {'displayModeBar': False}
            st.plotly_chart(fig, theme="streamlit", config=config) # Bar chart

            #create_metric_boxes(category_counts, num_rows, num_columns, clean_category) # Metric Box

            st.subheader("Map")
            draw_map(crime_parsed_data) # Function to draw the map

            st.subheader("Table") 
            st.write(crime_parsed_data) # Write out the df in a table
            
            
            
            #st.bar_chart(crime_category_counts_sorted, x="Crime Category", y="Count", color="#ffaa0088")

            
            

        
                
           
