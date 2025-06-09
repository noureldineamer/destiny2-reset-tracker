import fire
import os 
from dotenv import load_dotenv
from services import DestinyAPIService, DatabaseService, EmailService
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
manifest_db_path = os.getenv("MANIFEST_DB_PATH")
manifest_url = os.getenv("MANIFEST_URL")
milestone_url = os.getenv("MILESTONE_URL")

class Pipeline:
    def __init__(self):
        self.destiny = DestinyAPIService(
            api_key=API_KEY,
            header=header,
            authorization_url=authorization_url,
            token_url=token_url,
            refresh_url=refresh_url,
            manifest_url=manifest_url, 
            milestone_url=milestone_url,
        )
        self.database = DatabaseService(
            manifest_db_path=manifest_db_path,
            cache_db_path=cache_db_path,
        )
        self.email = EmailService(
            sender_email=email,
            sender_password=password,

        )
    
    def run(self, phone: str, carrier: str) -> None:
        extract_file(self.destiny.get_manifest())
        self.database.init_tables()
        self.database.fill_manifest_table()
        milestones = self.destiny.get_milestones()
        milestone_data = self.database.extract_milestone_data(milestones)
        self.database.fill_milestone_table(milestone_data)
        upcoming_activities = self.database.get_upcoming_activities(milestones)
        if upcoming_activities:
            self.email.send_sms_via_email(
                phone_number = phone,
                carrier_gateway = carrier,
                message=upcoming_activities
            )
        else:
            print("No upcoming activities found.")
        
if __name__ == "__main__":
    fire.Fire(Pipeline)
