""" 
Contact Category Enums
"""
from enum import Enum

class ContactCategory(str, Enum):
    INVESTOR = "investor"
    CLIENT = "client"
    PARTNER = "partner"
    FRIEND = "friend"
    FAMILY = "family"
    COLLEAGUE = "colleague"
    OTHER = "other"
