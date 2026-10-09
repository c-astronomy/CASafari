import datetime as dt
import math
import time
import subprocess
import pycurl
import os
import random
import json
import redis
import threading
from io import BytesIO

def setBool():
    global auto_safari
    auto_safari = False

def main(r):

    global auto_safari, auto_safari_idle_threshold, terminalMode, loop_delay, available_targets  #tmptarget_ra, 

    #load config
    load_config()


    #Refreshed objectlist
    objectlist = load_and_format_targets()
    #First filtered list
    available_targets = filter_targets(objectlist, obs_lat, obs_lon, min_altitude, max_altitude, min_azimuth, max_azimuth)
    #current / last target check for safari to not go to same target draw_distance_to_altitude_limits
    last_target_name = None

    #Print Ascii on startup
    print(logoAscii)

    listener_thread = threading.Thread(target=redis_listener, args=(r,))
    listener_thread.daemon = True # Allows the main program to exit without waiting for the thread
    listener_thread.start()

    print("[PYTHON MAIN] Subscription thread started. Continuing main program logic...")

    #Not sure if i want to load everythin here yet

    while True :
        load_config() #Not sure this is good idea, spamming reads

        if terminalMode :
            draw_terminal(available_targets)

        #Trigger auto safari test
        #Fetch NINA status from Redis

        status_raw = r.get("nina:status")
        nina_busy = False
        if status_raw:
            try:
                status_data = json.loads(status_raw)
                nina_busy = status_data.get("busy", False)
            except Exception:
                pass


        if nina_busy:
            r.set("nina:last_user_action", time.time())



        #print("Debug 0")
        last_action = r.get("nina:last_user_action")
        #print("Debug 1")
        if last_action:
            seconds_since_user = time.time() - float(last_action)
            #print("Debug 2")
            if seconds_since_user > auto_safari_idle_threshold :
                #print("Debug 3")
                # print(f"🤫 User was active {int(seconds_since_user)}s ago. Waiting...")
                if auto_safari == False :
                    r.publish("nina:speech", f"Starting automatic safari")

                auto_safari = True

                print(f"Starting auto Safari")
                #print(f"[CASA] 🤫 Starting auto Safari")
            else :
                auto_safari = False
            #    time.sleep(20)

                #r.publish("nina:speech", f"Stopping automatic safari")
                print(f"Stopping auto Safari")
                #print(f"[CASA] 🤫 Stopping auto Safari")
                #r.publish("nina:speech", f"Stopping automatic safari")
            #    continue




        if auto_safari:

            # Check the "User Interaction" timer

            objectlist = load_and_format_targets()
            available_targets = filter_targets(objectlist, obs_lat, obs_lon, min_altitude, max_altitude, min_azimuth, max_azimuth)
            
            if available_targets:

                #Exclude last target if more than one is available
                candidate_targets = [t for t in available_targets if t.get('name') != last_target_name]

                if not candidate_targets:
                    candidate_targets = available_targets



                #safariTarget = random.choice(available_targets)
                safariTarget = random.choice(candidate_targets)
                last_target_name = safariTarget.get('name') #Update tracker


                ra_deg, dec_deg = convert_for_slew(
                    safariTarget.get('ra', 0),
                    safariTarget.get('ra_min', 0),
                    safariTarget.get('dec', 0),
                    safariTarget.get('dec_min', 0)
                )



                # 1. Prepare the exact payload NINA needs
                payload = {
                    "action": "slew",
                    "name": safariTarget.get('name', 'Unknown Safari Target'),
                    "ra": safariTarget.get('ra', 0),
                    "ra_min": safariTarget.get('ra_min', 0),
                    "dec": safariTarget.get('dec', 0),
                    "dec_min": safariTarget.get('dec_min', 0),
                    "is_safari": True  # Useful flag for logging
                }

                #Twitch caht bot message send test
                #r.rpush("twitch:chat_queue", f"CASafari is slewing to {payload['name']}")
                #r.rpush("twitch:chat_queue", f"CASafari is slewing to ")
                #DO I NEED THIS ONE RIGHT NOW??
                r.publish("twitch:chat_queue", f"CASafari is slewing to {payload['name']}")



                #TTS TRIGGER TEST, THIS ONE WORKS  BUT I DONT NEED IT ATM SINCE INSIDE NINA I HAVE TTS TRIGGER
                #r.publish("nina:speech", f"CASafari is slewing to {payload['name']}")
                #r.publish("nina:speech", f"CASafari is starting an {exposure_time} second exposure of {payload['name']}")



                # 2. Save for reference (Web GUI)
                r.set("nina:current_safari_target", json.dumps(payload))

                # 3. Trigger NINA immediately
                r.publish("nina:commands", json.dumps(payload))


                print(f"Safari triggered! Slewing to: {payload['name']}")
            else:
                print(f"Safari: No targets visible right now.")




        #time.sleep(loop_delay)






        time.sleep(loop_delay) #60 original, was using 20



def load_config():
    """Reads configuration limits from config.json or falls back to defaults."""
    global min_altitude, max_altitude, min_azimuth, max_azimuth, obs_lat, obs_lon
   

    print("[PYTHON] READ config")

    # Default fallbacks
    defaults = {
        "min_altitude": 30,
        "max_altitude": 75,
        "min_azimuth": 230,
        "max_azimuth": 350,
        "obs_lon": 16.4903,
        "obs_lat": 59.6
    }

    if os.path.exists('casafari-config.json'):
        try:
            with open('casafari-config.json', 'r') as f:
                config = json.load(f)
                min_altitude = float(config.get('min_altitude', config.get('AltLim', defaults['min_altitude'])))
                max_altitude = float(config.get('max_altitude', config.get('AltLimMax', defaults['max_altitude'])))
                min_azimuth = float(config.get('min_azimuth', config.get('AzLim', defaults['min_azimuth'])))
                max_azimuth = float(config.get('max_azimuth', config.get('AzLimMax', defaults['max_azimuth'])))
                obs_lat = float(config.get('lat', defaults['obs_lat']))
                obs_lon = float(config.get('lon', defaults['obs_lon']))
                return
        except Exception as e:
            print(f"⚠️ Error reading config.json: {e}")

    # Fallback if config.json is missing or invalid
    min_altitude = defaults['min_altitude']
    max_altitude = defaults['max_altitude']
    min_azimuth = defaults['min_azimuth']
    max_azimuth = defaults['max_azimuth']
    obs_lat = defaults['obs_lat']
    obs_lon = defaults['obs_lon']








#Load list on startup

def load_and_format_targets():
    """
    Reads the JSON file written by the webserver, updates the global list.
    """
    global objectlist  # Ensure we update the list the rest of the script uses

    # 1. Fallback list in case the file is missing or corrupted
    fallback_list = [
        { "ra": 5, "ra_min": 42, "dec": -2, "dec_min": 26, "name": "fallback", "trigger": "!slew_fallback" },
        { "ra": 21, "ra_min": 0, "dec": 57, "dec_min": 0, "name": "Elephants trunk nebula", "trigger": "!slew_trunk" },
        { "ra": 0, "ra_min": 44, "dec": 41, "dec_min": 16, "name": "Andromeda galaxy", "trigger": "!slew_andromeda" }
    ]

    if not os.path.exists('targetlist.json'):
        print("⚠️ targetlist.json not found. Using fallback.")
        objectlist = fallback_list
        return fallback_list

    try:
        with open('targetlist.json', 'r') as f:
            data = json.load(f)
            
            # If the file is just an empty list []
            if not data:
                objectlist = fallback_list
                return fallback_list
            
            new_objectlist = []
            
            for t in data:
                new_objectlist.append({
                    "ra": t.get('ra', 0),
                    "ra_min": t.get('ra_min', 0),
                    "dec": t.get('dec', 0),
                    "dec_min": t.get('dec_min', 0),
                    "name": t.get('name', 'Unknown'),
                    "trigger": t.get('trigger', '')
                })
            
            # Update the global variable and return it
            #objectlist = new_objectlist
            print(f"Successfully loaded {len(new_objectlist)} targets from JSON.")
            return new_objectlist

    except Exception as e:
        print(f"❌ Error loading targetlist.json: {e}")
        objectlist = fallback_list
        return fallback_list




# --- 1. Define the Subscription Function (The worker thread's job) ---
def redis_listener(r):
    """Function to run in a separate thread, dedicated to listening."""
    pubsub = r.pubsub()
    pubsub.subscribe('twitch:updates')

    print("[PYTHON LISTENER] Thread started. Waiting for messages...")
    
    # This loop blocks only the thread it is running in
    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                #data = json.loads(message['data'].decode('utf-8')) # Use .decode if needed
                data = json.loads(message['data']) # Use .decode if needed
                print(f"[PYTHON] READ data from Redis: {data}")
                #print(f"[{time.strftime('%H:%M:%S')}] Tl-ti-nina: READ data from Redis: {data}")
                # You can now process data or place it in a shared queue
                if data == "!list" :
                    load_config()
                    objectlist = load_and_format_targets()
                    available_targets = filter_targets(objectlist, obs_lat, obs_lon, min_altitude, max_altitude, min_azimuth, max_azimuth)
#                   send_data_to_node(available_targets)
                    #auto_safari = False #Maybe do this a nicer way later because flow is hard to follow
                    #print("[PYTHON] Check if !list gets triggered.")
                    # Save to Redis key as JSON string for the bot to read
                    r.set("nina:available_targets", json.dumps(available_targets))

                    # Publish a ready signal so the bot knows it can look now
                    r.publish("nina:commands", "list_ready")
                    print(f"[CASA] Filtered list saved to Redis. Found {len(available_targets)} targets.")



                if data == "!safari" :
                    
                    auto_safari = True
                    #r.publish("nina:speech", "Automatic safari enabled")
                    print("[PYTHON] Auto Safari enabled via Redis command")

                if data == "!stopsafari" :
                    auto_safari = False
                    r.set("nina:last_user_action", time.time()) #Reset idle timer
                    #r.publish("nina:speech", "Automatic safari stopped")
                    print("[PYTHON] Auto Safari stopped via Redis command")
                    

            except Exception as e:
                print(f"[PYTHON LISTENER] Error processing message: {e}")




def convert_for_slew(ra, ra_min, dec, dec_min):
    ra_total_hours = float(ra) + (float(ra_min) / 60.0)
    slewRa_degrees = ra_total_hours * 15.0 # Hours for NINA

    dec_d = float(dec)
    dec_m = float(dec_min)
    
    is_negative = dec_d < 0 or math.copysign(1.0, dec_d) < 0 #math.copysign

    if is_negative:
#    if str(dec).startswith('-') or dec_d <0:
        slewDec_degrees = dec_d - (dec_m / 60.0)
    else:
        slewDec_degrees = dec_d + (dec_m / 60.0)

    return slewRa_degrees, slewDec_degrees



def draw_terminal(available_targets):
    #Clear terminal window 
    os.system('cls' if os.name == 'nt' else 'clear')
    print(logoAscii)
    #print(f"Current UTC Time: {current_utc.strftime('%Y-%m-%d %H:%M:%S')}")
    #print(f"Current LST: {lst_formatted}")
    print("-" * 50)
    print(f"Target FILTER: Between altitude {min_altitude}° and {max_altitude}°, azimuth {min_azimuth}° to {max_azimuth}°")
    print(f"The following targets are currently above {min_altitude}° altitude and within the azimuth range of {min_azimuth}° to {max_azimuth}°:")
    draw_distance_to_altitude_limits(available_targets)     
    if available_targets:
        for target in available_targets:
                print(f" - {target['name']} (RA: {target['ra']}h {target['ra_min']}m, Dec: {target['dec']}° {target['dec_min']}m, Alt: {target['altitude']}°, Az: {target['azimuth']}°)")
    else:
        print(f"No targets are currently available that meet the altitude and azimuth criteria.")
    draw_distance_to_limits(available_targets)  

    


def draw_distance_to_altitude_limits(available_targets):


    filter_limit_low = 30
    filter_limit_high = 75  #180 degreeor should i use 90, i have a preset value now, the real limits, might wanna use them?

    #Temp test to see if visuals etc updates correct
    filter_limit_low = min_altitude
    filter_limit_high = max_altitude

    scale_length = 50
    scale=['-'] * scale_length
    #0.13888 scaling factor
    

    max_input_value = 180 #forgot what this one is, default 180, just scalar total lenght of range maybe?
    max_scale_index = scale_length - 1 
    scale_factor = scale_length / max_input_value


    #Hardcode limit positions
    low_position = int(float(scale_factor * filter_limit_low))
    high_position = int(float(scale_factor * filter_limit_high))

    #extra check so its not longer than scale elements length
    for target in available_targets :

        value = target['altitude']
        converted_alt_value = int(float(value))
        scaled_position = int(float(scale_factor * converted_alt_value))
        if scaled_position <=49 :
            scale[scaled_position]='x'


        scale[low_position]='|' 
        scale[high_position]='|'    


        result = ''.join(scale)

    #print("----|" + "-" * 50 + "|----")
    print(result)
    return 0

def draw_distance_to_limits(available_targets):


    filter_limit_low = 230
    filter_limit_high = 350

    #Test to see if printed correct
    filter_limit_low = min_azimuth
    filter_limit_high = max_azimuth

    scale_length = 50
    scale=['-'] * scale_length
    #0.13888 scaling factor

    max_input_value = 360
    max_scale_index = scale_length - 1 
    scale_factor = scale_length / max_input_value


    #Hardcode limit positions
    low_position = int(float(scale_factor * filter_limit_low))
    high_position = int(float(scale_factor * filter_limit_high))

    #extra check so its not longer than scale elements length
    for target in available_targets :

        value = target['azimuth']
        converted_az_value = int(float(value))
        scaled_position = int(float(scale_factor * converted_az_value))
        if scaled_position <=49 :
            scale[scaled_position]='x'

        
        scale[low_position]='|' 
        scale[high_position]='|'
    
        result = ''.join(scale)

    #print("----|" + "-" * 50 + "|----")
    print(result)
    return 0



def calculate_accurate_lst(longitude_deg):
    """
    Calculates the Local Sidereal Time (LST) for the current moment
    using a high-precision, manual formula.
    
    Args:
        longitude_deg (float): Observer's longitude in degrees. East is positive.

    Returns:
        float: The LST in decimal hours.
    """
    # 1. Get the current time in UTC
    utc_time = dt.datetime.now(dt.timezone.utc)
    
    # 2. Calculate the Julian Date (JD)
    a = math.trunc((14 - utc_time.month) / 12)
    y = utc_time.year + 4800 - a
    m = utc_time.month + 12 * a - 3
    
    jdn = utc_time.day + math.trunc((153 * m + 2) / 5) + 365 * y + math.trunc(y / 4) - math.trunc(y / 100) + math.trunc(y / 400) - 32045
    
    jd = jdn + (utc_time.hour - 12) / 24 + utc_time.minute / 1440 + utc_time.second / 86400

    # 3. Calculate Greenwich Sidereal Time (GST)
    jd_2000 = jd - 2451545.0
    gst_h = (18.697374558 + 24.06570982441908 * jd_2000) % 24

    # 4. Convert GST to Local Sidereal Time (LST) using longitude
    lst_h = (gst_h + longitude_deg / 15) % 24
    
    return lst_h




def calculate_altitude_and_azimuth(ra_h, dec_deg, obs_lat_deg, lst_h):
    """
    Calculates the altitude and azimuth of a celestial object for the given LST.
    """
    ra_rad = math.radians(ra_h * 15)
    dec_rad = math.radians(dec_deg)
    obs_lat_rad = math.radians(obs_lat_deg)
    lst_rad = math.radians(lst_h * 15)
    
    h_rad = lst_rad - ra_rad
    
    sin_a = (math.sin(obs_lat_rad) * math.sin(dec_rad) +
             math.cos(obs_lat_rad) * math.cos(dec_rad) * math.cos(h_rad))
    sin_a = max(-1.0, min(1.0, sin_a))
    
    a_rad = math.asin(sin_a)
    altitude_deg = math.degrees(a_rad)

    y = -math.sin(h_rad) * math.cos(dec_rad)
    x = (math.cos(obs_lat_rad) * math.sin(dec_rad) -
         math.sin(obs_lat_rad) * math.cos(dec_rad) * math.cos(h_rad))
    
    azimuth_rad = math.atan2(y, x)
    azimuth_deg = math.degrees(azimuth_rad)
    azimuth_deg = (azimuth_deg + 360) % 360
    
    return altitude_deg, azimuth_deg



def filter_targets(objectlist, obs_lat, obs_lon, min_altitude_deg, max_altitude_deg, min_azimuth_deg, max_azimuth_deg):
    current_lst_h = calculate_accurate_lst(obs_lon)
    filtered_list = []

    for obj in objectlist:


        try:
            if isinstance(obj, dict):
                # NEW WEB DATA
                ra_h = float(str(obj.get('ra', 0)).replace(',', '.'))
                ra_m = float(str(obj.get('ra_min', 0)).replace(',', '.')) # Grab ra_min
                dec_d = float(str(obj.get('dec', 0)).replace(',', '.'))
                dec_m = float(str(obj.get('dec_min', 0)).replace(',', '.')) # Grab dec_min
                name = obj.get('name', 'Unknown')
                trigger = obj.get('trigger', '')
            else:
                # OLD FALLBACK DATA
                ra_h = float(obj[0])
                ra_m = float(obj[1])
                dec_d = float(obj[2])
                dec_m = float(obj[3])
                name = obj[4]
                trigger = obj[5]
        
            # If we got here, data extraction worked. Now check the math.


            # Ensure your math function uses the TOTAL float value
            ra_total = ra_h + (ra_m / 60.0)
            dec_total = dec_d + (dec_m / 60.0) if dec_d >= 0 else dec_d - (dec_m / 60.0)

            altitude, azimuth = calculate_altitude_and_azimuth(ra_total, dec_total, obs_lat, current_lst_h)
            #altitude, azimuth = calculate_altitude_and_azimuth(ra_h, dec_d, obs_lat, current_lst_h)

        except Exception as e:
                print(f"!!! Error processing target {obj}: {e}")
                continue # Skip this one and move to the next
        
        # FIXED: Changed max_altitude to max_altitude_deg
        if (min_altitude_deg <= altitude <= max_altitude and 
            min_azimuth_deg <= azimuth <= max_azimuth_deg):


            filtered_list.append({
                "name": name,
                "ra": ra_h,
                "ra_min": ra_m,
                "dec": dec_d,
                "dec_min": dec_m,
                "altitude": f"{altitude:.2f}",
                "azimuth": f"{azimuth:.2f}",
                "trigger": trigger
                #"ra_slew": ra_slew,
                #"dec_slew": dec_slew
            })
    return filtered_list


#ASCII ART
logoSimple = "CASafari"

logoAscii = r"""
  ____    _    ____         __            _ 
 / ___|  / \  / ___|  __ _ / _| __ _ _ __(_)
| |     / _ \ \___ \ / _` | |_ / _` | '__| |
| |___ / ___ \ ___) | (_| |  _| (_| | |  | |
 \____/_/   \_\____/ \__,_|_|  \__,_|_|  |_|
"""


# --- Configuration ---
# Your coordinates
obs_lat = 59.6
obs_lon = 16.4903
# Set a minimum altitude threshold (in degrees)
min_altitude = 30   #30
max_altitude = 75   #75 #65 seems to be good for balcony
# Set an azimuth range (in degrees)
# Azimuth: 0° = North, 90° = East, 180° = South, 270° = West
min_azimuth = 230   #230   #300 seems to be good for balcony
max_azimuth = 350   #350
printParsedOuput = True
# Autosafari, go to random targets within the available target list
#SHARED_DATA_LOCK = threading.Lock()
auto_safari = False #Default is False
#Safari autostart timer
auto_safari_idle_threshold = 240 #Default 600   for dev test 60, for steam test 240
#Just a way to protect from re-slews
tmptarget_ra = 0
#Run program as a loop or single shot
loop = True  #Default is on, ill try one with off
loop_delay = 120 #Default 30 or 60 ish. Was using 20 last,  120 for save mount life
#Send slew commands etc
send_commands_to_mount = False
#Updates and clears the terminal instead of log style
#DONT FORGET TO CHANGE THIS TO FALSE IF RUNNING ALL PROGRAMS AS ONE!
terminalMode = True #Default False
# --- Configuration END ---


#List objekt template
#[,, ,, "", "!"],

# Your list of objects (as a list of lists)
objectlist = []

#ADD MAIN TEST
if __name__ == '__main__':

    #Think ill load my list here before everything
    objectlist = load_and_format_targets()

    #TMP redish Initialize
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

    try:
        main(r)
    except KeyboardInterrupt:
        print("Shutting down...")

