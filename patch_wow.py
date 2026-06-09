import re

target_file = "/Users/maryann/sync_licensing_agent/dashboard_template.html"

with open(target_file, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update CSS
css_old_scene = """        .scene {
            width: 800px;
            height: 500px;
            perspective: 1500px;
            position: relative;
            display: flex;
            align-items: flex-end;
            justify-content: center;
        }"""
css_new_scene = """        .scene {
            width: 100%;
            height: 100%;
            flex: 1;
            perspective: 1500px;
            position: relative;
            display: flex;
            align-items: flex-end;
            justify-content: center;
        }"""

content = content.replace(css_old_scene, css_new_scene)

css_old_cell = """        .carousel-cell {
            position: absolute;
            width: 100%;
            height: 400px;
            left: 0;
            bottom: 50px;
            background-color: #171f33 !important; /* Solid surface-container */"""
css_new_cell = """        .carousel-cell {
            position: absolute;
            width: 90vw;
            max-width: 1100px;
            height: 65vh;
            max-height: 650px;
            left: 50%;
            transform: translateX(-50%); /* Center horizontally */
            bottom: 80px;
            background-color: #171f33 !important; /* Solid surface-container */"""

content = content.replace(css_old_cell, css_new_cell)

# 2. Update JS Logic (updateCarousel)
js_old = """                if (delta > 0) {
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
                cells[i].style.transform = `translateZ(${zOffset}px) rotateX(${rotation}deg)`;"""

js_new = """                let scale = 1;
                let yOffset = 0;

                if (delta > 0) {
                    // Card is back/inactive in the queue
                    const factor = Math.min(1, delta);
                    rotation = -90 * factor;
                    zIndex = panelCount - i;
                    
                    // Stagger backwards and upwards to create a grand staircase
                    zOffset = -delta * 60; 
                    yOffset = -delta * 30; 
                } else if (delta < 0) {
                    // Card is flipped/front
                    const factor = Math.min(1, -delta);
                    rotation = 110 * factor;
                    zIndex = i;
                    
                    // Flipped cards stack closely at the bottom
                    zOffset = delta * 15;
                    yOffset = 0;
                } else {
                    // Active card pops out
                    rotation = 0;
                    zIndex = panelCount + 10;
                    scale = 1.05;
                }

                // Apply transform with centering X (due to left: 50%)
                cells[i].style.transform = `translateX(-50%) translateZ(${zOffset}px) translateY(${yOffset}px) rotateX(${rotation}deg) scale(${scale})`;"""

content = content.replace(js_old, js_new)

with open(target_file, "w", encoding="utf-8") as f:
    f.write(content)
print("Applied WOW patch.")
