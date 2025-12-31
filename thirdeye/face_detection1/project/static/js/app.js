let cat = null;
let items = {};
let positions = {}; // Store positions for each category
let sizes = {}; // Store sizes for each category
let drag = null;
let resize = null;
let ox = 0;
let oy = 0;
let originalWidth = 0;
let originalHeight = 0;

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.cat-btn').forEach(b => {
        b.onclick = () => {
            document.querySelectorAll('.cat-btn').forEach(x => x.classList.remove('active'));
            b.classList.add('active');
            cat = b.dataset.cat;
            load(cat);
        };
    });
    
    document.onmousemove = move;
    document.onmouseup = stop;
    
    const clearBtn = document.getElementById('clear');
    if (clearBtn) {
        clearBtn.onclick = () => {
            Object.values(items).forEach(i => i.remove());
            items = {};
            positions = {}; // Clear saved positions
            sizes = {}; // Clear saved sizes
        };
    }
    
    const delBtn = document.getElementById('del');
    if (delBtn) {
        delBtn.onclick = () => {
            if (cat && items[cat]) {
                items[cat].remove();
                delete items[cat];
                delete positions[cat]; // Clear saved position for this category
                delete sizes[cat]; // Clear saved size for this category
            }
        };
    }
    
    const saveBtn = document.getElementById('save');
    if (saveBtn) {
        saveBtn.onclick = () => {
            let d = Object.entries(items).map(([c, e]) => ({
                category: c,
                filename: e.dataset.filename,
                x: parseInt(e.style.left),
                y: parseInt(e.style.top)
            }));
            fetch('/save-sketch', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({sketchData: {items: d, timestamp: new Date().toISOString()}})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    alert('Sketch saved successfully!');
                } else {
                    alert('Error saving sketch');
                }
            })
            .catch(() => alert('Error saving sketch'));
        };
    }
    
    const exportBtn = document.getElementById('export');
    if (exportBtn) {
        exportBtn.onclick = () => {
            exportCanvasToPNG();
        };
    }
});

function load(c) {
    document.getElementById('title').textContent = c.toUpperCase();
    let g = document.getElementById('grid');
    g.innerHTML = 'Loading...';
    fetch(`/assets/${c}`)
        .then(r => r.json())
        .then(d => {
            g.innerHTML = '';
            d.assets.forEach(a => {
                let div = document.createElement('div');
                div.className = 'asset';
                div.innerHTML = `<img src="/static/assets/${c}/${a}">`;
                div.onclick = () => add(c, a);
                g.appendChild(div);
            });
        });
}

function add(c, f) {
    if (items[c]) items[c].remove();
    let div = document.createElement('div');
    div.className = 'item';
    div.dataset.category = c;
    div.dataset.filename = f;
    
    let img = document.createElement('img');
    img.src = `/static/assets/${c}/${f}`;
    
    // Create resize handle
    let resizeHandle = document.createElement('div');
    resizeHandle.className = 'resize-handle';
    
    div.appendChild(img);
    div.appendChild(resizeHandle);
    
    // Use persisted position if available, otherwise use default
    let p;
    if (positions[c]) {
        p = positions[c];
    } else {
        p = {heads:{x:200,y:100},hair:{x:100,y:50},eyes:{x:220,y:280},eyebrows:{x:220,y:250},noses:{x:290,y:330},mouths:{x:270,y:410},ears:{x:160,y:280},mustach:{x:250,y:390}}[c] || {x:150,y:150};
        positions[c] = p; // Store initial position
    }
    
    // Set z-index based on category layering order (background to foreground)
    let zIndex = {heads:1, ears:2, hair:3, eyebrows:4, eyes:5, noses:6, mouths:7, mustach:8}[c] || 5;
    
    div.style.left = p.x + 'px';
    div.style.top = p.y + 'px';
    div.style.zIndex = zIndex;
    div.style.transition = 'opacity 0.2s, transform 0.1s';
    
    // Load image and set size
    img.onload = () => {
        if (sizes[c]) {
            img.style.width = sizes[c].width + 'px';
            img.style.height = sizes[c].height + 'px';
        } else {
            sizes[c] = {
                width: img.naturalWidth,
                height: img.naturalHeight
            };
        }
    };
    
    // Drag functionality
    div.onmousedown = e => {
        if (e.target === resizeHandle) return;
        e.preventDefault();
        drag = div;
        let r = div.getBoundingClientRect();
        ox = e.clientX - r.left;
        oy = e.clientY - r.top;
        div.style.transition = 'none'; // Disable transition during drag
        div.style.cursor = 'grabbing';
        div.style.opacity = '0.8';
        div.style.transform = 'scale(1.05)';
        div.style.zIndex = '999'; // Bring to front while dragging
    };
    
    // Resize functionality
    resizeHandle.onmousedown = e => {
        e.preventDefault();
        e.stopPropagation();
        resize = div;
        let r = div.getBoundingClientRect();
        ox = e.clientX;
        oy = e.clientY;
        originalWidth = img.offsetWidth;
        originalHeight = img.offsetHeight;
        div.classList.add('resizing');
        div.style.transition = 'none';
    };
    
    document.getElementById('canvas').appendChild(div);
    items[c] = div;
}

function move(e) {
    if (drag) {
        let c = document.getElementById('canvas').getBoundingClientRect();
        let x = e.clientX - c.left - ox;
        let y = e.clientY - c.top - oy;
        x = Math.max(0, Math.min(x, c.width - drag.offsetWidth));
        y = Math.max(0, Math.min(y, c.height - drag.offsetHeight));
        drag.style.left = x + 'px';
        drag.style.top = y + 'px';
    } else if (resize) {
        let dx = e.clientX - ox;
        let dy = e.clientY - oy;
        
        let img = resize.querySelector('img');
        let newWidth = originalWidth + dx;
        let newHeight = originalHeight + dy;
        
        // Minimum size constraint
        newWidth = Math.max(50, newWidth);
        newHeight = Math.max(50, newHeight);
        
        img.style.width = newWidth + 'px';
        img.style.height = newHeight + 'px';
    }
}

function stop() {
    if (drag) {
        // Save the final position
        let category = drag.dataset.category;
        positions[category] = {
            x: parseInt(drag.style.left),
            y: parseInt(drag.style.top)
        };
        
        // Restore visual state and z-index
        let zIndex = {heads:1, ears:2, hair:3, eyebrows:4, eyes:5, noses:6, mouths:7, mustach:8}[category] || 5;
        drag.style.transition = 'opacity 0.2s, transform 0.1s';
        drag.style.cursor = 'grab';
        drag.style.opacity = '1';
        drag.style.transform = 'scale(1)';
        drag.style.zIndex = zIndex; // Restore proper z-index
    }
    
    if (resize) {
        // Save the final size
        let category = resize.dataset.category;
        let img = resize.querySelector('img');
        sizes[category] = {
            width: img.offsetWidth,
            height: img.offsetHeight
        };
        
        resize.classList.remove('resizing');
        resize.style.transition = 'opacity 0.2s, transform 0.1s';
    }
    
    drag = null;
    resize = null;
}

function exportCanvasToPNG() {
    const canvas = document.getElementById('canvas');
    
    if (Object.keys(items).length === 0) {
        alert('Please add some elements to the canvas before exporting!');
        return;
    }
    
    // Check if html2canvas is loaded
    if (typeof html2canvas === 'undefined') {
        alert('Export library not loaded. Please refresh the page and try again.');
        return;
    }
    
    // Hide resize handles during export
    document.querySelectorAll('.resize-handle').forEach(handle => {
        handle.style.display = 'none';
    });
    
    // Use html2canvas to capture the canvas
    html2canvas(canvas, {
        backgroundColor: null,
        scale: 2,
        logging: false,
        useCORS: true,
        allowTaint: true,
        foreignObjectRendering: false
    }).then(canvasElement => {
        // Show resize handles again
        document.querySelectorAll('.resize-handle').forEach(handle => {
            handle.style.display = '';
        });
        
        // Convert canvas to blob
        canvasElement.toBlob(blob => {
            if (!blob) {
                alert('Error creating image. Please try again.');
                return;
            }
            
            // Create a download link
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            
            // Generate filename with timestamp
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
            link.download = `face_sketch_${timestamp}.png`;
            link.href = url;
            
            // Trigger download
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            // Clean up
            setTimeout(() => URL.revokeObjectURL(url), 100);
            
            alert('PNG exported successfully!');
        }, 'image/png');
    }).catch(error => {
        // Show resize handles again in case of error
        document.querySelectorAll('.resize-handle').forEach(handle => {
            handle.style.display = '';
        });
        console.error('Error exporting canvas:', error);
        alert('Error exporting PNG: ' + error.message);
    });
}
