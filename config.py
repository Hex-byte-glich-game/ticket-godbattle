import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TOKEN = os.getenv('BOT_TOKEN')
    GUILD_ID = int(os.getenv('GUILD_ID', 0))
    
    # Category IDs for each ticket type - with error checking
    BUY_SKIN_CATEGORY_ID = int(os.getenv('BUY_SKIN_CATEGORY_ID', 0))
    DONATION_CATEGORY_ID = int(os.getenv('DONATION_CATEGORY_ID', 0))
    POV_CATEGORY_ID = int(os.getenv('POV_CATEGORY_ID', 0))
    GENERAL_CATEGORY_ID = int(os.getenv('GENERAL_CATEGORY_ID', 0))
    REPORT_PLAYERS_CATEGORY_ID = int(os.getenv('REPORT_PLAYERS_CATEGORY_ID', 0))
    
    SUPPORT_ROLE_ID = int(os.getenv('SUPPORT_ROLE_ID', 0))
    LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID', 0))
    
    # Your 5 Custom Ticket Categories
    TICKET_TYPES = {
        "buy_skin": {
            "name": "BUY SKIN",
            "description": "Purchase skins or cosmetics",
            "emoji": "💸",
            "color": 0xff9900,  # Orange
            "category_id": "1445246243000553522",
            "category_id_value": BUY_SKIN_CATEGORY_ID  # Direct value for checking
        },
        "donation": {
            "name": "DONATION",
            "description": "Support the server with donations",
            "emoji": "💰",
            "color": 0xff69b4,  # Pink
            "category_id": "1464195372724523247",
            "category_id_value": DONATION_CATEGORY_ID
        },
        "pov": {
            "name": "POV",
            "description": "Share your point of view or evidence",
            "emoji": "🎥",
            "color": 0x9933ff,  # Purple
            "category_id": "1445246310839226611",
            "category_id_value": POV_CATEGORY_ID
        },
        "general": {
            "name": "GENERAL",
            "description": "General questions and support",
            "emoji": "❓",
            "color": 0x3498db,  # Blue
            "category_id": "1445246421438693591",
            "category_id_value": GENERAL_CATEGORY_ID
        },
        "report_players": {
            "name": "REPORT PLAYERS",
            "description": "Report rule-breaking players",
            "emoji": "❗",
            "color": 0xff3333,  # Red
            "category_id": "1445246498282668054",
            "category_id_value": REPORT_PLAYERS_CATEGORY_ID
        }
    }
    
    @classmethod
    def get_category_id(cls, ticket_type):
        """Get category ID with error handling"""
        try:
            # Direct access to the value
            if ticket_type == "buy_skin":
                return cls.BUY_SKIN_CATEGORY_ID
            elif ticket_type == "donation":
                return cls.DONATION_CATEGORY_ID
            elif ticket_type == "pov":
                return cls.POV_CATEGORY_ID
            elif ticket_type == "general":
                return cls.GENERAL_CATEGORY_ID
            elif ticket_type == "report_players":
                return cls.REPORT_PLAYERS_CATEGORY_ID
            else:
                return 0
        except:
            return 0