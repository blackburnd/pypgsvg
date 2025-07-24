document.addEventListener('DOMContentLoaded', () => {

    const svg = document.getElementById('main-svg');
    const mainGroup = document.getElementById('main-erd-group');
    const miniatureContainer = document.getElementById('miniature-container');
    const viewportIndicator = document.getElementById('viewport-indicator');
    const overlayContainer = document.getElementById('overlay-container');
    const graphDataElement = document.getElementById('graph-data');

    if (!svg || !mainGroup || !overlayContainer || !graphDataElement) {
        return;
    }

    if (!miniatureContainer || !viewportIndicator) {

    }

    const graphData = JSON.parse(graphDataElement.textContent);
    const { tables, edges } = graphData;

    // --- State variables
    let initialTx = 0, initialTy = 0, initialS = 1; // Transform from Graphviz
    let userTx = 0, userTy = 0, userS = 1; // User-applied transform (pan/zoom)

    let isPanning = false;
    let startX = 0, startY = 0;
    let mouseDownStartX = 0, mouseDownStartY = 0;
    let dragThreshold = 5; // Pixel threshold before panning starts

    let isDraggingIndicator = false;
    let indicatorStartX = 0, indicatorStartY = 0;
    let indicatorOffsetX = 0, indicatorOffsetY = 0; // Add these at the top with other state variables

    let highlightedElementId = null; // To track the currently highlighted table/edge

    // --- INITIALIZATION ---

    // Parse the initial transform applied by Graphviz to the main group
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

    const initialTransform = parseTransform(mainGroup.getAttribute('transform'));
    initialTx = initialTransform.tx;
    initialTy = initialTransform.ty;
    initialS = initialTransform.s;

    // --- CORE FUNCTIONS ---

    // Get the untransformed bounding box of the main diagram content
    const getMainERDBounds = () => {
        return mainGroup.getBBox();
    };

    // Apply the combined (initial + user) transform to the main group
    const applyTransform = () => {
        const finalS = userS * initialS;
        const finalTx = (userTx * initialS) + initialTx;
        const finalTy = (userTy * initialS) + initialTy;
        mainGroup.setAttribute('transform', `translate(${finalTx} ${finalTy}) scale(${finalS})`);
        // Update indicator after transform
        requestAnimationFrame(updateViewportIndicator);
    };

    // Update the red box on the minimap to show the current viewport
    const updateViewportIndicator = () => {
        if (!viewportIndicator) return;

        const mainBounds = getMainERDBounds();
        if (mainBounds.width === 0 || mainBounds.height === 0) return;

        const ctm = mainGroup.getScreenCTM();
        if (!ctm) return;
        const invCtm = ctm.inverse();

        // Find viewport corners in the main group's coordinate system
        const pt1 = svg.createSVGPoint();
        pt1.x = 0;
        pt1.y = 0;
        const svgPt1 = pt1.matrixTransform(invCtm);

        const pt2 = svg.createSVGPoint();
        pt2.x = window.innerWidth;
        pt2.y = window.innerHeight;
        const svgPt2 = pt2.matrixTransform(invCtm);

        const visibleWidth = svgPt2.x - svgPt1.x;
        const visibleHeight = svgPt2.y - svgPt1.y;

        // Calculate relative position and size
        const relLeft = (svgPt1.x - mainBounds.x) / mainBounds.width;
        const relTop = (svgPt1.y - mainBounds.y) / mainBounds.height;
        const relWidth = visibleWidth / mainBounds.width;
        const relHeight = visibleHeight / mainBounds.height;

        // Apply and clamp values
        viewportIndicator.style.left = `${Math.max(0, Math.min(1, relLeft)) * 100}%`;
        viewportIndicator.style.top = `${Math.max(0, Math.min(1, relTop)) * 100}%`;
        viewportIndicator.style.width = `${Math.max(0, Math.min(1, relWidth)) * 100}%`;
        viewportIndicator.style.height = `${Math.max(0, Math.min(1, relHeight)) * 100}%`;
    };

    // Combined handler for any event that changes the viewport
    const onViewportChange = () => {
        requestAnimationFrame(updateViewportIndicator);
    };

    // --- HIGHLIGHTING ---
    const setElementColor = (elem, color, isHighlighted = false) => {
        if (!elem) return;

        if (elem.classList && elem.classList.contains('node')) {
            const nodeId = elem.id;
            const connectedEdgeIds = tables[nodeId]?.edges || [];
            // Pick first two connected edges, fallback to default color if not enough
            const edge1 = edges[connectedEdgeIds[0]];
            const edge2 = edges[connectedEdgeIds[1]];
            const defaultColor = edge1 ? edge1.defaultColor : color;
            const highlightColor = edge2 ? edge2.highlightColor : color;
            const fillColor = defaultColor;
            const strokeColor = highlightColor;

            const mainPath = elem.querySelector('path');
            if (mainPath) {
                mainPath.setAttribute('fill', fillColor);
                mainPath.setAttribute('stroke', strokeColor);
                mainPath.setAttribute('stroke-width', isHighlighted ? '2' : '1');
            }

            const polygons = elem.querySelectorAll('polygon');
            polygons.forEach(polygon => {
                polygon.setAttribute('fill', fillColor);
                polygon.setAttribute('stroke', strokeColor);
                polygon.setAttribute('stroke-width', isHighlighted ? '2' : '1');
            });
        }

        if (elem.classList && elem.classList.contains('edge')) {
            const edgePath = elem.querySelector('path');
            if (edgePath) {
                edgePath.setAttribute('stroke', color);
                edgePath.setAttribute('stroke-width', isHighlighted ? '20' : '1');
            }
        }
    };

    const highlightElements = (tableIds, edgeIds) => {
        tableIds.forEach(id => {
            const tableElement = document.getElementById(id);
            if (tableElement) {
                setElementColor(tableElement, tables[id].highlightColor, true);
            }
        });
        edgeIds.forEach(id => {
            const edgeElement = document.getElementById(id);
            if (edgeElement) {
                setElementColor(edgeElement, edges[id].highlightColor, true);
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

    // --- USER ACTIONS ---

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

    svg.addEventListener('click', (event) => {
        let clickedElement = event.target;
        let tableId = null;
        let edgeId = null;

        while (clickedElement && clickedElement !== svg) {
            if (clickedElement.classList && clickedElement.classList.contains('node')) {
                tableId = clickedElement.id;
                break;
            }

            if (clickedElement.classList && clickedElement.classList.contains('edge')) {
                edgeId = clickedElement.id;
                break;
            }

            clickedElement = clickedElement.parentElement;
        }

        if (tableId && tables[tableId]) {
            event.preventDefault();
            event.stopPropagation();

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
            return;
        }

        if (edgeId && edges[edgeId]) {
            event.preventDefault();
            event.stopPropagation();

            if (highlightedElementId === edgeId) {
                clearAllHighlights();
            } else {
                clearAllHighlights();
                highlightedElementId = edgeId;
                const connectedTables = edges[edgeId].tables;
                highlightElements(connectedTables, [edgeId]);
            }
            return;
        }
    });

    // Handle dragging the viewport indicator
    if (viewportIndicator) {
        viewportIndicator.addEventListener('mousedown', (event) => {
            event.preventDefault();
            event.stopPropagation();
            isDraggingIndicator = true;
            indicatorStartX = event.clientX;
            indicatorStartY = event.clientY;

            // Calculate offset between mouse and indicator's top-left
            const rect = viewportIndicator.getBoundingClientRect();
            indicatorOffsetX = event.clientX - rect.left;
            indicatorOffsetY = event.clientY - rect.top;

            viewportIndicator.classList.add('dragging');
        });
    }

    // Handle minimap clicks for zoom-to-point
    if (miniatureContainer) {
        miniatureContainer.addEventListener('click', (event) => {
            // prevent click if dragging the indicator
            if (event.target === viewportIndicator) return;

            const miniRect = miniatureContainer.getBoundingClientRect();
            const clickX = event.clientX - miniRect.left;
            const clickY = event.clientY - miniRect.top;

            const mainBounds = getMainERDBounds();
            const targetX = mainBounds.x + (clickX / miniRect.width) * mainBounds.width;
            const targetY = mainBounds.y + (clickY / miniRect.height) * mainBounds.height;

            zoomToPoint(targetX, targetY);
        });
    }

    svg.addEventListener('mousedown', (event) => {
        if (event.button !== 0 ||
            event.target.closest('.metadata-box, .miniature-box, .instructions') ||
            event.target.id === 'overlay-container' ||
            event.target.closest('.node') ||
            event.target.closest('.edge')) {
            return;
        }
        mouseDownStartX = event.clientX;
        mouseDownStartY = event.clientY;
        startX = event.clientX;
        startY = event.clientY;
        event.preventDefault();
    });

    // Global mouse move for both panning and indicator dragging
    window.addEventListener('mousemove', (event) => {
        // Check if we should start panning (after drag threshold)
        if (!isPanning && mouseDownStartX !== undefined && mouseDownStartY !== undefined) {
            const dx = Math.abs(event.clientX - mouseDownStartX);
            const dy = Math.abs(event.clientY - mouseDownStartY);
            if (dx > dragThreshold || dy > dragThreshold) {
                isPanning = true;
                svg.classList.add('grabbing');
            }
        }

        if (isPanning) {
            event.preventDefault();
            const dx = event.clientX - startX;
            const dy = event.clientY - startY;
            userTx += dx / (userS * initialS);
            userTy += dy / (userS * initialS);
            startX = event.clientX;
            startY = event.clientY;
            applyTransform();
        } else if (isDraggingIndicator) {
            event.preventDefault();

            const miniRect = miniatureContainer.getBoundingClientRect();
            const mainBounds = getMainERDBounds();

            // Calculate where the indicator's top-left should be based on mouse position and offset
            let indicatorLeft = event.clientX - miniRect.left - indicatorOffsetX;
            let indicatorTop = event.clientY - miniRect.top - indicatorOffsetY;

            // Clamp to minimap bounds
            indicatorLeft = Math.max(0, Math.min(miniRect.width - viewportIndicator.offsetWidth, indicatorLeft));
            indicatorTop = Math.max(0, Math.min(miniRect.height - viewportIndicator.offsetHeight, indicatorTop));

            // Calculate the relative position
            const relLeft = indicatorLeft / miniRect.width;
            const relTop = indicatorTop / miniRect.height;

            // Move the main view accordingly
            const ctm = mainGroup.getScreenCTM();
            if (!ctm) return;
            const invCtm = ctm.inverse();

            const pt1 = svg.createSVGPoint();
            pt1.x = 0;
            pt1.y = 0;
            const svgPt1 = pt1.matrixTransform(invCtm);

            const pt2 = svg.createSVGPoint();
            pt2.x = window.innerWidth;
            pt2.y = window.innerHeight;
            const svgPt2 = pt2.matrixTransform(invCtm);

            const visibleWidth = svgPt2.x - svgPt1.x;
            const visibleHeight = svgPt2.y - svgPt1.y;

            // Set userTx and userTy so that the viewport aligns with the indicator
            userTx = ((mainBounds.x + relLeft * mainBounds.width) - svgPt1.x) / initialS;
            userTy = ((mainBounds.y + relTop * mainBounds.height) - svgPt1.y) / initialS;

            applyTransform();
        }
    });

    const endPan = () => {
        if (isPanning) {
            isPanning = false;
            svg.classList.remove('grabbing');
        }
        if (isDraggingIndicator) {
            isDraggingIndicator = false;
            viewportIndicator.classList.remove('dragging');
        }
        // Reset mouse tracking variables
        mouseDownStartX = undefined;
        mouseDownStartY = undefined;
    };

    window.addEventListener('mouseup', endPan);
    window.addEventListener('mouseleave', endPan);
    const zoomIntensity = 0.1;
    const maxZoomOut = 0.01; 
    const maxZoomIn = 5;   // Can zoom in to 500%
    const initZoomOut = 0.7; // Initial zoom out to 50%

    // Handle mouse wheel for zooming
    svg.addEventListener('wheel', (event) => {
        event.preventDefault();
        const dir = event.deltaY < 0 ? 1 : -1;
        const scaleAmount = 1 + dir * zoomIntensity;

        let newS = userS * scaleAmount;
        // Clamp the zoom level
        newS = Math.max(maxZoomOut, Math.min(maxZoomIn, newS));

        // Get mouse position in the main group's coordinate system to zoom towards it
        const pt = svg.createSVGPoint();
        pt.x = event.clientX
        pt.y = event.clientY;
        const svgP = pt.matrixTransform(mainGroup.getScreenCTM().inverse());

        // Update user transform to zoom towards the mouse pointer
        userTx -= (svgP.x * (newS - userS)) / initialS;
        userTy -= (svgP.y * (newS - userS)) / initialS;
        userS = newS;

        applyTransform();
    }, { passive: false });

    // Handle reset keys
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' || e.key.toLowerCase() === 'r') {
            resetZoom();
        }
    });

    // Handle window scroll and resize to keep UI fixed
    window.addEventListener('scroll', onViewportChange, { passive: true });
    window.addEventListener('resize', onViewportChange, { passive: true });

    requestAnimationFrame(() => {
        const mainBounds = getMainERDBounds();
        const centerX = mainBounds.x + mainBounds.width / 2;
        const centerY = mainBounds.y + mainBounds.height / 2;
        zoomToPoint(centerX, centerY, initZoomOut);
        endPan();
        if (document.activeElement && document.activeElement.blur) {
            document.activeElement.blur();
        }
        svg.focus && svg.focus(); // Optionally focus the SVG or document
    });

    // --- DRAGGING AND RESIZING WINDOWS ---

    function makeDraggable(container, handleSelector = null) {
        let isDragging = false;
        let offsetX = 0, offsetY = 0;

        const handle = handleSelector ? container.querySelector(handleSelector) : container;
        if (!handle) return;

        handle.style.cursor = 'move';

        handle.addEventListener('mousedown', (e) => {
            if (e.button !== 0) return;
            isDragging = true;
            // Get the current position of the container
            const rect = container.getBoundingClientRect();
            // Calculate offset between mouse and top-left corner of the window
            offsetX = e.clientX - rect.left;
            offsetY = e.clientY - rect.top;
            e.preventDefault();
            e.stopPropagation();
        });

        function onMouseMove(e) {
            if (!isDragging) return;
            // Keep the mouse at the same offset inside the window
            // Recalculate viewport indicator after moving
            left = container.style.left;
            top = container.style.top;

            container.style.left = (e.clientX - offsetX) + 'px';
            container.style.top = (e.clientY - offsetY) + 'px';
            requestAnimationFrame(updateViewportIndicator);
        }
        function onMouseUp() {
            requestAnimationFrame(updateViewportIndicator);
            isDragging = false;
        }

        window.addEventListener('mousemove', onMouseMove);
        window.addEventListener('mouseup', onMouseUp);
    }

    // Make metadata window draggable
    const metadataBox = document.querySelector('.metadata-box');
    if (metadataBox) {
        // If you have a header, use '.header', else null for whole box
        makeDraggable(metadataBox, '.header');
    }

    // Make minimap window draggable
    const miniatureBox = document.querySelector('.miniature-box') || document.getElementById('miniature-container');
    if (miniatureBox) {
        makeDraggable(miniatureBox, '.header'); // Or null for whole box
    }

    // --- RESIZABLE MINIMAP ---

    function makeResizable(container, handleSelector = '.resize-handle', minWidth = 100, minHeight = 100, maxWidth = 800, maxHeight = 800) {
        const handle = container.querySelector(handleSelector);
        if (!handle) return;

        let isResizing = false;
        let startX, startY, startW, startH;

        handle.addEventListener('mousedown', (e) => {
            if (e.button !== 0) return;
            isResizing = true;
            startX = e.clientX;
            startY = e.clientY;
            const rect = miniatureContainer.getBoundingClientRect();
            startW = rect.width;
            startH = rect.height;
            e.preventDefault();
            e.stopPropagation();
        });

        function onMouseMove(e) {
            if (!isResizing) return;
            let newW = Math.max(minWidth, Math.min(maxWidth, startW + (e.clientX - startX)));
            let newH = Math.max(minHeight, Math.min(maxHeight, startH + (e.clientY - startY)));
            container.style.width = newW + 'px';
            container.style.height = newH + 'px';
            // If your minimap SVG needs to resize, do it here:
            const miniSvg = container.querySelector('svg');
            if (miniSvg) {
                miniSvg.setAttribute('width', newW);
                miniSvg.setAttribute('height', newH);
            }
            // Update indicator, etc.
            requestAnimationFrame(updateViewportIndicator);
        }
        function onMouseUp() {
            isResizing = false;
            requestAnimationFrame(updateViewportIndicator);

        }

        window.addEventListener('mousemove', onMouseMove);
        window.addEventListener('mouseup', onMouseUp);
    }

    if (miniatureBox) {
        makeResizable(miniatureBox, '.resize-handle');
    }
});
