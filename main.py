import requests
import json
import os 
import zipfile
from typing import Generator
from smtplib import SMTP
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import sqlite3
from utils import extract_file


load_dotenv()


API_KEY = os.getenv("API_KEY")
header = {"x-api-key":API_KEY}
authorization_url = os.getenv("AUTHORIZATION_URL")
token_url = os.getenv("TOKEN_URL")
refresh_url = os.getenv("REFRESH_URL")
email = os.getenv("EMAIL")
password = os.getenv("PASSWORD")
activities = os.getenv("ACTIVITIES")
cache_db_path = os.getenv("CACHE_DB_PATH")
manifest_db_path = os.getenv("MILESTONE_DB_PATH")
number = os.getenv("NUMBER")
carrier = os.getenv("CARRIER_GATEWAY")

class DestinyAPIService:
    def __init__(self, api_key, header, authorization_url,
                token_url, refresh_url, manifest_url, milestone_url):
        self.api_key = api_key
        self.header = header
        self.authorization_url = authorization_url
        self.token_url = token_url
        self.refresh_url = refresh_url
        self.manifest_url = manifest_url
        self.milestone_url = milestone_url
        self.session = requests.Session()


        self.session = requests.Session()
    
    def get_manifest(self):
        response = self.session.get(self.manifest_url, headers=self.header)
        if response.status_code == 200: 
            response_json = response.json()
        content_path = response_json["Response"]["mobileWorldContentPaths"]["en"]
        content_path = self.session.get(f"https://www.bungie.net/{content_path}", headers=self.header)
        return content_path
    
    def get_milestones(self):
        response = self.session.get(self.milestone_url, headers=self.header)
        if response.status_code == 200:
            response_json = response.json()
            return response_json["Response"]
        




class DatabaseService:
    def __init__(self, manifest_db_path: str, cache_db_path: str):
        self.manifest_db_path = manifest_db_path
        self.cache_db_path = cache_db_path


    
    def init_tables(self) -> None:
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        manifest = """
        CREATE TABLE IF NOT EXISTS manifest(
            activity_hash INTEGER PRIMARY KEY NOT NULL,
            activity_name TEXT,
            destination_hash INTEGER NOT NULL,
            destination_name TEXT,
            original_name TEXT,
            modifier_hash INTEGER NOT NULL,
            modifier_name TEXT,
            updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """

        milestones = """
        CREATE TABLE IF NOT EXISTS milestones(
            milestone_hash INTEGER NOT NULL,
            activity_hash INTEGER NOT NULL,
            modifier_hash INTEGER NOT NULL,
            start_date TEXT,
            end_date TEXT,
            updated DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (activity_hash) REFERENCES manifest(activity_hash)
        )
        """
        cursor.execute(manifest)
        cursor.execute(milestones)
        conn.commit()
        cursor.close()
        conn.close()


    def extract_milestone_data(self, milestone_response: dict) -> list[set]:
        live_activity_entries = []
        for data in milestone_response.values():
            milestone_hash = data.get("milestoneHash", 0)
            start_date = data.get("startDate", "")
            end_date = data.get("endDate", "")
            activity_hashes = [activity["activityHash"] for activity in data.get("activities", [])]
            modifiers = [modifier["modifierHashes"] for modifier in data.get("activities", [])]
            live_activity_entries.append((milestone_hash, start_date, end_date, activity_hashes, modifiers))
        return live_activity_entries
 

    def fill_milestone_table(self, milestones_data: list[set]) -> None:
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM milestones)")
        if not cursor.fetchone()[0]:
            for milestone_hash, start_date, end_date, activity_hashes, modifiers in milestones_data:
                for activity_hash, modifier_hash in zip(activity_hashes, modifiers):
                    cursor.execute("""INSERT OR IGNORE INTO milestones (milestone_hash, activity_hash, modifier_hash,
                                    start_date, end_date) VALUES(?, ?, ?, ?, ?)""",
                                    (milestone_hash, activity_hash, json.dumps(modifier_hash), start_date, end_date))
        conn.commit()
        cursor.close()
        conn.close()

    def extract_manifest_data(self) -> Generator[list[tuple[int, str, list[int], int, str, str]], None, None]:
        activity_entries = []
        dest_map = {}
        conn = sqlite3.connect(self.manifest_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM DestinyDestinationDefinition")
        dest_rows = cursor.fetchall()
        for row in dest_rows:
            data = json.loads(row[1])
            destination_hash = data.get("hash", 0)
            destination_name = data.get("displayProperties", {}).get("name", "") or data.get("originalDisplayProperties", {}).get("name", "")
            if destination_hash and destination_name: 
                dest_map[destination_hash] = destination_name

        modifier_map = {}
        cursor.execute("SELECT * FROM DestinyActivityModifierDefinition")
        modifier_rows = cursor.fetchall()
        for row in modifier_rows:
            data = json.loads(row[1])
            modifier_hash = data.get("hash", 0)
            modifier_name = data.get("displayProperties", {}).get("name", "")
            if modifier_hash and modifier_name: 
                modifier_map[modifier_hash] = modifier_name


     
        cursor.execute("SELECT * FROM DestinyActivityDefinition")
        rows = cursor.fetchall()
        for row in rows:
            data = json.loads(row[1])
            activity_hash = data.get("hash", 0)
            activity_name = data.get("DisplayProperties", {}).get("name") or data.get("originalDisplayProperties", {}).get("name", "")

            destination_hash = data.get("destinationHash", 0)
            destination_name = dest_map.get(destination_hash, "")
            
            
            original_display_properties = data.get("originalDisplayProperties", {})
            original_name = original_display_properties.get("name", "")

            modifier_hash =  [data["activityModifierHash"] for data in data.get("modifiers", [])]
            modifier_name = [modifier_map.get(mh, "") for mh in modifier_hash]



            if activity_name or activity_hash:
                activity_entries.append((activity_hash, activity_name,  destination_hash, destination_name, original_name, modifier_hash,modifier_name))
            if len(activity_entries) >= 50:    
                yield activity_entries
                activity_entries = []
        
        if activity_entries: 
            yield activity_entries
        cursor.close()
        conn.close()


    def fill_manifest_table(self) -> None:
        manifest_data = self.extract_manifest_data()
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM manifest)")
        if not cursor.fetchone()[0]:
            for batch in manifest_data:
                for ah, an, dh, dn, on, mh, mn in batch:
                    cursor.execute("""INSERT OR IGNORE INTO manifest (activity_hash, activity_name, destination_hash,
                                    destination_name, original_name, modifier_hash, modifier_name) VALUES(?, ?, ?, ?, ?, ?, ?)""",
                                    (ah, an, dh, dn, on, json.dumps(mh) ,json.dumps(mn)))
                
        conn.commit()
        cursor.close()
        conn.close()






    def get_upcoming_activities(self, activities: dict) -> list[tuple]:
        reset_message_parts = []
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        placeholder = ','.join('?' for _ in set(activities.keys()))
        query = f"""
            SELECT ms.milestone_hash, m.activity_hash, m.activity_name, m.destination_name, m.modifier_name
            FROM milestones ms 
            JOIN manifest m ON ms.activity_hash = m.activity_hash 
            WHERE ms.milestone_hash IN ({placeholder})
            AND datetime(REPLACE(REPLACE(ms.end_date, 'T', ' '), 'Z', '')) > datetime('now', 'start of day')
            AND datetime(REPLACE(REPLACE(ms.start_date, 'T', ' '), 'Z', '')) < datetime('now', '+7 days')
        """
        cursor.execute(query, tuple(set(activities.keys())))
        rows = cursor.fetchall()
        reset_message_parts = []
        for row in rows:
            modifier_list = json.loads(row[4])
            modifiers = [modifier for modifier in modifier_list if modifier.strip() and modifier]
            if modifiers and ("Raid Challenges" in modifiers or "summoning Ritual" in modifiers):
                reset_message_parts.append(f"raid in rotation: {row[2]}\ndestination: {row[3]}\nmodifiers: {modifiers}\n{'-' * 35}")

            elif modifiers and len(modifiers) > 4 and (modifiers[4] == "Master Modifiers"):
                reset_message_parts.append(f"dungeon in rotation: {row[2]}\ndestination: {row[3]}\nmodifiers: {modifiers}\n{'-' * 35}")

            elif modifiers and  "Grandmaster Modifiers" in modifiers:
                reset_message_parts.append(f"activity name: {row[2]}\ndestination name: {row[3]}\nmodifiers: {modifiers}\n{'-' * 35}")
            else:
                continue
        reset_message_text = "\n".join(reset_message_parts)
        return reset_message_text
    


class EmailService:
    def __init__(self, sender_email: str, sender_password: str):
        self.sender_email = sender_email
        self.sender_password = sender_password
    

    def send_sms_via_email(self, phone_number: str, carrier_gateway: str, subject: str, message: str) -> None:
        to_number = f"{phone_number}@{carrier_gateway}"
        
        msg = MIMEMultipart()
        msg["from"] = self.sender_email
        msg["to"] = to_number
        msg["subject"] = "Destiny 2 Reset Information\n"

        msg.attach(MIMEText(message, "plain"))

        smtp_server = SMTP("smtp.gmail.com", 587)
        with smtp_server as server:
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, to_number, msg.as_string())
            print("sent email successfully")





if __name__ == "__main__":
    destiny = DestinyAPIService(
        api_key=API_KEY,
        header=header,
        authorization_url=authorization_url,
        token_url=token_url,
        refresh_url=refresh_url,
        manifest_url="https://www.bungie.net/Platform/Destiny2/Manifest/",
        milestone_url="https://www.bungie.net/Platform/Destiny2/Milestones/"
    )
    db = DatabaseService(
        manifest_db_path=manifest_db_path,
        cache_db_path=cache_db_path,
    )
    email_service = EmailService(
        sender_email=email,
        sender_password=password
    )
    extract_file(destiny.get_manifest())
    db.init_tables()
    db.fill_manifest_table()
    milestones = destiny.get_milestones()
    milestones_data = db.extract_milestone_data(milestones)
    db.fill_milestone_table(milestones_data)
    upcoming_activities = db.get_upcoming_activities(milestones)
    if upcoming_activities:
        email_service.send_sms_via_email(
            phone_number=f"{number}",
            carrier_gateway=f"{carrier}",
            message=upcoming_activities
        )
    else:
        print("No upcoming activities found.")
        
