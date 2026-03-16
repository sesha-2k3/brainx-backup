"""
Contact Category Enums
"""

from enum import StrEnum


class ContactCategory(StrEnum):
    INVESTOR = "investor"
    CLIENT = "client"
    PARTNER = "partner"
    FRIEND = "friend"
    FAMILY = "family"
    COLLEAGUE = "colleague"
    OTHER = "other"
