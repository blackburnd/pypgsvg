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

    // --- Window Controls ---
    function addWindowControls(windowElem, options = {}) {
        if (!windowElem) return;
        let controls = windowElem.querySelector('.window-controls');
        if (!controls) {
            controls = document.createElement('div');
            controls.className = 'window-controls';
            controls.style.position = 'absolute';
            controls.style.left = 'auto';
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
            console.log('minimize');

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
            console.log
            e.stopPropagation();
            windowElem.style.display = 'none';
            if (options.onClose) options.onClose();
        };
        controls.addEventListener('mousedown', e => e.stopPropagation());
        controls.addEventListener('click', e => e.stopPropagation());
    }

    function makeResizable(windowElem) {
        const handle = windowElem.querySelector('.resize-handle');
        if (!handle) return;
        handle.addEventListener('mousedown', function (event) {
            dragState.type = 'resize';
            dragState.target = windowElem;
            dragState.startX = event.clientX;
            dragState.startY = event.clientY;
            const style = window.getComputedStyle(windowElem);
            dragState.startWidth = parseInt(style.width, 10);
            dragState.startHeight = parseInt(style.height, 10);
            windowElem.classList.add('resizing');
            event.preventDefault();
            event.stopPropagation();
        });
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
    const GREY_COLOR = "#cccccc"; // color for non-highlighted elements

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
            elem.setAttribute('opacity', isHighlighted ? '1' : '0.5');
            const polygons = elem.querySelectorAll('polygon');
            polygons.forEach(polygon => {
                if (polygon.type !== 'title') {
                    //polygon.setAttribute('fill', isHighlighted ? color : 'white');
                }
            })
        }

        if (elem.classList && elem.classList.contains('edge')) {
            const polygons = elem.querySelectorAll('polygon');
            polygons.forEach(polygon => {
                polygon.setAttribute('stroke-width', isHighlighted ? '15' : '3');
                //polygon.setAttribute('fill', isHighlighted ? color : GREY_COLOR);
            })

            const edgeId = elem.id;
            const connectedTables = edges[edgeId]?.tables || [];


            const paths = elem.querySelectorAll('path');

            if (paths.length > 0) {
                //paths[0].setAttribute('stroke', colorA);
                paths[0].setAttribute('stroke-width', isHighlighted ? '16' : '1');
                paths[0].setAttribute('opacity', '1');

                // Set marker shapes to thick stroke when highlighted
                if (isHighlighted) {
                    // Get marker elements by ID and set their stroke-width
                    const svgDoc = svg.ownerDocument || document;
                }
            }
            if (paths.length > 1) {
                //paths[1].setAttribute('stroke', colorB);
                paths[1].setAttribute('stroke-width', isHighlighted ? '7' : '1');
                paths[1].setAttribute('opacity', '1');
            }
            if (paths.length === 1) {
                //paths[0].setAttribute('stroke', colorA);
                paths[0].setAttribute('stroke-width', isHighlighted ? '3' : '1');
                paths[0].setAttribute('opacity', '1');
            }

        }
    };


    const highlightElements = (tableIds, edgeIds, event) => {
        // Highlight selected tables/edges
        tableIds.forEach(id => {
            const tableElement = document.getElementById(id);
            color = tableElement.querySelector('title');
            console.log(color);

            if (tableElement) {
                tableElement.setAttribute('opacity', '1');
                tableElement.classList.add('highlighted');
                setElementColor(tableElement, tables[id].highlightColor, true);
                tableElement.querySelectorAll('text').forEach(textElem => {
                    textElem.setAttribute('fill', color);
                });
            }
        });

        edgeIds.forEach(id => {
            const edgeElement = document.getElementById(id);
            if (edgeElement) {

                edgeElement.classList.add('highlighted');
                edgeElement.setAttribute('opacity', '1');
                const paths = edgeElement.querySelectorAll('path');
                if (paths.length > 0) {
                    paths[0].setAttribute('stroke-width', '16');
                }
                if (paths.length > 1) {
                    paths[1].setAttribute('stroke-width', '7');
                    paths[1].setAttribute('opacity', '1');
                }
                if (paths.length === 1) {
                    paths[0].setAttribute('stroke-width', '3');
                    paths[0].setAttribute('opacity', '1');
                }
            }
        });
        // Grey out everything else
        Object.keys(tables).forEach(id => {
            if (!tableIds.includes(id)) {
                const tableElement = document.getElementById(id);
                if (tableElement) {
                    setElementColor(tableElement, tables[id].desaturatedColor, false);
                    if ('highlighted' in tableElement.classList) {
                        tableElement.classList.remove('highlighted');
                    }
                }
            }
        });
        Object.keys(edges).forEach(id => {
            if (!edgeIds.includes(id)) {
                const edgeElement = document.getElementById(id);
                if (edgeElement) {
                    if ('highlighted' in edgeElement.classList) {
                        edgeElement.classList.remove('highlighted');
                    }
                }
            }
        });
        showSelectionWindow(tableIds, edgeIds, event);
    };



    function showSelectionWindow(selectedTables, selectedEdges, event) {
        const selectionContainer = document.getElementById('selection-container');
        if (!selectionContainer) return;
        selectionContainer.style.display = 'block';
        selectionContainer.style.position = 'fixed';
        const inner = selectionContainer.querySelector('#selection-inner-container');
        if (!inner) return;

        let html = '';
        if (selectedTables.length) {
            html += '<div><b>Tables:</b> ' + selectedTables.join('<br/>') + '</div>';
        }
        if (selectedEdges.length) {
            html += '<div><b>Foreign Keys:</b><ul>';
            for (const edgeId of selectedEdges) {
                const edge = graphData.edges[edgeId];
                if (edge && edge.fkText) {
                    html += `<li><pre>${edge.fkText}</pre></li>`;
                } else {
                    html += `<li>${edgeId}</li>`;
                }
            }
            html += '</ul></div>';
        }
        inner.innerHTML = html;

        // Position the container next to the cursor, accounting for scroll offsets
        if (event) {
            console.log('Positioning selection window at cursor:', event.clientX, event.clientY);

            const viewportWidth = window.innerWidth;
            const viewportHeight = window.innerHeight;

            // Use getComputedStyle to get accurate dimensions
            const computedStyle = window.getComputedStyle(selectionContainer);
            const containerWidth = parseFloat(computedStyle.width);
            const containerHeight = parseFloat(computedStyle.height);

            let left = event.clientX - containerWidth / 2;
            let top = event.clientY - containerHeight / 2;

            selectionContainer.style.position = 'fixed';
            selectionContainer.style.left = `${Math.max(0, left)}px`;
            selectionContainer.style.top = `${Math.max(0, top)}px`;

            console.log(`Selection window positioned at (${left}, ${top})`);
        }
    }

    function hideSelectionWindow() {
        const selectionContainer = document.getElementById('selection-container');
        if (selectionContainer) {
            selectionContainer.style.display = 'none';
            const inner = selectionContainer.querySelector('#selection-inner-container');
            if (inner) inner.innerHTML = '';
        }
    }

    const clearAllHighlights = () => {
        Object.keys(tables).forEach(id => {
            const tableElement = document.getElementById(id);
            if (tableElement) {
                if ('highlighted' in tableElement.classList) {
                    tableElement.classList.remove('highlighted');
                }
                setElementColor(tableElement, tables[id].desaturatedColor, false);
            }
        });
        Object.keys(edges).forEach(id => {
            const edgeElement = document.getElementById(id);
            if (edgeElement) {
                if ('highlighted' in edgeElement.classList) {
                    edgeElement.classList.remove('highlighted');
                }
                setElementColor(edgeElement, edges[id].desaturatedColor, false);
            }
        });
        hideSelectionWindow();
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
    // Miniature drag
    const miniatureHeader = document.getElementById('miniature-header');
    if (miniatureHeader) {
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


    // Viewport indicator drag
    if (viewportIndicator) {
        viewportIndicator.addEventListener('mousedown', (event) => {
            dragState.type = 'indicator';
            dragState.target = viewportIndicator;
            dragState.startX = event.clientX;
            dragState.startY = event.clientY;
            const style = window.getComputedStyle(viewportIndicator);
            dragState.indicatorStartLeft = parseFloat(style.left);
            dragState.indicatorStartTop = parseFloat(style.top);
            viewportIndicator.classList.add('dragging');
            event.preventDefault();
        });
    }

    // Metadata box drag (whole container)
    const metadataContainer = document.getElementById('metadata-container');
    if (metadataContainer) {
        addWindowControls(metadataContainer);
        metadataContainer.addEventListener('mousedown', (event) => {
            // Prevent drag if clicking on controls/buttons
            if (
                event.target.closest('.window-controls') ||
                event.target.tagName === 'BUTTON'
            ) return;
            dragState.type = 'metadata';
            dragState.target = metadataContainer;
            const rect = metadataContainer.getBoundingClientRect();
            dragState.offsetX = event.clientX - rect.left;
            dragState.offsetY = event.clientY - rect.top;
            metadataContainer.classList.add('dragging');
            event.preventDefault();
            event.stopPropagation();
        });
    }

    // Selection window drag (whole container)
    const selectionContainer = document.getElementById('selection-container');
    const selectionInner = document.getElementById('selection-inner-container');
    if (selectionContainer) {
        addWindowControls(selectionContainer);
        selectionContainer.addEventListener('mousedown', (event) => {
            // Prevent drag if clicking on controls/buttons
            if (
                event.target.closest('.window-controls') ||
                event.target.tagName === 'BUTTON'
            ) return;

            dragState.type = 'selection';
            dragState.target = selectionContainer;
            const rect = selectionContainer.getBoundingClientRect();
            dragState.offsetX = event.clientX;
            dragState.offsetY = event.clientY;
            selectionContainer.classList.add('dragging');
            event.preventDefault();
            event.stopPropagation();
        });
    }

    // Add after DOMContentLoaded and selectionInner is defined:
    if (selectionInner) {
        selectionInner.addEventListener('click', function (event) {
            if (selectionInner.querySelector('textarea')) return;

            let text = selectionInner.innerText || selectionInner.textContent || '';
            const rect = selectionInner.getBoundingClientRect();
            const width = rect.width;
            const height = rect.height;

            const XHTML_NS = "http://www.w3.org/1999/xhtml";
            const textarea = document.createElementNS(XHTML_NS, 'textarea');
            textarea.value = text;
            textarea.setAttribute('aria-label', 'Copy selection details');
            textarea.setAttribute('style',
                `width:${width}px;height:${height}px;box-sizing:border-box;font-family:inherit;font-size:inherit;resize:vertical;`
            );

            selectionInner.innerHTML = '';
            selectionInner.appendChild(textarea);
            textarea.focus();

            // Prevent all mouse and keyboard handlers from interfering while textarea is focused
            function stopEvent(e) {
                e.stopPropagation();
            }
            textarea.addEventListener('mousedown', stopEvent, true);
            textarea.addEventListener('mousemove', stopEvent, true);
            textarea.addEventListener('mouseup', stopEvent, true);
            textarea.addEventListener('keydown', stopEvent, true);
            textarea.addEventListener('keyup', stopEvent, true);
            textarea.addEventListener('wheel', stopEvent, true);

            textarea.addEventListener('blur', function () {
                selectionInner.innerHTML = '';
                selectionInner.innerText = text;
            });
        });
    }

    // SVG panning (background drag)
    svg.addEventListener('mousedown', (event) => {
        if (event.button !== 0 ||
            event.target.closest('.metadata-container, .miniature-container, .instructions') ||
            event.target.id === 'overlay-container' ||
            event.target.id == 'selection-container' ||
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
            }
        } else if (['miniature', 'metadata', 'selection'].includes(dragState.type)) {
            let newLeft = event.clientX - dragState.offsetX;
            let newTop = event.clientY - dragState.offsetY;
            dragState.target.style.left = `${newLeft}px`;
            dragState.target.style.top = `${newTop}px`;
        } else if (dragState.type === 'indicator') {
            event.preventDefault();
            const miniRect = miniatureContainer.getBoundingClientRect();
            let indicatorLeft = dragState.indicatorStartLeft + (event.clientX - dragState.startX);
            let indicatorTop = dragState.indicatorStartTop + (event.clientY - dragState.startY);
            indicatorLeft = Math.max(0, Math.min(miniRect.width - viewportIndicator.offsetWidth, indicatorLeft));
            indicatorTop = Math.max(0, Math.min(miniRect.height - viewportIndicator.offsetHeight, indicatorTop));
            viewportIndicator.style.left = `${indicatorLeft}px`;
            viewportIndicator.style.top = `${indicatorTop}px`;
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
        } else if (dragState.type === 'resize') {
            const dx = event.clientX - dragState.startX;
            const dy = event.clientY - dragState.startY;
            let newWidth = dragState.startWidth;
            let newHeight = dragState.startHeight;
            if (dragState.handle.classList.contains('resize-handle-se')) {
                newWidth += dx;
                newHeight += dy;
            } else if (dragState.handle.classList.contains('resize-handle-nw')) {
                newWidth -= dx;
                newHeight -= dy;
                // Optionally move the window as well
                dragState.target.style.left = `${parseFloat(dragState.target.style.left || 0) + dx}px`;
                dragState.target.style.top = `${parseFloat(dragState.target.style.top || 0) + dy}px`;
            }
            dragState.target.style.width = `${Math.max(100, newWidth)}px`;
            dragState.target.style.height = `${Math.max(50, newHeight)}px`;
        }
    });

    // --- MOUSE UP HANDLER ---
    window.addEventListener('mouseup', (event) => {
        if (!dragState.type) return;
        if (dragState.target) dragState.target.classList.remove('dragging');
        if (dragState.type === 'pan') {
            svg.classList.remove('grabbing');
            isPanning = false;
        } else if (dragState.type === 'resize') {
            const rect = dragState.target.getBoundingClientRect();
            const newWidth = rect.width;
            const newHeight = rect.height;
            // Optionally, you can snap to a grid or minimum size
            const minSize = 50;
            if (newWidth < minSize || newHeight < minSize) {
                dragState.target.style.width = `${minSize}px`;
                dragState.target.style.height = `${minSize}px`;
            }
        }
        dragState.type = null;
        dragState.target = null;
    });

    // --- Other UI Events ---
    // Helper to compute minimum zoom to fit SVG in viewport
    function getMinZoomToFit() {
        const mainBounds = getMainERDBounds();
        if (!mainBounds.width || !mainBounds.height) return 0.01;
        const svgWidth = window.innerWidth;
        const svgHeight = window.innerHeight;
        const scaleX = svgWidth / mainBounds.width;
        const scaleY = svgHeight / mainBounds.height;
        return Math.min(scaleX, scaleY);
    }

    svg.addEventListener('wheel', (event) => {
        event.preventDefault();
        const dir = event.deltaY < 0 ? 1 : -1;
        const scaleAmount = 1 + dir * 0.1;
        let newS = userS * scaleAmount;
        const minZoom = getMinZoomToFit();
        newS = Math.max(minZoom, Math.min(5, newS)); // Clamp to minZoom
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
                showSelectionWindow(uniqueTables, connectedEdges, event);
            }
        }
        if (edgeId && edges[edgeId]) {
            event.preventDefault(); event.stopPropagation();
            if (highlightedElementId === edgeId) {
                clearAllHighlights();

            } else {
                console.log('Edge clicked:', edgeId);

                clearAllHighlights()
                highlightedElementId = edgeId;
                const connectedTables = edges[edgeId].tables;
                highlightElements(connectedTables, [edgeId]);
            }
        }
    });

    miniatureContainer.addEventListener('click', function (event) {
        // Get click position relative to the minimap
        const rect = miniatureContainer.getBoundingClientRect();
        const relX = (event.clientX - rect.left) / rect.width;
        const relY = (event.clientY - rect.top) / rect.height;

        // Get main SVG bounds
        const mainBounds = getMainERDBounds();
        const targetX = mainBounds.x + relX * mainBounds.width;
        const targetY = mainBounds.y + relY * mainBounds.height;

        // Zoom to the clicked point (use a sensible zoom level, e.g. 1)
        zoomToPoint(targetX, targetY, userS);
        event.stopPropagation();
    });

    requestAnimationFrame(() => {
        const mainBounds = getMainERDBounds();
        // Center coordinates
        const centerX = mainBounds.x + mainBounds.width / 2;
        const centerY = mainBounds.y + mainBounds.height / 2;
        // Fit to screen
        const minZoom = getMinZoomToFit();
        zoomToPoint(centerX, centerY, minZoom);
        if (document.activeElement && document.activeElement.blur) {
            document.activeElement.blur();
        }
        svg.focus && svg.focus();
    });

    function clampPan(tx, ty, s) {
        const mainBounds = getMainERDBounds();
        const svgWidth = window.innerWidth;
        const svgHeight = window.innerHeight;
        const scaledWidth = mainBounds.width * s * initialS;
        const scaledHeight = mainBounds.height * s * initialS;

        // Calculate min/max tx/ty so at least half of SVG stays visible
        const minTx = svgWidth / (2 * initialS) - (mainBounds.x + mainBounds.width) * s;
        const maxTx = (mainBounds.x + mainBounds.width / 2) * s - svgWidth;
        const minTy = svgHeight / (2 * initialS) - (mainBounds.y + mainBounds.height) * s;
        const maxTy = (mainBounds.y + mainBounds.height / 2) * s - svgHeight;

        return {
            tx: Math.min(Math.max(tx, minTx), maxTx),
            ty: Math.min(Math.max(ty, minTy), maxTy)
        };
    }

    function placeFloatingWindows() {
        // Top left for metadata
        const metadataContainer = document.getElementById('metadata-container');
        if (metadataContainer) {
            metadataContainer.style.position = 'fixed';
            metadataContainer.style.left = '2rem';
            metadataContainer.style.top = '2rem';
            metadataContainer.style.zIndex = '10000';
        }

        // Top right for miniature/overview
        const miniatureContainer = document.getElementById('miniature-container');
        if (miniatureContainer) {
            miniatureContainer.style.position = 'fixed';
            miniatureContainer.style.left = '2rem';
            miniatureContainer.style.right = '';
            miniatureContainer.style.top = '5rem';
            miniatureContainer.style.zIndex = '10001';
        }

        // Bottom left for selection
        const selectionContainer = document.getElementById('selection-container');
        if (selectionContainer) {
            // Additional positioning logic if needed
        }
    }
    placeFloatingWindows();
    document.querySelectorAll('.minimize-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const parent = btn.parentElement;
            const contents = btn.parentNode.parentNode.childNodes; // Select only children with the class 'container-content'

            // Toggle the button's text
            btn.innerHTML = btn.innerHTML === '+' ? '–' : '+';

            // Toggle the display of each content element
            contents.forEach(content => {
                if (content.nodeType !== Node.ELEMENT_NODE) return; // Skip non-element nodes
                console.log(content.id);
                if (content.classList.contains('container-content')) {
                    content.style.display = content.style.display === 'none' ? '' : 'none';
                }
            });
        });
    });

});
