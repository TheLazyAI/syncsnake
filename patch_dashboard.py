import os
import re

content_file = "/Users/maryann/sync_licensing_agent/stitch_content.html"
target_file = "/Users/maryann/sync_licensing_agent/scrape_agent.py"

with open(content_file, "r") as f:
    stitch_content = f.read()

# Extract just the HTML part from the content file
html_start = stitch_content.find("<!DOCTYPE html>")
stitch_html = stitch_content[html_start:]

# 1. Modify the navigation section to have id="categories-nav" and remove hardcoded items
nav_regex = re.compile(r'<nav class="([^"]+)">.*?</nav>', re.DOTALL)
stitch_html = nav_regex.sub(r'<nav class="\1" id="categories-nav"></nav>', stitch_html)

# 2. Modify the restricted resources button to be the agent map button
btn_regex = re.compile(r'<button class="w-full bg-secondary[^>]+>.*?</button>', re.DOTALL)
map_btn = """<button id="open-map-btn" class="w-full bg-secondary text-white py-3 px-4 rounded-lg font-label-bold flex items-center justify-center gap-2 glow-crimson">
<span class="material-symbols-outlined">map</span>
                View Agent Map
            </button>"""
stitch_html = btn_regex.sub(map_btn, stitch_html)

# 3. Add Agent Map Modal HTML before the closing </body>
map_modal = """
    <!-- Agent Map Modal -->
    <div id="map-modal" class="hidden fixed top-0 left-0 w-full h-full bg-black/85 z-[1000] backdrop-blur items-center justify-center">
        <div class="map-modal-content bg-background border-4 border-primary rounded-lg p-4 shadow-[0_0_30px_rgba(34,211,238,0.2)]">
            <div class="map-header flex justify-between items-center mb-4 font-mono text-primary">
                <h2 class="text-xl m-0">🛰️ AGENT NETWORK VISUALIZER</h2>
                <button id="close-map" class="close-btn bg-transparent text-secondary border-2 border-secondary rounded px-2 py-1 cursor-pointer font-bold font-mono hover:bg-secondary hover:text-black transition-all">X</button>
            </div>
            <canvas id="agent-canvas" width="800" height="500" class="bg-[#050508] border-2 border-[#1a1a24]" style="image-rendering: pixelated;"></canvas>
        </div>
    </div>
"""
stitch_html = stitch_html.replace('</body>', map_modal + '\n</body>')

# 4. Replace hardcoded JS data and logic with dynamic logic
js_logic = """
        const catalogueData = %DATA%;
        
        const categoryConfigs = {
            agencies: {
                label: "Sync Agencies",
                icon: "corporate_fare",
                titleKey: "name",
                subtitleKey: "location",
                descKey: "submission_guidelines",
                pills: ["roster_genre_focus", "regions"],
                urlKey: "website",
                contactKey: "contact_info"
            },
            supervisors: {
                label: "Music Supervisors",
                icon: "groups",
                titleKey: "name",
                subtitleKey: "company",
                descKey: "submission_policy",
                pills: ["location", "notable_projects"],
                urlKey: "contact_info",
                contactKey: "contact_info"
            },
            platforms: {
                label: "Brief Platforms",
                icon: "assignment",
                titleKey: "name",
                subtitleKey: "requirements",
                descKey: "description",
                pills: ["requirements"],
                urlKey: "url",
                contactKey: "url"
            },
            grants: {
                label: "Grants & Funding",
                icon: "payments",
                titleKey: "name",
                subtitleKey: "organization",
                descKey: "eligibility_summary",
                pills: ["deadlines"],
                urlKey: "url",
                contactKey: "deadlines"
            },
            festivals: {
                label: "Showcase Festivals",
                icon: "theater_comedy",
                titleKey: "name",
                subtitleKey: "location",
                descKey: "requirements_fees",
                pills: ["application_window"],
                urlKey: "url",
                contactKey: "application_window"
            },
            indie_games: {
                label: "Indie Video Games",
                icon: "sports_esports",
                titleKey: "project_name",
                subtitleKey: "developer_studio",
                descKey: "status_or_needs",
                pills: [],
                urlKey: "url",
                contactKey: "contact_info"
            },
            ad_agencies: {
                label: "Ad Agencies",
                icon: "campaign",
                titleKey: "name",
                subtitleKey: "location",
                descKey: "creative_director_or_leads",
                pills: ["location"],
                urlKey: "website",
                contactKey: "contact_info"
            },
            music_libraries: {
                label: "Music Libraries",
                icon: "library_music",
                titleKey: "name",
                subtitleKey: "submission_status",
                descKey: "requirements_genres",
                pills: ["payout_model"],
                urlKey: "url",
                contactKey: "submission_status"
            },
            competitions: {
                label: "Competitions",
                icon: "emoji_events",
                titleKey: "name",
                subtitleKey: "deadlines",
                descKey: "prizes_categories",
                pills: ["entry_fees_requirements"],
                urlKey: "url",
                contactKey: "deadlines"
            },
            restricted_resources: {
                label: "Restricted Resources",
                icon: "lock",
                titleKey: "source_name",
                subtitleKey: "reason_for_restriction",
                descKey: "expected_value",
                pills: ["reason_for_restriction"],
                urlKey: "url",
                contactKey: "url"
            }
        };

        let activeTab = "agencies";
        const carousel = document.getElementById('carousel');
        const navDots = document.getElementById('nav-dots');
        let panelCount = 0;
        const panelHeight = 400; // Matching CSS height
        let theta = 0;
        let radius = 0;
        
        let currAngle = 0;
        let selectedIndex = 0;
        let isDragging = false;
        let startY = 0;
        let currentY = 0;
        let velocity = 0;
        let lastFrameY = 0;
        let animationFrame;

        function init() {
            renderNav();
            switchTab(activeTab);
            
            // Map modal listeners
            document.getElementById('open-map-btn').addEventListener('click', () => {
                const modal = document.getElementById('map-modal');
                modal.classList.remove('hidden');
                modal.classList.add('flex');
            });
            document.getElementById('close-map').addEventListener('click', () => {
                const modal = document.getElementById('map-modal');
                modal.classList.remove('flex');
                modal.classList.add('hidden');
            });
        }

        function renderNav() {
            const nav = document.getElementById("categories-nav");
            nav.innerHTML = "";
            
            Object.keys(categoryConfigs).forEach(key => {
                const config = categoryConfigs[key];
                const items = catalogueData[key] || [];
                
                const a = document.createElement("a");
                a.className = `flex items-center py-3 px-4 gap-3 transition-colors cursor-pointer ${key === activeTab ? 'text-primary font-bold bg-primary/5 border-l-4 border-primary' : 'text-on-surface-variant hover:bg-surface-variant/50 hover:text-on-surface border-l-4 border-transparent'}`;
                a.id = `nav-${key}`;
                a.onclick = (e) => { e.preventDefault(); switchTab(key); };
                a.innerHTML = `
                    <span class="material-symbols-outlined">${config.icon}</span>
                    <span class="font-body-md text-body-md flex-1">${config.label}</span>
                    <span class="text-xs bg-white/5 px-2 py-0.5 rounded-full">${items.length}</span>
                `;
                nav.appendChild(a);
            });
        }

        function switchTab(key) {
            document.querySelectorAll("#categories-nav a").forEach(el => {
                el.className = "flex items-center py-3 px-4 gap-3 transition-colors cursor-pointer text-on-surface-variant hover:bg-surface-variant/50 hover:text-on-surface border-l-4 border-transparent";
            });
            const activeNav = document.getElementById(`nav-${key}`);
            if (activeNav) {
                activeNav.className = "flex items-center py-3 px-4 gap-3 transition-colors cursor-pointer text-primary font-bold bg-primary/5 border-l-4 border-primary";
            }

            activeTab = key;
            const config = categoryConfigs[key];
            const headerTitle = document.querySelector(".title-area h1") || document.querySelector("header h1");
            if (headerTitle) headerTitle.innerText = `${config.label} Catalogue`;
            
            initCarousel();
        }

        function initCarousel() {
            carousel.innerHTML = "";
            navDots.innerHTML = "";
            currAngle = 0;
            velocity = 0;
            
            const items = catalogueData[activeTab] || [];
            if (items.length === 0) {
                carousel.innerHTML = `<div class="carousel-cell border-outline-variant/30 flex items-center justify-center"><p class="text-outline">No records found for this category.</p></div>`;
                return;
            }
            
            panelCount = items.length;
            theta = 360 / panelCount;
            // Handle edge cases for radius
            radius = panelCount < 3 ? 0 : Math.round((panelHeight / 2) / Math.tan(Math.PI / panelCount));
            if (radius < panelHeight/2) radius = panelHeight/2 + 20;

            const config = categoryConfigs[activeTab];

            items.forEach((item, i) => {
                const cell = document.createElement('div');
                cell.className = `carousel-cell border-outline-variant/30 flex flex-col justify-between`;
                const angle = theta * i;
                cell.style.transform = `rotateX(${angle}deg) translateZ(${radius}px)`;
                
                const colorClass = (i % 2 === 0) ? 'text-primary' : 'text-secondary';
                const borderClass = (i % 2 === 0) ? 'border-primary/20 bg-primary/5' : 'border-secondary/20 bg-secondary/5';

                const title = item[config.titleKey] || "Untitled";
                const subtitle = item[config.subtitleKey] || "";
                const desc = item[config.descKey] || "No guidelines provided.";
                const link = item[config.urlKey] || "#";

                cell.innerHTML = `
                    <div class="flex flex-col gap-6 overflow-y-auto custom-scrollbar pr-2">
                        <div class="flex justify-between items-start">
                            <div class="w-16 h-16 rounded-xl bg-surface-variant flex items-center justify-center border border-outline-variant/30 flex-shrink-0">
                                <span class="material-symbols-outlined text-3xl ${colorClass}">${config.icon}</span>
                            </div>
                            <div class="flex flex-col items-end gap-1">
                                <span class="px-2 py-0.5 rounded-full text-[10px] font-label-bold uppercase tracking-wider ${borderClass} ${colorClass}">Verified</span>
                                <div class="flex gap-2">
                                    <span class="text-[10px] text-outline-variant">RECORD ${i+1}/${panelCount}</span>
                                </div>
                            </div>
                        </div>
                        
                        <div>
                            <h2 class="font-headline-lg text-headline-lg text-on-surface">${title}</h2>
                            <div class="flex items-center gap-3 mt-1 text-on-surface-variant font-body-md">
                                <span class="flex items-center gap-1 text-xs"><span class="material-symbols-outlined text-sm">link</span><span class="truncate max-w-[150px]">${link}</span></span>
                                ${subtitle ? `<span class="w-1 h-1 rounded-full bg-outline-variant"></span><span class="flex items-center gap-1 text-xs"><span class="material-symbols-outlined text-sm">info</span>${subtitle}</span>` : ''}
                            </div>
                        </div>

                        <div class="p-4 rounded-xl bg-surface-container-lowest border border-outline-variant/20">
                            <h3 class="text-[10px] font-label-bold uppercase tracking-widest text-outline mb-2 flex items-center gap-2">
                                <span class="material-symbols-outlined text-sm">description</span>Details
                            </h3>
                            <p class="text-sm leading-relaxed text-on-surface/80">
                                ${desc}
                            </p>
                        </div>
                    </div>

                    <div class="flex gap-3 mt-4 pt-2 border-t border-outline-variant/10">
                        <a href="${link.startsWith('http') ? link : 'http://'+link}" target="_blank" class="flex-1 ${i % 2 === 0 ? 'bg-primary text-on-primary glow-cyan' : 'bg-secondary text-white glow-crimson'} font-label-bold py-3.5 rounded-xl flex items-center justify-center gap-2 hover:scale-[1.02] transition-transform">
                            Visit Link <span class="material-symbols-outlined text-sm">open_in_new</span>
                        </a>
                    </div>
                `;
                carousel.appendChild(cell);

                // Add Indicator Dot
                const dot = document.createElement('div');
                dot.className = `w-1.5 h-1.5 rounded-full transition-all duration-300 ${i === 0 ? 'w-6 bg-primary' : 'bg-outline-variant/40'}`;
                navDots.appendChild(dot);
            });
            updateCarousel();
        }

        function updateCarousel() {
            if (panelCount === 0) return;
            // Apply rotation to container
            carousel.style.transform = `translateZ(-${radius}px) rotateX(${-currAngle}deg)`;
            
            // Calculate active index
            const rawIndex = Math.round(currAngle / theta) % panelCount;
            selectedIndex = rawIndex < 0 ? panelCount + rawIndex : rawIndex;

            // Visual depth management
            const cells = carousel.children;
            for (let i = 0; i < cells.length; i++) {
                const diff = Math.abs(i - selectedIndex);
                const loopDiff = Math.abs((i + panelCount) - selectedIndex);
                const loopDiffBack = Math.abs(i - (selectedIndex + panelCount));
                const finalDiff = Math.min(diff, loopDiff, loopDiffBack);
                
                if (finalDiff === 0) {
                    cells[i].classList.remove('is-inactive');
                    cells[i].style.opacity = '1';
                    cells[i].style.filter = 'none';
                    cells[i].style.scale = '1';
                } else if (finalDiff === 1) {
                    cells[i].classList.add('is-inactive');
                    cells[i].style.opacity = '0.5';
                    cells[i].style.filter = 'blur(1px)';
                    cells[i].style.scale = '0.92';
                } else {
                    cells[i].classList.add('is-inactive');
                    cells[i].style.opacity = '0.1';
                    cells[i].style.filter = 'blur(4px)';
                    cells[i].style.scale = '0.85';
                }
            }

            // Update dots
            const dots = navDots.children;
            for (let i = 0; i < dots.length; i++) {
                if (i === selectedIndex) {
                    dots[i].className = 'w-6 h-1.5 rounded-full bg-primary transition-all duration-300 glow-cyan';
                } else {
                    dots[i].className = 'w-1.5 h-1.5 rounded-full bg-outline-variant/40 transition-all duration-300';
                }
            }
        }

        // --- Interaction Logic ---

        const rolodexCanvas = document.getElementById('rolodex-canvas');

        // Snap logic
        function snapToNearest() {
            if (panelCount === 0) return;
            const snapAngle = Math.round(currAngle / theta) * theta;
            currAngle = snapAngle;
            updateCarousel();
        }

        // Dragging
        rolodexCanvas.addEventListener('mousedown', (e) => {
            isDragging = true;
            startY = e.clientY;
            lastFrameY = e.clientY;
            velocity = 0;
            if (animationFrame) cancelAnimationFrame(animationFrame);
        });

        window.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const deltaY = e.clientY - lastFrameY;
            lastFrameY = e.clientY;
            
            // Adjust sensitivity
            currAngle += (deltaY * 0.2); 
            velocity = deltaY * 0.5;
            updateCarousel();
        });

        window.addEventListener('mouseup', () => {
            if (!isDragging) return;
            isDragging = false;
            applyInertia();
        });

        // Wheel
        rolodexCanvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            currAngle += (e.deltaY * 0.1);
            updateCarousel();
            
            // Simple debounce for snap
            clearTimeout(window.wheelTimeout);
            window.wheelTimeout = setTimeout(snapToNearest, 150);
        }, { passive: false });

        function applyInertia() {
            if (Math.abs(velocity) < 0.1) {
                snapToNearest();
                return;
            }
            
            currAngle += velocity;
            velocity *= 0.95; // Friction
            updateCarousel();
            animationFrame = requestAnimationFrame(applyInertia);
        }

        function rotateToNext() {
            if (panelCount === 0) return;
            currAngle += theta;
            snapToNearest();
        }

        function rotateToPrev() {
            if (panelCount === 0) return;
            currAngle -= theta;
            snapToNearest();
        }

        // Keyboard navigation
        window.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowUp') rotateToPrev();
            if (e.key === 'ArrowDown') rotateToNext();
        });

        // Init
        document.addEventListener('DOMContentLoaded', init);
"""

js_start = stitch_html.find('<script>')
if js_start == -1:
    print("Could not find <script> tag in stitch HTML!")
    exit(1)

# we know there's `<script id="tailwind-config">` earlier, so we need to find the second `<script>`
js_starts = [m.start() for m in re.finditer(r'<script>', stitch_html)]
last_script_start = js_starts[-1]

stitch_html = stitch_html[:last_script_start] + f"<script>\\n{js_logic}\\n</script>\\n</body></html>"

# Read scrape_agent.py
with open(target_file, "r") as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if line.strip() == 'html_template = r"""<!DOCTYPE html>':
        start_idx = i
    elif start_idx != -1 and line.strip() == '</html>"""':
        end_idx = i
        break

if start_idx == -1 or end_idx == -1:
    print("Could not find html_template block in scrape_agent.py")
    exit(1)

# Reconstruct scrape_agent.py
new_lines = lines[:start_idx]
new_lines.append('    html_template = r"""' + stitch_html + '"""\\n')
new_lines.extend(lines[end_idx+1:])

with open(target_file, "w") as f:
    f.writelines(new_lines)

print("Updated scrape_agent.py successfully.")
