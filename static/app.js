// View Navigation
function showView(viewId) {
    document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
    document.getElementById(viewId).classList.add('active');
}

// Shader Logic for Landing Page
(function() {
    const canvas = document.getElementById('shader-canvas-ANIMATION_2');
    if (!canvas) return;

    function syncSize() {
        const w = canvas.clientWidth || 1280;
        const h = canvas.clientHeight || 720;
        if (canvas.width !== w || canvas.height !== h) {
            canvas.width = w;
            canvas.height = h;
        }
    }
    if (typeof ResizeObserver !== 'undefined') {
        new ResizeObserver(syncSize).observe(canvas);
    }
    syncSize();

    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    if (!gl) return;
    const vs = `attribute vec2 a_position;
    varying vec2 v_texCoord;
    void main() {
    v_texCoord = a_position * 0.5 + 0.5;
    gl_Position = vec4(a_position, 0.0, 1.0);
    }`;
    const fs = `precision highp float;
    uniform float u_time;
    uniform vec2 u_resolution;
    float noise(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
    void main() {
        vec2 uv = gl_FragCoord.xy / u_resolution.xy;
        uv.x *= u_resolution.x / u_resolution.y;
        vec3 color1 = vec3(0.1, 0.04, 0.0);
        vec3 color2 = vec3(0.05, 0.05, 0.05);
        float n = 0.0;
        vec2 p = uv * 3.0;
        for(float i=1.0; i<4.0; i++) {
            p += vec2(sin(u_time * 0.1 * i + p.y), cos(u_time * 0.1 * i + p.x));
            n += noise(p) * (1.0 / i);
        }
        vec3 finalColor = mix(color1, color2, uv.y + n * 0.1);
        for(float i=0.0; i<10.0; i++) {
            vec2 pos = vec2(noise(vec2(i, 1.0)), noise(vec2(i, 2.0)));
            pos.x += sin(u_time * 0.2 + i) * 0.1;
            pos.y += cos(u_time * 0.2 + i) * 0.1;
            float d = distance(uv, pos);
            float glow = smoothstep(0.15, 0.0, d);
            finalColor += vec3(1.0, 0.34, 0.13) * glow * 0.05;
        }
        gl_FragColor = vec4(finalColor, 1.0);
    }`;
    function cs(type, src) {
        const s = gl.createShader(type);
        gl.shaderSource(s, src);
        gl.compileShader(s);
        return s;
    }
    const prog = gl.createProgram();
    gl.attachShader(prog, cs(gl.VERTEX_SHADER, vs));
    gl.attachShader(prog, cs(gl.FRAGMENT_SHADER, fs));
    gl.linkProgram(prog);
    gl.useProgram(prog);
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 1,-1, -1,1, 1,1]), gl.STATIC_DRAW);
    const pos = gl.getAttribLocation(prog, 'a_position');
    gl.enableVertexAttribArray(pos);
    gl.vertexAttribPointer(pos, 2, gl.FLOAT, false, 0, 0);
    const uTime = gl.getUniformLocation(prog, 'u_time');
    const uRes = gl.getUniformLocation(prog, 'u_resolution');
    
    function render(t) {
        if (typeof ResizeObserver === 'undefined') syncSize();
        gl.viewport(0, 0, canvas.width, canvas.height);
        if (uTime) gl.uniform1f(uTime, t * 0.001);
        if (uRes) gl.uniform2f(uRes, canvas.width, canvas.height);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
        requestAnimationFrame(render);
    }
    render(0);
})();

// Budget indicator sliding logic
document.addEventListener("DOMContentLoaded", () => {
    const budgetRadios = document.querySelectorAll('input[name="budget"]');
    const indicator = document.getElementById('budget-indicator');
    
    budgetRadios.forEach((radio, index) => {
        radio.addEventListener('change', () => {
            if (index === 0) {
                indicator.style.left = '4px';
            } else if (index === 1) {
                indicator.style.left = 'calc(33.33% + 2px)';
            } else if (index === 2) {
                indicator.style.left = 'calc(66.66% + 0px)';
            }
        });
    });

    const ratingInput = document.getElementById('rating');
    const ratingFill = document.getElementById('rating-fill');
    const ratingVal = document.getElementById('rating-val');
    ratingInput.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        ratingVal.textContent = val.toFixed(1);
        const percentage = ((val - 3.0) / 2.0) * 100;
        ratingFill.style.width = percentage + '%';
    });

    // Fetch cities and populate dropdown
    fetch('/cities')
        .then(res => res.json())
        .then(data => {
            const locSelect = document.getElementById('location');
            if(data.cities && data.cities.length > 0) {
                data.cities.forEach(city => {
                    const opt = document.createElement('option');
                    opt.value = city;
                    opt.textContent = city;
                    locSelect.appendChild(opt);
                });
            } else {
                // Fallback cities
                ['Delhi', 'Gurgaon', 'Noida', 'Faridabad', 'Ghaziabad'].forEach(city => {
                    const opt = document.createElement('option');
                    opt.value = city;
                    opt.textContent = city;
                    locSelect.appendChild(opt);
                });
            }
        })
        .catch(err => console.error("Error fetching cities:", err));

    // Form Submission
    const form = document.getElementById('preferences-form');
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const location = document.getElementById('location').value;
        if (!location) {
            alert('Please select a location');
            return;
        }

        const budget = document.querySelector('input[name="budget"]:checked').value;
        const minRating = parseFloat(document.getElementById('rating').value);
        const vibe = document.getElementById('vibe').value;

        const cuisineChecks = document.querySelectorAll('.cuisine-checkbox:checked');
        const cuisines = Array.from(cuisineChecks).map(c => c.value);

        const requestData = {
            location: location,
            cuisines: cuisines,
            budget_tier: budget,
            min_rating: minRating,
            additional_notes: vibe
        };

        // Transition to Processing
        showView('view-processing');
        startProcessingAnimation();

        fetch('/recommend', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        })
        .then(res => res.json())
        .then(data => {
            stopProcessingAnimation();
            renderResults(data, requestData);
        })
        .catch(err => {
            console.error("Error during recommendation:", err);
            stopProcessingAnimation();
            alert("An error occurred while fetching recommendations.");
            showView('view-preferences');
        });
    });
});

let messageInterval;
function startProcessingAnimation() {
    const messages = document.querySelectorAll('.fade-text');
    let currentMessage = 0;
    messages.forEach(m => m.classList.remove('active'));
    messages[0].classList.add('active');

    if(messageInterval) clearInterval(messageInterval);
    messageInterval = setInterval(() => {
        messages[currentMessage].classList.remove('active');
        currentMessage = (currentMessage + 1) % messages.length;
        messages[currentMessage].classList.add('active');
    }, 2000);
}

function stopProcessingAnimation() {
    if(messageInterval) clearInterval(messageInterval);
}

function renderResults(data, requestData) {
    if(!data.recommendations || data.recommendations.length === 0) {
        showView('view-no-results');
        return;
    }

    // Populate Filters Header
    const filtersContainer = document.getElementById('results-filters');
    filtersContainer.innerHTML = '';
    
    // City chip
    filtersContainer.innerHTML += `
        <div class="flex items-center gap-2 px-4 py-2 rounded-full bg-surface-container border border-outline-variant font-label-sm text-label-sm text-on-surface">
            <span class="material-symbols-outlined text-primary text-[16px]" style="font-variation-settings: 'FILL' 1;">location_on</span>
            ${requestData.location}
        </div>
    `;

    // Cuisines chip
    if(requestData.cuisines.length > 0) {
        filtersContainer.innerHTML += `
            <div class="flex items-center gap-2 px-4 py-2 rounded-full bg-surface-container border border-outline-variant font-label-sm text-label-sm text-on-surface">
                <span class="material-symbols-outlined text-secondary text-[16px]" style="font-variation-settings: 'FILL' 1;">restaurant</span>
                ${requestData.cuisines.join(', ')}
            </div>
        `;
    }

    // Budget chip
    filtersContainer.innerHTML += `
        <div class="flex items-center gap-2 px-4 py-2 rounded-full bg-surface-container border border-outline-variant font-label-sm text-label-sm text-on-surface">
            <span class="material-symbols-outlined text-tertiary text-[16px]" style="font-variation-settings: 'FILL' 1;">payments</span>
            ${requestData.budget_tier.charAt(0).toUpperCase() + requestData.budget_tier.slice(1)}
        </div>
    `;

    // Populate Summary
    const summaryEl = document.getElementById('ai-summary-text');
    summaryEl.textContent = data.summaryOfChoice || "Here are your top restaurant matches.";

    // Populate Cards
    const container = document.getElementById('recommendations-container');
    container.innerHTML = '';

    data.recommendations.forEach((rec, idx) => {
        const score = rec.suitabilityScore || (data.fallback ? '--' : 'N/A');
        const scoreWidth = rec.suitabilityScore ? rec.suitabilityScore + '%' : '0%';
        const costLabel = rec.average_cost ? `₹${rec.average_cost} for two` : 'Price unknown';
        const cuisinesStr = rec.cuisines ? rec.cuisines.slice(0,3).join(', ') : '';

        // Generate Suggested Dishes Pills
        let dishesHtml = '';
        if(rec.recommendedDishesSuggest && rec.recommendedDishesSuggest.length > 0) {
            dishesHtml = rec.recommendedDishesSuggest.map(d => 
                `<span class="px-3 py-1 rounded-full bg-surface-container-high border border-outline-variant font-label-sm text-label-sm text-on-surface-variant">${d}</span>`
            ).join('');
        }

        // Build Explanation HTML
        let explanationHtml = '';
        if(rec.aiExplanation) {
            explanationHtml = `
                <div class="bg-primary/5 rounded-lg p-3 mb-4 border border-primary/10">
                    <p class="font-body-md text-body-md text-on-surface-variant italic flex items-start gap-2 text-sm">
                        <span class="material-symbols-outlined text-primary text-[16px] shrink-0 mt-0.5" style="font-variation-settings: 'FILL' 1;">auto_awesome</span>
                        ${rec.aiExplanation}
                    </p>
                </div>
            `;
        } else if (data.fallback) {
             explanationHtml = `
                <div class="bg-surface-bright rounded-lg p-3 mb-4 border border-outline-variant/30">
                    <p class="font-body-md text-body-md text-on-surface-variant italic text-sm">
                        Highly rated option based on local reviews.
                    </p>
                </div>
            `;
        }

        const card = document.createElement('article');
        card.className = "glass-panel rounded-xl overflow-hidden flex flex-col group hover:shadow-[0px_10px_30px_rgba(255,87,34,0.25)] transition-all duration-300";
        card.innerHTML = `
            <div class="p-6 flex flex-col flex-grow">
                <div class="flex justify-between items-start mb-2">
                    <div class="flex items-center gap-3">
                        <div class="w-8 h-8 rounded-full border-2 border-primary bg-surface-container flex items-center justify-center font-label-md text-label-md text-primary font-bold shadow-sm shrink-0">
                            #${rec.rank || (idx + 1)}
                        </div>
                        <h2 class="font-headline-md text-headline-md text-on-surface leading-tight">${rec.name}</h2>
                    </div>
                </div>
                
                <div class="flex flex-wrap items-center gap-2 mb-4 font-label-sm text-label-sm text-on-surface-variant mt-2">
                    <span>${cuisinesStr}</span>
                    <span>•</span>
                    <div class="flex items-center text-secondary">
                        <span class="material-symbols-outlined text-[14px]" style="font-variation-settings: 'FILL' 1;">star</span>
                        <span class="ml-1">${rec.rating || 'New'}</span>
                    </div>
                    <span>•</span>
                    <span>${costLabel}</span>
                </div>
                
                <!-- Match Score -->
                <div class="mb-4">
                    <div class="flex justify-between font-label-sm text-label-sm mb-1">
                        <span class="text-on-surface">AI Match Score</span>
                        <span class="text-primary font-semibold">${score === '--' ? score : score + '%'}</span>
                    </div>
                    <div class="h-2 w-full bg-surface-container rounded-full overflow-hidden">
                        <div class="h-full bg-primary progress-bar-fill" style="width: 0%;" data-target="${scoreWidth}"></div>
                    </div>
                </div>
                
                ${explanationHtml}
                
                <div class="flex flex-wrap gap-2 mb-6 mt-auto">
                    ${dishesHtml}
                </div>
                
                <button class="w-full py-3 rounded-lg bg-surface-container-high hover:bg-surface-bright border border-outline-variant font-label-md text-label-md text-on-surface transition-colors flex items-center justify-center gap-2 mt-auto">
                    <span class="material-symbols-outlined text-[18px]" style="font-variation-settings: 'FILL' 0;">map</span>
                    View on Map
                </button>
            </div>
        `;
        container.appendChild(card);
    });

    showView('view-results');

    // Trigger progress bar animations after DOM insertion
    setTimeout(() => {
        const bars = container.querySelectorAll('.progress-bar-fill');
        bars.forEach(bar => {
            bar.style.width = bar.getAttribute('data-target');
        });
    }, 100);
}
