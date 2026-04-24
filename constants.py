#constants.py 
MULTIMEDIA_FORMATS = ["CD", "DVD", "Software", "Other"]
ITEM_TYPES = ["Book", "Newspaper", "Periodical", "Multimedia"]
USER_ROLES = ["Student", "Teacher", "Staff"]
DAILY_PENALTY = 0.5

SUBJECTS = [
    "000 - General Works & Computer Science",
    "100 - Philosophy & Psychology",
    "200 - Religion",
    "300 - Social Sciences (Law, Politics, Education)",
    "400 - Language & Linguistics",
    "500 - Natural Sciences (Math, Physics, Biology)",
    "600 - Technology & Applied Sciences (Medicine, Engineering)",
    "700 - Arts & Recreation (Music, Sports, Fine Arts)",
    "800 - Literature & Rhetoric",
    "900 - History & Geography",
    "Fiction - Mystery",
    "Fiction - Science Fiction/Fantasy",
    "Fiction - Historical",
    "Reference (Dictionaries, Encyclopedias)"
]

LOCATIONS = [
    "Shelf A1", 
    "Shelf A2", 
    "Shelf B1", 
    "Shelf B2", 
    "Reference Section", 
    "Multimedia Room", 
    "Archive"
]

BORROW_LIMITS = {
    "Student": 5,
    "Teacher": 10,
    "Staff": 7
}

BORROW_DURATION = {
    "Student": 14,  
    "Teacher": 30,  
    "Staff": 21  
}