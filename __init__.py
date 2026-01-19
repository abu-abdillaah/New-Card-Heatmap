
"""def testFunction():
    # Get today's timestamp at Anki's new day start time
    #today = mw.col.sched.day_cutoff // 86400
    today = intTime() // 86400

    # Query revlog for all reviews up to today
    query = 
    SELECT (id/1000/86400) AS day, COUNT(*) 
    FROM revlog 
    WHERE type = 0 AND lastIvl = 0 AND id/1000/86400 <= ? 
    GROUP BY day
    ORDER BY day
    
    results = mw.col.db.all(query, today)

    # Print results: day (as days since epoch), count
    # Get the last 5 days from results
    # Create a dictionary mapping date (YYYY-MM-DD) to review count (0 if no reviews)
    date_counts = {}
    # Get all days in the range from the earliest to the latest in results
    if results:
        #make last day today
        first_day = results[0][0]
        last_day = today
        for day in range(first_day, last_day + 1):
            date_str = time.strftime('%Y-%m-%d', time.gmtime(day * 86400))
            # Find count for this day if present, else 0
            count = next((c for d, c in results if d == day), 0)
            date_counts[date_str] = count
    else:
        date_counts = {}
    msg = f'{date_counts["2025-08-29"]}'
    showInfo(msg)

action = QAction("test", mw)
qconnect(action.triggered, testFunction)
mw.form.menuTools.addAction(action)"""

"""import os

# Anki imports
from aqt import mw
from aqt.qt import QAction
from aqt.webview import AnkiWebView

# Path to the current add-on's folder
addon_path = os.path.dirname(__file__)

def show_static_heatmap():
    
    #Creates a webview and loads the static HTML file directly,
    #without injecting any data.
    
    webview = AnkiWebView(title="Review Heatmap (Static Test)")
    
    # Read the HTML file from the add-on folder
    with open(os.path.join(addon_path, "webview.html"), "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # Load the HTML directly into the webview
    webview.stdHtml(html_content)
    webview.show()

# Create a new menu item in Anki's "Tools" menu
action = QAction("Show Review Heatmap (Test)", mw)
# When the menu item is clicked, call the show_static_heatmap function
action.triggered.connect(show_static_heatmap)
# Add the menu item to the Tools menu
mw.form.menuTools.addAction(action)"""

import os
import json
from datetime import datetime
from collections import Counter

# Anki-specific imports
from aqt import mw
from aqt.qt import QAction
from aqt.webview import AnkiWebView
from aqt import deckbrowser
from aqt import gui_hooks

def calculate_streaks(day_timestamps, today_ts):
    """
    Takes a sorted list of unique day-start timestamps and calculates streaks.
    """
    if not day_timestamps:
        return {'longest': 0, 'current': 0}

    longest_streak = 0
    current_streak = 1

    for i in range(len(day_timestamps) - 1):
        if day_timestamps[i] + 86400 == day_timestamps[i+1]:
            current_streak += 1
        else:
            longest_streak = max(longest_streak, current_streak)
            current_streak = 1
    
    longest_streak = max(longest_streak, current_streak)

    last_study_ts = day_timestamps[-1]
    if last_study_ts == today_ts or last_study_ts == today_ts - 86400:
        active_current_streak = current_streak
    else:
        active_current_streak = 0

    return {'longest': longest_streak, 'current': active_current_streak}


def fetch_review_data():
    """
    Queries Anki's database to get a count of NEW CARDS learned per day,
    respecting the user's "new day starts at" setting.
    """
    # 1. Get the "new day starts at" hour from Anki's config (defaults to 4 if not set)
    rollover_hour = mw.col.conf.get("rollover", 4)

    # 2. Calculate the offset in seconds (e.g., 4 hours * 3600 seconds/hour)
    offset_seconds = rollover_hour * 3600
    day_in_seconds = 86400

    # The query remains the same: filter for 'learn' events
    query = "SELECT id FROM revlog WHERE type = 0 AND lastIvl = 0"
    all_timestamps_ms = mw.col.db.list(query)

    all_day_timestamps = [
        int((ts / 1000 - offset_seconds) // day_in_seconds * day_in_seconds)
        for ts in all_timestamps_ms
    ]

    # 2. Use Counter to count how many times each day-timestamp appears.
    #    This gives us a dictionary of {timestamp: count}.
    daily_counts = Counter(all_day_timestamps)
    
    # 3. Format the data for Cal-Heatmap using the correct counts.
    heatmap_data = [
        {"date": datetime.fromtimestamp(ts).strftime('%Y-%m-%d'), "value": count} 
        for ts, count in daily_counts.items()
    ]
    
    # --- Streak calculation remains the same, but uses the keys from our Counter ---
    unique_day_timestamps = sorted(daily_counts.keys())
    today_ts = mw.col.sched.day_cutoff - day_in_seconds
    streaks = calculate_streaks(unique_day_timestamps, today_ts)
    
    return {
        'heatmap_data': heatmap_data,
        'longest_streak': streaks['longest'],
        'current_streak': streaks['current']
    }
"""counts = Counter(
        # 3. For each timestamp, subtract the offset BEFORE converting to a date
        datetime.fromtimestamp((ts / 1000) - offset_seconds).strftime('%Y-%m-%d')
        for ts in all_timestamps_ms
    )
    
    # The rest of the function is unchanged
    heatmap_data = [{"date": date, "value": count} for date, count in counts.items()]
    return heatmap_data"""

def show_heatmap_with_data():
    """
    Called after the Deck Browser has rendered.
    Injects the heatmap into the page using JavaScript.
    """
    # 1. Prepare the data and HTML snippet as before
    addon_path = os.path.dirname(__file__)
    with open(os.path.join(addon_path, "webview.html"), "r", encoding="utf-8") as f:
        html_snippet = f.read()

    review_data = fetch_review_data()
    review_data_json = json.dumps(review_data)
    final_html = html_snippet.replace("%%DATA_JSON%%", review_data_json)
    
    # 2. Escape the HTML snippet so it can be safely used inside a JavaScript command
    #    json.dumps() is a clever and reliable way to do this.
    html_for_javascript = json.dumps(final_html)
    # 6. Create and show the webview with the final HTML
    webview = AnkiWebView(title="My Review Heatmap")
    webview.stdHtml(final_html)
    webview.show()

def on_deck_browser_did_render():
    """
    Called after the Deck Browser has rendered.
    Injects the heatmap into the page using JavaScript.
    """
    # 1. Prepare the data and HTML snippet as before
    addon_path = os.path.dirname(__file__)
    with open(os.path.join(addon_path, "webview.html"), "r", encoding="utf-8") as f:
        html_snippet = f.read()

    review_data = fetch_review_data()
    review_data_json = json.dumps(review_data)
    final_html = html_snippet.replace("%%DATA_JSON%%", review_data_json)
    
    # 2. Escape the HTML snippet so it can be safely used inside a JavaScript command
    #    json.dumps() is a clever and reliable way to do this.
    #html_for_javascript = json.dumps(final_html)

    # 3. Create the JavaScript command to inject the HTML at the end of the page
    #js_command = f"document.body.insertAdjacentHTML('beforeend', {html_for_javascript});"

    # 4. Execute the JavaScript command on the Deck Browser's webview
    #deck_browser.web.eval(js_command)
    return final_html

def displayHeatMap(deck_browser, content):
    """Display the heatmap by appending it to the stats part of the deck browser.
    This function is the main plugin function.

    It is registered by the gui-hook below, so it is called every time the decks browser is re-rendered.
    """
    content.stats += on_deck_browser_did_render()


# 👇 Register the hook that is confirmed to exist in your Anki version
gui_hooks.deck_browser_will_render_content.append(displayHeatMap)

# Add a menu item in Anki's "Tools" menu to trigger the heatmap
action = QAction("Show Review Heatmap", mw)
action.triggered.connect(show_heatmap_with_data)
mw.form.menuTools.addAction(action)