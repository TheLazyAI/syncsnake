import json
from scrape_agent import write_html_dashboard

with open("catalogue.json", "r") as f:
    data = json.load(f)

write_html_dashboard(data)
print("Regenerated dashboard.html")
