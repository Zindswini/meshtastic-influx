import json
import meshtastic
import meshtastic.serial_interface
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from time import sleep

# Load Configuration From Environment (or .env)
load_dotenv()

influx_token = os.getenv("INFLUXDB_TOKEN", None)
influx_org = os.getenv("INFLUXDB_ORG", None)
influx_bucket = os.getenv("INFLUXDB_BUCKET", None)
influx_url = os.getenv("INFLUXDB_URL", None)

# Connect to influxdb client
client = InfluxDBClient(url=influx_url, token=influx_token, org=influx_org)
write_api = client.write_api(write_options=SYNCHRONOUS)

# Connect to Meshtastic Node
interface = meshtastic.serial_interface.SerialInterface()

def nodeToPoint(node):
    if "lastHeard" not in node:
        print("Node without timestamp found, skipping...")
        return None

    point = (Point("node_db")
        .time(datetime.fromtimestamp(node["lastHeard"]).astimezone(timezone.utc), WritePrecision.MS)
    )
    
    point.field("snr", node.get("snr"))
    point.field("hopsAway", node.get("hopsAway"))

    if "user" in node:
        user = node["user"]
        point.tag("id", user.get("id"))
        point.tag("user.longName", user.get("longName"))
        point.tag("user.shortName", user.get("shortName"))
        point.tag("user.macaddr", user.get("macaddr"))
        point.tag("user.hwModel", user.get("hwModel"))
        point.tag("user.publicKey", user.get("publicKey"))

    if "deviceMetrics" in node:
        metrics = node["deviceMetrics"]
        point.field("deviceMetrics.batteryLevel", metrics.get("batteryLevel"))
        point.field("deviceMetrics.voltage", metrics.get("voltage"))
        point.field("deviceMetrics.channelUtilization", metrics.get("channelUtilization"))
        point.field("deviceMetrics.airUtilTx", metrics.get("airUtilTx"))
        point.field("deviceMetrics.uptimeSeconds", metrics.get("uptimeSeconds"))
    
    if "position" in node:
        position = node["position"]
        point.field("position.latitude", position.get("latitude"))
        point.field("position.longitude", position.get("longitude"))
        point.field("position.altitude", position.get("altitude"))
        point.field("position.time", position.get("time"))
        point.tag("position.locationSource", position.get("locationSource"))

    return point

def messageToPoint(message):
    pass

while(True):
    try:
        print("Writing to DB...")
        #raise Exception("hi")
        
        nodes = interface.nodes
        
        if nodes is None:
            continue
        
        for node in nodes:
            print(f"Writing node with id {node}")
            point = nodeToPoint(nodes[node])
            if point is None:
                continue
            write_api.write(record=point, bucket=influx_bucket, org=influx_org)
        print("Done, sleeping")
        
    except Exception as e:
        logfile = open("error.log", "a")
        logfile.write(f"[{datetime.now().isoformat()}] {e}\n")
        print(f"Encountered error! Error: {e}")
    sleep(30)


# Write the point
#write_api.write(bucket=bucket, org=org, record=point)
#print("Point written to InfluxDB")\
def getPowerOnTime():
    user = interface.getMyUser()
    nodes = interface.nodes
    
    if (user is None) or (nodes is None):
        return None
    
    node_id = user["id"]
    uptime = nodes[node_id]["deviceMetrics"]["uptimeSeconds"]
    return datetime.now() - timedelta(seconds=uptime)

#file = open("out.json", "w")
#file.write(json.dumps(interface.nodes, indent=2))
#file.close()
interface.close()
