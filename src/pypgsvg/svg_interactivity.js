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
    let selectionContainerManuallyPositioned = false; // Flag to track if user has manually positioned selection container
    let infoWindowsVisible = true; // Flag to track if informational windows are visible

    // --- Utility Functions ---

    // Get reliable viewport dimensions
    function getViewportDimensions() {
        return {
            width: document.documentElement.clientWidth || document.body.clientWidth || window.innerWidth,
            height: document.documentElement.clientHeight || document.body.clientHeight || window.innerHeight
        };
    }

    function fallbackCopyTextToClipboard(text, button) {
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.top = "0";
        textArea.style.left = "0";
        textArea.style.position = "fixed";
        textArea.style.opacity = "0";

        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();

        try {
            const successful = document.execCommand('copy');
            if (successful) {
                button.innerHTML = '✓';
                button.title = 'Copied!';
                setTimeout(() => {
                    button.innerHTML = '📋';
                    button.title = 'Copy to clipboard';
                }, 2000);
            } else {
                console.error('Fallback: Oops, unable to copy');
            }
        } catch (err) {
            console.error('Fallback: Oops, unable to copy', err);
        }

        document.body.removeChild(textArea);
    }

    function downloadTextAsFile(text, filename) {
        const blob = new Blob([text], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);

        // Create HTML anchor element explicitly
        const a = document.createElementNS('http://www.w3.org/1999/xhtml', 'a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;

        // Find a suitable parent element (body, html, or documentElement)
        let parentElement = document.body;
        if (!parentElement) {
            parentElement = document.documentElement;
        }
        if (!parentElement) {
            parentElement = document.querySelector('html');
        }
        if (!parentElement) {
            // Fallback: try to find any element we can append to
            parentElement = document.querySelector('svg') || document.firstElementChild;
        }

        if (parentElement) {
            parentElement.appendChild(a);
            a.click();
            parentElement.removeChild(a);
        } else {
            // Last resort: try direct click without appending
            a.click();
        }

        // Clean up
        window.URL.revokeObjectURL(url);
    }

    // --- URL Parameter Handling ---
    function parseUrlParameters() {
        const queryString = window.location.search;
        
        // Check if info windows should be hidden via URL parameter
        if (queryString.includes('hide')) {
            infoWindowsVisible = false;
            
            // Apply the hiding immediately since containers now exist
            const metadataContainer = document.getElementById('metadata-container');
            const miniatureContainer = document.getElementById('miniature-container');
            const selectionContainer = document.getElementById('selection-container');
            
            if (metadataContainer) {
                metadataContainer.style.display = 'none';
            }
            if (miniatureContainer) {
                miniatureContainer.style.display = 'none';
            }
            if (selectionContainer) {
                selectionContainer.style.display = 'none';
            }
        }
    }

    // --- Info Windows Toggle ---
    function toggleInfoWindows() {
        infoWindowsVisible = !infoWindowsVisible;
        
        const metadataContainer = document.getElementById('metadata-container');
        const miniatureContainer = document.getElementById('miniature-container');
        const selectionContainer = document.getElementById('selection-container');
        
        const displayValue = infoWindowsVisible ? 'block' : 'none';
        
        if (metadataContainer) {
            metadataContainer.style.display = displayValue;
        }
        if (miniatureContainer) {
            miniatureContainer.style.display = displayValue;
        }
        if (selectionContainer) {
            selectionContainer.style.display = displayValue;
        }
    }

    // --- Window Controls ---
    // Update the addWindowControls function to take a buttons config parameter
    function addWindowControls(windowElem, options = {}) {
        // Helper function to remove emojis from text
        function removeEmojis(text) {
            // Remove common emojis used in the interface
            return text
                .replace(/📊|⚡|🔗|🔑|→|•/g, '')  // Remove specific emojis
                .replace(/\s+/g, ' ')  // Normalize whitespace
                .trim();
        }

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

        // Only add download button if specified in options
        if (btnConfig.download) {
            let downloadBtn = controls.querySelector('.download-btn');
            if (!downloadBtn) {
                downloadBtn = document.createElement('button');
                downloadBtn.className = 'download-btn';
                downloadBtn.title = 'Download as file';
                downloadBtn.innerHTML = '💾';
                controls.appendChild(downloadBtn);
            }
            allControls.downloadBtn = downloadBtn;
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

        monclick = (container) => {
            container.classList.toggle('minimized');

            // Find all elements with container-content class within this container
            let elementsToToggle = container.querySelectorAll('.container-content');

            if (container.classList.contains('minimized')) {
                elementsToToggle.forEach(element => {
                    // Store the original display value before hiding
                    const currentDisplay = window.getComputedStyle(element).display;
                    element.setAttribute('data-original-display', currentDisplay);
                    element.style.display = 'none';
                });
                minBtn.innerHTML = '+';
                minBtn.title = 'Restore';
            } else {
                elementsToToggle.forEach(element => {
                    // Restore the original display value
                    const originalDisplay = element.getAttribute('data-original-display');
                    if (originalDisplay && originalDisplay !== 'none') {
                        element.style.display = originalDisplay;
                    } else {
                        // Fallback to empty string to use CSS default
                        element.style.display = '';
                    }
                    element.removeAttribute('data-original-display');
                });
                minBtn.innerHTML = '–';
                minBtn.title = 'Minimize';
            }
            if (options.onMinimize) options.onMinimize(container.classList.contains('minimized'));
        };

        // Also add event listener as backup
        minBtn.addEventListener('click', (e) => {
            let target = e.target.parentElement.parentElement;
            e.preventDefault();
            e.stopPropagation();
            monclick(target);
        });
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

        closeBtn.addEventListener('click', (e) => {
            windowElem.style.display = 'none';
        });

        allControls.closeBtn = closeBtn;

        if (allControls.copyBtn) {
            allControls.copyBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();

                let copyText = '';
                const containerId = windowElem.id;

                if (containerId === 'metadata-container') {
                    // For metadata container, copy the structured content
                    const sections = windowElem.querySelectorAll('.metadata-section');
                    sections.forEach(section => {
                        const title = section.querySelector('h3')?.textContent || '';
                        if (title) {
                            copyText += `${title}\n${'='.repeat(title.length)}\n`;
                        }

                        // Extract metadata items
                        const items = section.querySelectorAll('.metadata-item');
                        items.forEach(item => {
                            const label = item.querySelector('.label')?.textContent || '';
                            const value = item.querySelector('.value')?.textContent || '';
                            if (label && value) {
                                copyText += `${label}: ${value}\n`;
                            }
                        });

                        // Extract single metadata items
                        const singleItems = section.querySelectorAll('.metadata-single');
                        singleItems.forEach(item => {
                            const label = item.querySelector('.label')?.textContent || '';
                            const value = item.querySelector('.value')?.textContent || '';
                            if (label && value) {
                                copyText += `${label}: ${value}\n`;
                            }
                        });

                        // Extract parameter rows
                        const paramRows = section.querySelectorAll('.param-row');
                        paramRows.forEach(row => {
                            const label = row.querySelector('.param-label')?.textContent || '';
                            const value = row.querySelector('.param-value')?.textContent || '';
                            if (label && value) {
                                copyText += `${label} ${value}\n`;
                            }
                        });

                        copyText += '\n';
                    });
                } else if (containerId === 'selection-container') {
                    // For selection container, copy the organized content
                    const innerContainer = windowElem.querySelector('#selection-inner-container');
                    if (innerContainer) {
                        const sections = innerContainer.querySelectorAll('.selection-section');
                        sections.forEach(section => {
                            const title = section.querySelector('h3')?.textContent || '';
                            if (title) {
                                const cleanTitle = removeEmojis(title);
                                copyText += `${cleanTitle}\n${'='.repeat(cleanTitle.length)}\n`;
                            }

                            // Extract table names
                            const tableNames = section.querySelectorAll('.table-name');
                            tableNames.forEach(tableName => {
                                copyText += `${tableName.textContent}\n`;
                            });

                            // Extract edge information
                            const edgeNames = section.querySelectorAll('.edge-name');
                            edgeNames.forEach(edgeName => {
                                const h4 = edgeName.querySelector('h4');
                                const pre = edgeName.querySelector('pre');
                                if (h4) {
                                    const cleanH4 = removeEmojis(h4.textContent);
                                    copyText += `${cleanH4}\n`;
                                }
                                if (pre) {
                                    copyText += `${pre.textContent}\n`;
                                }
                            });

                            // Extract trigger information
                            const triggerInfos = section.querySelectorAll('.trigger-info');
                            triggerInfos.forEach(triggerInfo => {
                                const triggerName = triggerInfo.querySelector('.trigger-name')?.textContent || '';
                                const triggerEvent = triggerInfo.querySelector('.trigger-event')?.textContent || '';
                                if (triggerName && triggerEvent) {
                                    copyText += `${triggerName}: ${triggerEvent}\n`;
                                }
                                // Also get any additional function info
                                const functionDiv = triggerInfo.querySelector('div[style*="font-size: 0.8rem"]');
                                if (functionDiv) {
                                    const cleanFunction = removeEmojis(functionDiv.textContent);
                                    copyText += `  ${cleanFunction}\n`;
                                }
                            });

                            copyText += '\n';
                        });
                    }
                } else {
                    // Fallback: copy all text content
                    const textContent = windowElem.textContent || windowElem.innerText || '';
                    copyText = textContent.trim();
                }

                // Copy to clipboard
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(copyText).then(() => {
                        // Visual feedback
                        allControls.copyBtn.innerHTML = '✓';
                        allControls.copyBtn.title = 'Copied!';
                        setTimeout(() => {
                            allControls.copyBtn.innerHTML = '📋';
                            allControls.copyBtn.title = 'Copy to clipboard';
                        }, 2000);
                    }).catch(err => {
                        console.error('Failed to copy to clipboard:', err);
                        // Fallback for older browsers
                        fallbackCopyTextToClipboard(copyText, allControls.copyBtn);
                    });
                } else {
                    // Fallback for older browsers
                    fallbackCopyTextToClipboard(copyText, allControls.copyBtn);
                }
            });
        }

        // Download button handler (for metadata/selection)
        if (allControls.downloadBtn) {
            allControls.downloadBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();

                let downloadText = '';
                let filename = 'container-content.txt';
                const containerId = windowElem.id;

                if (containerId === 'metadata-container') {
                    filename = 'database-metadata.txt';
                    // For metadata container, copy the structured content
                    const sections = windowElem.querySelectorAll('.metadata-section');
                    sections.forEach(section => {
                        const title = section.querySelector('h3')?.textContent || '';
                        if (title) {
                            downloadText += `${title}\n${'='.repeat(title.length)}\n`;
                        }

                        // Extract metadata items
                        const items = section.querySelectorAll('.metadata-item');
                        items.forEach(item => {
                            const label = item.querySelector('.label')?.textContent || '';
                            const value = item.querySelector('.value')?.textContent || '';
                            if (label && value) {
                                downloadText += `${label}: ${value}\n`;
                            }
                        });

                        // Extract single metadata items
                        const singleItems = section.querySelectorAll('.metadata-single');
                        singleItems.forEach(item => {
                            const label = item.querySelector('.label')?.textContent || '';
                            const value = item.querySelector('.value')?.textContent || '';
                            if (label && value) {
                                downloadText += `${label}: ${value}\n`;
                            }
                        });

                        // Extract parameter rows
                        const paramRows = section.querySelectorAll('.param-row');
                        paramRows.forEach(row => {
                            const label = row.querySelector('.param-label')?.textContent || '';
                            const value = row.querySelector('.param-value')?.textContent || '';
                            if (label && value) {
                                downloadText += `${label} ${value}\n`;
                            }
                        });

                        downloadText += '\n';
                    });
                } else if (containerId === 'selection-container') {
                    filename = 'selection-details.txt';
                    // For selection container, copy the organized content
                    const innerContainer = windowElem.querySelector('#selection-inner-container');
                    if (innerContainer) {
                        const sections = innerContainer.querySelectorAll('.selection-section');
                        sections.forEach(section => {
                            const title = section.querySelector('h3')?.textContent || '';
                            if (title) {
                                const cleanTitle = removeEmojis(title);
                                downloadText += `${cleanTitle}\n${'='.repeat(cleanTitle.length)}\n`;
                            }

                            // Extract table names
                            const tableNames = section.querySelectorAll('.table-name');
                            tableNames.forEach(tableName => {
                                downloadText += `${tableName.textContent}\n`;
                            });

                            // Extract edge information
                            const edgeNames = section.querySelectorAll('.edge-name');
                            edgeNames.forEach(edgeName => {
                                const h4 = edgeName.querySelector('h4');
                                const pre = edgeName.querySelector('pre');
                                if (h4) {
                                    const cleanH4 = removeEmojis(h4.textContent);
                                    downloadText += `${cleanH4}\n`;
                                }
                                if (pre) {
                                    downloadText += `${pre.textContent}\n`;
                                }
                            });

                            // Extract trigger information
                            const triggerInfos = section.querySelectorAll('.trigger-info');
                            triggerInfos.forEach(triggerInfo => {
                                const triggerName = triggerInfo.querySelector('.trigger-name')?.textContent || '';
                                const triggerEvent = triggerInfo.querySelector('.trigger-event')?.textContent || '';
                                if (triggerName && triggerEvent) {
                                    downloadText += `${triggerName}: ${triggerEvent}\n`;
                                }
                                // Also get any additional function info
                                const functionDiv = triggerInfo.querySelector('div[style*="font-size: 0.8rem"]');
                                if (functionDiv) {
                                    const cleanFunction = removeEmojis(functionDiv.textContent);
                                    downloadText += `  ${cleanFunction}\n`;
                                }
                            });

                            downloadText += '\n';
                        });
                    }
                } else {
                    // Fallback: copy all text content
                    const textContent = windowElem.textContent || windowElem.innerText || '';
                    downloadText = textContent.trim();
                }

                // Download the file
                downloadTextAsFile(downloadText, filename);

                // Visual feedback
                allControls.downloadBtn.innerHTML = '✓';
                allControls.downloadBtn.title = 'Downloaded!';
                setTimeout(() => {
                    allControls.downloadBtn.innerHTML = '💾';
                    allControls.downloadBtn.title = 'Download as file';
                }, 2000);
            });
        }

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

                // Ensure we have inline styles set for consistent positioning
                if (!windowElem.style.left) {
                    windowElem.style.left = `${rect.left}px`;
                }
                if (!windowElem.style.top) {
                    windowElem.style.top = `${rect.top}px`;
                }
                if (!windowElem.style.width) {
                    windowElem.style.width = `${windowElem.offsetWidth}px`;
                }
                if (!windowElem.style.height) {
                    windowElem.style.height = `${windowElem.offsetHeight}px`;
                }

                dragState.target = windowElem; // The target is the window, not the handle
                dragState.handle = 'nw'; // Mark which handle we're using
                dragState.startX = event.clientX;
                dragState.startY = event.clientY;
                // Use consistent CSS dimensions instead of getBoundingClientRect
                dragState.startWidth = parseFloat(windowElem.style.width);
                dragState.startHeight = parseFloat(windowElem.style.height);
                // Now we can safely use the inline style values
                dragState.startLeft = parseFloat(windowElem.style.left);
                dragState.startTop = parseFloat(windowElem.style.top);
                windowElem.classList.add('resizing');
                event.preventDefault();
                event.stopPropagation();
            });

            // Prevent click events on resize handle
            nwHandle.addEventListener('click', function(event) {
                event.preventDefault();
                event.stopPropagation();
            });
        }

        if (seHandle) {
            seHandle.addEventListener('mousedown', function(event) {
                dragState.type = 'resize';
                const rect = windowElem.getBoundingClientRect();

                // Ensure we have inline styles and use consistent CSS dimensions
                if (!windowElem.style.width) {
                    windowElem.style.width = `${windowElem.offsetWidth}px`;
                }
                if (!windowElem.style.height) {
                    windowElem.style.height = `${windowElem.offsetHeight}px`;
                }

                dragState.target = windowElem; // The target is the window, not the handle
                dragState.handle = 'se'; // Mark which handle we're using
                dragState.startX = event.clientX;
                dragState.startY = event.clientY;
                // Use the CSS dimensions instead of getBoundingClientRect
                dragState.startWidth = parseFloat(windowElem.style.width);
                dragState.startHeight = parseFloat(windowElem.style.height);
                windowElem.classList.add('resizing');
                event.preventDefault();
                event.stopPropagation();
            });

            // Prevent click events on resize handle
            seHandle.addEventListener('click', function(event) {
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
        const viewport = getViewportDimensions();
        pt2.x = viewport.width; pt2.y = viewport.height;
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

    const updateSelectionContainerPosition = () => {
        const selectionContainer = document.getElementById('selection-container');
        const metadataContainer = document.getElementById('metadata-container');
        const miniatureContainer = document.getElementById('miniature-container');

        console.log('updateSelectionContainerPosition called', {
            selectionContainer: !!selectionContainer,
            metadataContainer: !!metadataContainer,
            miniatureContainer: !!miniatureContainer,
            manuallyPositioned: selectionContainerManuallyPositioned
        });

        // Don't auto-position if user has manually moved the selection container
        if (selectionContainerManuallyPositioned) {
            console.log('Selection container manually positioned, skipping auto-positioning');
            return;
        }

        if (selectionContainer && metadataContainer && miniatureContainer) {
            const miniatureRect = miniatureContainer.getBoundingClientRect();
            const metadataRect = metadataContainer.getBoundingClientRect();
            const margin = 16; // Same margin as other containers

            // Set width to be similar to metadata container
            const selectionWidth = metadataRect.width * 1.5;

            // Calculate max height (75% of viewport height)
            const viewport = getViewportDimensions();
            const maxHeight = Math.floor(viewport.height * 0.75);

            const leftPos = miniatureRect.right + margin;
            const topPos = miniatureRect.top;

            console.log(`Selection container positioning:`, {
                viewport: `${viewport.width}x${viewport.height}`,
                miniatureRect: miniatureRect,
                leftPos,
                topPos,
                selectionWidth,
                maxHeight
            });

            selectionContainer.style.position = 'fixed';
            selectionContainer.style.width = `${selectionWidth}px`;
            selectionContainer.style.maxHeight = `${maxHeight}px`;
            selectionContainer.style.left = `${leftPos}px`;
            selectionContainer.style.top = `${topPos}px`;
            selectionContainer.style.zIndex = '10001';

            console.log(`Selection container positioned at left: ${leftPos}px, top: ${topPos}px`);
        }
    };

    const onViewportChange = () => {
        requestAnimationFrame(updateViewportIndicator);
    };

    // --- Highlighting ---
    const GREY_COLOR = "#cccccc"; // color for non-highlighted elements

    // Helper function to convert hex color to rgba with specified opacity
    const hexToRgba = (hex, alpha = 1.0) => {
        // Remove # if present
        hex = hex.replace('#', '');

        // Handle 3-digit hex
        if (hex.length === 3) {
            hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
        }

        // Extract RGB values
        const r = parseInt(hex.substring(0, 2), 16);
        const g = parseInt(hex.substring(2, 4), 16);
        const b = parseInt(hex.substring(4, 6), 16);

        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    };

    // Helper function to convert RGB to HLS
    const rgbToHls = (r, g, b) => {
        r /= 255; g /= 255; b /= 255;
        const max = Math.max(r, g, b);
        const min = Math.min(r, g, b);
        let h, s, l = (max + min) / 2;

        if (max === min) {
            h = s = 0; // achromatic
        } else {
            const d = max - min;
            s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
            switch (max) {
                case r: h = (g - b) / d + (g < b ? 6 : 0); break;
                case g: h = (b - r) / d + 2; break;
                case b: h = (r - g) / d + 4; break;
            }
            h /= 6;
        }
        return [h, l, s];
    };

    // Helper function to convert HLS to RGB
    const hlsToRgb = (h, l, s) => {
        const hue2rgb = (p, q, t) => {
            if (t < 0) t += 1;
            if (t > 1) t -= 1;
            if (t < 1/6) return p + (q - p) * 6 * t;
            if (t < 1/2) return q;
            if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
            return p;
        };

        let r, g, b;
        if (s === 0) {
            r = g = b = l; // achromatic
        } else {
            const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
            const p = 2 * l - q;
            r = hue2rgb(p, q, h + 1/3);
            g = hue2rgb(p, q, h);
            b = hue2rgb(p, q, h - 1/3);
        }
        return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
    };

    // Helper function to saturate a hex color
    const saturateColor = (hexColor, saturationFactor = 2.0) => {
        // Validate input
        if (!hexColor || typeof hexColor !== 'string') {
            console.warn('Invalid hex color:', hexColor);
            return '#cccccc';
        }

        // Remove # if present
        let hex = hexColor.replace('#', '');

        // Handle 3-digit hex
        if (hex.length === 3) {
            hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
        }

        // Validate hex format
        if (hex.length !== 6 || !/^[0-9A-Fa-f]+$/.test(hex)) {
            console.warn('Invalid hex format:', hexColor, 'processed as:', hex);
            return hexColor; // Return original if invalid
        }

        // Convert hex to RGB
        const r = parseInt(hex.substring(0, 2), 16);
        const g = parseInt(hex.substring(2, 4), 16);
        const b = parseInt(hex.substring(4, 6), 16);

        // Validate RGB values
        if (isNaN(r) || isNaN(g) || isNaN(b)) {
            console.warn('Invalid RGB values:', r, g, b, 'from hex:', hexColor);
            return hexColor;
        }

        // Convert RGB to HLS
        const [h, l, s] = rgbToHls(r, g, b);

        // Increase saturation, clamping to valid range
        const newS = Math.min(1, Math.max(0, s * saturationFactor));

        // Convert back to RGB
        const [newR, newG, newB] = hlsToRgb(h, l, newS);

        // Validate final RGB values
        if (isNaN(newR) || isNaN(newG) || isNaN(newB)) {
            console.warn('Invalid final RGB values:', newR, newG, newB);
            return hexColor;
        }

        // Clamp to valid range
        const clampedR = Math.max(0, Math.min(255, Math.round(newR)));
        const clampedG = Math.max(0, Math.min(255, Math.round(newG)));
        const clampedB = Math.max(0, Math.min(255, Math.round(newB)));

        // Convert back to hex
        const finalHex = `#${clampedR.toString(16).padStart(2, '0')}${clampedG.toString(16).padStart(2, '0')}${clampedB.toString(16).padStart(2, '0')}`;

        return finalHex;
    };

    const getElementColor = (elem) => {
        if (!elem || !elem.id) return '#cccccc';

        const nodeId = elem.id.replace('mini-', '');

        if (elem.classList && elem.classList.contains('node')) {
            return tables[nodeId]?.defaultColor || '#cccccc';
        }

        if (elem.classList && elem.classList.contains('edge')) {
            return edges[nodeId]?.defaultColor || '#cccccc';
        }

        return '#cccccc';
    };

    // Function to apply visual emphasis effects for selection container hovers
    const setSaturationEffect = (elem, saturationFactor = 2.0, restore = false) => {
        if (!elem) return;
        let miniElem = null;
        const nodeId = elem.id;
        let isMini = nodeId.indexOf('mini-') != -1;

        if (!isMini) {
            const miniNodeId = 'mini-' + nodeId;
            miniElem = document.getElementById(miniNodeId);
            if (miniElem) {
                setSaturationEffect(miniElem, saturationFactor, restore);
            }
        }

        if (elem.classList && elem.classList.contains('node')) {
            if (restore) {
                // Remove visual emphasis
                elem.style.removeProperty('filter');
                elem.removeAttribute('transform');
                // Clear any stored original transform
                if (elem.dataset.originalTransform) {
                    elem.setAttribute('transform', elem.dataset.originalTransform);
                    delete elem.dataset.originalTransform;
                }
            } else {
                // Add visual emphasis - make the table more obvious
                elem.style.filter = 'brightness(1.3) contrast(1.2) drop-shadow(0px 0px 8px rgba(255,255,0,0.5))';

                // Store original transform if it exists
                const originalTransform = elem.getAttribute('transform');
                if (originalTransform) {
                    elem.dataset.originalTransform = originalTransform;
                }

                // For SVG elements, use SVG transform attribute for scaling
                const bbox = elem.getBBox();
                const centerX = bbox.x + bbox.width / 2;
                const centerY = bbox.y + bbox.height / 2;

                const scaleTransform = `translate(${centerX}, ${centerY}) scale(1.1) translate(${-centerX}, ${-centerY})`;
                const newTransform = originalTransform ? `${originalTransform} ${scaleTransform}` : scaleTransform;
                elem.setAttribute('transform', newTransform);
            }
        }

        if (elem.classList && elem.classList.contains('edge')) {
            if (restore) {
                // Remove edge emphasis
                const paths = elem.querySelectorAll('path');
                paths.forEach(path => {
                    path.style.removeProperty('filter');
                    path.style.removeProperty('stroke-width');
                });
            } else {
                // Add edge emphasis
                const paths = elem.querySelectorAll('path');
                paths.forEach(path => {
                    path.style.filter = 'brightness(1.6) contrast(1.9)';
                    const currentWidth = path.getAttribute('stroke-width') || '3';
                    path.style.strokeWidth = (parseFloat(currentWidth) * 1.5) + 'px';
                    path.style.transition = 'all 0.2s ease';
                });
            }
        }
    };

    // Function to apply saturation effects specifically for edges
    const setEdgeSaturationEffect = (edgeElement, saturationFactor = 2.0, restore = false) => {
        if (!edgeElement) return;

        const baseColor = getElementColor(edgeElement);
        const paths = edgeElement.querySelectorAll('path');

        paths.forEach((path) => {
            // Store original styles if not already stored
            if (!path.dataset.originalStroke) {
                path.dataset.originalStroke = path.getAttribute('stroke') || baseColor;
            }
            if (!path.dataset.originalStrokeWidth) {
                path.dataset.originalStrokeWidth = path.getAttribute('stroke-width') || '3';
            }

            if (restore) {
                // Restore original stroke color and width
                path.setAttribute('stroke', path.dataset.originalStroke);
                path.setAttribute('stroke-width', path.dataset.originalStrokeWidth);
            } else {
                // Apply saturated stroke color and slightly increased width
                const saturatedColor = saturateColor(baseColor, saturationFactor);
                path.setAttribute('stroke', saturatedColor);

                // Slightly increase stroke width for better visibility
                const originalWidth = parseFloat(path.dataset.originalStrokeWidth);
                path.setAttribute('stroke-width', (originalWidth * 1.5).toString());
            }
        });
    };

    const setElementColor = (elem, color, isHighlighted = false, isInActiveSelection = false) => {
        if (!elem) return;
        let miniElem = null;
        const nodeId = elem.id;
        let isMini = nodeId.indexOf('mini-') != -1;

        if (!isMini) {
            const miniNodeId = 'mini-' + nodeId;
            miniElem = document.getElementById(miniNodeId);
            if (miniElem) {
                setElementColor(miniElem, color, isHighlighted, isInActiveSelection)
            }
        }
        if (elem.classList && elem.classList.contains('node')) {
            // Set opacity based on selection state
            let opacity = '1';
            if (highlightedElementId !== null) {
                // Something is highlighted
                if (isHighlighted || isInActiveSelection) {
                    opacity = '1'; // Full opacity for highlighted elements
                } else {
                    opacity = '0.2'; // Reduced opacity for non-highlighted elements
                }
            } else {
                opacity = '1'; // Full opacity when nothing is highlighted
            }
            elem.setAttribute('opacity', opacity);

            const polygons = elem.querySelectorAll('polygon');

            // Get the table's header color for background with reduced opacity
            const tableColor = tables[nodeId.replace('mini-', '')]?.defaultColor || color;
            const backgroundColorWithOpacity = hexToRgba(tableColor, 0.1);

            polygons.forEach((polygon, index) => {
                const currentFill = polygon.getAttribute('fill');

                // Store original fill if not already stored
                if (!polygon.dataset.originalFill) {
                    polygon.dataset.originalFill = currentFill || 'white';
                }

                // Only modify white/transparent polygons (content areas)
                // NEVER touch any colored polygons (headers) - leave them completely alone
                const isContentPolygon = currentFill === 'white' || currentFill === 'none' || currentFill === 'transparent' || !currentFill;

                if (isContentPolygon && isHighlighted) {
                    // Only change content polygons when highlighting
                    polygon.setAttribute('fill', backgroundColorWithOpacity);
                } else if (isContentPolygon && !isHighlighted) {
                    // Restore content polygons to their original color instead of forcing to white
                    polygon.setAttribute('fill', polygon.dataset.originalFill || 'white');
                }
                // If it's a colored polygon (header), we NEVER touch it at all
            })
        }

        if (elem.classList && elem.classList.contains('edge')) {
            // Set opacity based on selection state
            let opacity = '1';
            if (highlightedElementId !== null) {
                // Something is highlighted
                if (isHighlighted || isInActiveSelection) {
                    opacity = '1'; // Full opacity for highlighted elements
                } else {
                    opacity = '0.2'; // Reduced opacity for non-highlighted elements
                }
            } else {
                opacity = '1'; // Full opacity when nothing is highlighted
            }
            elem.setAttribute('opacity', opacity);

            const polygons = elem.querySelectorAll('polygon');
            polygons.forEach(polygon => {
                polygon.setAttribute('stroke-width', isHighlighted ? '10' : '3');
                if (isMini) {
                    polygon.setAttribute('fill', isHighlighted ? color : GREY_COLOR);
                }
            })

            const edgeId = elem.id;
            const connectedTables = edges[edgeId]?.tables || [];

            const paths = elem.querySelectorAll('path');

            // Enhanced parallel edge handling - double width for all paths when highlighted
            if (paths.length > 1) {
                // Multiple parallel edges between same tables
                if (isHighlighted) {
                    // When highlighted, make both edges more prominent with doubled width
                    paths[0].setAttribute('stroke-width', '16'); // Primary edge: doubled from 8
                    paths[1].setAttribute('stroke-width', '12'); // Secondary edge: doubled from 6
                } else {
                    // Normal state for parallel edges
                    paths[0].setAttribute('stroke-width', '8');
                    paths[1].setAttribute('stroke-width', '6');
                }
                paths.forEach(path => path.setAttribute('opacity', '1'));
            } else if (paths.length === 1) {
                // Single edge
                if (isHighlighted) {
                    paths[0].setAttribute('stroke-width', '10'); // Doubled from 5
                } else {
                    paths[0].setAttribute('stroke-width', '5');
                }
                paths[0].setAttribute('opacity', '1');
            }
        }
    };


    const highlightElements = (tableIds, edgeIds, event) => {
        // Set the highlighted element ID
        if (tableIds.length > 0) {
            highlightedElementId = tableIds[0];
        } else if (edgeIds.length > 0) {
            highlightedElementId = edgeIds[0];
        }

        // First, reduce opacity of ALL elements
        Object.keys(tables).forEach(id => {
            const tableElement = document.getElementById(id);
            const miniTableElement = document.getElementById('mini-' + id);
            const isInSelection = tableIds.includes(id);

            if (tableElement) {
                setElementColor(tableElement, tables[id].defaultColor, false, isInSelection);
                if (isInSelection) {
                    tableElement.classList.add('highlighted');
                } else {
                    tableElement.classList.remove('highlighted');
                }
            }
            if (miniTableElement) {
                setElementColor(miniTableElement, tables[id].defaultColor, false, isInSelection);
                if (isInSelection) {
                    miniTableElement.classList.add('highlighted');
                } else {
                    miniTableElement.classList.remove('highlighted');
                }
            }
        });

        Object.keys(edges).forEach(id => {
            const edgeElement = document.getElementById(id);
            const miniEdgeElement = document.getElementById('mini-' + id);
            const isInSelection = edgeIds.includes(id);

            if (edgeElement) {
                setElementColor(edgeElement, getElementColor(edgeElement), false, isInSelection);
                if (isInSelection) {
                    edgeElement.classList.add('highlighted');
                } else {
                    edgeElement.classList.remove('highlighted');
                }
            }
            if (miniEdgeElement) {
                setElementColor(miniEdgeElement, getElementColor(miniEdgeElement), false, isInSelection);
                if (isInSelection) {
                    miniEdgeElement.classList.add('highlighted');
                } else {
                    miniEdgeElement.classList.remove('highlighted');
                }
            }
        });

        // Then, highlight the selected elements with full intensity
        tableIds.forEach(id => {
            const tableElement = document.getElementById(id);
            const miniTableElement = document.getElementById('mini-' + id);
            if (!tableElement) return;

            // Get the table's default color for highlighting
            const tableColor = tables[id].defaultColor || '#712e2eff';

            // Highlight with full intensity
            setElementColor(tableElement, tableColor, true, true);
            if (miniTableElement) {
                setElementColor(miniTableElement, tableColor, true, true);
            }
        });

        edgeIds.forEach(id => {
            let edgeElement = document.getElementById(id);
            let miniEdgeElement = document.getElementById('mini-' + id);
            if (!edgeElement) return;

            // Highlight with full intensity
            setElementColor(edgeElement, getElementColor(edgeElement), true, true);
            if (miniEdgeElement) {
                setElementColor(miniEdgeElement, getElementColor(edgeElement), true, true);
            }
        });

        showSelectionWindow(tableIds, edgeIds, event);
        
        // Update table selector to reflect current highlights
        if (window.updateTableSelector) {
            window.updateTableSelector();
        }
    };


    function showSelectionWindow(selectedTables, selectedEdges, event) {
        const selectionContainer = document.getElementById('selection-container');
        if (!selectionContainer) return;

        // Check if the selection window was previously hidden
        const wasHidden = selectionContainer.style.display === 'none' ||
                         window.getComputedStyle(selectionContainer).display === 'none';

        // Force visibility with strong inline styles
        selectionContainer.style.display = 'block';
        selectionContainer.style.position = 'fixed';
        selectionContainer.style.zIndex = '10001';

        // Reset manual positioning flag only if window was previously hidden
        // This allows auto-positioning on first show but preserves manual positioning during interactions
        if (wasHidden) {
            selectionContainerManuallyPositioned = false;
        }

        const inner = selectionContainer.querySelector('#selection-inner-container');
        const selection_header = document.getElementById('selection-header');
        if (!inner || !selection_header) return;

        let html = '';

        if (selectedTables.length) {
            let primaryTable = selectedTables[0];
            selection_header.innerHTML = `📋 ${primaryTable}`;

            // Table Information Section
            html += '<div class="selection-section">';
            html += '<h3>📊 Selected Tables</h3>';
            selectedTables.forEach((tableId, index) => {
                const tableData = graphData.tables[tableId];
                if (index === 0) {
                    html += `<div style="margin-bottom: 12px;">`;
                    html += `<span class="table-name" data-table-id="${tableId}" style="font-size: 1.1rem; font-weight: 600;">${tableId}</span>`;
                } else {
                    html += `<span class="table-name" data-table-id="${tableId}">${tableId}</span>`;
                }
                if (index === 0) html += `</div>`;
            });
            html += '</div>';

            // Add table details for the primary table
            const primaryTableData = graphData.tables[primaryTable];
            if (primaryTableData && primaryTableData.triggers && primaryTableData.triggers.length > 0) {
                html += '<div class="selection-section">';
                html += '<h3>⚡ Triggers</h3>';
                primaryTableData.triggers.forEach(trigger => {
                    html += '<div class="trigger-info">';
                    html += `<span class="trigger-name">${trigger.trigger_name}</span>`;
                    html += `<span class="trigger-event">${trigger.event}</span>`;
                    if (trigger.function) {
                        html += `<div style="font-size: 0.8rem; color: #7f8c8d; margin-top: 2px;">→ ${trigger.function}${trigger.function_args ? '(' + trigger.function_args + ')' : '()'}</div>`;
                    }
                    html += '</div>';
                });
                html += '</div>';
            }
        }

        // Foreign Keys Section
        if (selectedEdges.length) {
            html += '<div class="selection-section">';
            html += '<h3>🔗 Foreign Key Relationships</h3>';
            for (const edgeId of selectedEdges) {
                const edge = graphData.edges[edgeId];
                if (edge && edge.fkText) {
                    html += `<div class="edge-name" data-edge-id="${edgeId}">`;
                    html += `<h4>🔑 ${edge.fromColumn} → ${edge.toColumn}</h4>`;
                    html += `<pre>${edge.fkText}</pre>`;
                    html += '</div>';
                } else {
                    html += `<div class="edge-name" data-edge-id="${edgeId}">${edgeId}</div>`;
                }
            }
            html += '</div>';
        }

        inner.innerHTML = html;

        // Add click event listeners to table names (mouseover effects removed for performance)
        const tableNames = inner.querySelectorAll('.table-name');
        tableNames.forEach(tableNameSpan => {
            const tableId = tableNameSpan.getAttribute('data-table-id');

            // Mouseover event - apply saturation effect instead of highlighting
            tableNameSpan.addEventListener('mouseover', () => {
                // Get the table element in the SVG
                const tableElement = document.getElementById(tableId);
                const miniTableElement = document.getElementById('mini-' + tableId);

                if (tableElement) {
                    // Apply saturation effect with double saturation (2.0 factor)
                    setSaturationEffect(tableElement, 2.0, false);
                }

                // Also apply to the miniature version
                if (miniTableElement) {
                    setSaturationEffect(miniTableElement, 2.0, false);
                }
            });

            // Mouseout event - restore original appearance
            tableNameSpan.addEventListener('mouseout', (e) => {
                e.preventDefault();
                e.stopPropagation();

                const tableElement = document.getElementById(tableId);
                const miniTableElement = document.getElementById('mini-' + tableId);

                if (tableElement) {
                    setSaturationEffect(tableElement, 2.0, true);

                    // If this table should still be highlighted, ensure highlighting is maintained
                    if (highlightedElementId &&
                        (highlightedElementId === tableId ||
                         (tables[highlightedElementId] && tables[highlightedElementId].edges.some(edgeId =>
                             edges[edgeId] && edges[edgeId].tables.includes(tableId))))) {
                        // Re-apply highlighting to maintain background colors
                        tableElement.classList.add('highlighted');
                        setElementColor(tableElement, tables[tableId].defaultColor, true, true);
                    }
                }

                // Also restore the miniature version
                if (miniTableElement) {
                    setSaturationEffect(miniTableElement, 2.0, true);

                    // Maintain highlighting for mini version too
                    if (highlightedElementId &&
                        (highlightedElementId === tableId ||
                         (tables[highlightedElementId] && tables[highlightedElementId].edges.some(edgeId =>
                             edges[edgeId] && edges[edgeId].tables.includes(tableId))))) {
                        miniTableElement.classList.add('highlighted');
                        setElementColor(miniTableElement, tables[tableId].defaultColor, true, true);
                    }
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

        // Add click event listeners to edge names (mouseover effects removed for performance)
        const edgeNames = inner.querySelectorAll('.edge-name');
        edgeNames.forEach(edgeNameLi => {
            const edgeId = edgeNameLi.getAttribute('data-edge-id');

            // Mouseover event - apply saturation effect to the edge
            edgeNameLi.addEventListener('mouseover', () => {
                const edgeElement = document.getElementById(edgeId);
                const miniEdgeElement = document.getElementById('mini-' + edgeId);

                if (edgeElement) {
                    setEdgeSaturationEffect(edgeElement, 2.0, false);
                }

                if (miniEdgeElement) {
                    setEdgeSaturationEffect(miniEdgeElement, 2.0, false);
                }
            });

            // Mouseout event - restore original edge appearance
            edgeNameLi.addEventListener('mouseout', (e) => {
                e.preventDefault();
                e.stopPropagation();

                const edgeElement = document.getElementById(edgeId);
                const miniEdgeElement = document.getElementById('mini-' + edgeId);

                if (edgeElement) {
                    setEdgeSaturationEffect(edgeElement, 2.0, true);
                }

                if (miniEdgeElement) {
                    setEdgeSaturationEffect(miniEdgeElement, 2.0, true);
                }
            });
        });
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
        // Don't clear highlights during drag operations
        if (dragState.type !== null) {
            return;
        }

        // Also check if selection-container is being dragged (it has its own drag system)
        const selectionContainer = document.getElementById('selection-container');
        if (selectionContainer && selectionContainer._dragState) {
            return;
        }

        highlightedElementId = null; // Clear the highlighted element ID first

        Object.keys(tables).forEach(id => {
            const tableElement = document.getElementById(id);
            const miniTableElement = document.getElementById('mini-' + id);
            if (tableElement) {
                tableElement.classList.remove('highlighted');
                setElementColor(tableElement, tables[id].defaultColor, false, false);
            }
            if (miniTableElement) {
                miniTableElement.classList.remove('highlighted');
                setElementColor(miniTableElement, tables[id].defaultColor, false, false);
            }
        });
        Object.keys(edges).forEach(id => {
            const edgeElement = document.getElementById(id);
            const miniEdgeElement = document.getElementById('mini-' + id);
            if (edgeElement) {
                edgeElement.classList.remove('highlighted');
                setElementColor(edgeElement, edges[id].defaultColor, false, false);
            }
            if (miniEdgeElement) {
                miniEdgeElement.classList.remove('highlighted');
                setElementColor(miniEdgeElement, edges[id].defaultColor, false, false);
            }
        });
        hideSelectionWindow();
        
        // Update table selector to show all tables when highlights are cleared
        if (window.updateTableSelector) {
            window.updateTableSelector();
        }
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
        const viewport = getViewportDimensions();
        pt.x = viewport.width / 2;
        pt.y = viewport.height / 2;
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
            // Prevent drag if clicking on controls/buttons
            if (
                event.target.closest('.window-controls') ||
                event.target.tagName === 'BUTTON'
            ) {
                return;
            }

            const rect = miniatureContainer.getBoundingClientRect();

            // Ensure we have inline styles set for consistent positioning
            if (!miniatureContainer.style.left) {
                miniatureContainer.style.left = `${rect.left}px`;
            }
            if (!miniatureContainer.style.top) {
                miniatureContainer.style.top = `${rect.top}px`;
            }

            // Use the same isolated approach as selection container
            const miniatureDragState = {
                type: 'miniature-window',
                target: miniatureContainer,
                startX: event.clientX,
                startY: event.clientY,
                offsetX: parseFloat(miniatureContainer.style.left),
                offsetY: parseFloat(miniatureContainer.style.top)
            };

            miniatureContainer.classList.add('dragging');

            // Create miniature-specific mousemove handler
            const handleMouseMove = (moveEvent) => {
                moveEvent.preventDefault();
                moveEvent.stopPropagation();

                const dx = moveEvent.clientX - miniatureDragState.startX;
                const dy = moveEvent.clientY - miniatureDragState.startY;

                const newX = miniatureDragState.offsetX + dx;
                const newY = miniatureDragState.offsetY + dy;

                miniatureContainer.style.left = `${newX}px`;
                miniatureContainer.style.top = `${newY}px`;
            };

            // Create miniature-specific mouseup handler
            const handleMouseUp = (upEvent) => {
                upEvent.preventDefault();
                upEvent.stopPropagation();
                miniatureContainer.classList.remove('dragging');
                window.removeEventListener('mousemove', handleMouseMove);
                window.removeEventListener('mouseup', handleMouseUp);
            };

            // Add temporary event listeners for this drag operation only
            window.addEventListener('mousemove', handleMouseMove);
            window.addEventListener('mouseup', handleMouseUp);

            event.preventDefault();
            event.stopPropagation();
        });
        makeResizable(miniatureContainer);
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
        makeResizable(metadataContainer);
        metadataContainer.addEventListener('mousedown', (event) => {
            // Prevent drag if clicking on controls/buttons/interactive elements
            if (
                event.target.closest('.window-controls') ||
                event.target.tagName === 'BUTTON' ||
                event.target.tagName === 'SELECT' ||
                event.target.id === 'table-selector' ||
                event.target.closest('#table-selector')
            ) return;

            const rect = metadataContainer.getBoundingClientRect();

            // Ensure we have inline styles set for consistent positioning
            if (!metadataContainer.style.left) {
                metadataContainer.style.left = `${rect.left}px`;
            }
            if (!metadataContainer.style.top) {
                metadataContainer.style.top = `${rect.top}px`;
            }

            dragState.type = 'metadata';
            dragState.target = metadataContainer;
            dragState.startX = event.clientX;
            dragState.startY = event.clientY;
            // Now we can safely use the inline style values
            dragState.offsetX = parseFloat(metadataContainer.style.left);
            dragState.offsetY = parseFloat(metadataContainer.style.top);
            metadataContainer.classList.add('dragging');
            event.preventDefault();
            event.stopPropagation();
        });
    }

    // Selection window drag (whole container)
    const selectionContainer = document.getElementById('selection-container');
    const selectionInner = document.getElementById('selection-inner-container');
    if (selectionContainer) {
        makeResizable(selectionContainer);
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

            // Get the container's current position
            const rect = selectionContainer.getBoundingClientRect();

            // Ensure we have inline styles set for consistent positioning
            if (!selectionContainer.style.left) {
                selectionContainer.style.left = `${rect.left}px`;
            }
            if (!selectionContainer.style.top) {
                selectionContainer.style.top = `${rect.top}px`;
            }

            // Use the global dragState (same as other containers)
            dragState.type = 'selection';
            dragState.target = selectionContainer;
            dragState.startX = event.clientX;
            dragState.startY = event.clientY;
            dragState.offsetX = parseFloat(selectionContainer.style.left);
            dragState.offsetY = parseFloat(selectionContainer.style.top);

            // Mark that user has manually positioned the selection container
            selectionContainerManuallyPositioned = true;

            selectionContainer.classList.add('dragging');
        });
    }



    // SVG panning (background drag)
    svg.addEventListener('mousedown', (event) => {
        // Check if we're inside any of the overlay containers or their children
        if (event.target.closest('#selection-container') ||
            event.target.closest('#miniature-container') ||
            event.target.closest('#metadata-container')) {
            return; // Don't initiate pan if we're in these containers
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

        // Track that we moved during drag (for any drag type)
        if (startX !== undefined && startY !== undefined) {
            const dx = Math.abs(event.clientX - startX);
            const dy = Math.abs(event.clientY - startY);
            if (dx > dragThreshold || dy > dragThreshold) {
                dragDidMove = true;
            }
        }

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
            // Calculate movement delta and apply to original position
            dx = event.clientX - dragState.startX;
            dy = event.clientY - dragState.startY;

            const newX = dragState.offsetX + dx;
            const newY = dragState.offsetY + dy;

            dragState.target.style.left = `${newX}px`;
            dragState.target.style.top = `${newY}px`;

        } else if (dragState.type === 'indicator') {
            event.preventDefault();
            event.stopPropagation();

            const miniRect = miniatureContainer.getBoundingClientRect();

            // Clamp mouse position to miniature container bounds
            const clampedX = Math.max(miniRect.left, Math.min(miniRect.right, event.clientX));
            const clampedY = Math.max(miniRect.top, Math.min(miniRect.bottom, event.clientY));

            // Calculate relative position within the clamped bounds
            const relX = (clampedX - miniRect.left) / miniRect.width;
            const relY = (clampedY - miniRect.top) / miniRect.height;

            // Additional safety clamping to ensure we stay within 0-1 range
            const safeRelX = Math.max(0, Math.min(1, relX));
            const safeRelY = Math.max(0, Math.min(1, relY));

            // Get main SVG bounds
            const mainBounds = getMainERDBounds();
            const targetX = mainBounds.x + safeRelX * mainBounds.width;
            const targetY = mainBounds.y + safeRelY * mainBounds.height;

            // Zoom to the calculated point
            zoomToPoint(targetX, targetY, userS);

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

    // Track if we actually moved during drag (to distinguish from simple clicks)
    let dragDidMove = false;

    // --- MOUSE UP HANDLER ---
    window.addEventListener('mouseup', (event) => {
        if (!dragState.type) return;

        // Prevent click events after drag operations
        event.preventDefault();
        event.stopPropagation();

        if (dragState.target) {
            dragState.target.classList.remove('dragging');
            dragState.target.classList.remove('resizing');
        }
        if (dragState.type === 'pan') {
            svg.classList.remove('grabbing');
            isPanning = false;
        } else if (dragState.type === 'resize') {
            const rect = dragState.target.getBoundingClientRect();
            const currentLeft = parseFloat(dragState.target.style.left) || rect.left;
            const currentTop = parseFloat(dragState.target.style.top) || rect.top;
            const newWidth = rect.width;
            const newHeight = rect.height;

            // Apply minimum size constraints while preserving position
            const minSize = 50;
            if (newWidth < minSize || newHeight < minSize) {
                const constrainedWidth = Math.max(minSize, newWidth);
                const constrainedHeight = Math.max(minSize, newHeight);

                // Only update dimensions, don't touch position
                dragState.target.style.width = `${constrainedWidth}px`;
                dragState.target.style.height = `${constrainedHeight}px`;

                // Update SVG inside if it exists
                const svgImage = dragState.target.querySelector('svg');
                if (svgImage) {
                    svgImage.setAttribute('width', `${constrainedWidth}px`);
                    svgImage.setAttribute('height', `${constrainedHeight}px`);
                }
            }
        }
        // Reset all dragState properties
        dragState.type = null;
        dragState.target = null;
        dragState.handle = null;
        dragDidMove = false;
    });

    // --- Other UI Events ---
    // Helper to compute minimum zoom to fit SVG in viewport
    function getMinZoomToFit() {
        const mainBounds = getMainERDBounds();
        if (!mainBounds.width || !mainBounds.height) return 0.005; // Reduced from 0.01 to allow more zoom out
        const viewport = getViewportDimensions();
        const svgWidth = viewport.width;
        const svgHeight = viewport.height;
        const scaleX = svgWidth / mainBounds.width;
        const scaleY = svgHeight / mainBounds.height;
        return Math.min(scaleX, scaleY) * 0.5; // Added multiplier to allow zooming out beyond fit
    }

    svg.addEventListener('wheel', (event) => {
        // Check if mouse is over selection container - if so, let it scroll naturally
        const selectionContainer = document.getElementById('selection-container');
        if (selectionContainer && event.target.closest('#selection-container')) {
            // Don't prevent default - let the selection container scroll
            return;
        }

        // Check if mouse is over other containers that might need scrolling
        if (event.target.closest('#metadata-container')) {
            return;
        }

        // Otherwise, handle zoom as normal
        event.preventDefault();
        const dir = event.deltaY < 0 ? 1 : -1;
        const scaleAmount = 1 + dir * 0.04;
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
        } else if (e.key.toLowerCase() === 'i') {
            toggleInfoWindows();
        }
    });

    window.addEventListener('scroll', onViewportChange, { passive: true });
    window.addEventListener('resize', onViewportChange, { passive: true });



    // --- Consolidated event listeners
    document.addEventListener('click', function (event) {
        // SVG highlight click handler
        if (event.target.closest('svg')) {
            let clickedElement = event.target;
            let tableId = null, edgeId = null;

            // First, try to find a node or edge by traversing up the DOM tree
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

            // If we didn't find a node/edge by class, try finding by ID pattern
            if (!tableId && !edgeId) {
                clickedElement = event.target;
                while (clickedElement && clickedElement !== svg) {
                    if (clickedElement.id && clickedElement.id.startsWith('edge-')) {
                        edgeId = clickedElement.id;
                        break;
                    }
                    // Check if this element's ID matches a known table
                    if (clickedElement.id && tables[clickedElement.id]) {
                        tableId = clickedElement.id;
                        break;
                    }
                    clickedElement = clickedElement.parentElement;
                }
            }

            // Handle table click
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
                    showSelectionWindow(uniqueTables, connectedEdges, event);
                }
                return;
            }

            // Handle edge click
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

            // Click on SVG background (not node/edge and not in containers): clear all highlights
            if (
                event.target === svg ||
                (!event.target.closest('.node') &&
                 !event.target.closest('.edge') &&
                 !event.target.closest('#selection-container') &&
                 !event.target.closest('#metadata-container') &&
                 !event.target.closest('#miniature-container'))
            ) {
                // Clear all highlights and restore original state
                clearAllHighlights();
                event.stopPropagation();
                return;
            }
        }

    });

    // Function to enhance edge clickability by adding invisible click areas
    function enhanceEdgeClickability() {
        const edges = svg.querySelectorAll('.edge');
        edges.forEach(edge => {
            const paths = edge.querySelectorAll('path');
            paths.forEach(path => {
                // Create a copy of the path with wider stroke for easier clicking
                const clickPath = path.cloneNode(true);
                clickPath.style.stroke = 'transparent';
                clickPath.style.strokeWidth = '12px'; // Much wider for easier clicking
                clickPath.style.fill = 'none';
                clickPath.style.pointerEvents = 'stroke';
                clickPath.style.cursor = 'pointer';

                // Insert the click path before the visible path
                edge.insertBefore(clickPath, path);

                // Make the original path non-interactive so the click path handles clicks
                path.style.pointerEvents = 'none';
            });
        });
    }

    // Table Selector functionality
    function initializeTableSelector() {
        const tableSelector = document.getElementById('table-selector');
        if (!tableSelector) {
            console.warn('Table selector element not found');
            return;
        }

        // Make sure we have access to the tables data
        if (!tables || Object.keys(tables).length === 0) {
            console.warn('No tables data available for table selector');
            return;
        }

        console.log('Initializing table selector with', Object.keys(tables).length, 'tables');

        // Function to populate the selector with tables
        function populateTableSelector(tablesToShow = null) {
            // Clear existing options
            while (tableSelector.firstChild) {
                tableSelector.removeChild(tableSelector.firstChild);
            }
            
            let tablesToDisplay;
            let optionText;
            
            if (!tablesToShow) {
                // Show all tables
                tablesToDisplay = Object.keys(tables);
                optionText = `All Tables (${tablesToDisplay.length})`;
            } else {
                // Show only highlighted/selected tables
                tablesToDisplay = tablesToShow;
                optionText = `Selected Tables (${tablesToDisplay.length})`;
            }
            
            console.log('About to populate selector with options:', optionText);
            
            // Add the default option - create in HTML namespace explicitly
            const defaultOption = document.createElementNS('http://www.w3.org/1999/xhtml', 'option');
            defaultOption.value = '';
            defaultOption.textContent = optionText;
            tableSelector.appendChild(defaultOption);
            console.log('Added default option, current option count:', tableSelector.options.length);
            
            // Add table options
            let addedCount = 0;
            tablesToDisplay.sort().forEach((tableId, index) => {
                const option = document.createElementNS('http://www.w3.org/1999/xhtml', 'option');
                option.value = tableId;
                option.textContent = tableId;
                tableSelector.appendChild(option);
                addedCount++;
                
                // Log progress for first few and last few
                if (index < 3 || index >= tablesToDisplay.length - 3) {
                    console.log(`Added option ${index + 1}: ${tableId}, total options now: ${tableSelector.options.length}`);
                }
            });

            console.log('Populated table selector with', tablesToDisplay.length, 'tables, final option count:', tableSelector.options.length);
            console.log('TableSelector element:', tableSelector);
            console.log('TableSelector innerHTML length:', tableSelector.innerHTML.length);
        }

        // Function to update selector based on current highlights
        function updateTableSelector() {
            const highlightedTables = document.querySelectorAll('.node.highlighted');
            if (highlightedTables.length > 0) {
                const tableIds = Array.from(highlightedTables).map(el => el.id).filter(id => tables[id]);
                populateTableSelector(tableIds);
            } else {
                populateTableSelector(); // Show all tables
            }
        }

        // Handle selector change
        tableSelector.addEventListener('change', function() {
            const selectedTableId = this.value;
            if (!selectedTableId) return;

            // Clear existing highlights
            clearAllHighlights();

            if (tables[selectedTableId]) {
                // Set this table as highlighted
                highlightedElementId = selectedTableId;
                
                // Get connected edges and tables (same logic as SVG click handler)
                const connectedEdges = tables[selectedTableId].edges;
                const connectedTables = [selectedTableId, ...connectedEdges.map(edgeId => edges[edgeId].tables).flat()];
                const uniqueTables = [...new Set(connectedTables)];
                
                // Highlight the table and its connections
                highlightElements(uniqueTables, connectedEdges);
                
                // Show selection window
                showSelectionWindow(uniqueTables, connectedEdges, null);
                
                // Focus on the selected table
                focusOnTable(selectedTableId);
            }
            
            // Reset selector to default option
            this.selectedIndex = 0;
        });

        // Prevent drag events from interfering with table selector interaction
        tableSelector.addEventListener('mousedown', function(event) {
            event.stopPropagation();
        });

        tableSelector.addEventListener('click', function(event) {
            event.stopPropagation();
        });

        tableSelector.addEventListener('focus', function(event) {
            event.stopPropagation();
        });

        // Function to focus on a table (zoom to it)
        function focusOnTable(tableId) {
            const tableElement = document.getElementById(tableId);
            if (!tableElement) return;

            try {
                // Get the table's SVG bounding box
                const bbox = tableElement.getBBox();
                
                // Calculate the center of the table in SVG coordinates
                const tableCenterX = bbox.x + bbox.width / 2;
                const tableCenterY = bbox.y + bbox.height / 2;
                
                // Zoom to the table with a reasonable zoom level
                zoomToPoint(tableCenterX, tableCenterY, Math.max(userS, 1.2));
            } catch (error) {
                console.warn('Could not focus on table:', tableId, error);
            }
        }

        // Store the update function globally so it can be called from other parts
        window.updateTableSelector = updateTableSelector;

        // Initial population
        populateTableSelector();
    }


    function initializeSvgView() {

        if (!svg || !mainGroup || !miniatureContainer || !viewportIndicator || !getMainERDBounds()) {
            setTimeout(initializeSvgView, 200);
            return;
        }

        try {
            // Get bounds and verify they're valid
            const mainBounds = getMainERDBounds();
            if (!mainBounds || typeof mainBounds !== 'object' ||
                mainBounds.width <= 0 || mainBounds.height <= 0) {
                setTimeout(initializeSvgView, 200);
                return;
            }

            // Calculate center of the diagram
            const centerX = mainBounds.x + mainBounds.width / 2;
            const centerY = mainBounds.y + mainBounds.height / 2;

            // Calculate zoom level (fit the diagram with some padding, but more zoomed in)
            const viewport = getViewportDimensions();
            const viewportWidth = viewport.width;
            const viewportHeight = viewport.height;
            const scaleX = viewportWidth / (mainBounds.width * 0.8); // Less padding = more zoomed in
            const scaleY = viewportHeight / (mainBounds.height * 0.8);
            const scale = Math.min(scaleX, scaleY, 1.5); // Allow zoom in up to 1.5x

            // Reset and apply transformation
            userTx = 0;
            userTy = 0;
            userS = scale;


            // Use zoomToPoint for consistent positioning
            zoomToPoint(centerX, centerY, scale);

            // Force viewport indicator update
            updateViewportIndicator();

            // Enhance edge clickability by adding invisible click areas
            enhanceEdgeClickability();

            // Ensure viewport indicator is visible
            if (viewportIndicator) {
                viewportIndicator.style.display = 'block';
                viewportIndicator.style.opacity = '1';
                viewportIndicator.style.border = '2px solid #ff4081';
                viewportIndicator.style.backgroundColor = 'rgba(255, 64, 129, 0.2)';
                viewportIndicator.style.pointerEvents = 'all';

                // Add this debug to check viewport indicator dimensions
                const viStyle = window.getComputedStyle(viewportIndicator);
            }

            // Position miniature container next to metadata container
            const metadataContainer = document.getElementById('metadata-container');
            if (miniatureContainer && metadataContainer) {
                const metadataRect = metadataContainer.getBoundingClientRect();
                const margin = 16; // 16px margin between containers

                miniatureContainer.style.position = 'fixed';
                miniatureContainer.style.left = `${metadataRect.right + margin}px`;
                miniatureContainer.style.top = `${metadataRect.top}px`;

            }

            // Position containers
            updateSelectionContainerPosition();

            // Add browser zoom level to metadata
            const addBrowserZoomToMetadata = () => {
                const metadataInner = document.querySelector('.metadata-inner-container ul');
                if (metadataInner) {
                    // Remove existing browser zoom entry if it exists
                    const existingZoomItem = metadataInner.querySelector('.browser-zoom-item');
                    if (existingZoomItem) {
                        existingZoomItem.remove();
                    }

                    // Calculate browser zoom level
                    const browserZoom = Math.round(window.devicePixelRatio * 100);

                    // Create new browser zoom item
                    const zoomItem = document.createElement('li');
                    zoomItem.className = 'browser-zoom-item';
                    zoomItem.innerHTML = `Browser Zoom: ${browserZoom}%`;

                    // Add it to the metadata list
                    metadataInner.appendChild(zoomItem);
                }
            };

            // Add browser zoom to metadata initially
            addBrowserZoomToMetadata();

            // Update browser zoom when window is resized/zoomed
            window.addEventListener('resize', addBrowserZoomToMetadata);

            // Initialize window controls for all containers
            if (metadataContainer) {
                addWindowControls(metadataContainer, {
                    buttons: { copy: true, download: true, edit: false }
                });
                makeResizable(metadataContainer);
            }

            if (miniatureContainer) {
                addWindowControls(miniatureContainer, {
                    buttons: { copy: false, edit: false }
                });
                makeResizable(miniatureContainer);
            }

            if (selectionContainer) {
                addWindowControls(selectionContainer, {
                    buttons: { copy: true, download: true, edit: true }
                });
                makeResizable(selectionContainer);
            }

            // Initialize table selector
            initializeTableSelector();
            
            // Parse and apply URL parameters after all containers are initialized
            parseUrlParameters();
        } catch (error) {
            console.error("Error during SVG initialization:", error);
            setTimeout(initializeSvgView, 300);
        }
    }

    // Primary initialization on DOMContentLoaded
    document.addEventListener('DOMContentLoaded', () => {
        // Small delay to ensure SVG is fully parsed
        setTimeout(initializeSvgView, 300);

        // Also initialize when window is resized
        window.addEventListener('resize', () => {
            // Debounce the resize event
            if (window.resizeTimer) clearTimeout(window.resizeTimer);
            window.resizeTimer = setTimeout(() => {
                updateViewportIndicator();
                updateSelectionContainerPosition();
            }, 250);
        });
    });

    // Backup initialization for cases when DOMContentLoaded already fired
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        setTimeout(initializeSvgView, 300);
    }
});
