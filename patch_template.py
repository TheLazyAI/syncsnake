import re

target_file = "/Users/maryann/sync_licensing_agent/dashboard_template.html"

with open(target_file, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update CSS
css_old = """        /* 3D Scene Styles for Rolodex */
        .scene {
            width: 800px;
            height: 500px;
            perspective: 1200px;
            position: relative;
        }
        .carousel {
            width: 100%;
            height: 100%;
            position: absolute;
            transform-style: preserve-3d;
            transition: transform 0.1s;
        }
        .carousel-cell {
            position: absolute;
            width: 100%;
            height: 400px;
            left: 0;
            top: 50px;
            background: rgba(23, 31, 51, 0.85);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(133, 147, 151, 0.3);
            border-radius: 24px;
            backface-visibility: hidden;
            padding: 32px;
            display: flex;
            flex-direction: column;
            transition: opacity 0.5s, filter 0.5s, transform 0.5s;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5);
        }"""

css_new = """        /* 3D Scene Styles for Rolodex - Solid Mechanical */
        .scene {
            width: 800px;
            height: 500px;
            perspective: 1500px;
            position: relative;
            display: flex;
            align-items: flex-end;
            justify-content: center;
        }
        .carousel {
            width: 100%;
            height: 100%;
            position: absolute;
            transform-style: preserve-3d;
            bottom: 0;
        }
        .carousel-cell {
            position: absolute;
            width: 100%;
            height: 400px;
            left: 0;
            bottom: 50px;
            background-color: #171f33 !important; /* Solid surface-container */
            backdrop-filter: none !important;
            border: 2px solid #3c494c !important; /* Thicker mechanical border */
            border-radius: 24px;
            backface-visibility: hidden;
            padding: 32px;
            display: flex;
            flex-direction: column;
            transform-origin: bottom center; /* MECHANICAL ANCHOR */
            box-shadow: 0 20px 40px rgba(0,0,0,0.8);
            transition: transform 0.4s cubic-bezier(0.19, 1, 0.22, 1), opacity 0.4s, filter 0.4s;
        }
        
        .carousel-cell.bg-on-surface {
            background-color: #dae2fd !important; /* Solid Light */
            color: #0b1326 !important;
        }
        .carousel-cell.bg-primary {
            background-color: #22d3ee !important; /* Solid Cyan */
        }
        .carousel-cell.bg-secondary {
            background-color: #aa0266 !important; /* Solid Crimson */
        }
        
        .carousel-cell.is-inactive {
            filter: brightness(0.4) grayscale(0.2) !important;
            pointer-events: none;
        }"""

if css_old in content:
    content = content.replace(css_old, css_new)
else:
    print("WARNING: Could not find old CSS block to replace.")

# 2. Add Spine HTML
spine_html = """            <div class="scene" id="scene">
                <div class="absolute bottom-[50px] w-[90%] h-[12px] rounded-full left-[5%] z-10" style="background: linear-gradient(to bottom, #3c494c, #171f33, #3c494c); box-shadow: 0 4px 12px rgba(0,0,0,0.8);"></div>
                <div class="carousel" id="carousel">"""
content = content.replace('            <div class="scene" id="scene">\n                <div class="carousel" id="carousel">', spine_html)

# 3. Update JS Logic
js_split = content.split('// ==========================================\n        // 3D ROLODEX LOGIC (Showcase View)\n        // ==========================================')
if len(js_split) == 2:
    js_logic_part = js_split[1]
    js_logic_split = js_logic_part.split('// ==========================================\n        // EXPANDED BENTO GRID LOGIC\n        // ==========================================')
    if len(js_logic_split) == 2:
        new_js = """
        function initCarousel() {
            carousel.innerHTML = "";
            navDots.innerHTML = "";
            currAngle = 0; velocity = 0;
            
            const items = catalogueData[activeTab] || [];
            if (items.length === 0) {
                carousel.innerHTML = `<div class="carousel-cell flex items-center justify-center text-outline">No records found.</div>`;
                return;
            }
            
            panelCount = items.length;

            const config = categoryConfigs[activeTab];

            items.forEach((item, i) => {
                const cell = document.createElement('div');
                
                const themeIndex = i % 3;
                let themeClasses = "";
                let titleColor = "text-on-surface";
                let subTextColor = "text-outline";
                let iconColor = "text-primary";
                let actionBtn = "bg-primary text-on-primary";

                if (themeIndex === 0) {
                    themeClasses = "carousel-cell bg-surface-container";
                } else if (themeIndex === 1) {
                    themeClasses = "carousel-cell bg-on-surface text-surface-container-lowest";
                    titleColor = "text-surface-container-lowest";
                    subTextColor = "text-surface-container-low/70";
                    iconColor = "text-surface-container-lowest";
                    actionBtn = "bg-surface-container-lowest text-on-surface";
                } else {
                    const isPrimary = i % 2 === 0;
                    themeClasses = isPrimary ? "carousel-cell bg-primary text-on-primary" : "carousel-cell bg-secondary text-white";
                    titleColor = isPrimary ? "text-on-primary" : "text-white";
                    subTextColor = isPrimary ? "text-on-primary/70" : "text-white/70";
                    iconColor = isPrimary ? "text-on-primary" : "text-white";
                    actionBtn = isPrimary ? "bg-on-primary text-primary" : "bg-on-secondary text-secondary";
                }

                cell.className = themeClasses;

                const title = item[config.titleKey] || "Untitled";
                const subtitle = item[config.subtitleKey] || "";
                const desc = item[config.descKey] || "No details provided.";
                const link = item[config.urlKey] || "#";

                cell.innerHTML = `
                    <div class="flex flex-col gap-6 overflow-y-auto custom-scrollbar pr-2 h-full">
                        <div class="flex justify-between items-start">
                            <div class="w-14 h-14 rounded-2xl bg-black/10 border border-white/20 flex items-center justify-center flex-shrink-0 shadow-inner">
                                <span class="material-symbols-outlined text-3xl ${iconColor}">${config.icon}</span>
                            </div>
                            <div class="flex flex-col items-end gap-2">
                                <span class="px-3 py-1 rounded-full text-[9px] font-black uppercase tracking-widest bg-black/10 border border-white/20 ${iconColor}">Verified</span>
                                <span class="text-[10px] font-mono opacity-50">RECORD ${i+1}/${panelCount}</span>
                            </div>
                        </div>
                        
                        <div>
                            <h2 class="text-3xl font-bold ${titleColor} tracking-tight leading-tight">${title}</h2>
                            <div class="flex items-center gap-3 mt-2 ${subTextColor} font-medium text-sm">
                                ${subtitle ? `<span class="flex items-center gap-1"><span class="material-symbols-outlined text-[16px]">info</span>${subtitle}</span>` : ''}
                            </div>
                        </div>

                        <div class="p-5 rounded-2xl bg-black/5 border border-white/10 relative overflow-hidden flex-1">
                            <h3 class="text-[10px] font-bold uppercase tracking-widest opacity-60 mb-2 flex items-center gap-2">
                                <span class="material-symbols-outlined text-[16px]">subject</span>Details
                            </h3>
                            <p class="text-sm leading-relaxed opacity-90 font-light">
                                ${desc}
                            </p>
                        </div>
                        
                        <div class="pt-4 flex gap-3">
                            <a href="${link.startsWith('http') ? link : 'http://'+link}" target="_blank" class="flex-1 ${actionBtn} text-xs font-bold uppercase tracking-widest py-4 rounded-xl flex items-center justify-center gap-2 tactile-btn border border-black/10">
                                Visit Resource <span class="material-symbols-outlined text-[18px]">open_in_new</span>
                            </a>
                        </div>
                    </div>
                `;
                carousel.appendChild(cell);

                const dot = document.createElement('div');
                dot.className = `h-1.5 rounded-full transition-all duration-300 ${i === 0 ? 'w-6 bg-primary glow-cyan' : 'w-1.5 bg-outline-variant/40'}`;
                navDots.appendChild(dot);
            });
            updateCarousel();
        }

        function updateCarousel() {
            if (panelCount === 0) return;
            
            // currAngle represents currentRotation index
            const currentRotation = currAngle;
            
            // Calculate active index
            selectedIndex = Math.round(currentRotation);
            if (selectedIndex < 0) selectedIndex = 0;
            if (selectedIndex >= panelCount) selectedIndex = panelCount - 1;

            const cells = carousel.children;
            for (let i = 0; i < cells.length; i++) {
                const delta = i - currentRotation;
                let rotation = 0;
                let zIndex = 0;
                let zOffset = 0;

                if (delta > 0) {
                    // Card is back/inactive
                    const factor = Math.min(1, delta);
                    rotation = -90 * factor;
                    zIndex = panelCount - i;
                    zOffset = -delta * 0.5; // Slight stack effect
                } else if (delta < 0) {
                    // Card is flipped/front
                    const factor = Math.min(1, -delta);
                    rotation = 110 * factor;
                    zIndex = i;
                    zOffset = delta * 0.5;
                } else {
                    // Active card
                    rotation = 0;
                    zIndex = panelCount + 10;
                }

                // Apply transform
                cells[i].style.transform = `translateZ(${zOffset}px) rotateX(${rotation}deg)`;
                cells[i].style.zIndex = zIndex;
                
                // Visual effects
                const dist = Math.abs(delta);
                if (dist < 0.5) {
                    cells[i].classList.remove('is-inactive');
                } else {
                    cells[i].classList.add('is-inactive');
                }
            }

            const dots = navDots.children;
            for (let i = 0; i < dots.length; i++) {
                dots[i].className = `h-1.5 rounded-full transition-all duration-300 ${i === selectedIndex ? 'w-6 bg-primary glow-cyan' : 'w-1.5 bg-outline-variant/40'}`;
            }
        }

        function setupRolodexInteraction() {
            const rc = document.getElementById('rolodex-canvas');
            
            function snapToNearest() {
                if (panelCount === 0) return;
                
                let target = Math.round(currAngle);
                if (target < 0) target = 0;
                if (target >= panelCount) target = panelCount - 1;
                
                const start = currAngle;
                const change = target - start;
                let currentTime = 0;
                const duration = 25; // frames

                function animateSnap() {
                    currentTime++;
                    const t = currentTime / duration;
                    const ease = 1 - Math.pow(1 - t, 3);
                    currAngle = start + change * ease;
                    updateCarousel();
                    if (currentTime < duration) {
                        animationFrame = requestAnimationFrame(animateSnap);
                    }
                }
                if (animationFrame) cancelAnimationFrame(animationFrame);
                animateSnap();
            }

            rc.addEventListener('mousedown', (e) => {
                isDragging = true; lastFrameY = e.clientY; velocity = 0;
                if (animationFrame) cancelAnimationFrame(animationFrame);
            });
            window.addEventListener('mousemove', (e) => {
                if (!isDragging) return;
                const deltaY = e.clientY - lastFrameY; lastFrameY = e.clientY;
                // Map Y pixels to rotation index
                currAngle += (deltaY * 0.015); 
                velocity = deltaY * 0.02;
                updateCarousel();
            });
            window.addEventListener('mouseup', () => {
                if (!isDragging) return;
                isDragging = false; applyInertia();
            });
            rc.addEventListener('wheel', (e) => {
                e.preventDefault();
                currAngle += (e.deltaY * 0.005); updateCarousel();
                clearTimeout(window.wheelTimeout);
                window.wheelTimeout = setTimeout(snapToNearest, 200);
            }, { passive: false });

            function applyInertia() {
                if (Math.abs(velocity) < 0.005) { snapToNearest(); return; }
                currAngle += velocity; velocity *= 0.92;
                
                // Bounds
                if (currAngle < -1 || currAngle > panelCount) {
                    snapToNearest(); return;
                }
                
                updateCarousel(); animationFrame = requestAnimationFrame(applyInertia);
            }
        }
        
        function rotateToNext() { 
            if (panelCount) { 
                let target = Math.round(currAngle) + 1;
                if (target >= panelCount) target = panelCount - 1;
                animateTo(target); 
            } 
        }
        function rotateToPrev() { 
            if (panelCount) { 
                let target = Math.round(currAngle) - 1;
                if (target < 0) target = 0;
                animateTo(target); 
            } 
        }
        function animateTo(target) {
            const start = currAngle;
            const change = target - start;
            let t = 0;
            function frame() {
                t += 0.05;
                if (t >= 1) {
                    currAngle = target;
                    updateCarousel();
                    return;
                }
                const ease = 1 - Math.pow(1 - t, 4);
                currAngle = start + change * ease;
                updateCarousel();
                requestAnimationFrame(frame);
            }
            if (animationFrame) cancelAnimationFrame(animationFrame);
            frame();
        }

        window.addEventListener('keydown', (e) => {
            if (currentView === "showcase") {
                if (e.key === 'ArrowUp') rotateToPrev();
                if (e.key === 'ArrowDown') rotateToNext();
            }
        });

"""
        content = content.replace(js_logic_part, new_js + '// ==========================================\n        // EXPANDED BENTO GRID LOGIC\n        // ==========================================\n' + js_logic_split[1])
    else:
        print("WARNING: Could not split at expanded bento logic")
else:
    print("WARNING: Could not split JS logic.")

with open(target_file, "w", encoding="utf-8") as f:
    f.write(content)
print("Applied Python patch.")
