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
    // Update the addWindowControls function to take a buttons config parameter
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
        
        const btnConfig = options.buttons || {};
        const allControls = {};
        
        // Only add edit button if specified in options
        if (btnConfig.edit) {
            let editBtn = controls.querySelector('.edit-btn');
            if (!editBtn) {
                editBtn = document.createElement('button');
                editBtn.className = 'edit-btn';
                editBtn.title = 'Edit content';
                editBtn.innerHTML = '✏️';  // Pencil emoji
                controls.appendChild(editBtn);
            }
            allControls.editBtn = editBtn;
        }
        
        // Only add copy button if specified in options
        if (btnConfig.copy) {
            let copyBtn = controls.querySelector('.copy-btn');
            if (!copyBtn) {
                copyBtn = document.createElement('button');
                copyBtn.className = 'copy-btn';
                copyBtn.title = 'Copy to clipboard';
                copyBtn.innerHTML = '📋';
                controls.appendChild(copyBtn);
            }
            allControls.copyBtn = copyBtn;
        }
        
        // Always add minimize button
        let minBtn = controls.querySelector('.minimize-btn');
        if (!minBtn) {
            minBtn = document.createElement('button');
            minBtn.className = 'minimize-btn';
            minBtn.title = 'Minimize';
            minBtn.innerHTML = '–';
            controls.appendChild(minBtn);
        }
        allControls.minBtn = minBtn;
        
        // Always add close button
        let closeBtn = controls.querySelector('.close-btn');
        if (!closeBtn) {
            closeBtn = document.createElement('button');
            closeBtn.className = 'close-btn';
            closeBtn.title = 'Close';
            closeBtn.innerHTML = '×';
            controls.appendChild(closeBtn);
        }
        allControls.closeBtn = closeBtn;

        // Set up event handlers
        
        // Edit button handler (only for selection window)
        if (allControls.editBtn) {
            allControls.editBtn.onclick = (e) => {
                e.stopPropagation();
                
                // Find the inner container
                const innerContainer = windowElem.querySelector('#selection-inner-container');
                if (!innerContainer) return;
                
                // Skip if textarea already exists
                if (innerContainer.querySelector('textarea')) return;
                
                // Save the original content
                const originalContent = innerContainer.innerHTML;
                let text = innerContainer.innerText || innerContainer.textContent || '';
                
                // Create textarea
                const rect = innerContainer.getBoundingClientRect();
                const width = rect.width;
                const height = rect.height;
                
                const XHTML_NS = "http://www.w3.org/1999/xhtml";
                const textarea = document.createElementNS(XHTML_NS, 'textarea');
                textarea.value = text;
                textarea.setAttribute('aria-label', 'Edit selection details');
                textarea.setAttribute('style', 
                    `width:${width}px;height:${height}px;box-sizing:border-box;font-family:inherit;font-size:inherit;resize:vertical;`
                );
                
                // Replace content with textarea
                innerContainer.innerHTML = '';
                innerContainer.appendChild(textarea);
                textarea.focus();
                textarea.select();
                
                // Stop event propagation
                function stopEvent(e) {
                    e.stopPropagation();
                }
                
                textarea.addEventListener('mousedown', stopEvent, true);
                textarea.addEventListener('mousemove', stopEvent, true);
                textarea.addEventListener('mouseup', stopEvent, true);
                textarea.addEventListener('keydown', stopEvent, true);
                textarea.addEventListener('keyup', stopEvent, true);
                textarea.addEventListener('wheel', stopEvent, true);
                
                // Restore content on blur
                textarea.addEventListener('blur', function() {
                    innerContainer.innerHTML = originalContent;
                    
                    // Reattach table and edge event listeners
                    const tableNames = innerContainer.querySelectorAll('.table-name');
                    tableNames.forEach(tableName => {
                        const tableId = tableName.getAttribute('data-table-id');
                        // Re-attach all event handlers...
                        // (Your existing code for attaching event handlers)
                    });
                    
                    const edgeNames = innerContainer.querySelectorAll('.edge-name');
                    edgeNames.forEach(edgeName => {
                        const edgeId = edgeName.getAttribute('data-edge-id');
                        // Re-attach all event handlers...
                        // (Your existing code for attaching event handlers)
                    });
                });
            };
        }

        // Copy button handler (for metadata/miniature)
        if (allControls.copyBtn) {
            allControls.copyBtn.onclick = (e) => {
                e.stopPropagation();
                // Your existing copy-to-clipboard code
                const selectedTables = Array.from(document.querySelectorAll('.table-name.selected')).map(el => el.dataset.tableId);
                const selectedEdges = Array.from(document.querySelectorAll('.edge-name.selected')).map(el => el.dataset.edgeId);
                let copyText = '';
                
                // Rest of your copying logic...
                if (selectedTables.length) {
                    copyText += 'Tables:\n';
                    selectedTables.forEach(id => {
                        const table = tables[id];
                        if (table) {
                            copyText += `- ${id}: ${table.label || ''}\n`;
                        }
                    });
                }
                
                // Copy to clipboard
                navigator.clipboard.writeText(copyText).then(() => {
                    allControls.copyBtn.classList.add('copied');
                    setTimeout(() => {
                        allControls.copyBtn.classList.remove('copied');
                    }, 2000);
                });
            };
        }

        // Minimize button handler
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
        
        // Close button handler
        closeBtn.onclick = (e) => {
            e.stopPropagation();
            e.target.destroyRecursive = true;
            windowElem.style.display = 'none';
            if (options.onClose) options.onClose();
        };
        
        controls.addEventListener('mousedown', e => e.stopPropagation());
        controls.addEventListener('click', e => e.stopPropagation());
        
        return allControls;
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
            
            // ADD THE NEW CLICK HANDLER HERE
            tableNameSpan.addEventListener('click', (e) => {
                e.preventDefault(); // Prevent scrolling
                e.stopPropagation();
                
                // Clear any existing highlights
                clearAllHighlights();
                
                // Set this table as the highlighted element
                highlightedElementId = tableId;
                
                // Get connected edges and tables (same logic as SVG click handler)
                const connectedEdges = tables[tableId].edges;
                const connectedTables = [tableId, ...connectedEdges.map(edgeId => edges[edgeId].tables).flat()];
                const uniqueTables = [...new Set(connectedTables)];
                
                // Highlight everything
                highlightElements(uniqueTables, connectedEdges);
                
                // Center view on the selected table
                const tableElement = document.getElementById(tableId);
                if (tableElement) {
                    // Get the bounding box of the table element
                    const bbox = tableElement.getBBox();
                    // Center coordinates of the table
                    const centerX = bbox.x + bbox.width / 2;
                    const centerY = bbox.y + bbox.height / 2;
                    // Center the view on the table, maintaining current zoom level
                    zoomToPoint(centerX, centerY, userS);
                }
                
                // No need to call showSelectionWindow again since we're already in it
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

        // Get
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
        addWindowControls(miniatureContainer, { 
            buttons: { copy: false, edit: false }  // No copy or edit button
        });
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
        addWindowControls(metadataContainer, { 
            buttons: { copy: true, edit: false }   // Copy button but no edit
        });
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
        addWindowControls(selectionContainer, { 
            buttons: { copy: false, edit: true }   // Edit button but no copy
        });
        // Modified selection window mousedown handler
        selectionContainer.addEventListener('mousedown', (event) => {
            // Prevent drag if clicking on controls/buttons
            if (
                event.target.closest('.window-controls') ||
                event.target.tagName === 'BUTTON'
            ) return;

            // Stop event from reaching the SVG
            event.preventDefault();
            event.stopPropagation();

            // Create a separate drag state specifically for the window
            // This avoids conflicts with the SVG pan state
            const windowDragState = {
                type: 'selection-window',
                target: selectionContainer,
                startX: event.clientX,
                startY: event.clientY,
                offsetX: selectionContainer.getBoundingClientRect().left,
                offsetY: selectionContainer.getBoundingClientRect().top
            };
            
            // Store this separate state
            selectionContainer._dragState = windowDragState;
            selectionContainer.classList.add('dragging');
            
            // Create window-specific mousemove handler that won't interfere with SVG
            const handleMouseMove = (moveEvent) => {
                moveEvent.preventDefault();
                moveEvent.stopPropagation();
                
                const dx = moveEvent.clientX - windowDragState.startX + windowDragState.offsetX;
                const dy = moveEvent.clientY - windowDragState.startY + windowDragState.offsetY;
                
                selectionContainer.style.left = `${dx}px`;
                selectionContainer.style.top = `${dy}px`;
            };
            
            // Create window-specific mouseup handler
            const handleMouseUp = (upEvent) => {
                selectionContainer.classList.remove('dragging');
                window.removeEventListener('mousemove', handleMouseMove);
                window.removeEventListener('mouseup', handleMouseUp);
                selectionContainer._dragState = null;
            };
            
            // Add temporary event listeners for this drag operation only
            window.addEventListener('mousemove', handleMouseMove);
            window.addEventListener('mouseup', handleMouseUp);
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
  

    function initializeSvgView() {
        console.log("Starting SVG initialization...");
        
        // Ensure all required elements exist
        if (!svg || !mainGroup || !miniatureContainer || !viewportIndicator || !getMainERDBounds()) {
            console.log("SVG elements not ready, retrying in 200ms...");
            setTimeout(initializeSvgView, 200);
            return;
        }
        
        try {
            // Get bounds and verify they're valid
            const mainBounds = getMainERDBounds();
            if (!mainBounds || typeof mainBounds !== 'object' || 
                mainBounds.width <= 0 || mainBounds.height <= 0) {
                console.log("Invalid SVG bounds, retrying in 200ms...");
                setTimeout(initializeSvgView, 200);
                return;
            }
            
            console.log("SVG bounds:", mainBounds);
            
            // Calculate center of the diagram
            const centerX = mainBounds.x + mainBounds.width / 2;
            const centerY = mainBounds.y + mainBounds.height / 2;
            
            // Calculate zoom level (fit the diagram with some padding)
            const viewportWidth = window.innerWidth;
            const viewportHeight = window.innerHeight;
            const scaleX = viewportWidth / (mainBounds.width * 1.1); // 10% padding
            const scaleY = viewportHeight / (mainBounds.height * 1.1);
            const scale = Math.min(scaleX, scaleY, 1); // Don't zoom in beyond 1:1
            
            // Reset and apply transformation
            userTx = 0;
            userTy = 0;
            userS = scale;
            
            console.log(`Centering at (${centerX}, ${centerY}) with scale ${scale}`);
            
            // Use zoomToPoint for consistent positioning
            zoomToPoint(centerX, centerY, scale);
            
            // Force viewport indicator update
            updateViewportIndicator();
            
            // Ensure viewport indicator is visible
            if (viewportIndicator) {
                viewportIndicator.style.display = 'block';
                viewportIndicator.style.opacity = '1';
                viewportIndicator.style.border = '2px solid #ff4081';
                viewportIndicator.style.backgroundColor = 'rgba(255, 64, 129, 0.2)';
                viewportIndicator.style.pointerEvents = 'all';
                
                // Add this debug to check viewport indicator dimensions
                const viStyle = window.getComputedStyle(viewportIndicator);
                console.log("Viewport indicator styles:", {
                    display: viStyle.display,
                    width: viStyle.width,
                    height: viStyle.height,
                    left: viStyle.left,
                    top: viStyle.top,
                    opacity: viStyle.opacity
                });
            }
        } catch (error) {
            console.error("Error during SVG initialization:", error);
            setTimeout(initializeSvgView, 300);
        }
    }

    // Primary initialization on DOMContentLoaded
    document.addEventListener('DOMContentLoaded', () => {
        console.log("DOMContentLoaded fired");
        // Small delay to ensure SVG is fully parsed
        setTimeout(initializeSvgView, 300);
        
        // Also initialize when window is resized
        window.addEventListener('resize', () => {
            // Debounce the resize event
            if (window.resizeTimer) clearTimeout(window.resizeTimer);
            window.resizeTimer = setTimeout(() => {
                console.log("Window resized, updating viewport indicator");
                updateViewportIndicator();
            }, 250);
        });
    });

    // Backup initialization for cases when DOMContentLoaded already fired
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        console.log("Document already loaded, initializing directly");
        setTimeout(initializeSvgView, 300);
    }
});
