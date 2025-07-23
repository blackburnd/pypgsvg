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
        if (!elem) {
            return;
        }

        if (elem.classList && elem.classList.contains('node')) {
            const mainPath = elem.querySelector('path');
            if (mainPath) {
                mainPath.setAttribute('fill', color);
                if (isHighlighted) {
                    mainPath.setAttribute('stroke-width', '6');
                    mainPath.setAttribute('stroke', color);
                } else {
                    mainPath.setAttribute('stroke-width', '1');
                    mainPath.setAttribute('stroke', 'black');
                }
            }

            const polygons = elem.querySelectorAll('polygon');
            polygons.forEach(polygon => {
                polygon.setAttribute('fill', color);
                if (isHighlighted) {
                    polygon.setAttribute('stroke-width', '6');
                    polygon.setAttribute('stroke', color);
                } else {
                    polygon.setAttribute('stroke-width', '1');
                    polygon.setAttribute('stroke', 'black');
                }
            });
        }

        if (elem.classList && elem.classList.contains('edge')) {
            const edgePath = elem.querySelector('path');
            if (edgePath) {
                edgePath.setAttribute('stroke', color);
                if (isHighlighted) {
                    edgePath.setAttribute('stroke-width', '6');
                } else {
                    edgePath.setAttribute('stroke-width', '3');
                }
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
            event.stopPropagation(); // Prevent main canvas panning
            isDraggingIndicator = true;
            indicatorStartX = event.clientX;
            indicatorStartY = event.clientY;
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
            const dx = event.clientX - indicatorStartX;
            const dy = event.clientY - indicatorStartY;

            const miniRect = miniatureContainer.getBoundingClientRect();
            const mainBounds = getMainERDBounds();

            if (miniRect.width > 0 && miniRect.height > 0) {
                const panX = (dx / miniRect.width) * mainBounds.width;
                const panY = (dy / miniRect.height) * mainBounds.height;

                // Calculate the visible area in main coordinates
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

                // Clamp so the viewport indicator stays inside the minimap
                let newUserTx = userTx - panX / initialS;
                let newUserTy = userTy - panY / initialS;

                // Calculate the min/max allowed pan so the viewport stays inside
                const minTx = -(svgPt1.x - mainBounds.x) / initialS;
                const maxTx = (mainBounds.width - visibleWidth - (svgPt1.x - mainBounds.x)) / initialS;
                const minTy = -(svgPt1.y - mainBounds.y) / initialS;
                const maxTy = (mainBounds.height - visibleHeight - (svgPt1.y - mainBounds.y)) / initialS;

                // Clamp the new values
                newUserTx = Math.max(minTx, Math.min(maxTx, newUserTx));
                newUserTy = Math.max(minTy, Math.min(maxTy, newUserTy));

                userTx = newUserTx;
                userTy = newUserTy;

                applyTransform();
            }

            indicatorStartX = event.clientX;
            indicatorStartY = event.clientY;
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
    const maxZoomOut = 0.1; // Can zoom out to 20%
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
        pt.x = event.clientX;
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
});
