import os

target_file = "/Users/maryann/sync_licensing_agent/scrape_agent.py"

with open(target_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if line.strip() == 'def write_html_dashboard(data):':
        start_idx = i
    if start_idx != -1 and line.strip() == '</html>"""':
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    new_lines = lines[:start_idx + 2] # def write_html_dashboard(data): and docstring
    new_lines.append('    import json\n')
    new_lines.append('    with open("dashboard_template.html", "r", encoding="utf-8") as f:\n')
    new_lines.append('        html_template = f.read()\n')
    new_lines.append('\n')
    
    # Find the next lines after the template string
    # Usually it's:
    #    # Inject data into the template
    #    import json
    #    data_json = json.dumps(data)
    #    final_html = html_template.replace("%DATA%", data_json)
    
    # Let's just keep everything after end_idx + 1
    new_lines.extend(lines[end_idx + 1:])
    
    with open(target_file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print("Updated scrape_agent.py")
else:
    print("Could not find write_html_dashboard block")
