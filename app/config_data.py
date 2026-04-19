"""
config_data.py
--------------
Structured ground-truth data for the Event Assistant chatbot.

Design rule: If an event policy or venue detail is NOT listed here, the
chatbot must refuse to answer. Gemini is used only to phrase grounded responses,
never to invent facts about the venue or event.
"""

EVENT_INFO = {
    "event_name": "CrowdPulse Premier League Final 2026",
    "sport": "Cricket",
    "venue": "Wankhede Stadium, Mumbai",
    "date": "Saturday, 19 April 2026",
    "gates_open_time": "14:00",
    "match_start_time": "16:00",
    "estimated_end_time": "23:00",
    "key_phases": [
        "Gates open: 14:00 – 15:30 (early entry window)",
        "Match start: 16:00 (first innings begins)",
        "Innings break: approx. 19:00 – 19:30 (30 min interval)",
        "Second innings: 19:30 – approx. 23:00",
        "Post-match exit: 23:00 – 00:30 (staggered exit by zone)",
    ],
    "team_a": "Mumbai Indians",
    "team_b": "Chennai Super Kings",
    "capacity": 33000,
}

VENUE_POLICY = {
    "prohibited_items": [
        "Weapons or sharp objects of any kind",
        "Glass bottles or containers",
        "Alcohol brought from outside the venue",
        "Flares, fireworks, smoke bombs, or pyrotechnics",
        "Flag poles or banner poles longer than 1 metre",
        "Laser pointers or strobe devices",
        "Drones or remotely piloted aircraft",
        "Large umbrellas (compact collapsible umbrellas are permitted)",
        "Selfie sticks or monopods",
        "Outside food or hot beverages",
        "Professional camera equipment (no detachable lenses above 100 mm)",
        "Portable speakers or amplifiers",
        "Power banks exceeding 20,000 mAh capacity",
    ],
    "allowed_items": [
        "Clear plastic bags up to 30 cm × 20 cm × 10 cm",
        "One small clutch bag or purse (max A4 size)",
        "Sealed, factory-capped plastic water bottles (up to 500 ml)",
        "Medical equipment and prescription medication (with letter from GP)",
        "Compact collapsible umbrella",
        "Hearing aids and cochlear implants",
        "Baby changing supplies in a clear bag",
        "Fan scarves, hats, and replica team shirts",
        "Sunscreen and sunglasses",
    ],
    "bag_policy": (
        "A strict clear bag policy is in effect. You may bring one clear plastic, "
        "vinyl, or PVC bag no larger than 30 cm × 20 cm × 10 cm, plus one small "
        "clutch bag or purse the size of an A4 sheet. All bags are subject to search "
        "at the gate. Non-compliant bags will not be stored — they must be returned "
        "to your vehicle or handed to someone outside the venue."
    ),
    "re_entry_rules": (
        "Re-entry is NOT permitted once you have exited the stadium during the match. "
        "If you have a medical emergency or operational need, speak to a steward at "
        "the nearest gate before exiting. Re-entry tokens are available only in "
        "extraordinary circumstances at the discretion of the duty manager."
    ),
    "restricted_areas": (
        "Team dugouts and pitch-side areas are restricted to match officials and support "
        "staff. The Media Box near Corridor 2 is restricted to accredited press. VIP "
        "hospitality boxes (Gate D corridor) require a printed hospitality pass in addition "
        "to your match ticket. The Pavilion End is reserved for members only."
    ),
    "accessibility_services": [
        "Wheelchair spaces and companion seats are available in all four stands — "
        "book in advance via the accessibility team (access@wankhede.example.com).",
        "Ambulant disabled seating is located on rows 1–3 of each stand with step-free access.",
        "Sensory-friendly quiet areas are available inside Gate A and Gate D concourses.",
        "Assistive listening loop systems cover the main public address areas.",
        "Sign language interpretation is available on request — contact the stadium "
        "at least 72 hours in advance.",
        "All gates, concourses, restrooms, and the Food Court are wheelchair-accessible.",
        "Mobility scooters may be used in designated concourse areas — ask a steward.",
        "Personal assistance dogs are welcome throughout the venue.",
        "Large-print and audio match programmes are available from the Information Desk (Gate A).",
    ],
    "ticket_guidance": (
        "Match tickets are digital only. Have your QR code ready on your phone before "
        "joining the gate queue. Paper print-outs are accepted only if pre-arranged "
        "with the box office. Season pass holders use their membership card."
    ),
    "first_aid": (
        "First-aid stations are located at the Gate A concourse, Gate B concourse, the "
        "Medical Centre near Corridor 3, and pitch-side. Defibrillators (AEDs) are "
        "positioned at every gate entrance and at the Main Restroom block. For emergencies, "
        "flag down any steward — they can summon medical staff within 90 seconds."
    ),
    "lost_property": (
        "Lost property found before the match is held at the Information Desk near "
        "Gate A. Items found after the match are logged and held for 28 days. "
        "Contact lost.property@wankhede.example.com to report or claim items."
    ),
    "parking": (
        "Limited parking is available in the adjacent D-Road parking structure (enter from "
        "Marine Drive). We strongly recommend public transport — Churchgate railway station "
        "is a 5-minute walk from Gate A. Auto-rickshaws and ride-share drop-off zones are "
        "located on D-Road near Gate B."
    ),
    "weather_policy": (
        "In case of rain delays, please remain in your seat or move to the covered concourse "
        "areas. The match referee will communicate updates via the PA system. Refund policies "
        "apply only if fewer than 5 overs are bowled; check your ticket terms."
    ),
    "food_and_beverages": (
        "The Food Court (Level 1) offers a wide range of options:\n"
        "- Indian street food: Vada pav, pav bhaji, samosas, chaat (₹80–₹200)\n"
        "- South Indian: Dosa, idli, uttapam (₹120–₹250)\n"
        "- International: Pizza slices, burgers, wraps (₹200–₹400)\n"
        "- Snacks: Popcorn, nachos, chips (₹100–₹200)\n"
        "- Beverages: Soft drinks, juices, chai, coffee (₹60–₹150)\n"
        "- Premium: Craft beer and cocktails (available at Gate D VIP lounge only)\n"
        "All food stalls accept UPI, cards, and cash. "
        "Vegetarian and Jain options are clearly marked at every stall. "
        "Allergen information is displayed at each food counter."
    ),
}
