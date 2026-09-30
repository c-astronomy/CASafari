from flask import Flask, render_template_string, request, redirect
import redis
import json
import time
import os

app = Flask(__name__)

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

#Want to add AltLimMax AxLimMax etc to defaults. not sure yet if this affects other parts

CONFIG_FILE = 'casafari-config.json'

def load_config():
    defaults = {
        "lat": "59", "lon": "16", "AltLim": "30", "AltLimMax": "75", 
        "AzLim": "240", "AzLimMax": "350", "expo": "30", "ip": "localhost:6379"
    }
    if not os.path.exists(CONFIG_FILE):
        return defaults
    
    with open(CONFIG_FILE, 'r') as f:
        try:
            data = json.load(f)
            # Merge with defaults in case some keys are missing
            return {**defaults, **data}
        except json.JSONDecodeError:
            return defaults

def save_config(config_data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=4)



CREDS_FILE = 'credentials.json'

#CREDENTIALS LOAD / WRITE   I MIGHT CHANGE THIS TO ANOTHER PART OF PROGRAM LATER
def load_credentials():
    """Loads credentials from the JSON file. Returns a dict."""
    if not os.path.exists(CREDS_FILE):
        # Return empty values if file doesn't exist yet
        return {
            "client_id": "", "client_secret": "", 
            "owner_id": "", "bot_id": "", "token": ""
        }
    
    with open(CREDS_FILE, 'r') as f:
        return json.load(f)

def save_credentials(new_creds):
    """Saves a dictionary of credentials back to the JSON file."""
    with open(CREDS_FILE, 'w') as f:
        json.dump(new_creds, f, indent=4)
    print("✅ Credentials saved to disk.")

# --- Example Usage at Startup ---
creds = load_credentials()
TWITCH_TOKEN = creds['token']



HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>CASafari Console</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root {
            --bg: #121212;
            --card-bg: #1e1e1e;
            --text: #e0e0e0;
            --accent: #00adb5;
            --danger: #ff4d4d;
            --success: #2ecc71;
        }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }
        
        /* Grid Layout */
        .container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            max-width: 1200px;
            margin: auto;
        }

        .card { background: var(--card-bg); padding: 15px; border-radius: 10px; border: 1px solid #333; }
        h3 { margin-top: 0; border-bottom: 1px solid var(--accent); padding-bottom: 5px; color: var(--accent); font-size: 0.9rem; text-transform: uppercase; }
        
        /* Dashboard Styling */
        .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.85rem;}
        .stat-item { background: #252525; padding: 8px; border-radius: 4px; border-left: 3px solid var(--accent); }
        .stat-label { display: block; font-size: 0.7rem; color: #888; }

        /* Form Styling */
        input { width: 100%; padding: 8px; margin: 5px 0; background: #2a2a2a; border: 1px solid #444; color: white; border-radius: 4px; box-sizing: border-box; }
        .btn-group { display: flex; gap: 10px; }
        button { flex: 1; padding: 10px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; background: var(--accent); color: white; }
        .btn-stop { background: var(--danger); }
        .btn-save { background: var(--success); }
        .btn-remove { background: var(--danger); }

        .status-dot { height: 8px; width: 8px; background-color: var(--success); border-radius: 50%; display: inline-block; margin-right: 5px; border:1px solid #555;}
    </style>
</head>
<body>

<div class="container">
    <div class="card" style="grid-column: 1 / -1;">
        <h3>CASafari Real-time Dashboard</h3>
        <div class="stats-grid">
            <div class="stat-item"><span class="stat-label">Longitude</span>{{ lon }}</div>
            <div class="stat-item"><span class="stat-label">Latitude</span>{{ lat }}</div>
            <div class="stat-item"><span class="stat-label">Alt Limit min</span>{{ alt_lim }}</div>
            <div class="stat-item"><span class="stat-label">Alt Limit Max</span>{{ alt_lim_max }}</div>
            <div class="stat-item"><span class="stat-label">Az Limit Min</span>{{ az_lim }}</div>
            <div class="stat-item"><span class="stat-label">Az Limit Max</span>{{ az_lim_max }}</div>
            <div class="stat-item"><span class="stat-label">Local Time</span>{{ local_time }}</div>
            <div class="stat-item"><span class="stat-label">Connections</span>
                <small><span class="status-dot"></span>CASafari</small>
                <small><span class="status-dot" style="background: var(--success);"></span>Twitch</small>
                <small><span id="nina-dot" class="status-dot" style="background: {{ nina_dot }};"></span>NINA</small>
                <small><span id="redis-dot" class="status-dot" style="background: {{ redis_dot }};"></span>Redis</small>
                <small><span id="slew-dot" class="status-dot" style="background: {{ slew_dot }};"></span>Mount slewing</small>
                <small><span id="camera-dot" class="status-dot" style="background: {{ camera_dot }};"></span>Camera imaging</small>
            </div>
        </div>
    </div>

    <div class="card">
        <h3>CASafari Setup</h3>
        <form method="POST">
            <label for="lon">Longitude</label>
            <input type="text" name="lon" placeholder="Longitude" value="{{ config.lon }}">
            <label for="lat">Latitude</label>
            <input type="text" name="lat" placeholder="Latitude" value="{{ config.lat }}">
            <label for="AltLim">Altitude Limit Min (°)</label>
            <label for="AltLimMax">Altitude Limit Max(°)</label>
            <input type="text" name="AltLim" placeholder="Altitude limit min" value="{{ config.AltLim }}">
            <input type="text" name="AltLimMax" placeholder="Altitude limit max" value="{{ config.AltLimMax }}">
            <label for="AzLim">Azimuth Limit Min (°)</label>
            <label for="AzLimMax">Azimuth Limit Max(°)</label>
            <input type="text" name="AzLim" placeholder="Azimut limit min" value="{{ config.AzLim }}">
            <input type="text" name="AzLimMax" placeholder="Azimut limit max" value="{{ config.AzLimMax }}">
            <label for="expo">Exposure Time (sec)</label>
            <input type="text" name="expo" placeholder="Exposure time" value="{{ config.expo }}">
            <label for="ip">IP to NINA</label>
            <input type="text" name="ip" placeholder="IP to NINA" value="{{ config.ip }}">
            <button type="submit" name="action" value="update_loc">Update Settings</button>
        </form>
    </div>

    <div class="card">
        <h3>Twitch Bot Configuration</h3>
        <form method="POST">
            <label for="client_id">Client ID</label>
            <input type="password" name="client_id" placeholder="Client ID" value="{{ creds.client_id }}">
            <label for="client_secret">Client SECRET</label>
            <input type="password" name="client_secret" placeholder="Client Secret" value="{{ creds.client_secret }}">
            <label for="owner_id">Owner ID</label>
            <input type="password" name="owner_id" placeholder="Owner ID" value="{{ creds.owner_id }}">
            <label for="bot_id">Bot ID</label>
            <input type="password" name="bot_id" placeholder="Bot ID" value="{{ creds.bot_id }}">
            <button type="submit" name="action" value="update_twitch">Save Credentials</button>
        </form>
    </div>


    <div class="card">
            <h3>Add New Target</h3>
            <form method="POST">
                <label for="t_name">Target Name</label>
                <input type="text" name="t_name" placeholder="Target Name (e.g. Orion)" required>
                <label for="t_trigger">Trigger</label>
                <input type="text" name="t_trigger" placeholder="Trigger (e.g. orion)" required>
                <div style="display: flex; gap: 5px;">
                    <div style="display: flex; flex-direction: column; flex: 1;">
                        <label for="t_ra">RA</label>
                        <input type="text" name="t_ra" placeholder="RA (Decimal)" required>
                    </div>
                    <div style="display: flex; flex-direction: column; flex: 1;">
                        <label for="t_dec">DEC</label>
                        <input type="text" name="t_dec" placeholder="DEC (Decimal)" required>
                
                    </div>
                </div>
                <button type="submit" name="action" value="save_target" class="btn-save" style="margin-top: 10px;">Add Target</button>
            </form>

            <hr style="border: 0.5px solid #333; margin: 15px 0;">
            <h3>Remove Target</h3>
            <form method="POST">
                <label for="t_trigger">Remove Trigger</label>
                <input type="text" name="t_trigger" placeholder="Trigger to remove (e.g. m31)">
                <button type="submit" name="action" value="remove_target" class="btn-remove">Remove from List</button>
            </form>
        </div>

        <div class="card">
            <h3>System Master Control</h3>
            
            <div style="margin-bottom: 20px;">
                <small style="color: #888; display: block; margin-bottom: 5px;">Twitch Bot Status</small>
                <form method="POST" class="btn-group">
                    <button type="submit" name="action" value="start_twitch" style="background: var(--success);">START</button>
                    <button type="submit" name="action" value="stop_twitch" class="btn-stop">STOP</button>
                </form>
            </div>

            <div>
                <small style="color: #888; display: block; margin-bottom: 5px;">Automation Engine (Casafari)</small>
                <form method="POST" class="btn-group">
                    <button type="submit" name="action" value="start_casa" style="background: var(--success);">START</button>
                    <button type="submit" name="action" value="stop_casa" class="btn-stop">STOP</button>
                </form>
            </div>


        <p style="font-size: 0.75rem; color: #666; margin-top: 20px;">
            <i>Automation Engine handles target rotation when chat is idle.</i>
        </p>
    </div>

    <div class="card" style="grid-column: 1 / -1;">
        <h3>CASafari Target List</h3>
        <div class="stats-grid">
            {% if target_list %}
                {% for target in target_list %}
                <div class="stat-item">
                    <span class="stat-label">{{ target.trigger }}</span>
                    {{ target.name }}
                </div>
                {% endfor %}
            {% else %}
                <div class="stat-item">No targets found in targetlist.json</div>
            {% endif %}
        </div>
    </div>

</div>
    <script>
        function updateLiveStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    // Update the background colors of the dots
                    document.getElementById('nina-dot').style.background = data.nina_dot;
                    document.getElementById('slew-dot').style.background = data.slew_dot;
                    document.getElementById('camera-dot').style.background = data.camera_dot;

                    // Optional: Update a clock on the screen if you have a <span id="clock">
                    const clock = document.getElementById('clock');
                    if(clock) clock.innerText = data.local_time;
                })
                .catch(err => console.error('Status Update Failed:', err));
        }

        // Refresh every 2 seconds (2000 milliseconds)
        setInterval(updateLiveStatus, 2000);
    </script>
</body>
</html>
"""

# --- LOAD TARGETS ON STARTUP ---
try:
    with open('targetlist.json', 'r') as f:
        target_list = json.load(f)
except FileNotFoundError:
    target_list = []  # Fallback if file is missing
    print("⚠️ Warning: targetlist.json not found.")



@app.route('/api/status')
def get_status():
    # 1. Pull NINA status
    nina_status_raw = r.get("nina:status")
    data = json.loads(nina_status_raw) if nina_status_raw else {"online": False, "is_slewing": False, "camera_busy": False}

    # Determine status colors
    is_online = data.get("online", False)
    is_slewing = data.get("is_slewing", False)
    is_imaging = data.get("camera_busy", False)

    if not is_online:
        # Everything is dark if NINA isn't found
        slew_dot = "#000000"
        camera_dot = "#000000"
    else:
        # Mount Logic: Red if moving, Green if parked/ready
        slew_dot = "var(--danger)" if is_slewing else "var(--success)"
    
        # Camera Logic: Orange if exposing, Green if idle/ready
        camera_dot = "#e67e22" if is_imaging else "var(--success)"
    
    # 2. Return ONLY the colors as JSON
    return {
        "nina_dot": "var(--success)" if is_online else "var(--danger)",
        "slew_dot": slew_dot,
        "camera_dot": camera_dot,
        "local_time": time.strftime("%H:%M:%S") #This is currently only updating when action is taken. should be sideral from casfari also, not normal time
    }


@app.route('/', methods=['GET', 'POST'])
def index():

    global target_list

    config = load_config()
    creds = load_credentials()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == "update_loc":
            # Save all the form fields to Redis
            r.set("config:lon", request.form.get("lon"))
            r.set("config:lat", request.form.get("lat"))
            r.set("config:alt_lim", request.form.get("AltLim"))
            r.set("config:alt_lim_max", request.form.get("AltLimMax"))
            r.set("config:az_lim", request.form.get("AzLim"))
            r.set("config:az_lim_max", request.form.get("AzLimMax"))
            config_data = {
                "lat": request.form.get("lat"),
                "lon": request.form.get("lon"),
                "AltLim": request.form.get("AltLim"),
                "AltLimMax": request.form.get("AltLimMax"),
                "AzLim": request.form.get("AzLim"),
                "AzLimMax": request.form.get("AzLimMax"),
                "expo": request.form.get("expo"),
                "ip": request.form.get("ip")
            }
            
            #Save config data           
            save_config(config_data)
            # Sync to Redis for your backend processes
            r.set("config:lat", config_data["lat"])
            r.set("config:lon", config_data["lon"])
            r.set("config:alt_lim", config_data["AltLim"])
            r.set("config:alt_lim_max", config_data["AltLimMax"])
            r.set("config:az_lim", config_data["AzLim"])
            r.set("config:az_lim_max", config_data["AzLimMax"])

        elif action == "update_twitch":
            # 1. Grab values from the form
            new_data = {
                "client_id": request.form.get("client_id"),
                "client_secret": request.form.get("client_secret"),
                "owner_id": request.form.get("owner_id"),
                "bot_id": request.form.get("bot_id"),
                "token": creds.get("token") # Keep the old token if not in form
            }
            # 2. Save to file
            save_credentials(new_data)
            # 3. Optional: Also push to Redis so the Bot sees the change instantly
            r.set("config:twitch", json.dumps(new_data))

        elif action == "save_target":
            new_target = {
                "name": request.form.get("t_name"),
                "trigger": f"!slew_{request.form.get('t_trigger').lower().replace('!slew_', '')}",
                "ra": request.form.get("t_ra"),
                "dec": request.form.get("t_dec")
            }

            target_list.append(new_target)

            with open('targetlist.json', 'w') as f:
                json.dump(target_list, f, indent=4)
            
            r.set("nina:available_targets", json.dumps(target_list))
            #return redirect('/')

        elif action == "remove_target":
            trigger_to_remove = request.form.get("t_trigger").lower().strip()
            if not trigger_to_remove.startswith("!slew_"):
                trigger_to_remove = f"!slew_{trigger_to_remove}"
            
            target_list = [t for t in target_list if t['trigger'].lower() != trigger_to_remove]
            
            with open('targetlist.json', 'w') as f:
                json.dump(target_list, f, indent=4)
                
            r.set("nina:available_targets", json.dumps(target_list))
            #return redirect('/')


            #Some start switches
        elif action == "start_twitch":
            r.set("status:twitch_enabled", "true")
        elif action == "stop_twitch":
            r.set("status:twitch_enabled", "false")

        elif action == "start_casa":
            r.set("status:casa_enabled", "true")
        elif action == "stop_casa":
            r.set("status:casa_enabled", "false")

        return redirect('/')

    # 1. Pull NINA status
    nina_status_raw = r.get("nina:status")
    # Default to "offline/not busy" if Redis is empty
    nina_data = json.loads(nina_status_raw) if nina_status_raw else {"online": False, "is_slewing": False, "camera_busy": False}
    
    # 2. Define colors
    is_online = nina_data.get("online", False)
    
    # Logic: If offline, dots are Red. If online, Slewing/Imaging are Yellow if active, or Grey if idle.
    context = {
        "lon": r.get("config:lon") or "Not Set",
        "lat": r.get("config:lat") or "Not Set",
        "alt_lim": r.get("config:alt_lim") or "30",
        "alt_lim_max": r.get("config:alt_lim_max") or "75",
        "az_lim": r.get("config:az_lim") or "240", #360 for some reason, ill try set it to normal 240
        "az_lim_max": r.get("config:az_lim_max") or "350",
        "local_time": time.strftime("%H:%M:%S"),
        
        # Connection Dot Colors
        "nina_dot": "var(--success)" if is_online else "var(--danger)",
        "redis_dot": "var(--success)", # If Flask is running, Redis is up
        "twitch_dot": "var(--success)", # You can link this to your twitch bot status later
        "casafari_dot": "var(--success)",
        
        # Activity Dot Colors (Yellow/Orange if active, else dark grey)
        "slew_dot": "#f1c40f" if nina_data.get("is_slewing") else "#444",
        "camera_dot": "#e67e22" if nina_data.get("camera_busy") else "#444",
        "target_list": target_list,
        "creds": creds,
        "config": config
    }
    
    return render_template_string(HTML_TEMPLATE, **context)
if __name__ == '__main__':
    # host='0.0.0.0' allows access from any device on your local network
    app.run(host='0.0.0.0', port=5000, debug=True)
