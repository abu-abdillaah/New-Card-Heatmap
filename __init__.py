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
from aqt.theme import theme_manager

def _get_anki_day_for_timestamp(timestamp_ms: int) -> int:
    """
    Takes a single millisecond timestamp and returns a normalized
    "Anki day" timestamp using a direct db.scalar query.
    """
    rollover_hour = mw.col.conf.get("rollover", 4)
    
    # This query format is identical to your example
    # It doesn't need a 'FROM' because it operates directly on the input value
    query = f"""
        SELECT CAST(strftime('%s', '{timestamp_ms/1000}', 'unixepoch', 
        '-{rollover_hour} hours', 'localtime', 'start of day') AS INT)
    """
    
    return mw.col.db.scalar(query)

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
    query = """SELECT id 
    FROM revlog AS r1
    WHERE 
        type = 0 
        AND id IN (
            SELECT
                id
            FROM
                revlog AS r2
            WHERE
                r1.cid = r2.cid
            ORDER BY
                id
            LIMIT
                1)
        """
    all_timestamps_ms = mw.col.db.list(query)

    all_day_timestamps = [
        _get_anki_day_for_timestamp(ts) for ts in all_timestamps_ms
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
    today_ts = _get_anki_day_for_timestamp((mw.col.sched.day_cutoff-day_in_seconds)*1000)
    streaks = calculate_streaks(unique_day_timestamps, today_ts)
    
    return {
        'heatmap_data': heatmap_data,
        'longest_streak': streaks['longest'],
        'current_streak': streaks['current']
    }

def show_heatmap_with_data():
    """
    Called after the Deck Browser has rendered.
    Injects the heatmap into the page using JavaScript.
    """
    # 1. Prepare the data and HTML snippet as before
    addon_path = os.path.dirname(__file__)
    with open(os.path.join(addon_path, "webview.html"), "r", encoding="utf-8") as f:
        html_snippet_1 = f.read()
        html_snippet = html_snippet_1.replace("%%WEB_PATH%%", addon_path)

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

def set_theme():
    """
    Sets the theme of the heatmap based on Anki's current theme.
    """
    if theme_manager.night_mode:
        return 'dark'
    else:
        return 'light'

def on_deck_browser_did_render():
    """
    Called after the Deck Browser has rendered.
    Injects the heatmap into the page using JavaScript.
    """
    theme = set_theme()
    addon_path = os.path.dirname(__file__)
    with open(os.path.join(addon_path, "webview.html"), "r", encoding="utf-8") as f:
        html_snippet_1 = f.read()
        html_snippet = html_snippet_1.replace("%%WEB_PATH%%", __name__)

    review_data = fetch_review_data()
    review_data_json = json.dumps(review_data)
    final_html = html_snippet.replace("%%DATA_JSON%%", review_data_json).replace("%%THEME%%", theme)
    
    return final_html

def displayHeatMap(deck_browser, content):
    """Display the heatmap by appending it to the stats part of the deck browser.
    This function is the main plugin function.

    It is registered by the gui-hook below, so it is called every time the decks browser is re-rendered.
    """
    content.stats += on_deck_browser_did_render()

def on_webview_will_set_content(web_content, context):
    """
    Called before any Anki webview sets its content.
    If it's our heatmap webview, we can modify the content here if needed.
    """
    if not isinstance(context, deckbrowser.DeckBrowser):
        return
    theme = set_theme()
    addon_path = os.path.dirname(__file__)
    with open(os.path.join(addon_path, "webview.html"), "r", encoding="utf-8") as f:
        html_snippet_1 = f.read()
        html_snippet = html_snippet_1.replace("%%WEB_PATH%%", __name__)

    review_data = fetch_review_data()
    review_data_json = json.dumps(review_data)
    final_html = html_snippet.replace("%%DATA_JSON%%", review_data_json).replace("%%THEME%%", theme)

    web_content.body += final_html

mw.addonManager.setWebExports(__name__, r"user_files(\/|\\).*\.(css|js)")
# 👇 Register the hook that is confirmed to exist in your Anki version
#gui_hooks.deck_browser_will_render_content.append(displayHeatMap)
gui_hooks.webview_will_set_content.append(on_webview_will_set_content)
#gui_hooks.theme_did_change.append(displayHeatMap)
