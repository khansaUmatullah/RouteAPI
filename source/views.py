from http import HTTPStatus

import numpy as np
import pandas as pd
import requests
from urllib.parse import quote
import plotly.express as px

from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView


class RouteView(APIView):

    def get(self,request):
        start_city = request.query_params.get('start_city')
        finish_city = request.query_params.get('finish_city')
        start = request.query_params.get('start')
        finish = request.query_params.get('finish')
        if not (start_city and finish_city):
            return Response(
                {"error": "Missing required query parameters: start_City, finish_City"},
                status=400,
            )

        api_key = "daddc0b315034d34b9921b00a23713c8"

        start_encoded = quote(start)
        end_encoded = quote(finish)

        url_start = f"https://api.geoapify.com/v1/geocode/search?text={start_encoded}&apiKey={api_key}"
        resp_start = requests.get(url_start)
        source_coords = resp_start.json()["features"][0]["geometry"]["coordinates"]

        url_end = f"https://api.geoapify.com/v1/geocode/search?text={end_encoded}&apiKey={api_key}"
        resp_end = requests.get(url_end)
        dest_coords = resp_end.json()["features"][0]["geometry"]["coordinates"]

        url_route = f"https://api.geoapify.com/v1/routing?waypoints={source_coords[1]}%2C{source_coords[0]}%7C{dest_coords[1]}%2C{dest_coords[0]}&mode=drive&apiKey={api_key}"
        resp_route = requests.get(url_route)
        if resp_route.status_code == 200:
            route_data = resp_route.json()
            route_coordinates = route_data['features'][0]['geometry']['coordinates']

            coordinates_reversed = [[coord[1], coord[0]] for coord in route_coordinates[0]]
            df_out = pd.DataFrame({'Node': np.arange(len(coordinates_reversed))})
            df_out['coordinates'] = coordinates_reversed
            df_out[['lat', 'long']] = pd.DataFrame(df_out['coordinates'].tolist())
            df_out['lat'] = df_out['lat'].astype(float)
            df_out['long'] = df_out['long'].astype(float)

        fuel_stations = pd.read_csv('fuel-prices-for-be-assessment.csv')


        route_cities = [start_city,finish_city]
        truck_stops_df = fuel_stations[fuel_stations['City'].isin(route_cities)]

        base_url = "https://api.geoapify.com/v1/geocode/search"
        truck_stops_df["Latitude"], truck_stops_df["Longitude"] = zip(*truck_stops_df.apply(
            lambda row: self.get_coordinates(row["Truckstop Name"], row["City"], row["State"],base_url,api_key),
            axis=1
        ))

        fuel_stations_df = pd.DataFrame(truck_stops_df)

        fig = px.scatter_mapbox(df_out,
                                lat="lat",
                                lon="long",
                                title="Route with Fuel Stations and Prices")

        fig.add_scattermapbox(lat=fuel_stations_df['Latitude'],
                              lon=fuel_stations_df['Longitude'],
                              mode='markers+text',
                              marker=dict(
                                  size=20,
                              ),
                              text=fuel_stations_df['Truckstop Name'] + ' ($' + fuel_stations_df['Retail Price'].astype(
                                  str) + ')',

                              textposition='top center',
                              name='Fuel Stations')



        fig.update_layout(mapbox_style="open-street-map")
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

        fig.show()
        distance_meters = route_data['features'][0]['properties']['distance']
        time_seconds = route_data['features'][0]['properties']['time']

        distance_miles = distance_meters * 0.000621371

        time_hours = int(time_seconds // 3600)
        time_minutes = int((time_seconds % 3600) // 60)
        total_fuel_consumption= distance_miles/10
        fuel_price = [
            row['Retail Price'] * total_fuel_consumption
            for _, row in truck_stops_df.iloc[1:].iterrows()
        ]
        min_fuel_cost = min(fuel_price)

        data={
            "time": f"{time_hours} hours {time_minutes} minutes",
            "distance": f"{distance_miles:.2f} miles",
            "optimal fuel cost": f"${min_fuel_cost}",
        }
        return Response(data=data, status=HTTPStatus.OK )

    def get_coordinates(self,name, city, state,base_url,api_key):
            query = f"{name}, {city}, {state}"
            encoded_query = quote(query)
            url = f"{base_url}?text={encoded_query}&apiKey={api_key}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if data["features"]:
                    coords = data["features"][0]["geometry"]["coordinates"]
                    return coords[1], coords[0]
            return None, None

