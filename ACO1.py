
import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from math import radians, sin, cos, sqrt, atan2
import numpy as np
import random

# 🔹 Replace with your LocationIQ API Key
LOCATIONIQ_API_KEY = "pk.4acc4b9ee785532e6bca33ee24026c06"

# 🔹 Function to get latitude & longitude of the delivery address
def get_coordinates(address):
    url = "https://us1.locationiq.com/v1/search.php"
    params = {"key": LOCATIONIQ_API_KEY, "q": address, "format": "json"}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, list) and data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    return None, None

# 🔹 Function to find nearby restaurants within 10km
def get_nearby_restaurants(lat, lon):
    url = "https://us1.locationiq.com/v1/nearby.php"
    params = {"key": LOCATIONIQ_API_KEY, "lat": lat, "lon": lon, "tag": "restaurant", "radius": 10000, "format": "json"}
    try:
        response = requests.get(url, params=params)
        data = response.json()
        return data[:10] if isinstance(data, list) else []
    except:
        return []

# 🔹 Haversine formula to calculate the distance between two points
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))

# 🔹 ACO Algorithm for Route Optimization
def aco_optimize_route(start, end, iterations=50, ants=20, evaporation_rate=0.5, alpha=1, beta=2):
    nodes = [start, end]
    num_nodes = len(nodes)
    pheromones = np.ones((num_nodes, num_nodes))
    best_route, best_distance = None, float('inf')
    
    for _ in range(iterations):
        all_routes = []
        for _ in range(ants):
            route = [0]
            while len(route) < num_nodes:
                i = route[-1]
                probabilities = []
                for j in range(num_nodes):
                    if j not in route:
                        dist = haversine(nodes[i][0], nodes[i][1], nodes[j][0], nodes[j][1])
                        pheromone = pheromones[i][j] ** alpha
                        heuristic = (1 / dist) ** beta if dist > 0 else 1
                        probabilities.append((j, pheromone * heuristic))
                if probabilities:
                    total = sum(p[1] for p in probabilities)
                    probabilities = [(p[0], p[1] / total) for p in probabilities]
                    next_node = random.choices([p[0] for p in probabilities], [p[1] for p in probabilities])[0]
                    route.append(next_node)
            all_routes.append((route, sum(haversine(nodes[route[i]][0], nodes[route[i]][1], nodes[route[i+1]][0], nodes[route[i+1]][1]) for i in range(len(route)-1))))
        
        for route, dist in all_routes:
            if dist < best_distance:
                best_route, best_distance = route, dist
                
        pheromones *= (1 - evaporation_rate)
        for route, dist in all_routes:
            for i in range(len(route) - 1):
                pheromones[route[i]][route[i + 1]] += 1 / dist
    
    return [nodes[i] for i in best_route], best_distance

# 🔹 Carbon Emission Calculation (grams of CO2 per kilometer)
CO2_EMISSION_FACTOR = 120  # grams of CO2 per km (adjust this as needed)

def calculate_carbon_footprint(distance_km):
    return CO2_EMISSION_FACTOR * distance_km  # in grams

# 🔹 Streamlit UI
st.title("🚀 Optimized Food Delivery Route (ACO) with Carbon Tracking")

# 🔹 User selects a delivery location
st.subheader("📍 Select a delivery location on the map")
m = folium.Map(location=[12.9716, 80.2750], zoom_start=15)
marker = folium.Marker([12.9716, 80.2750], popup="Drag to select location", draggable=True)
marker.add_to(m)
selected_location = st_folium(m, width=725, height=500)

# if selected_location and 'last_object_clicked' in selected_location:
#     last_clicked = selected_location['last_object_clicked']
#     lat, lon = last_clicked.get('lat'), last_clicked.get('lng')
if selected_location:
    last_clicked = selected_location.get('last_object_clicked', {})  # getting the last clicked location

    lat, lon = None, None  # initializing coordinates

    if last_clicked and 'lat' in last_clicked and 'lng' in last_clicked:
        lat, lon = last_clicked['lat'], last_clicked['lng']

    if lat is not None and lon is not None:
        st.write(f"✅ Selected location: **Lat: {lat}, Lon: {lon}**")
        # Continue with the rest of the processing...
    else:
        st.warning("⚠️ Please select a location on the map.")
    if lat and lon:
        st.write(f"✅ Selected delivery location: **Lat: {lat}, Lon: {lon}**")
        restaurants = get_nearby_restaurants(lat, lon)
        if restaurants:
            restaurant_options = [f"{r.get('name', 'Unnamed Restaurant')}" for r in restaurants]
            selected_restaurant = st.selectbox("🍽 Choose a restaurant", restaurant_options)
            selected_restaurant_data = next((r for r in restaurants if r.get('name') == selected_restaurant), None)
            if selected_restaurant_data:
                restaurant_lat, restaurant_lon = float(selected_restaurant_data['lat']), float(selected_restaurant_data['lon'])
                st.write(f"📍 Restaurant location: **Lat: {restaurant_lat}, Lon: {restaurant_lon}**")
                best_route, best_distance = aco_optimize_route((restaurant_lat, restaurant_lon), (lat, lon))
                st.write(f"🚗 Optimized Route Distance: **{best_distance:.2f} km**")
                
                # 🔹 Calculate Carbon Emissions
                carbon_emissions = calculate_carbon_footprint(best_distance)
                st.write(f"🌍 Estimated Carbon Emissions: **{carbon_emissions:.2f} grams CO2**")

                st.success(f"🎉 Best optimized route selected!")

                # Create a new Folium map centered at the restaurant
                optimized_map = folium.Map(location=[restaurant_lat, restaurant_lon], zoom_start=14)

                # Add markers for the restaurant and delivery location
                folium.Marker([restaurant_lat, restaurant_lon], tooltip="Restaurant", icon=folium.Icon(color="green")).add_to(optimized_map)
                folium.Marker([lat, lon], tooltip="Delivery Location", icon=folium.Icon(color="red")).add_to(optimized_map)

                # Plot the optimized route on the map
                route_coordinates = [(restaurant_lat, restaurant_lon)] + best_route + [(lat, lon)]  # Include start and end points

                folium.PolyLine(route_coordinates, color="blue", weight=5, opacity=0.8).add_to(optimized_map)

                # Display the map in Streamlit
                st_folium(optimized_map, width=725, height=500)
        else:
            st.warning("⚠️ No nearby restaurants found.")
    else:
        st.error("⚠️ Invalid location. Please select again.")
else:
    st.error("⚠️ Please select a location on the map.")
