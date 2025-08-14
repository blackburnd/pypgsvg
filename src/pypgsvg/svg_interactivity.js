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
    let dragThreshold = 5;
    let highlightedElementId = null;
    let dragState = { type: null, startX: 0, startY: 0, offsetX: 0, offsetY: 0, target: null, handle: null };

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
            //console.log('minimize');

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
            e.target.destroyRecursive = true;

            windowElem.style.display = 'none';
            if (options.onClose) options.onClose();
        };
        controls.addEventListener('mousedown', e => e.stopPropagation());
        controls.addEventListener('click', e => e.stopPropagation());
    }

    function makeResizable(windowElem) {
        // Get both handles
        const nwHandle = windowElem.querySelector('#resize_handle_nw');
        const seHandle = windowElem.querySelector('#resize_handle_se');
        
        if (nwHandle) {
            nwHandle.addEventListener('mousedown', function(event) {
                dragState.type = 'resize';
                const rect = windowElem.getBoundingClientRect();
                dragState.target = windowElem; // The target is the window, not the handle
                dragState.handle = 'nw'; // Mark which handle we're using
                dragState.startX = event.clientX;
                dragState.startY = event.clientY;
                dragState.startWidth = rect.width;
                dragState.startHeight = rect.height;
                dragState.startLeft = rect.left;
                dragState.startTop = rect.top;
                windowElem.classList.add('resizing');
                event.preventDefault();
                event.stopPropagation();
            });
        }
        
        if (seHandle) {
            seHandle.addEventListener('mousedown', function(event) {
                dragState.type = 'resize';
                const rect = windowElem.getBoundingClientRect();
                dragState.target = windowElem; // The target is the window, not the handle
                dragState.handle = 'se'; // Mark which handle we're using
                dragState.startX = event.clientX;
                dragState.startY = event.clientY;
                dragState.startWidth = rect.width;
                dragState.startHeight = rect.height;
                windowElem.classList.add('resizing');
                event.preventDefault();
                event.stopPropagation();
            });
        }
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
        let isMini = nodeId.indexOf('mini-') != -1;

        if (!isMini) {
            const miniNodeId = 'mini-' + nodeId;
            miniElem = document.getElementById(miniNodeId);
            if (miniElem) {
                setElementColor(miniElem, 'red', isHighlighted)
            }
        }
        if (elem.classList && elem.classList.contains('node')) {
            elem.setAttribute('opacity', isHighlighted ? '1' : '0.5');
            const polygons = elem.querySelectorAll('polygon');
            polygons.forEach(polygon => {
                if (polygon.type !== 'title') {
                    if (isMini) {
                        polygon.setAttribute('fill', isHighlighted ? color : 'white');
                    }
                }
            })
        }

        if (elem.classList && elem.classList.contains('edge')) {
            const polygons = elem.querySelectorAll('polygon');
            polygons.forEach(polygon => {
                polygon.setAttribute('stroke-width', isHighlighted ? '15' : '3');
                if (isMini) {
                    polygon.setAttribute('fill', isHighlighted ? color : GREY_COLOR);
                }
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
            const miniTableElement = document.getElementById('mini-' + id);
            if (!tableElement) return;

            // Get the background color from the title element
            const titleElement = tableElement.querySelector('title');
            backgroundColor = tables[id].defaultColor || '#712e2eff'; // Default to white if no color defin
            // Highlight the table
            tableElement.setAttribute('opacity', '1');
            tableElement.classList.add('highlighted');

            miniTableElement.setAttribute('opacity', '1');
            miniTableElement.classList.add('highlighted');

            // Apply the background color to all text elements in the table
            miniTableElement.querySelectorAll('text').forEach(textElem => {
                textElem.style.fill = 'black'; // Ensure text is readable
                textElem.style.fill = backgroundColor; // Set background color
            });
        });
        edgeIds.forEach(id => {
            let edgeElement = document.getElementById(id);
            let miniEdgeElement = document.getElementById('mini-' + id);
            if (!edgeElement) return;

            // Highlight the edge
            edgeElement.classList.add('highlighted');
            edgeElement.setAttribute('opacity', '1');

            miniEdgeElement.setAttribute('fill', edges[id].defaultColor || '#712e2eff');
            miniEdgeElement.setAttribute('opacity', '1');
            miniEdgeElement.classList.add('highlighted');

            // Adjust stroke widths for paths
            let paths = edgeElement.querySelectorAll('path');
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

            // Adjust stroke widths for mini paths
            let mpaths = miniEdgeElement.querySelectorAll('path');
            if (mpaths.length > 0) {
                mpaths[0].setAttribute('stroke-width', '24');
            }
            if (mpaths.length > 1) {
                mpaths[1].setAttribute('stroke-width', '10');
                mpaths[1].setAttribute('opacity', '1');
            }
            if (mpaths.length === 1) {
                mpaths[0].setAttribute('stroke-width', '5');
                mpaths[0].setAttribute('opacity', '1');
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
            let this_table = selectedTables[0];
            selection_header = document.getElementById('selection-header');
            selection_header.setAttribute('innerHTML', `Selected Table: ${this_table}`);
            
            // Create table entries with data attributes for hover effects
            html += '<div><b>Related Tables:</b><br/>';
            selectedTables.forEach(tableId => {
                // Add data-table-id attribute for event handling
                html += `<span class="table-name" data-table-id="${tableId}">${tableId}</span><br/>`;
            });
            html += '</div>';
        }

        // Update the foreign keys section in showSelectionWindow function

        if (selectedEdges.length) {
            html += '<div id="selected_edges"><b>Foreign Keys:</b><ul>';
            for (const edgeId of selectedEdges) {
                const edge = graphData.edges[edgeId];
                if (edge && edge.fkText) {
                    // Add edge-name class and data-edge-id attribute
                    html += `<li class="edge-name" data-edge-id="${edgeId}"><pre>${edge.fkText}</pre></li>`;
                } else {
                    html += `<li class="edge-name" data-edge-id="${edgeId}">${edgeId}</li>`;
                }
            }
            html += '</ul></div>';
        }
        
        inner.innerHTML = html;

        // Add hover event listeners to table names
        const tableNames = inner.querySelectorAll('.table-name');
        tableNames.forEach(tableNameSpan => {
            const tableId = tableNameSpan.getAttribute('data-table-id');
            
            // Mouseover event - highlight the table
            tableNameSpan.addEventListener('mouseover', () => {
                // Get the table element in the SVG
                const tableElement = document.getElementById(tableId);
                const miniTableElement = document.getElementById('mini-' + tableId);
                
                if (tableElement) {
                    // Store original background for restoration
                    if (!tableElement.dataset.originalBackground) {
                        const polygons = tableElement.querySelectorAll('polygon');
                        polygons.forEach(polygon => {
                            if (!polygon.dataset.originalFill) {
                                polygon.dataset.originalFill = polygon.getAttribute('fill') || 'white';
                            }
                        });
                    }
                    
                    // Apply highlighting
                    const backgroundColor = tables[tableId].defaultColor || '#712e2eff';
                    const polygons = tableElement.querySelectorAll('polygon');
                    polygons.forEach(polygon => {
                        // Only change non-header polygons
                        if (!polygon.classList.contains('title')) {
                            polygon.setAttribute('fill', backgroundColor);
                        }
                    });
                    
                    // Increase opacity for better visibility
                    tableElement.setAttribute('opacity', '1');
                }
                
                // Also highlight the miniature version
                if (miniTableElement) {
                    // Store original background for restoration
                    if (!miniTableElement.dataset.originalBackground) {
                        const miniPolygons = miniTableElement.querySelectorAll('polygon');
                        miniPolygons.forEach(polygon => {
                            if (!polygon.dataset.originalFill) {
                                polygon.dataset.originalFill = polygon.getAttribute('fill') || 'white';
                            }
                        });
                    }
                    
                    // Apply highlighting to miniature
                    const backgroundColor = tables[tableId].defaultColor || '#712e2eff';
                    const miniPolygons = miniTableElement.querySelectorAll('polygon');
                    miniPolygons.forEach(polygon => {
                        polygon.setAttribute('fill', backgroundColor);
                    });
                    
                    // Increase opacity for better visibility
                    miniTableElement.setAttribute('opacity', '1');
                }
            });
            
            // Mouseout event - restore original background
            tableNameSpan.addEventListener('mouseout', () => {
                const tableElement = document.getElementById(tableId);
                const miniTableElement = document.getElementById('mini-' + tableId);
                
                if (tableElement) {
                    const polygons = tableElement.querySelectorAll('polygon');
                    polygons.forEach(polygon => {
                        // Only reset non-header polygons
                        if (!polygon.classList.contains('title')) {
                            polygon.setAttribute('fill', polygon.dataset.originalFill || 'white');
                        }
                    });
                }
                
                // Also restore the miniature version
                if (miniTableElement) {
                    const miniPolygons = miniTableElement.querySelectorAll('polygon');
                    miniPolygons.forEach(polygon => {
                        polygon.setAttribute('fill', polygon.dataset.originalFill || 'white');
                    });
                }
            });
        });

        // Add hover event listeners to edge names
        const edgeNames = inner.querySelectorAll('.edge-name');
        edgeNames.forEach(edgeNameLi => {
            const edgeId = edgeNameLi.getAttribute('data-edge-id');
            
            // Mouseover event - highlight the edge
            edgeNameLi.addEventListener('mouseover', () => {
                // First reduce opacity of ALL edges in the graph
                Object.keys(edges).forEach(currEdgeId => {
                    const currEdgeElement = document.getElementById(currEdgeId);
                    const currMiniEdgeElement = document.getElementById('mini-' + currEdgeId);
                    
                    if (currEdgeElement) {
                        // Store original opacity if not already stored
                        if (!currEdgeElement.dataset.originalOpacity) {
                            currEdgeElement.dataset.originalOpacity = currEdgeElement.getAttribute('opacity') || '1';
                        }
                        // Reduce opacity for all edges
                        currEdgeElement.setAttribute('opacity', '0.2');
                    }
                    
                    if (currMiniEdgeElement) {
                        // Store original opacity for miniature
                        if (!currMiniEdgeElement.dataset.originalOpacity) {
                            currMiniEdgeElement.dataset.originalOpacity = currMiniEdgeElement.getAttribute('opacity') || '1';
                        }
                        // Reduce opacity for all mini edges
                        currMiniEdgeElement.setAttribute('opacity', '0.2');
                    }
                });
                
                // Now highlight just the edge we're hovering over
                const edgeElement = document.getElementById(edgeId);
                const miniEdgeElement = document.getElementById('mini-' + edgeId);
                
                if (edgeElement) {
                    // Store original styles for restoration if not already stored
                    if (!edgeElement.dataset.originalStyles) {
                        const paths = edgeElement.querySelectorAll('path');
                        paths.forEach((path, index) => {
                            path.dataset.originalStrokeWidth = path.getAttribute('stroke-width') || '1';
                            path.dataset.originalOpacity = path.getAttribute('opacity') || '1';
                        });
                        edgeElement.dataset.originalStyles = 'saved';
                    }
                    
                    // Apply highlighting to the hovered edge
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
                    
                    // Set this edge to full opacity
                    edgeElement.setAttribute('opacity', '1');
                }
                
                // Also highlight the miniature edge
                if (miniEdgeElement) {
                    // Store original styles for mini edge
                    if (!miniEdgeElement.dataset.originalStyles) {
                        const miniPaths = miniEdgeElement.querySelectorAll('path');
                        miniPaths.forEach((path, index) => {
                            path.dataset.originalStrokeWidth = path.getAttribute('stroke-width') || '1';
                            path.dataset.originalOpacity = path.getAttribute('opacity') || '1';
                        });
                        miniEdgeElement.dataset.originalStyles = 'saved';
                    }
                    
                    // Apply highlighting to mini edge
                    const miniPaths = miniEdgeElement.querySelectorAll('path');
                    if (miniPaths.length > 0) {
                        miniPaths[0].setAttribute('stroke-width', '6'); // Smaller for mini
                    }
                    if (miniPaths.length > 1) {
                        miniPaths[1].setAttribute('stroke-width', '3'); // Smaller for mini
                        miniPaths[1].setAttribute('opacity', '1');
                    }
                    if (miniPaths.length === 1) {
                        miniPaths[0].setAttribute('stroke-width', '2'); // Smaller for mini
                        miniPaths[0].setAttribute('opacity', '1');
                    }
                    
                    // Set miniature edge to full opacity
                    miniEdgeElement.setAttribute('opacity', '1');
                }
            });
            
            // Mouseout event - restore original styles for all edges
            edgeNameLi.addEventListener('mouseout', () => {
                // Restore opacity for all edges
                Object.keys(edges).forEach(currEdgeId => {
                    const currEdgeElement = document.getElementById(currEdgeId);
                    const currMiniEdgeElement = document.getElementById('mini-' + currEdgeId);
                    
                    if (currEdgeElement && currEdgeElement.dataset.originalOpacity) {
                        currEdgeElement.setAttribute('opacity', currEdgeElement.dataset.originalOpacity);
                    }
                    
                    if (currMiniEdgeElement && currMiniEdgeElement.dataset.originalOpacity) {
                        currMiniEdgeElement.setAttribute('opacity', currMiniEdgeElement.dataset.originalOpacity);
                    }
                });
                
                // Restore specific styles for the edge we were hovering over
                const edgeElement = document.getElementById(edgeId);
                const miniEdgeElement = document.getElementById('mini-' + edgeId);
                
                if (edgeElement && edgeElement.dataset.originalStyles) {
                    const paths = edgeElement.querySelectorAll('path');
                    paths.forEach((path, index) => {
                        path.setAttribute('stroke-width', path.dataset.originalStrokeWidth || '1');
                        path.setAttribute('opacity', path.dataset.originalOpacity || '1');
                    });
                }
                
                if (miniEdgeElement && miniEdgeElement.dataset.originalStyles) {
                    const miniPaths = miniEdgeElement.querySelectorAll('path');
                    miniPaths.forEach((path, index) => {
                        path.setAttribute('stroke-width', path.dataset.originalStrokeWidth || '1');
                        path.setAttribute('opacity', path.dataset.originalOpacity || '1');
                    });
                }
            });
        });

        // Use getComputedStyle to get accurate dimensions
        const computedStyle = window.getComputedStyle(selectionContainer);
        const containerWidth = parseFloat(computedStyle.width);
        const containerHeight = parseFloat(computedStyle.height);
        rect = selectionContainer.getBoundingClientRect();
        const left = window.innerWidth - (containerWidth * 2);

        selectionContainer.style.position = 'fixed';
        selectionContainer.style.left = `${left}px`;
        selectionContainer.style.right = 'auto';
        selectionContainer.style.top = `30px`;
        selectionContainer.style.bottom = 'auto';
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
            rect = miniatureContainer.getBoundingClientRect();
            dragState.type = 'miniature';
            dragState.target = miniatureContainer;
            dragState.startX = event.clientX;
            dragState.startY = event.clientY;
            dragState.offsetX = rect.left;
            dragState.offsetY = rect.top;
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
            dragState.offsetX = event.target.left;
            dragState.offsetY = event.target.top;
            const style = window.getComputedStyle(viewportIndicator);
            dragState.indicatorStartLeft = parseFloat(style.left);
            dragState.indicatorStartTop = parseFloat(style.top);
            viewportIndicator.classList.add('dragging');
            event.preventDefault();
            event.stopPropagation();
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
            dragState.startX = event.clientX;
            dragState.startY = event.clientY;
            dragState.offsetX = rect.left;
            dragState.offsetY = rect.top;
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

            // Stop event from reaching the SVG
            event.preventDefault();
            event.stopPropagation();

            dragState.type = 'selection';
            dragState.target = selectionContainer;
            const rect = selectionContainer.getBoundingClientRect();
            dragState.startX = event.clientX;
            dragState.startY = event.clientY;
            dragState.offsetX = rect.left;
            dragState.offsetY = rect.top;
            
            // Don't add dragging to metadataContainer - BUG FIX
            // metadataContainer.classList.add('dragging');
            selectionContainer.classList.add('dragging');
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
        // Check if we're inside selection-container or its children
        if (event.target.closest('#selection-container')) {
            return; // Don't initiate pan if we're in the selection container
        }

        event.preventDefault();
        dragState.handle = event;
        event.stopPropagation();
        let rect = event.target.getBoundingClientRect();
        dragState.target = event.target;
        dragState.startX = event.clientX;
        dragState.startY = event.clientY;
        dragState.offsetX = rect.left;
        dragState.offsetY = rect.top;
        dragState.startHeight = rect.height;
        dragState.startWidth = rect.width;
        dragState.handle = event.target;
        if (event.target.id === 'resize_handle_se' || event.target.id === 'resize_handle_nw') {
            // Don't do anything here - the dedicated event listeners will handle it
            return;
        }
        dragState.type = 'pan';
        dragState.startX = event.clientX;
        dragState.startY = event.clientY;

        dragState.offsetX = rect.left;
        dragState.offsetY = rect.top;

    });

    // --- MOUSE MOVE HANDLER ---
    window.addEventListener('mousemove', (event) => {
        let target, enclosing_container, dx, dy;
        target = event.target;
        enclosing_container = target.getBoundingClientRect();
        startX = dragState.startX;
        startY = dragState.startY;

        if (!dragState.type) return;
        if (dragState.type === 'pan') {
            if (!isPanning && startX !== undefined && startY !== undefined) {
                dx = Math.abs(event.clientX - startX);
                dy = Math.abs(event.clientY - startY);
                if (dx > dragThreshold || dy > dragThreshold) {
                    isPanning = true;
                    svg.classList.add('grabbing');
                }
            }
            if (isPanning) {
                let panX = 0.03
                event.preventDefault();
                event.stopPropagation();
                dx = event.clientX - startX;
                dy = event.clientY - startY;
                userTx += (dx * panX) / (userS * initialS);
                userTy += (dy * panX) / (userS * initialS);
                applyTransform();
            }
        } else if (['miniature', 'metadata', 'selection'].includes(dragState.type)) {
            dx = event.clientX - dragState.startX + dragState.offsetX;
            dy = event.clientY - dragState.startY + dragState.offsetY;

            //console.log(`Dragging ${dragState.type} to (${dx}, ${dy})`);
            dragState.target.style.left = `${dx}px`;
            dragState.target.style.top = `${dy}px`;

        } else if (dragState.type === 'indicator') {
            event.preventDefault();
            const miniRect = miniatureContainer.getBoundingClientRect();

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

        } else if (dragState.type === 'resize') {
            event.preventDefault();
            event.stopPropagation();
            
            // Calculate how much the mouse has moved
            const dx = event.clientX - dragState.startX;
            const dy = event.clientY - dragState.startY;
            
            // Get the SVG element inside the container
            const container = dragState.target;
            const svgImage = container.querySelector('svg');
            
            // Calculate new dimensions based on which handle is being dragged
            let newWidth, newHeight, newLeft, newTop;
            
            if (dragState.handle === 'nw') {
                // Northwest handle: resize and reposition
                newWidth = Math.max(100, dragState.startWidth - dx);
                newHeight = Math.max(80, dragState.startHeight - dy);
                newLeft = dragState.startLeft + (dragState.startWidth - newWidth);
                newTop = dragState.startTop + (dragState.startHeight - newHeight);
                
                // Update position
                container.style.left = `${newLeft}px`;
                container.style.top = `${newTop}px`;
            } 
            else if (dragState.handle === 'se') {
                // Southeast handle: just resize
                newWidth = Math.max(100, dragState.startWidth + dx);
                newHeight = Math.max(80, dragState.startHeight + dy);
            }
            
            // Update dimensions for both container and SVG
            container.style.width = `${newWidth}px`;
            container.style.height = `${newHeight}px`;
            
            if (svgImage) {
                svgImage.setAttribute('width', `${newWidth}px`);
                svgImage.setAttribute('height', `${newHeight}px`);
            }
        }
    });

    // --- MOUSE UP HANDLER ---
    window.addEventListener('mouseup', (event) => {
        if (!dragState.type) return;
        if (dragState.target) {
            dragState.target.classList.remove('dragging');
            dragState.target.classList.remove('resizing');
        }
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
        // Reset all dragState properties
        dragState.type = null;
        dragState.target = null;
        dragState.handle = null;
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
            window.location.reload();

        }
    });

    window.addEventListener('scroll', onViewportChange, { passive: true });
    window.addEventListener('resize', onViewportChange, { passive: true });

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
        // Click on SVG background (not node/edge): zoom to point
        if (
            event.target === svg ||
            (!event.target.closest('.node') && !event.target.closest('.edge'))
        ) {
            // Get mouse position relative to SVG
            const pt = svg.createSVGPoint();
            pt.x = event.clientX;
            pt.y = event.clientY;
            const svgP = pt.matrixTransform(mainGroup.getScreenCTM().inverse());
            zoomToPoint(svgP.x, svgP.y, userS);
            event.stopPropagation();
            return;
        }
    }
    );


    // --- Consolidated event listeners
    document.addEventListener('click', function (event) {
        if (event.target.classList.contains('minimize-btn')) {
            const btn = event.target;
            const contents = btn.parentNode.parentNode.childNodes;
            btn.innerHTML = btn.innerHTML === '+' ? '–' : '+';
            contents.forEach(content => {
                if (content.nodeType !== Node.ELEMENT_NODE) return;
                if (content.classList.contains('container-content')) {
                    content.style.display = content.style.display === 'none' ? '' : 'none';
                }
            });
            event.stopPropagation();
            return;
        }

        // SVG highlight click handler
        if (event.target.closest('svg')) {
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
                return;
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
                return;
            }

            // Click on SVG background (not node/edge): zoom to point
            if (
                event.target === svg ||
                (!event.target.closest('.node') && !event.target.closest('.edge'))
            ) {
                // Get mouse position relative to SVG
                const pt = svg.createSVGPoint();
                pt.x = event.clientX;
                pt.y = event.clientY;
                const svgP = pt.matrixTransform(mainGroup.getScreenCTM().inverse());
                zoomToPoint(svgP.x, svgP.y, userS);
                event.stopPropagation();
                return;
            }
        }

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
            metadataContainer.style.left = '10px';
            metadataContainer.style.top = '20px';
            metadataContainer.style.zIndex = '10000';
        }

        // Top right for miniature/overview
        const miniatureContainer = document.getElementById('miniature-container');
        let rect = metadataContainer.getClientRects()[0];
        if (miniatureContainer) {
            miniatureContainer.style.position = 'fixed';
            miniatureContainer.style.left = rect.width + 'px';
            miniatureContainer.style.right = '';
            miniatureContainer.style.top = '20px';
            miniatureContainer.style.zIndex = '10001';
        }
        // Bottom left for selection
        const selectionContainer = document.getElementById('selection-container');
        if (selectionContainer) {
            // Additional positioning logic if needed
        }
    }
    placeFloatingWindows();
    ensureResizeHandles(miniatureContainer);
    ensureResizeHandles(selectionContainer);
    makeResizable(miniatureContainer);
    makeResizable(selectionContainer);

    // Add this function after the showSelectionWindow function
    function ensureResizeHandles(container) {
        if (!container) return;
        
        // Check for SE handle
        let seHandle = container.querySelector('#resize_handle_se');
        if (!seHandle) {
            seHandle = document.createElement('div');
            seHandle.id = 'resize_handle_se';
            seHandle.className = 'resize-handle se';
            seHandle.style.position = 'absolute';
            seHandle.style.right = '0';
            seHandle.style.bottom = '0';
            seHandle.style.width = '10px';
            seHandle.style.height = '10px';
            seHandle.style.cursor = 'nwse-resize';
            seHandle.style.backgroundColor = '#666';
            container.appendChild(seHandle);
        }
        
        // Check for NW handle
        let nwHandle = container.querySelector('#resize_handle_nw');
        if (!nwHandle) {
            nwHandle = document.createElement('div');
            nwHandle.id = 'resize_handle_nw';
            nwHandle.className = 'resize-handle nw';
            nwHandle.style.position = 'absolute';
            nwHandle.style.left = '0';
            nwHandle.style.top = '0';
            nwHandle.style.width = '10px';
            nwHandle.style.height = '10px';
            nwHandle.style.cursor = 'nwse-resize';
            nwHandle.style.backgroundColor = '#666';
            container.appendChild(nwHandle);
        }
    }

    // Add this after makeResizable(selectionContainer)

    // Add font scaling functionality for the selection window
    function setupAdaptiveFontSize(container, innerContainer) {
        if (!container || !innerContainer) return;
        
        // Set initial overflow to hidden to prevent content spilling
        innerContainer.style.overflow = 'hidden';
        
        // Function to adjust font size based on container width
        const adjustFontSize = () => {
            const containerWidth = container.clientWidth;
            const containerHeight = container.clientHeight;
            
            // Base font size and minimum font size
            const baseFontSize = 14; // Default font size in pixels
            const minFontSize = 9;   // Minimum font size in pixels
            
            // Calculate scaling factor based on width
            // Adjust these numbers to tune the scaling behavior
            const idealWidth = 400;  // Width at which we want the base font size
            let scaleFactor = containerWidth / idealWidth;
            
            // Ensure font size stays within reasonable bounds
            let newFontSize = Math.max(minFontSize, Math.min(baseFontSize, baseFontSize * scaleFactor));
            
            // Apply the new font size to the inner container
            innerContainer.style.fontSize = `${newFontSize}px`;
            
            // Also adjust line height for better readability
            innerContainer.style.lineHeight = `${Math.max(1.2, 1 + (scaleFactor * 0.2))}`;
        };
        
        // Create a ResizeObserver to watch for size changes
        const resizeObserver = new ResizeObserver(() => {
            requestAnimationFrame(adjustFontSize);
        });
        
        // Start observing the container
        resizeObserver.observe(container);
        
        // Apply initial font sizing
        adjustFontSize();
    }

    // Call the function for the selection container
    if (selectionContainer && selectionInner) {
        setupAdaptiveFontSize(selectionContainer, selectionInner);
    }
});
