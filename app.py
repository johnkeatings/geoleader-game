import streamlit as st
from streamlit_folium import st_folium
import folium
import math
import datetime
import gspread
import pandas as pd
import random

# --- 1. GOOGLE SHEETS AUTOMATION BACKEND ---
def get_all_scores_df():
    """Helper to fetch the master dataframe from the summary sheet."""
    try:
        # CONFIGURED FOR LOCAL VS CODE WORKSPACE
        gc = gspread.service_account_from_dict(st.secrets["gspread"])
        worksheet = gc.open("GeoLeader Database").worksheet("Master_Scores")
        all_records = worksheet.get_all_records()
        if not all_records:
            return pd.DataFrame(columns=['Date', 'Player', 'Score'])
        
        df = pd.DataFrame(all_records)
        df['Score'] = pd.to_numeric(df['Score'], errors='coerce')
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime("%Y-%m-%d")
        return df.dropna(subset=['Score', 'Date'])
    except Exception as e:
        return pd.DataFrame(columns=['Date', 'Player', 'Score'])

def push_full_game_data(player_name, final_score, detailed_rounds):
    """Logs data to both sheets simultaneously in a relational manner."""
    try:
        # CONFIGURED FOR LOCAL VS CODE WORKSPACE
        gc = gspread.service_account_from_dict(st.secrets["gspread"])
        sheet = gc.open("GeoLeader Database") 
        today_date = datetime.date.today().strftime("%Y-%m-%d")
        
        # A. Append to Master Summary Sheet
        master_ws = sheet.worksheet("Master_Scores")
        master_ws.append_row([today_date, player_name, final_score])
        
        # B. Append to Detailed Round Breakdowns Sheet
        round_ws = sheet.worksheet("Round_Details")
        round_rows = []
        for r in detailed_rounds:
            round_rows.append([
                today_date, 
                player_name, 
                r['round'], 
                r['target_city'], 
                r['distance_km'], 
                r['points_earned']
            ])
        round_ws.append_rows(round_rows)
        return True
    except Exception as e:
        st.error(f"Database Sync Error: {e}")
        return False

# --- 2. ANTI-CHEAT ENGINE ---
def has_user_played_today(player_name):
    """Returns True if the player already has a score logged for today."""
    df = get_all_scores_df()
    if df.empty:
        return False
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    played_today = df[(df['Date'] == today_str) & (df['Player'] == player_name)]
    return len(played_today) > 0

# --- 3. TIMEFRAME LEADERBOARDS ---
def get_leaderboards():
    """Generates filtered DataFrames for Daily, Weekly, and Monthly tracking."""
    df = get_all_scores_df()
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    
    if df.empty:
        return None, None, None

    # Daily
    daily_df = df[df['Date'] == today_str].sort_values(by='Score', ascending=False).reset_index(drop=True)
    daily_df.index = daily_df.index + 1
    daily_table = daily_df[['Player', 'Score']] if not daily_df.empty else pd.DataFrame()

    # Weekly
    today = datetime.date.today()
    last_7_days = (today - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    weekly_filter = df[df['Date'] >= last_7_days]
    weekly_df = weekly_filter.groupby('Player')['Score'].max().reset_index()
    weekly_df = weekly_df.sort_values(by='Score', ascending=False).reset_index(drop=True)
    weekly_df.index = weekly_df.index + 1
    weekly_table = weekly_df if not weekly_df.empty else pd.DataFrame()

    # Monthly
    last_30_days = (today - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    monthly_filter = df[df['Date'] >= last_30_days]
    monthly_df = monthly_filter.groupby('Player')['Score'].max().reset_index()
    monthly_df = monthly_df.sort_values(by='Score', ascending=False).reset_index(drop=True)
    monthly_df.index = monthly_df.index + 1
    monthly_table = monthly_df if not monthly_df.empty else pd.DataFrame()

    return daily_table, weekly_table, monthly_table

# --- 4. ADVANCED LEAGUE ANALYTICS ---
def get_historical_analytics():
    """Processes historical records to calculate daily champions and running tallies."""
    df = get_all_scores_df()
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    idx_max = df.groupby('Date')['Score'].idxmax()
    daily_winners_df = df.loc[idx_max].sort_values(by='Date', ascending=False).reset_index(drop=True)
    
    crown_counts = daily_winners_df['Player'].value_counts().reset_index()
    crown_counts.columns = ['Player', 'Total Wins 👑']
    
    avg_scores = df.groupby('Player')['Score'].mean().round(0).reset_index()
    avg_scores.columns = ['Player', 'Avg Score 🎯']
    
    hall_of_fame = pd.merge(crown_counts, avg_scores, on='Player', how='outer').fillna(0)
    hall_of_fame['Total Wins 👑'] = hall_of_fame['Total Wins 👑'].astype(int)
    hall_of_fame = hall_of_fame.sort_values(by='Total Wins 👑', ascending=False).reset_index(drop=True)
    hall_of_fame.index = hall_of_fame.index + 1
    
    daily_winners_log = daily_winners_df[['Date', 'Player', 'Score']].rename(columns={'Player': 'Daily Champion 👑', 'Score': 'Winning Score'})
    
    return hall_of_fame, daily_winners_log

# --- 5. HAVERSINE MATH ENGINE ---
def calculate_geoleader_score(user_lat, user_lng, target_lat, target_lng):
    rlat1, rlng1 = math.radians(user_lat), math.radians(user_lng)
    rlat2, rlng2 = math.radians(target_lat), math.radians(target_lng)
    dlat, dlng = rlat2 - rlat1, rlng2 - rlng1
    a = math.sin(dlat/2)**2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlng/2)**2
    distance_km = 2 * 6371 * math.asin(math.sqrt(a))
    
    max_score = 5000
    penalty_per_km = 1.5
    final_score = max_score - (distance_km * penalty_per_km)
    return max(0, round(final_score)), round(distance_km)

# --- 6. MASTER GEOGRAPHY POOL ---
GLOBAL_CITY_POOL = [
    # --- Americas ---
    {"city": "New York City, USA", "lat": 40.7128, "lng": -74.0060},
    {"city": "Los Angeles, USA", "lat": 34.0522, "lng": -118.2437},
    {"city": "Chicago, USA", "lat": 41.8781, "lng": -87.6298},
    {"city": "Vancouver, Canada", "lat": 49.2827, "lng": -123.1207},
    {"city": "Toronto, Canada", "lat": 43.6532, "lng": -79.3832},
    {"city": "Mexico City, Mexico", "lat": 19.4326, "lng": -99.1332},
    {"city": "Havana, Cuba", "lat": 23.1136, "lng": -82.3666},
    {"city": "Bogota, Colombia", "lat": 4.7110, "lng": -74.0721},
    {"city": "Lima, Peru", "lat": -12.0464, "lng": -77.0428},
    {"city": "Santiago, Chile", "lat": -33.4489, "lng": -70.6693},
    {"city": "Buenos Aires, Argentina", "lat": -34.6037, "lng": -58.3816},
    {"city": "Rio de Janeiro, Brazil", "lat": -22.9068, "lng": -43.1729},
    {"city": "Sao Paulo, Brazil", "lat": -23.5558, "lng": -46.6396},
    {"city": "Quito, Ecuador", "lat": -0.1807, "lng": -78.4678},
    {"city": "Caracas, Venezuela", "lat": 10.4806, "lng": -66.9036},
    {"city": "Panama City, Panama", "lat": 8.9824, "lng": -79.5199},
    {"city": "Anchorage, Alaska, USA", "lat": 61.2181, "lng": -149.9003},
    {"city": "Nuuk, Greenland", "lat": 64.1743, "lng": -51.7373},
    {"city": "Honolulu, Hawaii, USA", "lat": 21.3069, "lng": -157.8583},
    {"city": "San Jose, Costa Rica", "lat": 9.9281, "lng": -84.0907},
    # --- Europe ---
    {"city": "London, UK", "lat": 51.5074, "lng": -0.1278},
    {"city": "Paris, France", "lat": 48.8566, "lng": 2.3522},
    {"city": "Rome, Italy", "lat": 41.9028, "lng": 12.4964},
    {"city": "Berlin, Germany", "lat": 52.5200, "lng": 13.4050},
    {"city": "Madrid, Spain", "lat": 40.4168, "lng": -3.7038},
    {"city": "Lisbon, Portugal", "lat": 38.7223, "lng": -9.1393},
    {"city": "Athens, Greece", "lat": 37.9838, "lng": 23.7275},
    {"city": "Amsterdam, Netherlands", "lat": 52.3676, "lng": 4.9041},
    {"city": "Reykjavik, Iceland", "lat": 64.1466, "lng": -21.9426},
    {"city": "Oslo, Norway", "lat": 59.9139, "lng": 10.7522},
    {"city": "Stockholm, Sweden", "lat": 59.3293, "lng": 18.0686},
    {"city": "Helsinki, Finland", "lat": 60.1699, "lng": 24.9384},
    {"city": "Moscow, Russia", "lat": 55.7558, "lng": 37.6173},
    {"city": "Vienna, Austria", "lat": 48.2082, "lng": 16.3738},
    {"city": "Warsaw, Poland", "lat": 52.2297, "lng": 21.0122},
    {"city": "Prague, Czech Republic", "lat": 50.0755, "lng": 14.4378},
    {"city": "Dublin, Ireland", "lat": 53.3498, "lng": -6.2603},
    {"city": "Budapest, Hungary", "lat": 47.4979, "lng": 19.0402},
    {"city": "Torshavn, Faroe Islands", "lat": 62.0107, "lng": -6.7741},
    {"city": "Svalbard, Norway", "lat": 78.2232, "lng": 15.6469},
    # --- Africa ---
    {"city": "Cairo, Egypt", "lat": 30.0444, "lng": 31.2357},
    {"city": "Cape Town, South Africa", "lat": -33.9249, "lng": 18.4241},
    {"city": "Johannesburg, South Africa", "lat": -26.2041, "lng": 28.0473},
    {"city": "Nairobi, Kenya", "lat": -1.2921, "lng": 36.8219},
    {"city": "Casablanca, Morocco", "lat": 33.5731, "lng": -7.5898},
    {"city": "Lagos, Nigeria", "lat": 6.5244, "lng": 3.3792},
    {"city": "Accra, Ghana", "lat": 5.6037, "lng": -0.1870},
    {"city": "Addis Ababa, Ethiopia", "lat": 9.0300, "lng": 38.7400},
    {"city": "Dakar, Senegal", "lat": 14.7167, "lng": -17.4677},
    {"city": "Antananarivo, Madagascar", "lat": -18.8792, "lng": 47.5079},
    {"city": "Tunis, Tunisia", "lat": 36.8065, "lng": 10.1815},
    {"city": "Algiers, Algeria", "lat": 36.7538, "lng": 3.0588},
    {"city": "Luanda, Angola", "lat": -8.8390, "lng": 13.2894},
    {"city": "Dar es Salaam, Tanzania", "lat": -6.7924, "lng": 39.2083},
    {"city": "Timbuktu, Mali", "lat": 16.7666, "lng": -3.0026},
    {"city": "Khartoum, Sudan", "lat": 15.5007, "lng": 32.5599},
    {"city": "Tripoli, Libya", "lat": 32.8872, "lng": 13.1913},
    {"city": "Maputo, Mozambique", "lat": -25.9692, "lng": 32.5732},
    {"city": "Harare, Zimbabwe", "lat": -17.8252, "lng": 31.0335},
    {"city": "Port Louis, Mauritius", "lat": -20.1609, "lng": 57.5012},
    # --- Asia & Middle East ---
    {"city": "Tokyo, Japan", "lat": 35.6762, "lng": 139.6503},
    {"city": "Seoul, South Korea", "lat": 37.5665, "lng": 126.9780},
    {"city": "Beijing, China", "lat": 39.9042, "lng": 116.4074},
    {"city": "Shanghai, China", "lat": 31.2304, "lng": 121.4737},
    {"city": "Hong Kong", "lat": 22.3193, "lng": 114.1694},
    {"city": "Bangkok, Thailand", "lat": 13.7563, "lng": 100.5018},
    {"city": "Singapore", "lat": 1.3521, "lng": 103.8198},
    {"city": "Mumbai, India", "lat": 19.0760, "lng": 72.8777},
    {"city": "Delhi, India", "lat": 28.6139, "lng": 77.2090},
    {"city": "Jakarta, Indonesia", "lat": -6.2088, "lng": 106.8456},
    {"city": "Manila, Philippines", "lat": 14.5995, "lng": 120.9842},
    {"city": "Kuala Lumpur, Malaysia", "lat": 3.1390, "lng": 101.6869},
    {"city": "Hanoi, Vietnam", "lat": 21.0285, "lng": 105.8542},
    {"city": "Dubai, UAE", "lat": 25.2048, "lng": 55.2708},
    {"city": "Riyadh, Saudi Arabia", "lat": 24.7136, "lng": 46.6753},
    {"city": "Jerusalem, Israel", "lat": 31.7683, "lng": 35.2137},
    {"city": "Istanbul, Turkey", "lat": 41.0082, "lng": 28.9784},
    {"city": "Tehran, Iran", "lat": 35.6892, "lng": 51.3890},
    {"city": "Baghdad, Iraq", "lat": 33.3152, "lng": 44.3661},
    {"city": "Ulaanbaatar, Mongolia", "lat": 47.8864, "lng": 106.9057},
    # --- Oceania & Remote ---
    {"city": "Sydney, Australia", "lat": -33.8688, "lng": 151.2093},
    {"city": "Melbourne, Australia", "lat": -37.8136, "lng": 144.9631},
    {"city": "Perth, Australia", "lat": -31.9505, "lng": 115.8605},
    {"city": "Auckland, New Zealand", "lat": -36.8485, "lng": 174.7633},
    {"city": "Wellington, New Zealand", "lat": -41.2865, "lng": 174.7762},
    {"city": "Fiji (Suva)", "lat": -18.1248, "lng": 178.4501},
    {"city": "Papua New Guinea (Port Moresby)", "lat": -9.4438, "lng": 147.1803},
    {"city": "Antarctica (McMurdo Station)", "lat": -77.8460, "lng": 166.6660},
    {"city": "Maldives (Male)", "lat": 4.1755, "lng": 73.5093},
    {"city": "Seychelles (Victoria)", "lat": -4.6191, "lng": 55.4513},
    {"city": "Galapagos Islands, Ecuador", "lat": -0.9538, "lng": -90.9656},
    {"city": "Tahiti, French Polynesia", "lat": -17.6509, "lng": -149.4260},
    {"city": "Easter Island, Chile", "lat": -27.1127, "lng": -109.3497},
    {"city": "Guam, USA", "lat": 13.4443, "lng": 144.7937},
    {"city": "Samoa (Apia)", "lat": -13.8333, "lng": -171.7667},
    {"city": "Vanuatu (Port Vila)", "lat": -17.7333, "lng": 168.3213},
    {"city": "Mauritius", "lat": -20.3484, "lng": 57.5522},
    {"city": "Azores, Portugal", "lat": 37.7412, "lng": -25.6756},
    {"city": "Canary Islands, Spain", "lat": 28.2916, "lng": -16.6291},
    {"city": "Solomon Islands (Honiara)", "lat": -9.4333, "lng": 159.9500}
]

# --- 7. DAILY SEED ALGORITHM ---
today_str = datetime.date.today().strftime("%Y-%m-%d")
local_random = random.Random(today_str)
DAILY_CITIES = local_random.sample(GLOBAL_CITY_POOL, 5)

# --- 8. STATE ENGINE ---
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "current_round" not in st.session_state:
    st.session_state.current_round = 0
if "total_score" not in st.session_state:
    st.session_state.total_score = 0
if "game_round_history" not in st.session_state:
    st.session_state.game_round_history = []
if "has_guessed" not in st.session_state:
    st.session_state.has_guessed = False
if "last_guess_lat" not in st.session_state:
    st.session_state.last_guess_lat = None
if "last_guess_lng" not in st.session_state:
    st.session_state.last_guess_lng = None
if "score_submitted" not in st.session_state:
    st.session_state.score_submitted = False

# --- 9. INTERFACE CONFIG ---
st.set_page_config(page_title="GeoLeader", page_icon="📍", layout="wide")

st.markdown("""
<style>
    .folium-container { 
        border-radius: 50% !important; 
        border: 8px solid #333; 
        overflow: hidden; 
        margin: 20px auto; 
        /* Ensure the map stays circular even during interaction */
        clip-path: circle(50%); 
    }
    </style>
    """, unsafe_allow_html=True)

# --- PROFILE LOGIN SCREEN ---
if st.session_state.current_user is None:
    st.title("📱 Welcome to GeoLeader Leagues")
    
    col_left, col_right = st.columns([1, 1.5])
    
    with col_left:
        st.subheader("Select Profile:")
        selected_player = st.selectbox("Who is playing?", ["Eric", "Elliott", "Mark", "Nate", "John"])
        st.caption(f"🗓️ Map Seed: **{today_str}**")
        st.caption("🔒 *Note: PIN verification for profiles coming soon.*")
        
        already_played = has_user_played_today(selected_player)
        
        if already_played:
            st.error(f"⚠️ {selected_player} has locked in their score for today!")
            st.button("Start Game 🚀", disabled=True, use_container_width=True)
        else:
            if st.button("Start Game 🚀", use_container_width=True):
                st.session_state.current_user = selected_player
                st.rerun()
                
        st.markdown("---")
        st.subheader("📊 League Analytics (All-Time)")
        hall_of_fame_df, daily_log_df = get_historical_analytics()
        
        if not hall_of_fame_df.empty:
            st.markdown("**Crown Standings & Consistency**")
            st.dataframe(hall_of_fame_df, use_container_width=True)
            
            st.markdown("**Historical Daily Winner Log**")
            st.dataframe(daily_log_df, use_container_width=True, hide_index=True)
        else:
            st.info("Accumulate more match histories to generate the Hall of Fame data!")
            
    with col_right:
        st.subheader("🏆 Current Tournament Standings")
        daily_t, weekly_t, monthly_t = get_leaderboards()
        
        tab1, tab2, tab3 = st.tabs(["⚡ Daily", "📅 Weekly", "🌕 Monthly"])
        
        with tab1:
            st.markdown("**Today's Active Battles**")
            if daily_t is not None and not daily_t.empty:
                st.dataframe(daily_t, use_container_width=True, column_config={"Score": st.column_config.NumberColumn(format="%d pts")})
            else:
                st.info("Nobody has submitted a run today yet!")
                
        with tab2:
            st.markdown("**Peak Scores (Last 7 Days)**")
            if weekly_t is not None and not weekly_t.empty:
                st.dataframe(weekly_t, use_container_width=True, column_config={"Score": st.column_config.NumberColumn(format="%d pts")})
            else:
                st.info("No scores in the last 7 days.")
                
        with tab3:
            st.markdown("**Peak Scores (Last 30 Days)**")
            if monthly_t is not None and not monthly_t.empty:
                st.dataframe(monthly_t, use_container_width=True, column_config={"Score": st.column_config.NumberColumn(format="%d pts")})
            else:
                st.info("No scores in the last 30 days.")

# --- MAIN GAME PLAY LOOP ---
else:
    _, game_center_col, _ = st.columns([1, 4, 1])
    
    with game_center_col:
        st.title("🏆 Daily GeoLeader Challenge")
        
        if st.session_state.current_round >= len(DAILY_CITIES):
            st.header("🏁 Game Over!")
            st.subheader(f"Final Score: {st.session_state.total_score:,} / 25,000 pts")
            
            if not st.session_state.score_submitted:
                with st.spinner("Logging score and round breakdowns securely..."):
                    success = push_full_game_data(
                        st.session_state.current_user, 
                        st.session_state.total_score,
                        st.session_state.game_round_history
                    )
                    if success:
                        st.session_state.score_submitted = True
                        st.success(f"🎉 All deep stats synced for {st.session_state.current_user}!")
                        st.balloons()
            
            # --- CONDENSED SHARE SCORE CLIPBOARD ENGINE ---
            st.markdown("### 📣 Share Your Results")
            
            # Ultra condensed Wordle style line layout
            emojis_line = ""
            for r in st.session_state.game_round_history:
                emojis_line += "🟩" if r['points_earned'] >= 4500 else ("🟨" if r['points_earned'] >= 3000 else "🟥")
                
            summary_lines = [
                f"📍 GeoLeader ({today_str})",
                f"👤 {st.session_state.current_user}: {st.session_state.total_score:,} pts",
                emojis_line,
                "www.geoleader.streamlit.app"
            ]
            
            raw_js_text = "\\n".join(summary_lines)

            components_html = f"""
            <script>
            function copyToClipboard() {{
                const el = document.createElement('textarea');
                el.value = `{raw_js_text}`;
                document.body.appendChild(el);
                el.select();
                document.execCommand('copy');
                document.body.removeChild(el);
                alert('🏆 Score copied! Send it over to the group chat!');
            }}
            </script>
            <button onclick="copyToClipboard()" style="
                width: 100%; 
                background-color: #FF4B4B; 
                color: white; 
                padding: 12px 24px; 
                border: none; 
                border-radius: 8px; 
                font-size: 16px; 
                font-weight: bold;
                cursor: pointer;
                box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
            ">📋 Copy Share Text</button>
            """
            st.components.v1.html(components_html, height=65)
            
            st.markdown("---")
            st.write("### Today's Performance Breakdown:")
            for r in st.session_state.game_round_history:
                st.write(f"📍 Round {r['round']} ({r['target_city']}): **{r['points_earned']:,} pts** ({r['distance_km']:,} km miss)")
                
            if st.button("Return to Hub", use_container_width=True):
                st.session_state.current_user = None
                st.session_state.current_round = 0
                st.session_state.total_score = 0
                st.session_state.game_round_history = []
                st.session_state.has_guessed = False
                st.session_state.score_submitted = False
                st.rerun()

        else:
            round_num = st.session_state.current_round
            active_target = DAILY_CITIES[round_num]
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"👤 Player: **{st.session_state.current_user}**")
                st.markdown(f"🎯 Round {round_num + 1} of 5 — Find: **{active_target['city']}**")
            with col2:
                st.markdown("### 📈 Running Total")
                st.markdown(f"**{st.session_state.total_score:,} pts**")

            # GUESSING PHASE (ORBITAL GLOBE SAT RENDER)
            if not st.session_state.has_guessed:
                # Centered over the middle of the planet at Zoom 1 to create an orbital visual capsule look
                m = folium.Map(
                    location=[15.0, -25.0], 
                    zoom_start=2, 
                    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                    attr="Esri World Imagery",
                    zoom_control=True,      # Enable zoom +/- buttons
                    scrollWheelZoom=True    # Enable mouse wheel scrolling
                )
                map_click_data = st_folium(
                    m, 
                    width=900, 
                    height=500, 
                    key=f"map_r_{round_num}"
                )
                
                if map_click_data and map_click_data.get("last_clicked"):
                    click_lat = map_click_data["last_clicked"]["lat"]
                    click_lng = map_click_data["last_clicked"]["lng"]
                    
                    st.session_state.last_guess_lat = click_lat
                    st.session_state.last_guess_lng = click_lng
                    
                    score, distance = calculate_geoleader_score(click_lat, click_lng, active_target['lat'], active_target['lng'])
                    st.session_state.latest_score = score
                    st.session_state.latest_distance = distance
                    st.session_state.has_guessed = True
                    st.rerun()
                    
            # REVEAL PHASE
            else:
                mid_lat = (st.session_state.last_guess_lat + active_target['lat']) / 2
                mid_lng = (st.session_state.last_guess_lng + active_target['lng']) / 2
                
                m_reveal = folium.Map(
                    location=[mid_lat, mid_lng], 
                    zoom_start=2, 
                    tiles="https://{s}.basemaps.cartocdn.com/rastertiles/light_nolabels/{z}/{x}/{y}.png",
                    attr="CartoDB Positron No Labels"
                )
                
                folium.Marker([st.session_state.last_guess_lat, st.session_state.last_guess_lng], tooltip="Your Guess", icon=folium.Icon(color="red", icon="crosshair", prefix="fa")).add_to(m_reveal)
                folium.Marker([active_target['lat'], active_target['lng']], tooltip=active_target['city'], icon=folium.Icon(color="green", icon="check", prefix="fa")).add_to(m_reveal)
                folium.PolyLine(locations=[[st.session_state.last_guess_lat, st.session_state.last_guess_lng], [active_target['lat'], active_target['lng']]], color="black", weight=3, dash_array="5, 10").add_to(m_reveal)
                
                st_folium(m_reveal, width=900, height=500, key=f"map_result_{round_num}")

            if st.session_state.has_guessed:
                st.markdown("---")
                st.metric("Points Earned", f"+{st.session_state.latest_score:,} pts")
                st.write(f"You missed by {st.session_state.latest_distance:,} km.")
                
                if st.button("Next Round ➡️", use_container_width=True):
                    st.session_state.game_round_history.append({
                        "round": round_num + 1,
                        "target_city": active_target['city'],
                        "distance_km": st.session_state.latest_distance,
                        "points_earned": st.session_state.latest_score
                    })
                    
                    st.session_state.total_score += st.session_state.latest_score
                    st.session_state.current_round += 1
                    st.session_state.has_guessed = False
                    st.session_state.last_guess_lat = None
                    st.session_state.last_guess_lng = None
                    st.rerun()
