#!/usr/bin/env python3
"""Build dashboard.html by injecting catalogue.json into the template."""
import json
import os
import sys

base = os.path.dirname(os.path.abspath(__file__))
cat_path = os.path.join(base, 'catalogue.json')
template_path = os.path.join(base, 'dashboard_template.html')

if not os.path.exists(cat_path):
    print(f"Error: {cat_path} not found.")
    sys.exit(1)

if not os.path.exists(template_path):
    print(f"Error: {template_path} not found.")
    sys.exit(1)

with open(cat_path, 'r', encoding='utf-8') as f:
    cat = json.load(f)

with open(template_path, 'r', encoding='utf-8') as f:
    HTML = f.read()

output = HTML.replace('%DATA%', json.dumps(cat, indent=2))
out_path = os.path.join(base, 'dashboard.html')

with open(out_path, 'w', encoding='utf-8') as f:
    f.write(output)

lines = output.count('\n')
print(f"dashboard.html written: {len(output):,} bytes, {lines} lines")
print(f"Catalogue: {sum(len(v) for v in cat.values() if isinstance(v, list))} records across {len(cat)} categories")
