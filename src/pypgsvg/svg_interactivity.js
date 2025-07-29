document.addEventListener('DOMContentLoaded', () => {
    const svg = document.children[0];
    const mainGroup = document.getElementById('main-erd-group');
    const miniatureContainer = document.getElementById('miniature-container');
    const viewportIndicator = document.getElementById('viewport-indicator');
    const overlayContainer = document.getElementById('overlay-container');
    const graphDataElement = document.getElementById('graph-data');
    const graphData = JSON.parse(graphDataElement.textContent);
    const { tables, edges } = graphData;

    // --- State variables ---
    let initialTx = 0, initialTy = 0, initialS = 1;
    let userTx = 0, userTy = 0, userS = 1;
    let isPanning = false;
    let startX = 0, startY = 0;
    let mouseDownStartX = 0, mouseDownStartY = 0;
    let dragThreshold = 5;
    let highlightedElementId = null;
    let dragState = { type: null, startX: 0, startY: 0, offsetX: 0, offsetY: 0, target: null };


        function addWindowControls(windowElem, options = {}) {
        if (!windowElem) return;
        let controls = windowElem.querySelector('.window-controls');
        if (!controls) {
            controls = document.createElement('div');
            controls.className = 'window-controls';
            controls.style.position = 'absolute';
            controls.style.top = '2px';
            controls.style.right = '2px';
            controls.style.zIndex = '10001';
            windowElem.appendChild(controls);
        }
        let minBtn = controls.querySelector('.minimize-btn');
        if (!minBtn) {
            minBtn = document.createElement('button');
            minBtn.className = 'minimize-btn';
            minBtn.title = 'Minimize';
            minBtn.innerHTML = '–';
            controls.appendChild(minBtn);
        }
        let closeBtn = controls.querySelector('.close-btn');
        if (!closeBtn) {
            closeBtn = document.createElement('button');
            closeBtn.className = 'close-btn';
            closeBtn.title = 'Close';
            closeBtn.innerHTML = '×';
            controls.appendChild(closeBtn);
        }
        minBtn.onclick = (e) => {
            e.stopPropagation();
            windowElem.classList.toggle('minimized');
            const content = windowElem.querySelector('.window-content');


            if (windowElem.classList.contains('minimized')) {
                if (content) content.style.display = 'none';
                minBtn.innerHTML = '+';
            } else {
                if (content) content.style.display = '';
                minBtn.innerHTML = '–';
            }
            if (options.onMinimize) options.onMinimize(windowElem.classList.contains('minimized'));
        };
        closeBtn.onclick = (e) => {
            e.stopPropagation();
            windowElem.style.display = 'none';
            if (options.onClose) options.onClose();
        };
        controls.addEventListener('mousedown', e => e.stopPropagation());
        controls.addEventListener('click', e => e.stopPropagation());
    }
    // --- Initialization ---
    const parseTransform = (transform) => {
        const result = { tx: 0, ty: 0, s: 1 };
        if (!transform) return result;
        const translateMatch = transform.match(/translate\(([^,)]+),([^,)]+)\)/);
        if (translateMatch) {
            result.tx = parseFloat(translateMatch[1]);
            result.ty = parseFloat(translateMatch[2]);
        }
        const scaleMatch = transform.match(/scale\(([^)]+)\)/);
        if (scaleMatch) {
            result.s = parseFloat(scaleMatch[1]);
        }
        return result;
    };
    const initialTransform = parseTransform(mainGroup ? mainGroup.getAttribute('transform') : '');
    initialTx = isNaN(initialTransform.tx) ? 0 : initialTransform.tx;
    initialTy = isNaN(initialTransform.ty) ? 0 : initialTransform.ty;
    initialS = isNaN(initialTransform.s) ? 1 : initialTransform.s;

    // --- Core Functions ---
    const getMainERDBounds = () => mainGroup.getBBox();
    const applyTransform = () => {
        const finalS = userS * initialS;
        const finalTx = (userTx * initialS) + initialTx;
        const finalTy = (userTy * initialS) + initialTy;
        mainGroup.setAttribute('transform', `translate(${finalTx} ${finalTy}) scale(${finalS})`);
        requestAnimationFrame(updateViewportIndicator);
    };
    
    const updateViewportIndicator = () => {
        if (!viewportIndicator) return;
        const mainBounds = getMainERDBounds();
        if (mainBounds.width === 0 || mainBounds.height === 0) return;
        const ctm = mainGroup.getScreenCTM();
        if (!ctm) return;
        const invCtm = ctm.inverse();
        const pt1 = svg.createSVGPoint();
        pt1.x = 0; pt1.y = 0;
        const svgPt1 = pt1.matrixTransform(invCtm);
        const pt2 = svg.createSVGPoint();
        pt2.x = window.innerWidth; pt2.y = window.innerHeight;
        const svgPt2 = pt2.matrixTransform(invCtm);
        const visibleWidth = svgPt2.x - svgPt1.x;
        const visibleHeight = svgPt2.y - svgPt1.y;
        const relLeft = (svgPt1.x - mainBounds.x) / mainBounds.width;
        const relTop = (svgPt1.y - mainBounds.y) / mainBounds.height;
        const relWidth = visibleWidth / mainBounds.width;
        const relHeight = visibleHeight / mainBounds.height;
        viewportIndicator.style.left = `${Math.max(0, Math.min(1, relLeft)) * 100}%`;
        viewportIndicator.style.top = `${Math.max(0, Math.min(1, relTop)) * 100}%`;
        viewportIndicator.style.width = `${Math.max(0, Math.min(1, relWidth)) * 100}%`;
        viewportIndicator.style.height = `${Math.max(0, Math.min(1, relHeight)) * 100}%`;
    };
    const onViewportChange = () => requestAnimationFrame(updateViewportIndicator);

    // --- Highlighting ---
    const setElementColor = (elem, color, isHighlighted = false) => {
        if (!elem) return;
        let miniElem = null;
        const nodeId = elem.id;
        if (nodeId.indexOf('mini-') == -1) {
            const miniNodeId = 'mini-' + nodeId;
            miniElem = document.getElementById(miniNodeId);
            if (miniElem) {
                setElementColor(miniElem, color, isHighlighted);
            }
        }

        if (elem.classList && elem.classList.contains('node')) {
            // Node coloring logic unchanged
            const connectedEdgeIds = tables[nodeId]?.edges || [];
            const edge1 = edges[connectedEdgeIds[0]];
            const edge2 = edges[connectedEdgeIds[1]];
            const highlightColor = edge2 ? edge2.highlightColor : color;
            const defaultColor = edge1 ? edge1.defaultColor : color;
            const strokeColor = highlightColor;

            const mainPath = elem.querySelector('path');
            if (mainPath) {
                mainPath.setAttribute('stroke', strokeColor);
                mainPath.setAttribute('stroke-width', isHighlighted ? '4' : '2');
            }

            const polygons = elem.querySelectorAll('polygon');
            polygons.forEach(polygon => {
                polygon.setAttribute('fill', defaultColor);
                polygon.setAttribute('stroke', strokeColor);
                polygon.setAttribute('stroke-width', isHighlighted ? '4' : '2');
            });
        }

        // --- PATCH: Edge highlighting for parallel splines ---
        if (elem.classList && elem.classList.contains('edge')) {
            const edgeId = elem.id;
            const connectedTables = edges[edgeId]?.tables || [];
            console.log(`Highlighting edge ${edgeId} connecting tables:`, connectedTables);
            const colorA = tables[connectedTables[0]]?.highlightColor || color;
            const colorB = tables[connectedTables[1]]?.highlightColor || color;
            const paths = elem.querySelectorAll('path');
            // For parallel splines, set colorA for first path, colorB for second path
            // To make both colors equally visible, set both paths to same stroke-width and opacity
            if (paths.length > 0) {
                paths[0].setAttribute('stroke', colorA);
                paths[0].setAttribute('stroke-width', isHighlighted ? '16' : '3');
                paths[0].setAttribute('opacity', '1');
            }
            if (paths.length > 1) {
                paths[1].setAttribute('stroke', colorB);
                paths[1].setAttribute('stroke-width', isHighlighted ? '9' : '3');
                paths[1].setAttribute('opacity', '1');
            }
            // If only one path, fallback to colorA
            if (paths.length === 1) {
                paths[0].setAttribute('stroke', colorA);
                paths[0].setAttribute('stroke-width', isHighlighted ? '10' : '3');
                paths[0].setAttribute('opacity', '1');
            }
        }
    };


    const highlightElements = (tableIds, edgeIds) => {
        tableIds.forEach(id => {
            const tableElement = document.getElementById(id);
            if (tableElement) {
                setElementColor(tableElement, tables[id].color, true);
            }
        });
        edgeIds.forEach(id => {
            const edgeElement = document.getElementById(id);
            if (edgeElement) {
                setElementColor(edgeElement, edges[id].color, true);
            }
        });

        Object.keys(tables).forEach(id => {
            if (!tableIds.includes(id)) {
                const tableElement = document.getElementById(id);
                if (tableElement) {
                    setElementColor(tableElement, tables[id].desaturatedColor, false);
                }
            }
        });
        Object.keys(edges).forEach(id => {
            if (!edgeIds.includes(id)) {
                const edgeElement = document.getElementById(id);
                if (edgeElement) {
                    setElementColor(edgeElement, edges[id].desaturatedColor, false);
                }
            }
        });
    };

    const clearAllHighlights = () => {
        Object.keys(tables).forEach(id => {
            const tableElement = document.getElementById(id);
            if (tableElement) {
                setElementColor(tableElement, tables[id].defaultColor, false);
            }
        });
        Object.keys(edges).forEach(id => {
            const edgeElement = document.getElementById(id);
            if (edgeElement) {
                setElementColor(edgeElement, edges[id].defaultColor, false);
            }
        });
        highlightedElementId = null;
    };

    // Reset pan and zoom to the initial state
    const resetZoom = () => {
        userTx = 0;
        userTy = 0;
        userS = 1;
        clearAllHighlights(); // Also clear highlights on reset
        applyTransform();
    };

    const zoomToPoint = (targetX, targetY, zoomLevel = userS) => {
        userS = zoomLevel;
        const finalS = userS * initialS;
        const pt = svg.createSVGPoint();
        pt.x = window.innerWidth / 2;
        pt.y = window.innerHeight / 2;
        const svgCenterPt = pt.matrixTransform(svg.getScreenCTM().inverse());
        const finalTx = svgCenterPt.x - targetX * finalS;
        const finalTy = svgCenterPt.y - targetY * finalS;
        userTx = (finalTx - initialTx) / initialS;
        userTy = (finalTy - initialTy) / initialS;
        applyTransform();
    };


    // --- EVENT LISTENERS ---

    // --- DRAG HANDLERS ---

    // 1. Miniature (overview window) drag
    
    const miniatureHeader = document.getElementById('miniature-header');
    if (miniatureHeader) {
        // --- Miniature drag mousedown ---
        miniatureHeader.addEventListener('mousedown', (event) => {
            dragState.type = 'miniature';
            dragState.target = miniatureContainer;
            dragState.offsetX = event.clientX;
            dragState.offsetY = event.clientY;
            dragState.target.classList.add('dragging');
            event.preventDefault();

            event.stopPropagation();
        });
        addWindowControls(miniatureContainer);





        
    }




    // 2. Viewport indicator drag (inside minimap)
    if (viewportIndicator) {
        // --- Indicator drag mousedown ---
        viewportIndicator.addEventListener('mousedown', (event) => {
            dragState.type = 'indicator';
            dragState.target = viewportIndicator;
            dragState.startX = event.clientX;
            dragState.startY = event.clientY;
            // Store initial indicator position
            const style = window.getComputedStyle(viewportIndicator);
            dragState.indicatorStartLeft = parseFloat(style.left);
            dragState.indicatorStartTop = parseFloat(style.top);
            viewportIndicator.classList.add('dragging');
            event.preventDefault();
        });
    }

    // 3. Metadata box drag
    const metadataContainer = document.getElementById('metadata-box');
    if (metadataContainer) {
        addWindowControls(metadataContainer);
        metadataContainer.addEventListener('mousedown', (event) => {
            // Prevent drag if clicking on controls/buttons
            if (
                event.target.closest('.window-controls') ||
                event.target.tagName === 'BUTTON'
            ) return;
            if (event.target !== metadataContainer) return;
            dragState.type = 'metadata';
            dragState.startX = event.clientX;
            dragState.startY = event.clientY;
            dragState.target = metadataContainer;
            const rect = metadataContainer.getBoundingClientRect();
            dragState.offsetX = event.clientX - rect.left;
            dragState.offsetY = event.clientY - rect.top;
            metadataContainer.classList.add('dragging');
            event.preventDefault();
            event.stopPropagation();
        });
        addWindowControls(metadataContainer);
    }

    // 4. SVG panning (background drag)
    svg.addEventListener('mousedown', (event) => {
        if (event.button !== 0 ||
            event.target.closest('.metadata-box, .miniature-box, .instructions') ||
            event.target.id === 'overlay-container' ||
            event.target.closest('.node') ||
            event.target.closest('.edge')) {
            return;
        }
        dragState.type = 'pan';
        dragState.startX = event.clientX;
        dragState.startY = event.clientY;
        startX = event.clientX;
        startY = event.clientY;
        mouseDownStartX = event.clientX;
        mouseDownStartY = event.clientY;
        event.preventDefault();
    });

    // --- MOUSE MOVE HANDLER ---
    window.addEventListener('mousemove', (event) => {
        if (!dragState.type) return;

        if (dragState.type === 'pan') {
            // Check if we should start panning (after drag threshold)
            if (!isPanning && mouseDownStartX !== undefined && mouseDownStartY !== undefined) {
                const dx = Math.abs(event.clientX - mouseDownStartX);
                const dy = Math.abs(event.clientY - mouseDownStartY);
                if (dx > dragThreshold || dy > dragThreshold) {
                    isPanning = true;
                    svg.classList.add('grabbing');
                }
            }
            //console.log('isPanning:', isPanning, 'isDraggingIndicator:', isDraggingIndicator, 'isDraggingMiniature:', isDraggingMiniature);
            if (isPanning) {
                event.preventDefault();
                const dx = event.clientX - startX;
                const dy = event.clientY - startY;
                userTx += dx / (userS * initialS);
                userTy += dy / (userS * initialS);
                startX = event.clientX;
                startY = event.clientY;
                applyTransform();
            }
        } else if (dragState.type === 'miniature' || dragState.type === 'metadata') {
            let newLeft = event.clientX - dragState.offsetX;
            let newTop = event.clientY - dragState.offsetY;
            dragState.target.style.left = `${newLeft}px`;
            dragState.target.style.top = `${newTop}px`;
        } else if (dragState.type === 'indicator') {
            event.preventDefault();
            const miniRect = miniatureContainer.getBoundingClientRect();
            // Calculate new position based on drag start
            let indicatorLeft = dragState.indicatorStartLeft + (event.clientX - dragState.startX);
            let indicatorTop = dragState.indicatorStartTop + (event.clientY - dragState.startY);
            indicatorLeft = Math.max(0, Math.min(miniRect.width - viewportIndicator.offsetWidth, indicatorLeft));
            indicatorTop = Math.max(0, Math.min(miniRect.height - viewportIndicator.offsetHeight, indicatorTop));
            // Update indicator position visually during drag
            viewportIndicator.style.left = `${indicatorLeft}px`;
            viewportIndicator.style.top = `${indicatorTop}px`;

            // Calculate relative position and update main view
            const relLeft = indicatorLeft / miniRect.width;
            const relTop = indicatorTop / miniRect.height;
            const mainBounds = getMainERDBounds();
            const ctm = mainGroup.getScreenCTM();
            if (!ctm) return;
            const invCtm = ctm.inverse();
            const pt1 = svg.createSVGPoint();
            pt1.x = 0; pt1.y = 0;
            const svgPt1 = pt1.matrixTransform(invCtm);
            userTx = ((mainBounds.x + relLeft * mainBounds.width) - svgPt1.x) / initialS;
            userTy = ((mainBounds.y + relTop * mainBounds.height) - svgPt1.y) / initialS;
            applyTransform();
        }
    });

    // --- MOUSE UP HANDLER ---
    window.addEventListener('mouseup', () => {
        if (!dragState.type) return;
        if (dragState.target) dragState.target.classList.remove('dragging');
        if (dragState.type === 'pan') {
            svg.classList.remove('grabbing');
            isPanning = false;
        }
        dragState.type = null;
        dragState.target = null;
        resizing = false;
    });

    // --- Other UI Events ---
    svg.addEventListener('wheel', (event) => {
        event.preventDefault();
        const dir = event.deltaY < 0 ? 1 : -1;
        const scaleAmount = 1 + dir * 0.1;
        let newS = userS * scaleAmount;
        newS = Math.max(0.01, Math.min(5, newS));
        const pt = svg.createSVGPoint();
        pt.x = event.clientX;
        pt.y = event.clientY;
        const svgP = pt.matrixTransform(mainGroup.getScreenCTM().inverse());
        userTx -= (svgP.x * (newS - userS)) / initialS;
        userTy -= (svgP.y * (newS - userS)) / initialS;
        userS = newS;
        applyTransform();
    }, { passive: false });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' || e.key.toLowerCase() === 'r') {
            userTx = 0; userTy = 0; userS = 1;
            clearAllHighlights();
            applyTransform();
        }
    });

    window.addEventListener('scroll', onViewportChange, { passive: true });
    window.addEventListener('resize', onViewportChange, { passive: true });

    requestAnimationFrame(() => {
        const mainBounds = getMainERDBounds();
        const centerX = mainBounds.x + mainBounds.width;
        const centerY = mainBounds.y + mainBounds.height;
        zoomToPoint(centerX, centerY, 0.7);
        if (document.activeElement && document.activeElement.blur) {
            document.activeElement.blur();
        }
        svg.focus && svg.focus();
    });

    // --- Highlight click handler ---
    svg.addEventListener('click', (event) => {
        let clickedElement = event.target;
        let tableId = null, edgeId = null;
        while (clickedElement && clickedElement !== svg) {
            if (clickedElement.classList && clickedElement.classList.contains('node')) {
                tableId = clickedElement.id; break;
            }
            if (clickedElement.classList && clickedElement.classList.contains('edge')) {
                edgeId = clickedElement.id; break;
            }
            clickedElement = clickedElement.parentElement;
        }
        if (tableId && tables[tableId]) {
            event.preventDefault(); event.stopPropagation();
            if (highlightedElementId === tableId) {
                clearAllHighlights();
            } else {
                clearAllHighlights();
                highlightedElementId = tableId;
                const connectedEdges = tables[tableId].edges;
                const connectedTables = [tableId, ...connectedEdges.map(edgeId => edges[edgeId].tables).flat()];
                const uniqueTables = [...new Set(connectedTables)];
                highlightElements(uniqueTables, connectedEdges);
            }
        }
        if (edgeId && edges[edgeId]) {
            event.preventDefault(); event.stopPropagation();
            if (highlightedElementId === edgeId) {
                clearAllHighlights();
            } else {
                clearAllHighlights();
                highlightedElementId = edgeId;
                const connectedTables = edges[edgeId].tables;
                highlightElements(connectedTables, [edgeId]);
            }
        }
    });

    miniatureContainer.addEventListener('click', function(event) {
        // Get click position relative to the minimap
        const rect = miniatureContainer.getBoundingClientRect();
        const relX = (event.clientX - rect.left) / rect.width;
        const relY = (event.clientY - rect.top) / rect.height;

        // Get main SVG bounds
        const mainBounds = getMainERDBounds();
        const targetX = mainBounds.x + relX * mainBounds.width;
        const targetY = mainBounds.y + relY * mainBounds.height;

        // Zoom to the clicked point (use a sensible zoom level, e.g. 1)
        zoomToPoint(targetX, targetY, 1);
        event.stopPropagation();
    });
});
