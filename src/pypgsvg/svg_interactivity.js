document.addEventListener('DOMContentLoaded', () => {
    const svg = document.children[0];
    const mainGroup = document.getElementById('main-erd-group');
    const miniatureContainer = document.getElementById('miniature-container');
    const viewportIndicator = document.getElementById('viewport-indicator');
    const overlayContainer = document.getElementById('overlay-container');
    const graphDataElement = document.getElementById('graph-data');
    const graphData = JSON.parse(graphDataElement.textContent);
    const { tables, edges, views } = graphData;

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
    let originalMetadataValues = null; // Store original metadata values for restoration

    // --- Utility Functions ---

    /**
     * Escape HTML special characters for safe insertion into HTML content.
     * For use in innerHTML - only escapes characters that would break HTML parsing.
     */
    function escapeHtml(unsafe) {
        if (typeof unsafe !== 'string') return String(unsafe || '');
        return unsafe
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    /**
     * Sanitize label text for Graphviz compatibility (matches Python sanitize_label function).
     * Removes or replaces special characters to create safe identifiers.
     */
    function sanitizeLabel(text) {
        if (typeof text !== 'string') text = String(text || '');
        return text.replace(/[^a-zA-Z0-9_]/g, '_');
    }

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

    function copyToClipboard(text, button) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(() => {
                const originalText = button.textContent || button.innerHTML;
                button.textContent = '✓';
                button.title = 'Copied!';
                setTimeout(() => {
                    button.textContent = originalText.includes('Copy') ? originalText : '📋';
                    button.title = 'Copy to clipboard';
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy to clipboard:', err);
                fallbackCopyTextToClipboard(text, button);
            });
        } else {
            fallbackCopyTextToClipboard(text, button);
        }
    }

    function makeDraggable(windowElem, handleElem) {
        handleElem.addEventListener('mousedown', (event) => {
            // Prevent drag if clicking on controls/buttons
            if (event.target.closest('.window-controls') || event.target.tagName === 'BUTTON') {
                return;
            }

            const rect = windowElem.getBoundingClientRect();
            const dragState = {
                startX: event.clientX,
                startY: event.clientY,
                offsetX: rect.left,
                offsetY: rect.top
            };

            windowElem.classList.add('dragging');

            const handleMouseMove = (moveEvent) => {
                moveEvent.preventDefault();
                moveEvent.stopPropagation();

                const dx = moveEvent.clientX - dragState.startX;
                const dy = moveEvent.clientY - dragState.startY;

                const newX = dragState.offsetX + dx;
                const newY = dragState.offsetY + dy;

                windowElem.style.left = `${newX}px`;
                windowElem.style.top = `${newY}px`;
                windowElem.style.transform = 'none';
            };

            const handleMouseUp = (upEvent) => {
                upEvent.preventDefault();
                upEvent.stopPropagation();
                windowElem.classList.remove('dragging');
                window.removeEventListener('mousemove', handleMouseMove);
                window.removeEventListener('mouseup', handleMouseUp);
            };

            window.addEventListener('mousemove', handleMouseMove);
            window.addEventListener('mouseup', handleMouseUp);

            event.preventDefault();
            event.stopPropagation();
        });
    }

    function showSqlWindow(tableName, sqlText, triggeringButton) {
        // Check if SQL window already exists, if so remove it
        const existingSqlWindow = document.getElementById('sql-viewer-window');
        if (existingSqlWindow) {
            existingSqlWindow.remove();
            // Reset button text if provided
            if (triggeringButton) {
                const originalText = triggeringButton.getAttribute('data-original-text');
                if (originalText) {
                    triggeringButton.textContent = originalText;
                }
            }
            return; // Exit early, window was closed
        }

        // Split SQL into lines for individual line copying
        const sqlLines = sqlText.split('\n');

        // Create the SQL viewer window - use HTML namespace explicitly
        const sqlWindow = document.createElementNS('http://www.w3.org/1999/xhtml', 'div');
        sqlWindow.id = 'sql-viewer-window';
        sqlWindow.className = 'container';

        // Calculate initial size based on content
        const lineCount = sqlText.split('\n').length;
        const lineHeight = 1.4; // Matches textarea line-height
        const fontSize = 0.8; // rem
        const approxLineHeightPx = fontSize * 16 * lineHeight;
        const contentHeight = lineCount * approxLineHeightPx;
        const windowChrome = 120; // Header + padding + margins
        const calculatedHeight = contentHeight + windowChrome;

        // Initial size: content-based but capped at 60vh
        const initialWidth = Math.min(900, window.innerWidth * 0.7);
        const maxHeight = window.innerHeight * 0.6;
        const initialHeight = Math.min(calculatedHeight, maxHeight, 800);
        const initialLeft = (window.innerWidth - initialWidth) / 2;
        const initialTop = (window.innerHeight - initialHeight) / 2;

        sqlWindow.style.cssText = `
            position: fixed;
            left: ${initialLeft}px;
            top: ${initialTop}px;
            width: ${initialWidth}px;
            height: ${initialHeight}px;
            max-width: 80vw;
            max-height: 90vh;
            background: rgba(248, 249, 250, 0.98);
            border: 2px solid #3498db;
            border-radius: 8px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
            z-index: 100000;
            display: flex;
            flex-direction: column;
            pointer-events: auto;
        `;

        // Header
        const header = document.createElementNS('http://www.w3.org/1999/xhtml', 'div');
        header.className = 'header';
        header.style.cssText = `
            background: linear-gradient(135deg, #3498db, #2980b9);
            color: white;
            padding: 12px 16px;
            font-size: 1rem;
            font-weight: 600;
            border-radius: 6px 6px 0 0;
            cursor: grab;
            user-select: none;
            display: flex;
            align-items: center;
            justify-content: space-between;
        `;

        // Header title
        const headerTitle = document.createElementNS('http://www.w3.org/1999/xhtml', 'span');
        headerTitle.textContent = `📝 ${tableName} - SQL Definition`;
        header.appendChild(headerTitle);

        // Close button
        const closeBtn = document.createElementNS('http://www.w3.org/1999/xhtml', 'button');
        closeBtn.textContent = '✕';
        closeBtn.style.cssText = `
            background: rgba(255, 255, 255, 0.2);
            border: none;
            color: white;
            font-size: 1.2rem;
            cursor: pointer;
            padding: 2px 8px;
            border-radius: 4px;
            line-height: 1;
        `;
        closeBtn.addEventListener('click', () => {
            sqlWindow.remove();
            // Reset triggering button text if provided
            if (triggeringButton) {
                const originalText = triggeringButton.getAttribute('data-original-text');
                if (originalText) {
                    triggeringButton.textContent = originalText;
                }
            }
        });
        header.appendChild(closeBtn);

        // Content area
        const content = document.createElementNS('http://www.w3.org/1999/xhtml', 'div');
        content.className = 'container-content';
        content.style.cssText = `
            padding: 16px;
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            position: relative;
        `;

        // SQL textarea
        const sqlTextarea = document.createElementNS('http://www.w3.org/1999/xhtml', 'textarea');
        sqlTextarea.value = sqlText;
        sqlTextarea.readOnly = true;
        sqlTextarea.style.cssText = `
            width: 100%;
            flex: 1;
            min-height: 100px;
            background: #ffffff;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 0.8rem;
            padding: 12px;
            padding-top: 40px;
            resize: none;
            color: #2c3e50;
            line-height: 1.4;
            box-sizing: border-box;
            overflow-y: auto;
        `;
        content.appendChild(sqlTextarea);

        // Copy button - overlayed on top right of textarea
        const copyBtn = document.createElementNS('http://www.w3.org/1999/xhtml', 'button');
        copyBtn.textContent = '📋';
        copyBtn.style.cssText = `
            position: absolute;
            top: 24px;
            right: 24px;
            padding: 8px 10px;
            background: rgba(52, 152, 219, 0.95);
            color: white;
            border: 1px solid #3498db;
            border-radius: 4px;
            font-size: 1rem;
            cursor: pointer;
            z-index: 10;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            transition: all 0.2s ease;
        `;
        copyBtn.addEventListener('mouseenter', () => {
            copyBtn.style.background = 'rgba(41, 128, 185, 0.95)';
            copyBtn.style.transform = 'scale(1.1)';
        });
        copyBtn.addEventListener('mouseleave', () => {
            copyBtn.style.background = 'rgba(52, 152, 219, 0.95)';
            copyBtn.style.transform = 'scale(1)';
        });
        copyBtn.addEventListener('click', () => {
            copyToClipboard(sqlText, copyBtn);
        });
        content.appendChild(copyBtn);

        // Resize handles
        const nwHandle = document.createElementNS('http://www.w3.org/1999/xhtml', 'div');
        nwHandle.className = 'resize-handle nw';
        nwHandle.style.cssText = `
            position: absolute;
            left: 2px;
            top: 42px;
            width: 16px;
            height: 16px;
            cursor: nw-resize;
            background: rgba(52, 152, 219, 0.3);
            border: 1px solid rgba(52, 152, 219, 0.5);
            border-radius: 3px;
            transition: all 0.2s ease;
        `;
        nwHandle.addEventListener('mouseenter', () => {
            nwHandle.style.background = 'rgba(52, 152, 219, 0.6)';
        });
        nwHandle.addEventListener('mouseleave', () => {
            nwHandle.style.background = 'rgba(52, 152, 219, 0.3)';
        });

        const seHandle = document.createElementNS('http://www.w3.org/1999/xhtml', 'div');
        seHandle.className = 'resize-handle se';
        seHandle.style.cssText = `
            position: absolute;
            right: 2px;
            bottom: 2px;
            width: 16px;
            height: 16px;
            cursor: se-resize;
            background: rgba(52, 152, 219, 0.3);
            border: 1px solid rgba(52, 152, 219, 0.5);
            border-radius: 3px;
            transition: all 0.2s ease;
        `;
        seHandle.addEventListener('mouseenter', () => {
            seHandle.style.background = 'rgba(52, 152, 219, 0.6)';
        });
        seHandle.addEventListener('mouseleave', () => {
            seHandle.style.background = 'rgba(52, 152, 219, 0.3)';
        });

        sqlWindow.appendChild(header);
        sqlWindow.appendChild(content);
        sqlWindow.appendChild(nwHandle);
        sqlWindow.appendChild(seHandle);

        // Append to overlay container (not document.body since we're in SVG context)
        const overlayContainer = document.getElementById('overlay-container');
        if (overlayContainer) {
            overlayContainer.appendChild(sqlWindow);
        } else {
            // Fallback to document.body if overlay container not found
            if (document.body) {
                document.body.appendChild(sqlWindow);
            }
        }

        // Prevent wheel events from propagating to underlying ERD
        sqlWindow.addEventListener('wheel', (event) => {
            event.stopPropagation();
        }, { passive: false });

        // Prevent all mouse events from propagating to underlying ERD
        sqlWindow.addEventListener('mousedown', (event) => {
            event.stopPropagation();
        });

        sqlWindow.addEventListener('click', (event) => {
            event.stopPropagation();
        });

        // Make the window draggable and resizable
        makeDraggable(sqlWindow, header);
        makeResizable(sqlWindow, nwHandle, seHandle);

        // Change the triggering button text to "Close SQL"
        if (triggeringButton) {
            // Store original text if not already stored
            if (!triggeringButton.getAttribute('data-original-text')) {
                triggeringButton.setAttribute('data-original-text', triggeringButton.textContent);
            }
            if (triggeringButton.textContent.includes('SQL')) {
                triggeringButton.textContent = '❌ SQL';
            } else if (triggeringButton.textContent.includes('👁️')) {
                triggeringButton.textContent = '❌';
            }
        }
    }

    function showFunctionWindow(functionData, triggersUsingFunction, tablesUsingFunction) {
        // Check if function window already exists, if so remove it
        const existingFunctionWindow = document.getElementById('function-viewer-window');
        if (existingFunctionWindow) {
            existingFunctionWindow.remove();
            return; // Exit early, window was closed
        }

        const functionName = functionData.name || 'Unknown Function';
        const functionText = functionData.full_definition || functionData.body || '';

        // Create the function viewer window
        const functionWindow = document.createElementNS('http://www.w3.org/1999/xhtml', 'div');
        functionWindow.id = 'function-viewer-window';
        functionWindow.className = 'container';

        // Calculate initial size based on content
        const lineCount = functionText.split('\n').length;
        const lineHeight = 1.4;
        const fontSize = 0.8;
        const approxLineHeightPx = fontSize * 16 * lineHeight;
        const contentHeight = lineCount * approxLineHeightPx;
        const windowChrome = 200; // Header + usage info + padding + margins
        const calculatedHeight = contentHeight + windowChrome;

        // Initial size: content-based but capped at 60vh
        const initialWidth = Math.min(900, window.innerWidth * 0.7);
        const maxHeight = window.innerHeight * 0.6;
        const initialHeight = Math.min(calculatedHeight, maxHeight, 800);
        const initialLeft = (window.innerWidth - initialWidth) / 2;
        const initialTop = (window.innerHeight - initialHeight) / 2;

        functionWindow.style.cssText = `
            position: fixed;
            left: ${initialLeft}px;
            top: ${initialTop}px;
            width: ${initialWidth}px;
            height: ${initialHeight}px;
            max-width: 80vw;
            max-height: 90vh;
            background: rgba(248, 249, 250, 0.98);
            border: 2px solid #2ecc71;
            border-radius: 8px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
            z-index: 100000;
            display: flex;
            flex-direction: column;
            pointer-events: auto;
        `;

        // Header
        const header = document.createElementNS('http://www.w3.org/1999/xhtml', 'div');
        header.className = 'header';
        header.style.cssText = `
            background: linear-gradient(135deg, #2ecc71, #27ae60);
            color: white;
            padding: 12px 16px;
            font-size: 1rem;
            font-weight: 600;
            border-radius: 6px 6px 0 0;
            cursor: grab;
            user-select: none;
            display: flex;
            align-items: center;
            justify-content: space-between;
        `;

        // Header title
        const headerTitle = document.createElementNS('http://www.w3.org/1999/xhtml', 'span');
        headerTitle.textContent = `🔧 ${functionName}`;
        header.appendChild(headerTitle);

        // Close button
        const closeBtn = document.createElementNS('http://www.w3.org/1999/xhtml', 'button');
        closeBtn.textContent = '✕';
        closeBtn.style.cssText = `
            background: rgba(255, 255, 255, 0.2);
            border: none;
            color: white;
            font-size: 1.2rem;
            cursor: pointer;
            padding: 2px 8px;
            border-radius: 4px;
            line-height: 1;
        `;
        closeBtn.addEventListener('click', () => {
            functionWindow.remove();
        });
        header.appendChild(closeBtn);

        // Content area
        const content = document.createElementNS('http://www.w3.org/1999/xhtml', 'div');
        content.className = 'container-content';
        content.style.cssText = `
            padding: 16px;
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow-y: auto;
            position: relative;
        `;

        // Usage information section
        if (triggersUsingFunction.length > 0) {
            const usageSection = document.createElementNS('http://www.w3.org/1999/xhtml', 'div');
            usageSection.style.cssText = `
                margin-bottom: 12px;
                padding: 12px;
                background: rgba(46, 204, 113, 0.1);
                border: 1px solid #2ecc71;
                border-radius: 4px;
            `;

            const usageTitle = document.createElementNS('http://www.w3.org/1999/xhtml', 'h4');
            usageTitle.textContent = `⚡ Used by ${triggersUsingFunction.length} Trigger(s)`;
            usageTitle.style.cssText = `
                margin: 0 0 8px 0;
                font-size: 0.9rem;
                color: #27ae60;
            `;
            usageSection.appendChild(usageTitle);

            const usageList = document.createElementNS('http://www.w3.org/1999/xhtml', 'ul');
            usageList.style.cssText = `
                margin: 0;
                padding-left: 20px;
                font-size: 0.85rem;
            `;

            triggersUsingFunction.forEach(trigger => {
                const listItem = document.createElementNS('http://www.w3.org/1999/xhtml', 'li');
                listItem.textContent = `${trigger.triggerName} on ${trigger.tableName} (${trigger.event})`;
                listItem.style.cssText = `
                    margin-bottom: 4px;
                    color: #555;
                `;
                usageList.appendChild(listItem);
            });

            usageSection.appendChild(usageList);
            content.appendChild(usageSection);
        } else {
            const noUsageSection = document.createElementNS('http://www.w3.org/1999/xhtml', 'div');
            noUsageSection.style.cssText = `
                margin-bottom: 12px;
                padding: 12px;
                background: rgba(189, 195, 199, 0.1);
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                font-size: 0.85rem;
                color: #7f8c8d;
            `;
            noUsageSection.textContent = 'ℹ️ This function is not currently used by any triggers.';
            content.appendChild(noUsageSection);
        }

        // Textarea container with relative positioning for the copy button
        const textareaContainer = document.createElementNS('http://www.w3.org/1999/xhtml', 'div');
        textareaContainer.style.cssText = `
            position: relative;
            flex: 1;
            display: flex;
        `;

        // Function definition textarea
        const functionTextarea = document.createElementNS('http://www.w3.org/1999/xhtml', 'textarea');
        functionTextarea.value = functionText;
        functionTextarea.readOnly = true;
        functionTextarea.style.cssText = `
            width: 100%;
            flex: 1;
            min-height: 100px;
            background: #ffffff;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 0.8rem;
            padding: 12px;
            padding-top: 40px;
            resize: none;
            color: #2c3e50;
            line-height: 1.4;
            box-sizing: border-box;
            overflow-y: auto;
        `;
        textareaContainer.appendChild(functionTextarea);

        // Copy button - overlayed on top right of textarea
        const copyBtn = document.createElementNS('http://www.w3.org/1999/xhtml', 'button');
        copyBtn.textContent = '📋';
        copyBtn.style.cssText = `
            position: absolute;
            top: 8px;
            right: 8px;
            padding: 8px 10px;
            background: rgba(46, 204, 113, 0.95);
            color: white;
            border: 1px solid #2ecc71;
            border-radius: 4px;
            font-size: 1rem;
            cursor: pointer;
            z-index: 10;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            transition: all 0.2s ease;
        `;
        copyBtn.addEventListener('mouseenter', () => {
            copyBtn.style.background = 'rgba(39, 174, 96, 0.95)';
            copyBtn.style.transform = 'scale(1.1)';
        });
        copyBtn.addEventListener('mouseleave', () => {
            copyBtn.style.background = 'rgba(46, 204, 113, 0.95)';
            copyBtn.style.transform = 'scale(1)';
        });
        copyBtn.addEventListener('click', () => {
            copyToClipboard(functionText, copyBtn);
        });
        textareaContainer.appendChild(copyBtn);

        content.appendChild(textareaContainer);

        // Resize handles
        const nwHandle = document.createElementNS('http://www.w3.org/1999/xhtml', 'div');
        nwHandle.className = 'resize-handle nw';
        nwHandle.style.cssText = `
            position: absolute;
            left: 2px;
            top: 42px;
            width: 16px;
            height: 16px;
            cursor: nw-resize;
            background: rgba(46, 204, 113, 0.3);
            border: 1px solid rgba(46, 204, 113, 0.5);
            border-radius: 3px;
            transition: all 0.2s ease;
        `;
        nwHandle.addEventListener('mouseenter', () => {
            nwHandle.style.background = 'rgba(46, 204, 113, 0.6)';
        });
        nwHandle.addEventListener('mouseleave', () => {
            nwHandle.style.background = 'rgba(46, 204, 113, 0.3)';
        });

        const seHandle = document.createElementNS('http://www.w3.org/1999/xhtml', 'div');
        seHandle.className = 'resize-handle se';
        seHandle.style.cssText = `
            position: absolute;
            right: 2px;
            bottom: 2px;
            width: 16px;
            height: 16px;
            cursor: se-resize;
            background: rgba(46, 204, 113, 0.3);
            border: 1px solid rgba(46, 204, 113, 0.5);
            border-radius: 3px;
            transition: all 0.2s ease;
        `;
        seHandle.addEventListener('mouseenter', () => {
            seHandle.style.background = 'rgba(46, 204, 113, 0.6)';
        });
        seHandle.addEventListener('mouseleave', () => {
            seHandle.style.background = 'rgba(46, 204, 113, 0.3)';
        });

        // Assemble window
        functionWindow.appendChild(header);
        functionWindow.appendChild(content);
        functionWindow.appendChild(nwHandle);
        functionWindow.appendChild(seHandle);

        // Append to overlay container
        const overlayContainer = document.getElementById('overlay-container');
        if (overlayContainer) {
            overlayContainer.appendChild(functionWindow);
        }

        // Prevent wheel events from propagating to underlying ERD
        functionWindow.addEventListener('wheel', (event) => {
            event.stopPropagation();
        }, { passive: false });

        // Prevent all mouse events from propagating to underlying ERD
        functionWindow.addEventListener('mousedown', (event) => {
            event.stopPropagation();
        });

        functionWindow.addEventListener('click', (event) => {
            event.stopPropagation();
        });

        // Make the window draggable and resizable
        makeDraggable(functionWindow, header);
        makeResizable(functionWindow, nwHandle, seHandle);

        // If there are tables using this function, highlight them
        if (tablesUsingFunction.length > 0) {
            clearAllHighlights();
            highlightElements(tablesUsingFunction, []);
        }
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
                metadataContainer.style.display = '';
            }
            if (miniatureContainer) {
                miniatureContainer.style.display = '';
            }
            if (selectionContainer) {
                selectionContainer.style.display = '';
            }
        }
    }

    // --- Info Windows Toggle ---
    function toggleInfoWindows() {
        infoWindowsVisible = !infoWindowsVisible;
        
        const metadataContainer = document.getElementById('metadata-container');
        const miniatureContainer = document.getElementById('miniature-container');
        const selectionContainer = document.getElementById('selection-container');
        
        const displayValue = infoWindowsVisible ? 'block' : 'block';
        
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

            // If closing the selection container, also clear the selection
            if (windowElem.id === 'selection-container') {
                // Temporarily allow clearing by removing the visibility check
                highlightedElementId = null;

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
                        setEdgeColor(edgeElement, edges[id].defaultColor, false);
                    }
                    if (miniEdgeElement) {
                        miniEdgeElement.classList.remove('highlighted');
                        setEdgeColor(miniEdgeElement, edges[id].defaultColor, false);
                    }
                });
            }
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
        // Get both handles - try by ID first, then by class
        const nwHandle = windowElem.querySelector('#resize_handle_nw') || windowElem.querySelector('.resize-handle.nw');
        const seHandle = windowElem.querySelector('#resize_handle_se') || windowElem.querySelector('.resize-handle.se');

        if (nwHandle) {
            nwHandle.addEventListener('mousedown', function(event) {
                dragState.type = 'resize';
                const rect = windowElem.getBoundingClientRect();

                // Ensure we have inline styles set for consistent positioning
                // Skip setting left if right is already set (for right-aligned elements)
                if (!windowElem.style.left && !windowElem.style.right) {
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

    const updateViewportIndicator = () => {
        if (!viewportIndicator) return;

        // Get the bounding box of the main ERD content
        const mainBounds = getMainERDBounds();
        if (mainBounds.width === 0 || mainBounds.height === 0) return;

        // Get the current transform matrix
        const ctm = mainGroup.getScreenCTM();
        if (!ctm) return;
        const invCtm = ctm.inverse();

        // Get the viewport dimensions (browser window size)
        const viewport = getViewportDimensions();

        // Transform viewport corners from screen space to SVG coordinate space
        const pt1 = svg.createSVGPoint();
        pt1.x = 0;
        pt1.y = 0;
        const svgPt1 = pt1.matrixTransform(invCtm);

        const pt2 = svg.createSVGPoint();
        pt2.x = viewport.width;
        pt2.y = viewport.height;
        const svgPt2 = pt2.matrixTransform(invCtm);

        // Calculate visible area dimensions in SVG coordinate space
        const visibleWidth = svgPt2.x - svgPt1.x;
        const visibleHeight = svgPt2.y - svgPt1.y;

        // Calculate the visible area's position and size relative to the main ERD bounds
        // This gives us the percentage of the ERD that is visible
        const relLeft = (svgPt1.x - mainBounds.x) / mainBounds.width;
        const relTop = (svgPt1.y - mainBounds.y) / mainBounds.height;
        const relWidth = visibleWidth / mainBounds.width;
        const relHeight = visibleHeight / mainBounds.height;

        // Now position using percentages (simpler and should work correctly)
        viewportIndicator.style.left = `${Math.max(0, Math.min(100, relLeft * 100))}%`;
        viewportIndicator.style.top = `${Math.max(0, Math.min(100, relTop * 100))}%`;
        viewportIndicator.style.width = `${Math.max(0, Math.min(100, relWidth * 100))}%`;
        viewportIndicator.style.height = `${Math.max(0, Math.min(100, relHeight * 100))}%`;
    };

    const applyTransform = () => {
        const finalS = userS * initialS;
        const finalTx = (userTx * initialS) + initialTx;
        const finalTy = (userTy * initialS) + initialTy;
        mainGroup.setAttribute('transform', `translate(${finalTx} ${finalTy}) scale(${finalS})`);
        requestAnimationFrame(updateViewportIndicator);
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

                // Add prominent stroke to highlighted nodes in miniature view
                if (isMini) {
                    if (isHighlighted || isInActiveSelection) {
                        polygon.setAttribute('stroke', tableColor);
                        polygon.setAttribute('stroke-width', '8'); // Doubled for more visibility
                    } else {
                        polygon.setAttribute('stroke-width', '1');
                    }
                }
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
                // For miniature view, use thicker strokes for better visibility
                if (isMini) {
                    polygon.setAttribute('stroke-width', isHighlighted ? '12' : '2'); // Doubled from 6
                    polygon.setAttribute('fill', isHighlighted ? color : GREY_COLOR);
                } else {
                    polygon.setAttribute('stroke-width', isHighlighted ? '20' : '3'); // Doubled from 10
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
                    if (isMini) {
                        paths[0].setAttribute('stroke-width', '16'); // Miniature: doubled for visibility
                        paths[1].setAttribute('stroke-width', '12');
                    } else {
                        paths[0].setAttribute('stroke-width', '32'); // Main: doubled from 16
                        paths[1].setAttribute('stroke-width', '24'); // Main: doubled from 12
                    }
                } else {
                    // Normal state for parallel edges
                    if (isMini) {
                        paths[0].setAttribute('stroke-width', '2');
                        paths[1].setAttribute('stroke-width', '1.5');
                    } else {
                        paths[0].setAttribute('stroke-width', '8');
                        paths[1].setAttribute('stroke-width', '6');
                    }
                }
                paths.forEach(path => path.setAttribute('opacity', '1'));
            } else if (paths.length === 1) {
                // Single edge
                if (isHighlighted) {
                    if (isMini) {
                        paths[0].setAttribute('stroke-width', '12'); // Miniature: doubled for visibility
                    } else {
                        paths[0].setAttribute('stroke-width', '20'); // Main: doubled from 10
                    }
                } else {
                    if (isMini) {
                        paths[0].setAttribute('stroke-width', '1.5');
                    } else {
                        paths[0].setAttribute('stroke-width', '5');
                    }
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


    // Function to update metadata statistics based on current selection
    function updateMetadataStats(selectedTables, selectedEdges) {
        const metadataContainer = document.getElementById('metadata-container');
        if (!metadataContainer) return;
        
        // Store original values on first call
        if (!originalMetadataValues) {
            const columnsValueElem = metadataContainer.querySelector('.metadata-grid .metadata-item:nth-child(3) .value');
            const fkValueElem = metadataContainer.querySelector('.metadata-grid .metadata-item:nth-child(4) .value');
            const connectionsValueElem = metadataContainer.querySelector('.metadata-grid .metadata-item:nth-child(5) .value');
            const triggersValueElem = metadataContainer.querySelector('.metadata-grid .metadata-item:nth-child(6) .value');
            
            originalMetadataValues = {
                columns: columnsValueElem ? columnsValueElem.textContent : '0',
                foreignKeys: fkValueElem ? fkValueElem.textContent : '0',
                connections: connectionsValueElem ? connectionsValueElem.textContent : '0',
                triggers: triggersValueElem ? triggersValueElem.textContent : '0'
            };
        }
        
        // If no selection (clearing), restore original values
        if (selectedTables.length === 0 && selectedEdges.length === 0) {
            const columnsValue = metadataContainer.querySelector('.metadata-grid .metadata-item:nth-child(3) .value');
            const fkValue = metadataContainer.querySelector('.metadata-grid .metadata-item:nth-child(4) .value');
            const connectionsValue = metadataContainer.querySelector('.metadata-grid .metadata-item:nth-child(5) .value');
            const triggersValue = metadataContainer.querySelector('.metadata-grid .metadata-item:nth-child(6) .value');
            
            if (columnsValue) columnsValue.textContent = originalMetadataValues.columns;
            if (fkValue) fkValue.textContent = originalMetadataValues.foreignKeys;
            if (connectionsValue) connectionsValue.textContent = originalMetadataValues.connections;
            if (triggersValue) triggersValue.textContent = originalMetadataValues.triggers;
            
            // Update selectors to show all
            if (window.updateTableSelector) {
                window.updateTableSelector();
            }
            if (window.updateViewSelector) {
                window.updateViewSelector();
            }
            return;
        }
        
        // Count statistics for selected items
        let totalColumns = 0;
        let totalTriggers = 0;
        
        selectedTables.forEach(tableId => {
            const tableData = graphData.tables[tableId];
            if (tableData) {
                // Count columns
                if (tableData.columnCount) {
                    totalColumns += tableData.columnCount;
                }
                // Count triggers
                if (tableData.triggers) {
                    totalTriggers += tableData.triggers.length;
                }
            }
        });
        
        // Update the metadata container values with selection stats
        const columnsValue = metadataContainer.querySelector('.metadata-grid .metadata-item:nth-child(3) .value');
        const fkValue = metadataContainer.querySelector('.metadata-grid .metadata-item:nth-child(4) .value');
        const connectionsValue = metadataContainer.querySelector('.metadata-grid .metadata-item:nth-child(5) .value');
        const triggersValue = metadataContainer.querySelector('.metadata-grid .metadata-item:nth-child(6) .value');
        
        if (columnsValue) columnsValue.textContent = totalColumns;
        if (fkValue) fkValue.textContent = selectedEdges.length;
        if (connectionsValue) connectionsValue.textContent = selectedEdges.length;
        if (triggersValue) triggersValue.textContent = totalTriggers;
        
        // Update table selector to reflect selected tables
        if (window.updateTableSelector) {
            window.updateTableSelector();
        }
        
        // Update view selector to reflect selected views
        if (window.updateViewSelector) {
            window.updateViewSelector();
        }
    }

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

        // Update metadata statistics based on current selection
        updateMetadataStats(selectedTables, selectedEdges);

        let html = '';

        if (selectedTables.length) {
            let primaryTable = selectedTables[0];
            selection_header.textContent = `📋 ${primaryTable}`;

            // Table Information Section
            html += '<div class="selection-section">';
            html += `<div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px;">`;
            html += `<h3 style="margin: 0;">📊 Selected Tables (${selectedTables.length})</h3>`;
            html += `<button id="generate-focused-erd-btn" class="db-action-btn" style="
                padding: 6px 12px;
                background: linear-gradient(135deg, #3498db, #2980b9);
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 0.85rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s ease;
                white-space: nowrap;
            ">
                🔍 Generate Focused ERD
            </button>`;
            html += `</div>`;

            // Add collapsible settings panel
            html += `<div id="focused-erd-settings" style="
                max-height: 0;
                overflow-y: auto;
                overflow-x: hidden;
                transition: max-height 0.3s ease-out;
                margin-bottom: 12px;
            ">
                <div style="
                    background: rgba(46, 125, 219, 0.08);
                    border: 1px solid rgba(46, 125, 219, 0.2);
                    border-radius: 4px;
                    padding: 12px;
                    margin-top: 8px;
                    pointer-events: auto;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <h4 style="margin: 0; font-size: 0.9rem; color: #2e7ddb;">⚙️ Graphviz Layout Settings</h4>
                        <button id="generate-focused-erd-confirm" class="db-action-btn" style="
                            padding: 6px 16px;
                            background: linear-gradient(135deg, #2e7ddb, #1e5bb8);
                            color: white;
                            border: none;
                            border-radius: 4px;
                            font-size: 0.85rem;
                            font-weight: 600;
                            cursor: pointer;
                            transition: all 0.2s ease;
                        ">
                            Create ERD from ${selectedTables.length} ${selectedTables.length === 1 ? 'table' : 'tables'}
                        </button>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px 12px; font-size: 0.8rem;">
                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6c757d; font-weight: 500;">Rank Direction</label>
                            <select id="focused-rankdir" style="width: 100%; padding: 6px; border-radius: 3px; border: 1px solid #ced4da; background: white; cursor: pointer;">
                                <option value="TB">Top to Bottom</option>
                                <option value="LR">Left to Right</option>
                                <option value="BT">Bottom to Top</option>
                                <option value="RL">Right to Left</option>
                            </select>
                        </div>

                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6c757d; font-weight: 500;">Pack Mode</label>
                            <select id="focused-packmode" style="width: 100%; padding: 6px; border-radius: 3px; border: 1px solid #ced4da; background: white; cursor: pointer;">
                                <option value="array">Array</option>
                                <option value="cluster">Cluster</option>
                                <option value="graph">Graph</option>
                            </select>
                        </div>

                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6c757d; font-weight: 500;">Node Separation</label>
                            <input type="number" id="focused-nodesep" value="0.5" step="0.1" min="0" style="width: 100%; padding: 6px; border-radius: 3px; border: 1px solid #ced4da; box-sizing: border-box;">
                        </div>

                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6c757d; font-weight: 500;">Rank Separation</label>
                            <input type="number" id="focused-ranksep" value="1.2" step="0.1" min="0" style="width: 100%; padding: 6px; border-radius: 3px; border: 1px solid #ced4da; box-sizing: border-box;">
                        </div>

                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6c757d; font-weight: 500;">Edge Separation</label>
                            <input type="number" id="focused-esep" value="8" step="1" min="0" style="width: 100%; padding: 6px; border-radius: 3px; border: 1px solid #ced4da; box-sizing: border-box;">
                        </div>

                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6c757d; font-weight: 500;">Font Name</label>
                            <input type="text" id="focused-fontname" value="Sans-Serif" style="width: 100%; padding: 6px; border-radius: 3px; border: 1px solid #ced4da; box-sizing: border-box;">
                        </div>

                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6c757d; font-weight: 500;">Graph Font Size</label>
                            <input type="number" id="focused-fontsize" value="24" step="1" min="8" style="width: 100%; padding: 6px; border-radius: 3px; border: 1px solid #ced4da; box-sizing: border-box;">
                        </div>

                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6c757d; font-weight: 500;">Node Font Size</label>
                            <input type="number" id="focused-node-fontsize" value="20" step="1" min="8" style="width: 100%; padding: 6px; border-radius: 3px; border: 1px solid #ced4da; box-sizing: border-box;">
                        </div>

                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6c757d; font-weight: 500;">Edge Font Size</label>
                            <input type="number" id="focused-edge-fontsize" value="16" step="1" min="8" style="width: 100%; padding: 6px; border-radius: 3px; border: 1px solid #ced4da; box-sizing: border-box;">
                        </div>

                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6c757d; font-weight: 500;">Node Style</label>
                            <input type="text" id="focused-node-style" value="filled" style="width: 100%; padding: 6px; border-radius: 3px; border: 1px solid #ced4da; box-sizing: border-box;">
                        </div>

                        <div>
                            <label style="display: block; margin-bottom: 4px; color: #6c757d; font-weight: 500;">Node Shape</label>
                            <select id="focused-node-shape" style="width: 100%; padding: 6px; border-radius: 3px; border: 1px solid #ced4da; background: white; cursor: pointer;">
                                <option value="rect">Rectangle</option>
                                <option value="box">Box</option>
                                <option value="ellipse">Ellipse</option>
                                <option value="circle">Circle</option>
                                <option value="plaintext">Plain Text</option>
                            </select>
                        </div>
                    </div>
                </div>
            </div>`;

            selectedTables.forEach((tableId, index) => {
                const tableData = graphData.tables[tableId];
                const safeTableId = escapeHtml(tableId);
                if (index === 0) {
                    // Primary table row with its SQL buttons
                    html += `<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">`;
                    html += `<span class="table-name" data-table-id="${safeTableId}" style="font-size: 1.1rem; font-weight: 600;">${safeTableId}</span>`;
                    // Add View SQL and Copy SQL buttons for the primary table
                    if (tableData && tableData.sql) {
                        html += `<button id="view-table-sql" class="db-action-btn" style="
                            padding: 4px 8px;
                            background: rgba(52, 152, 219, 0.1);
                            color: #3498db;
                            border: 1px solid #3498db;
                            border-radius: 4px;
                            font-size: 0.75rem;
                            font-weight: 600;
                            cursor: pointer;
                            transition: all 0.2s ease;
                        " title="View table SQL in a window">
                            👁️ SQL
                        </button>`;
                        html += `<button id="copy-table-sql" class="db-action-btn" style="
                            padding: 4px 8px;
                            background: rgba(52, 152, 219, 0.1);
                            color: #3498db;
                            border: 1px solid #3498db;
                            border-radius: 4px;
                            font-size: 0.75rem;
                            font-weight: 600;
                            cursor: pointer;
                            transition: all 0.2s ease;
                        " title="Copy SQL to clipboard">
                            📋
                        </button>`;
                    }
                    html += `</div>`;
                }
            });

            // Additional table names row with copy button
            if (selectedTables.length > 1) {
                html += `<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px; flex-wrap: wrap;">`;

                // Copy button on the left
                html += `<button id="copy-all-table-names" class="db-action-btn" style="
                    padding: 4px 8px;
                    background: rgba(52, 152, 219, 0.1);
                    color: #3498db;
                    border: 1px solid #3498db;
                    border-radius: 4px;
                    font-size: 0.85rem;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    flex-shrink: 0;
                " title="Copy all table names to clipboard">
                    📋
                </button>`;

                // Additional table names
                selectedTables.forEach((tableId, index) => {
                    if (index > 0) {
                        const safeTableId = escapeHtml(tableId);
                        html += `<span class="table-name" data-table-id="${safeTableId}">${safeTableId}</span>`;
                    }
                });

                html += '</div>'; // Close additional table names row
            }

            // Add table details for the primary table
            const primaryTableData = graphData.tables[primaryTable];
            if (primaryTableData && primaryTableData.triggers && primaryTableData.triggers.length > 0) {
                html += '<div class="selection-section">';
                html += '<h3>⚡ Triggers</h3>';
                primaryTableData.triggers.forEach((trigger, triggerIndex) => {
                    html += '<div class="trigger-info" style="margin-bottom: 8px;">';
                    html += `<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">`;
                    html += `<span class="trigger-name" style="font-weight: 600;">${escapeHtml(trigger.trigger_name)}</span>`;
                    html += `<span class="trigger-event" style="font-size: 0.8rem; color: #7f8c8d;">${escapeHtml(trigger.event)}</span>`;
                    if (trigger.full_line) {
                        html += `<button class="view-trigger-function" data-trigger-index="${triggerIndex}" style="
                            padding: 2px 6px;
                            background: rgba(52, 152, 219, 0.1);
                            color: #3498db;
                            border: 1px solid #3498db;
                            border-radius: 3px;
                            font-size: 0.7rem;
                            font-weight: 600;
                            cursor: pointer;
                            transition: all 0.2s ease;
                        " title="View trigger function">
                            👁️
                        </button>`;
                        html += `<button class="copy-trigger-function" data-trigger-index="${triggerIndex}" style="
                            padding: 2px 6px;
                            background: rgba(52, 152, 219, 0.1);
                            color: #3498db;
                            border: 1px solid #3498db;
                            border-radius: 3px;
                            font-size: 0.7rem;
                            font-weight: 600;
                            cursor: pointer;
                            transition: all 0.2s ease;
                        " title="Copy trigger function">
                            📋
                        </button>`;
                    }
                    html += `</div>`;
                    if (trigger.function) {
                        const functionName = trigger.function;
                        const safeFunctionName = sanitizeLabel(functionName);
                        const functionData = graphData.functions && graphData.functions[safeFunctionName];

                        html += `<div style="font-size: 0.75rem; color: #7f8c8d; display: flex; align-items: center; gap: 8px; margin-top: 4px;">`;
                        html += `<span>→ ${escapeHtml(functionName)}${trigger.function_args ? '(' + escapeHtml(trigger.function_args) + ')' : '()'}</span>`;

                        if (functionData && functionData.full_definition) {
                            html += `<button class="view-function-definition" data-function-name="${escapeHtml(safeFunctionName)}" style="
                                padding: 2px 6px;
                                background: rgba(46, 204, 113, 0.1);
                                color: #2ecc71;
                                border: 1px solid #2ecc71;
                                border-radius: 3px;
                                font-size: 0.7rem;
                                font-weight: 600;
                                cursor: pointer;
                                transition: all 0.2s ease;
                            " title="View function definition">
                                👁️
                            </button>`;
                            html += `<button class="copy-function-definition" data-function-name="${escapeHtml(safeFunctionName)}" style="
                                padding: 2px 6px;
                                background: rgba(46, 204, 113, 0.1);
                                color: #2ecc71;
                                border: 1px solid #2ecc71;
                                border-radius: 3px;
                                font-size: 0.7rem;
                                font-weight: 600;
                                cursor: pointer;
                                transition: all 0.2s ease;
                            " title="Copy function definition">
                                📋
                            </button>`;
                        }
                        html += `</div>`;
                    }
                    html += '</div>';
                });
                html += '</div>';
            }
        }

        // Foreign Keys Section
        if (selectedEdges.length) {
            html += '<div class="selection-section">';
            html += `<h3>🔗 Foreign Key Relationships (${selectedEdges.length})</h3>`;
            for (const edgeId of selectedEdges) {
                const edge = graphData.edges[edgeId];
                if (edge && edge.fkText) {
                    html += `<div class="edge-name" data-edge-id="${escapeHtml(edgeId)}" style="position: relative;">`;
                    html += `<div style="display: flex; align-items: center; justify-content: space-between;">`;
                    html += `<h4>🔑 ${escapeHtml(edge.fromColumn)} → ${escapeHtml(edge.toColumn)}</h4>`;
                    html += `<button class="copy-sql-text" data-sql-text="${escapeHtml(edge.fkText)}" style="background: none; border: none; cursor: pointer; padding: 4px; font-size: 0.9rem; opacity: 0.6; transition: opacity 0.2s;" title="Copy SQL">📋</button>`;
                    html += `</div>`;
                    html += `<pre>${escapeHtml(edge.fkText)}</pre>`;
                    html += '</div>';
                } else {
                    html += `<div class="edge-name" data-edge-id="${escapeHtml(edgeId)}">${escapeHtml(edgeId)}</div>`;
                }
            }
            html += '</div>';
        }

        // Add Generate SVG buttons
        html += `
            <div style="margin-top: 20px; padding-top: 16px; border-top: 2px solid #ecf0f1;">
                <button id="generate-selected-svg-btn" class="db-action-btn" style="
                    width: 100%;
                    padding: 10px 16px;
                    background: linear-gradient(135deg, #27ae60, #229954);
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 0.9rem;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s ease;
                ">
                    📥 Generate Standalone SVG
                </button>
                <div id="focused-erd-status" style="
                    margin-top: 8px;
                    padding: 6px;
                    border-radius: 3px;
                    font-size: 0.8rem;
                    text-align: center;
                    display: none;
                "></div>
            </div>
        `;

        // Parse HTML in a separate HTML document (not XML/SVG context)
        // This completely avoids innerHTML issues in XML documents
        try {
            const parser = new DOMParser();
            const htmlDoc = parser.parseFromString(html, 'text/html');
            const parsedContent = htmlDoc.body;

            // Clear existing content without using innerHTML
            while (inner.firstChild) {
                inner.removeChild(inner.firstChild);
            }

            // Import and append parsed nodes
            // Convert to array first to avoid issues with live NodeList
            const nodes = Array.from(parsedContent.childNodes);
            nodes.forEach(node => {
                // Import node into current document
                const importedNode = document.importNode(node, true);
                inner.appendChild(importedNode);
            });
        } catch (error) {
            console.error('Error populating selection window:', error);
            console.error('HTML content:', html.substring(0, 500));
            // Fallback: show error message
            const errorDiv = document.createElement('div');
            errorDiv.textContent = 'Error displaying selection. Check console for details.';
            errorDiv.style.color = 'red';
            errorDiv.style.padding = '10px';
            inner.appendChild(errorDiv);
        }

        // Add click event listeners to table names
        const tableNames = inner.querySelectorAll('.table-name');
        tableNames.forEach(tableNameSpan => {
            const tableId = tableNameSpan.getAttribute('data-table-id');

            // Click handler
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
                
                // Update metadata with new selection
                updateMetadataStats(uniqueTables, connectedEdges);
                
                // Update the selection window content
                showSelectionWindow(uniqueTables, connectedEdges, null);

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
            });
        });

        // Edge names - no mouse event handlers needed
        const edgeNames = inner.querySelectorAll('.edge-name');
        edgeNames.forEach(edgeNameLi => {
            const edgeId = edgeNameLi.getAttribute('data-edge-id');
            // Mouse events handled at table/view container level only
        });

        // Copy all table names button handler
        const copyAllTableNamesBtn = document.getElementById('copy-all-table-names');
        if (copyAllTableNamesBtn) {
            copyAllTableNamesBtn.addEventListener('click', () => {
                const tableNames = selectedTables.join('\n');
                copyToClipboard(tableNames, copyAllTableNamesBtn);
            });
        }

        // Copy table SQL button handler
        const copyTableSqlBtn = document.getElementById('copy-table-sql');
        if (copyTableSqlBtn) {
            copyTableSqlBtn.addEventListener('click', () => {
                const primaryTable = selectedTables[0];
                const primaryTableData = graphData.tables[primaryTable];
                if (primaryTableData && primaryTableData.sql) {
                    copyToClipboard(primaryTableData.sql, copyTableSqlBtn);
                }
            });
        }

        // View table SQL button handler - opens a new window
        const viewTableSqlBtn = document.getElementById('view-table-sql');
        if (viewTableSqlBtn) {
            viewTableSqlBtn.addEventListener('click', () => {
                const primaryTable = selectedTables[0];
                const primaryTableData = graphData.tables[primaryTable];
                if (primaryTableData && primaryTableData.sql) {
                    showSqlWindow(primaryTable, primaryTableData.sql, viewTableSqlBtn);
                }
            });
        }

        // View trigger function button handlers
        const viewTriggerButtons = inner.querySelectorAll('.view-trigger-function');
        viewTriggerButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const triggerIndex = parseInt(btn.getAttribute('data-trigger-index'));
                const primaryTable = selectedTables[0];
                const primaryTableData = graphData.tables[primaryTable];
                if (primaryTableData && primaryTableData.triggers && primaryTableData.triggers[triggerIndex]) {
                    const trigger = primaryTableData.triggers[triggerIndex];
                    const triggerText = trigger.full_line || '';
                    showSqlWindow(`${trigger.trigger_name} - Trigger Function`, triggerText, btn);
                }
            });
        });

        // Copy trigger function button handlers
        const copyTriggerButtons = inner.querySelectorAll('.copy-trigger-function');
        copyTriggerButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const triggerIndex = parseInt(btn.getAttribute('data-trigger-index'));
                const primaryTable = selectedTables[0];
                const primaryTableData = graphData.tables[primaryTable];
                if (primaryTableData && primaryTableData.triggers && primaryTableData.triggers[triggerIndex]) {
                    const trigger = primaryTableData.triggers[triggerIndex];
                    const triggerText = trigger.full_line || '';
                    copyToClipboard(triggerText, btn);
                }
            });
        });

        // View function definition button handlers
        const viewFunctionButtons = inner.querySelectorAll('.view-function-definition');
        viewFunctionButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const functionName = btn.getAttribute('data-function-name');
                const functionData = graphData.functions && graphData.functions[functionName];
                if (functionData && functionData.full_definition) {
                    showSqlWindow(`${functionData.name} - Function Definition`, functionData.full_definition, btn);
                }
            });
        });

        // Copy function definition button handlers
        const copyFunctionButtons = inner.querySelectorAll('.copy-function-definition');
        copyFunctionButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const functionName = btn.getAttribute('data-function-name');
                const functionData = graphData.functions && graphData.functions[functionName];
                if (functionData && functionData.full_definition) {
                    copyToClipboard(functionData.full_definition, btn);
                }
            });
        });

        // Copy SQL text button handlers
        const copySqlButtons = inner.querySelectorAll('.copy-sql-text');
        copySqlButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const sqlText = btn.getAttribute('data-sql-text');
                copyToClipboard(sqlText, btn);
            });
        });

        // Generate Focused ERD button handler - toggle settings panel
        const focusedErdBtn = document.getElementById('generate-focused-erd-btn');
        const focusedSettingsPanel = document.getElementById('focused-erd-settings');

        if (focusedErdBtn && focusedSettingsPanel) {
            focusedErdBtn.addEventListener('click', () => {
                const isOpen = focusedSettingsPanel.style.maxHeight !== '0px' && focusedSettingsPanel.style.maxHeight !== '';

                if (isOpen) {
                    // Collapse
                    focusedSettingsPanel.style.maxHeight = '0';
                    focusedErdBtn.textContent = '🔍 Generate Focused ERD';
                } else {
                    // Expand - increased to accommodate all settings
                    focusedSettingsPanel.style.maxHeight = '800px';
                    focusedErdBtn.textContent = '🔼 Hide Settings';
                }
            });
        }

        // Add event listeners to stop propagation for all inputs in the settings panel
        if (focusedSettingsPanel) {
            focusedSettingsPanel.addEventListener('mousedown', (e) => {
                e.stopPropagation();
            });
            focusedSettingsPanel.addEventListener('click', (e) => {
                e.stopPropagation();
            });
            focusedSettingsPanel.addEventListener('wheel', (e) => {
                e.stopPropagation();
            }, { passive: false });
        }

        // Print ERD button handler - creates a print-friendly version
        const printErdBtn = document.getElementById('print-erd-btn');
        if (printErdBtn) {
            printErdBtn.addEventListener('click', () => {
                // Hide all interactive UI elements for printing
                const elementsToHide = [
                    document.getElementById('metadata-container'),
                    document.getElementById('miniature-container'),
                    document.getElementById('selection-container'),
                    document.getElementById('overlay-container')
                ];

                // Store original display values
                const originalDisplayValues = elementsToHide.map(el => el ? el.style.display : null);

                // Hide elements
                elementsToHide.forEach(el => {
                    if (el) el.style.display = 'none';
                });

                // Reset zoom and pan to show full ERD
                if (mainGroup) {
                    const mainBounds = mainGroup.getBBox();
                    const viewport = getViewportDimensions();

                    // Calculate scale to fit the entire ERD with padding
                    const padding = 50;
                    const scaleX = (viewport.width - padding * 2) / mainBounds.width;
                    const scaleY = (viewport.height - padding * 2) / mainBounds.height;
                    const scale = Math.min(scaleX, scaleY, 1.0);

                    // Center the ERD
                    const centerX = mainBounds.x + mainBounds.width / 2;
                    const centerY = mainBounds.y + mainBounds.height / 2;

                    // Calculate translation to center
                    const tx = (viewport.width / 2) - (centerX * scale);
                    const ty = (viewport.height / 2) - (centerY * scale);

                    // Apply transform
                    mainGroup.setAttribute('transform', `translate(${tx}, ${ty}) scale(${scale})`);
                }

                // Wait a bit for rendering, then print
                setTimeout(() => {
                    window.print();

                    // Restore hidden elements after print dialog closes
                    setTimeout(() => {
                        elementsToHide.forEach((el, index) => {
                            if (el && originalDisplayValues[index] !== null) {
                                el.style.display = originalDisplayValues[index] || '';
                            }
                        });
                    }, 100);
                }, 100);
            });
        }

        // Generate Focused ERD confirm button handler - actually generate the ERD
        const focusedErdConfirmBtn = document.getElementById('generate-focused-erd-confirm');
        const focusedStatusDiv = document.getElementById('focused-erd-status');

        if (focusedErdConfirmBtn) {
            focusedErdConfirmBtn.addEventListener('click', async () => {
                focusedErdConfirmBtn.disabled = true;
                focusedErdConfirmBtn.textContent = '⏳ Generating...';

                if (focusedStatusDiv) {
                    focusedStatusDiv.style.display = 'block';
                    focusedStatusDiv.textContent = 'Generating focused ERD...';
                    focusedStatusDiv.style.background = 'rgba(33, 150, 243, 0.1)';
                    focusedStatusDiv.style.border = '1px solid rgba(33, 150, 243, 0.3)';
                    focusedStatusDiv.style.color = '#1565c0';
                }

                try {
                    // Get selected table and edge IDs
                    const selectedTableIds = selectedTables.map(sanitizedId => {
                        const tableData = graphData.tables[sanitizedId];
                        return tableData?.originalName || sanitizedId;
                    });
                    const selectedEdgeIds = selectedEdges;

                    // Get Graphviz settings from the focused ERD settings panel
                    const graphvizSettings = {
                        packmode: document.getElementById('focused-packmode')?.value || 'array',
                        rankdir: document.getElementById('focused-rankdir')?.value || 'TB',
                        esep: document.getElementById('focused-esep')?.value || '8',
                        node_sep: document.getElementById('focused-nodesep')?.value || '0.5',
                        rank_sep: document.getElementById('focused-ranksep')?.value || '1.2',
                        fontname: document.getElementById('focused-fontname')?.value || 'Sans-Serif',
                        fontsize: parseInt(document.getElementById('focused-fontsize')?.value) || 24,
                        node_fontsize: parseInt(document.getElementById('focused-node-fontsize')?.value) || 20,
                        edge_fontsize: parseInt(document.getElementById('focused-edge-fontsize')?.value) || 16,
                        node_style: document.getElementById('focused-node-style')?.value || 'filled',
                        node_shape: document.getElementById('focused-node-shape')?.value || 'rect'
                    };

                    // Send request to generate focused ERD
                    const response = await fetch('/api/generate_focused_erd', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            table_ids: selectedTableIds,
                            edge_ids: selectedEdgeIds,
                            graphviz_settings: graphvizSettings
                        })
                    });

                    const result = await response.json();

                    if (result.success && result.new_file) {
                        if (focusedStatusDiv) {
                            focusedStatusDiv.textContent = 'Success! Opening in popup...';
                            focusedStatusDiv.style.background = 'rgba(76, 175, 80, 0.1)';
                            focusedStatusDiv.style.border = '1px solid rgba(76, 175, 80, 0.3)';
                            focusedStatusDiv.style.color = '#2e7d32';
                        }

                        // Open focused ERD in a popup window
                        setTimeout(() => {
                            const screenWidth = window.screen.availWidth;
                            const screenHeight = window.screen.availHeight;
                            const popupWidth = Math.floor(screenWidth * 0.8);
                            const popupHeight = Math.floor(screenHeight * 0.8);
                            const left = Math.floor((screenWidth - popupWidth) / 2);
                            const top = Math.floor((screenHeight - popupHeight) / 2);

                            window.open(
                                `/${result.new_file}`,
                                'focusedERD',
                                `width=${popupWidth},height=${popupHeight},left=${left},top=${top},resizable=yes,scrollbars=yes,status=yes,toolbar=no,menubar=no,location=no`
                            );
                            focusedErdConfirmBtn.textContent = '✓ Generate ERD';
                            focusedErdConfirmBtn.disabled = false;
                            if (focusedStatusDiv) {
                                setTimeout(() => {
                                    focusedStatusDiv.style.display = 'none';
                                }, 2000);
                            }
                            // Collapse the settings panel after successful generation
                            if (focusedSettingsPanel) {
                                focusedSettingsPanel.style.maxHeight = '0';
                            }
                            if (focusedErdBtn) {
                                focusedErdBtn.textContent = '🔍 Generate Focused ERD';
                            }
                        }, 500);
                    } else {
                        throw new Error(result.message || 'Failed to generate focused ERD');
                    }
                } catch (error) {
                    console.error('Error generating focused ERD:', error);
                    if (focusedStatusDiv) {
                        focusedStatusDiv.textContent = `Error: ${error.message}`;
                        focusedStatusDiv.style.background = 'rgba(244, 67, 54, 0.1)';
                        focusedStatusDiv.style.border = '1px solid rgba(244, 67, 54, 0.3)';
                        focusedStatusDiv.style.color = '#c62828';
                    }
                    focusedErdConfirmBtn.textContent = '✓ Generate ERD';
                    focusedErdConfirmBtn.disabled = false;
                }
            });
        }

        // Generate Standalone SVG button handler
        const generateBtn = document.getElementById('generate-selected-svg-btn');
        if (generateBtn) {
            generateBtn.addEventListener('click', async () => {
                generateBtn.disabled = true;
                generateBtn.textContent = '⏳ Generating...';

                try {
                    // Get selected table and edge IDs
                    // selectedTables and selectedEdges are already arrays of string IDs (sanitized), not objects
                    // Convert sanitized IDs back to original table names using graph data
                    const selectedTableIds = selectedTables.map(sanitizedId => {
                        const tableData = graphData.tables[sanitizedId];
                        return tableData?.originalName || sanitizedId;  // Fallback to sanitized if originalName not found
                    });
                    const selectedEdgeIds = selectedEdges;

                    // Get Graphviz settings from the UI
                    const graphvizSettings = {
                        packmode: document.getElementById('gv-packmode')?.value || 'array',
                        rankdir: document.getElementById('gv-rankdir')?.value || 'TB',
                        esep: document.getElementById('gv-esep')?.value || '8',
                        node_sep: document.getElementById('gv-node-sep')?.value || '0.5',
                        rank_sep: document.getElementById('gv-rank-sep')?.value || '1.2',
                        fontname: document.getElementById('gv-fontname')?.value || 'Arial',
                        fontsize: parseInt(document.getElementById('gv-fontsize')?.value) || 18,
                        node_fontsize: parseInt(document.getElementById('gv-node-fontsize')?.value) || 14,
                        edge_fontsize: parseInt(document.getElementById('gv-edge-fontsize')?.value) || 12,
                        node_style: document.getElementById('gv-node-style')?.value || 'rounded,filled',
                        node_shape: document.getElementById('gv-node-shape')?.value || 'rect'
                    };

                    // Send request to server
                    const response = await fetch('/api/generate_selected_svg', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            table_ids: selectedTableIds,
                            edge_ids: selectedEdgeIds,
                            graphviz_settings: graphvizSettings
                        })
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }

                    // Get the SVG content
                    const svgContent = await response.text();

                    // Create a blob and download it
                    const blob = new Blob([svgContent], { type: 'image/svg+xml' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'selected_erd.svg';

                    // In SVG context, document.body may be null, so use documentElement or svg root
                    const parentElement = document.body || document.documentElement || document.querySelector('svg');
                    if (parentElement) {
                        parentElement.appendChild(a);
                        a.click();
                        parentElement.removeChild(a);
                    } else {
                        // Fallback: click without appending to DOM
                        a.style.display = 'none';
                        a.click();
                    }
                    URL.revokeObjectURL(url);

                    generateBtn.textContent = '✅ Downloaded!';
                    setTimeout(() => {
                        generateBtn.textContent = '📥 Generate Standalone SVG';
                        generateBtn.disabled = false;
                    }, 2000);
                } catch (error) {
                    console.error('Error generating SVG:', error);
                    generateBtn.textContent = '❌ Error';
                    setTimeout(() => {
                        generateBtn.textContent = '📥 Generate Standalone SVG';
                        generateBtn.disabled = false;
                    }, 2000);
                }
            });
        }

    }

    function hideSelectionWindow() {
        const selectionContainer = document.getElementById('selection-container');
        if (selectionContainer) {
            selectionContainer.style.display = 'none';
            const inner = selectionContainer.querySelector('#selection-inner-container');
            if (inner) {
                // Clear without using innerHTML in SVG context
                while (inner.firstChild) {
                    inner.removeChild(inner.firstChild);
                }
            }
        }
    }

    const clearAllHighlights = () => {
        // Don't clear highlights during drag operations
        if (dragState.type !== null) {
            return;
        }

        // Don't clear if selection-container is visible (user is actively working with a selection)
        const selectionContainer = document.getElementById('selection-container');
        const isSelectionVisible = selectionContainer &&
            selectionContainer.style.display !== 'none' &&
            window.getComputedStyle(selectionContainer).display !== 'none';

        if (isSelectionVisible) {
            return;
        }

        // Also check if selection-container is being dragged (it has its own drag system)
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
        
        // Reset metadata stats to full totals when highlights are cleared
        updateMetadataStats([], []);
        
        // Update table selector to show all tables when highlights are cleared
        if (window.updateTableSelector) {
            window.updateTableSelector();
        }
        
        // Update view selector to show all views when highlights are cleared
        if (window.updateViewSelector) {
            window.updateViewSelector();
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

            // Convert right positioning to left for dragging
            const viewport = getViewportDimensions();
            const currentRight = parseFloat(miniatureContainer.style.right) || 16;
            const currentTop = parseFloat(miniatureContainer.style.top) || 16;
            const currentLeft = viewport.width - rect.width - currentRight;

            // Switch to left-based positioning for dragging
            miniatureContainer.style.left = `${currentLeft}px`;
            miniatureContainer.style.right = '';

            const miniatureDragState = {
                type: 'miniature-window',
                target: miniatureContainer,
                startX: event.clientX,
                startY: event.clientY,
                offsetX: currentLeft,
                offsetY: currentTop
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

    // Click-to-center on miniature container
    const miniatureSvg = document.getElementById('miniature-svg');
    if (miniatureSvg && miniatureContainer) {
        miniatureSvg.addEventListener('click', (event) => {
            // Ignore clicks on the viewport indicator itself (those should drag)
            if (event.target.closest('#viewport-indicator')) {
                return;
            }

            // Ignore if we're dragging
            if (dragState.type === 'indicator') {
                return;
            }

            const miniRect = miniatureContainer.getBoundingClientRect();

            // Calculate relative position of click within miniature container
            const relX = (event.clientX - miniRect.left) / miniRect.width;
            const relY = (event.clientY - miniRect.top) / miniRect.height;

            // Clamp to 0-1 range
            const safeRelX = Math.max(0, Math.min(1, relX));
            const safeRelY = Math.max(0, Math.min(1, relY));

            // Get main SVG bounds
            const mainBounds = getMainERDBounds();
            const targetX = mainBounds.x + safeRelX * mainBounds.width;
            const targetY = mainBounds.y + safeRelY * mainBounds.height;

            // Center the view on the clicked point
            zoomToPoint(targetX, targetY, userS);

            event.preventDefault();
            event.stopPropagation();
        });
    }

    // Metadata box drag (only from header)
    const metadataContainer = document.getElementById('metadata-container');
    const metadataHeader = document.getElementById('metadata-header');
    if (metadataContainer && metadataHeader) {
        makeResizable(metadataContainer);
        metadataHeader.addEventListener('mousedown', (event) => {
            // Prevent drag if clicking on controls/buttons in header
            if (event.target.closest('.window-controls') || event.target.tagName === 'BUTTON') {
                return;
            }

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

    // --- Auto-zoom for focused ERD ---
    // If this is a focused ERD (check URL contains 'focused'), zoom all the way out
    let lockedMinZoom = null;
    if (mainGroup) {
        // Simulate scrolling out to the absolute minimum
        let previousS = userS;
        for (let i = 0; i < 200; i++) {
            const mainBounds = getMainERDBounds();
            const viewport = getViewportDimensions();
            const scaleX = viewport.width / mainBounds.width;
            const scaleY = viewport.height / mainBounds.height;
            const calculatedMin = Math.min(scaleX, scaleY) * 0.5;
            userS = userS * 0.96;
            if (userS < calculatedMin) {
                userS = calculatedMin;
            }
            if (userS === previousS) {
                break;
            }
            previousS = userS;
        }
        lockedMinZoom = userS;

        // Center horizontally and position at 50% vertically
        const mainBounds = getMainERDBounds();
        const viewport = getViewportDimensions();
        const scaledWidth = mainBounds.width * userS * initialS;
        const scaledHeight = mainBounds.height * userS * initialS;

        // Horizontally centered
        const centerX = (viewport.width - scaledWidth) / 2;
        // 50% down vertically
        const centerY = viewport.height * 0.5 - scaledHeight / 2;

        userTx = (centerX - mainBounds.x * userS * initialS) / initialS;
        userTy = (centerY - mainBounds.y * userS * initialS) / initialS;

        applyTransform();
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
        const minZoom = lockedMinZoom !== null ? lockedMinZoom : getMinZoomToFit();
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

            // First, use closest() to check if we're within a node or edge
            const nodeElement = event.target.closest('.node');
            const edgeElement = event.target.closest('.edge');

            // If we found a node element, get its table ID
            if (nodeElement && nodeElement.id && tables[nodeElement.id]) {
                tableId = nodeElement.id;
            }
            // If we found an edge element
            else if (edgeElement && edgeElement.id) {
                edgeId = edgeElement.id;
            }
            // Fallback: traverse up looking for any element with a known table/edge ID
            else {
                clickedElement = event.target;
                while (clickedElement && clickedElement !== svg) {
                    // Check if element ID directly matches a known table
                    if (clickedElement.id && tables[clickedElement.id]) {
                        tableId = clickedElement.id;
                        break;
                    }
                    // Check for edge ID pattern
                    if (clickedElement.id && clickedElement.id.startsWith('edge-')) {
                        edgeId = clickedElement.id;
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

            // Click on empty space (not on nodes/edges): clear highlights and center view
            const isOnNode = event.target.closest('.node');
            const isOnEdge = event.target.closest('.edge');
            const isOnContainer = event.target.closest('#selection-container') ||
                                 event.target.closest('#metadata-container') ||
                                 event.target.closest('#miniature-container');

            // Allow recentering on empty space - everything except nodes, edges, and containers
            if (!isOnNode && !isOnEdge && !isOnContainer) {
                // Check if selection container is visible - if so, don't clear selection
                const selectionContainer = document.getElementById('selection-container');
                const isSelectionVisible = selectionContainer &&
                    selectionContainer.style.display !== 'none' &&
                    window.getComputedStyle(selectionContainer).display !== 'none';

                // Only clear highlights if selection container is not visible
                if (!isSelectionVisible) {
                    clearAllHighlights();
                }

                // Center the view on the clicked point
                const svgRect = svg.getBoundingClientRect();
                const clickX = event.clientX - svgRect.left;
                const clickY = event.clientY - svgRect.top;

                // Convert to SVG coordinates
                const ctm = mainGroup.getScreenCTM();
                if (ctm) {
                    const invCtm = ctm.inverse();
                    const pt = svg.createSVGPoint();
                    pt.x = clickX;
                    pt.y = clickY;
                    const svgPt = pt.matrixTransform(invCtm);

                    // Center the view on the clicked point
                    zoomToPoint(svgPt.x, svgPt.y, userS);
                }

                event.stopPropagation();
                return;
            }
        }

    });

    // Double-click handler to zoom to connected nodes
    document.addEventListener('dblclick', function (event) {
        if (event.target.closest('svg')) {
            const nodeElement = event.target.closest('.node');

            if (nodeElement && nodeElement.id && tables[nodeElement.id]) {
                const tableId = nodeElement.id;
                event.preventDefault();
                event.stopPropagation();

                // Get all connected tables and edges
                const connectedEdges = tables[tableId].edges;
                const connectedTables = [tableId, ...connectedEdges.map(edgeId => edges[edgeId].tables).flat()];
                const uniqueTables = [...new Set(connectedTables)];

                // Calculate bounding box for all connected nodes
                let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
                let foundAny = false;

                uniqueTables.forEach(id => {
                    const element = document.getElementById(id);
                    if (element) {
                        try {
                            const bbox = element.getBBox();
                            minX = Math.min(minX, bbox.x);
                            minY = Math.min(minY, bbox.y);
                            maxX = Math.max(maxX, bbox.x + bbox.width);
                            maxY = Math.max(maxY, bbox.y + bbox.height);
                            foundAny = true;
                        } catch (e) {
                            console.warn('Could not get bbox for', id);
                        }
                    }
                });

                if (foundAny) {
                    // Add padding around the bounding box
                    const padding = 100;
                    minX -= padding;
                    minY -= padding;
                    maxX += padding;
                    maxY += padding;

                    // Calculate center and dimensions
                    const centerX = (minX + maxX) / 2;
                    const centerY = (minY + maxY) / 2;
                    const width = maxX - minX;
                    const height = maxY - minY;

                    // Calculate zoom level to fit the bounding box in viewport
                    const viewport = getViewportDimensions();
                    const scaleX = viewport.width / width;
                    const scaleY = viewport.height / height;
                    const newScale = Math.min(scaleX, scaleY, 2.0) * 0.75; // Max 2x zoom, 75% to leave more margin

                    // Zoom to the calculated center and scale
                    zoomToPoint(centerX, centerY, newScale);
                }
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
    /**
     * Initialize close button to shut down server and close window
     */
    function initializeCloseButton() {
        const closeBtn = document.getElementById('close-server-btn');
        if (!closeBtn) return;

        closeBtn.addEventListener('click', async () => {
            closeBtn.disabled = true;
            closeBtn.style.opacity = '0.5';

            try {
                // Try to shut down server gracefully
                await fetch('/api/shutdown', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });

                // Give server time to shut down
                setTimeout(() => {
                    // Close the window/tab
                    window.close();

                    // If window.close() didn't work (some browsers prevent it),
                    // show a message
                    setTimeout(() => {
                        alert('Server stopped. You can now close this window.');
                    }, 500);
                }, 500);
            } catch (error) {
                // Server might already be down, just close the window
                window.close();
                setTimeout(() => {
                    alert('You can now close this window.');
                }, 500);
            }
        });
    }

    /**
     * Initialize collapsible sections in the metadata panel
     */
    function initializeCollapsibleSections() {
        // Function to make a section collapsible
        const makeCollapsible = (headerId, contentId) => {
            const header = document.getElementById(headerId);
            const content = document.getElementById(contentId);

            if (!header || !content) return;

            header.addEventListener('click', () => {
                const isHidden = content.style.display === 'none';
                const icon = header.querySelector('.collapse-icon');

                if (isHidden) {
                    // Expand
                    content.style.display = 'block';
                    if (icon) icon.textContent = '▼';
                } else {
                    // Collapse
                    content.style.display = 'none';
                    if (icon) icon.textContent = '▶';
                }
            });
        };

        // Initialize all collapsible sections
        makeCollapsible('source-info-header', 'source-info-content');
        makeCollapsible('schema-stats-header', 'schema-stats-content');
        makeCollapsible('graphviz-settings-header', 'graphviz-settings-content');
        makeCollapsible('db-config-header', 'db-config-content');
    }

    /**
     * Initialize Graphviz settings apply button
     */
    function initializeGraphvizSettings() {
        const applyBtn = document.getElementById('apply-graphviz-settings-btn');
        const optimizeBtn = document.getElementById('optimize-layout-btn');
        const statusDiv = document.getElementById('apply-settings-status');
        const optimizeStatusDiv = document.getElementById('optimize-status');

        if (!applyBtn) return;

        const showStatus = (message, type, statusElement = statusDiv) => {
            if (!statusElement) return;
            statusElement.textContent = message;
            statusElement.style.display = 'block';
            statusElement.className = type; // 'success', 'error', 'info'

            // Set background color based on type
            if (type === 'success') {
                statusElement.style.background = 'rgba(76, 175, 80, 0.1)';
                statusElement.style.border = '1px solid rgba(76, 175, 80, 0.3)';
                statusElement.style.color = '#2e7d32';
            } else if (type === 'error') {
                statusElement.style.background = 'rgba(244, 67, 54, 0.1)';
                statusElement.style.border = '1px solid rgba(244, 67, 54, 0.3)';
                statusElement.style.color = '#c62828';
            } else {
                statusElement.style.background = 'rgba(33, 150, 243, 0.1)';
                statusElement.style.border = '1px solid rgba(33, 150, 243, 0.3)';
                statusElement.style.color = '#1565c0';
            }
        };

        // Optimize Layout button handler
        if (optimizeBtn) {
            optimizeBtn.addEventListener('click', async () => {
                optimizeBtn.disabled = true;
                optimizeBtn.textContent = '🤖 Analyzing...';
                showStatus('AI is analyzing your schema for optimal layout...', 'info', optimizeStatusDiv);

                try {
                    // Collect CURRENT settings from UI (user's current defaults)
                    const currentSettings = {
                        packmode: document.getElementById('gv-packmode')?.value || 'array',
                        rankdir: document.getElementById('gv-rankdir')?.value || 'TB',
                        esep: document.getElementById('gv-esep')?.value || '8',
                        node_sep: document.getElementById('gv-node-sep')?.value || '0.5',
                        rank_sep: document.getElementById('gv-rank-sep')?.value || '1.2',
                        fontname: document.getElementById('gv-fontname')?.value || 'Arial',
                        fontsize: parseInt(document.getElementById('gv-fontsize')?.value) || 18,
                        node_fontsize: parseInt(document.getElementById('gv-node-fontsize')?.value) || 14,
                        edge_fontsize: parseInt(document.getElementById('gv-edge-fontsize')?.value) || 12,
                        node_style: document.getElementById('gv-node-style')?.value || 'rounded,filled',
                        node_shape: document.getElementById('gv-node-shape')?.value || 'rect'
                    };

                    // Send request to optimize layout, including current settings as baseline
                    const response = await fetch('/api/optimize_layout', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            current_settings: currentSettings
                        })
                    });

                    const result = await response.json();

                    if (result.success && result.optimized_settings) {
                        // Apply optimized settings to UI
                        const settings = result.optimized_settings;
                        if (settings.packmode) document.getElementById('gv-packmode').value = settings.packmode;
                        if (settings.rankdir) document.getElementById('gv-rankdir').value = settings.rankdir;
                        if (settings.esep) document.getElementById('gv-esep').value = settings.esep;
                        if (settings.node_sep) document.getElementById('gv-node-sep').value = settings.node_sep;
                        if (settings.rank_sep) document.getElementById('gv-rank-sep').value = settings.rank_sep;
                        if (settings.fontname) document.getElementById('gv-fontname').value = settings.fontname;
                        if (settings.fontsize) document.getElementById('gv-fontsize').value = settings.fontsize;
                        if (settings.node_fontsize) document.getElementById('gv-node-fontsize').value = settings.node_fontsize;
                        if (settings.edge_fontsize) document.getElementById('gv-edge-fontsize').value = settings.edge_fontsize;
                        if (settings.node_style) document.getElementById('gv-node-style').value = settings.node_style;
                        if (settings.node_shape) document.getElementById('gv-node-shape').value = settings.node_shape;

                        const explanation = result.explanation || 'Optimized settings applied!';
                        showStatus(`✨ ${explanation} Click "Apply Settings" to regenerate.`, 'success', optimizeStatusDiv);
                        optimizeBtn.textContent = '🤖 AI-Optimize Layout';
                        optimizeBtn.disabled = false;

                        // Highlight the Apply button to indicate user should click it
                        applyBtn.style.animation = 'pulse 1.5s ease-in-out 3';
                    } else {
                        showStatus(`Error: ${result.message || 'Failed to optimize layout'}`, 'error', optimizeStatusDiv);
                        optimizeBtn.textContent = '🤖 AI-Optimize Layout';
                        optimizeBtn.disabled = false;
                    }
                } catch (error) {
                    console.error('Error optimizing layout:', error);
                    showStatus(`Error: ${error.message}`, 'error', optimizeStatusDiv);
                    optimizeBtn.textContent = '🤖 AI-Optimize Layout';
                    optimizeBtn.disabled = false;
                }
            });
        }

        // Check if we're viewing a focused ERD and show/hide the appropriate button
        const applyFocusedBtn = document.getElementById('apply-focused-settings-btn');
        const applyRegularBtn = document.getElementById('apply-graphviz-settings-btn');
        if (applyFocusedBtn && graphData.includedTables) {
            // We're viewing a focused ERD - show the focused button, hide the regular button
            applyFocusedBtn.style.display = 'block';
            if (applyRegularBtn) {
                applyRegularBtn.style.display = 'none';
            }
        }

        // Apply Focused Settings button handler
        if (applyFocusedBtn) {
            applyFocusedBtn.addEventListener('click', async () => {
                applyFocusedBtn.disabled = true;
                applyFocusedBtn.textContent = '⏳ Applying Settings...';
                showStatus('Regenerating focused ERD with new settings...', 'info');

                try {
                    // Collect Graphviz settings from UI
                    const graphvizSettings = {
                        packmode: document.getElementById('gv-packmode')?.value || 'array',
                        rankdir: document.getElementById('gv-rankdir')?.value || 'TB',
                        esep: document.getElementById('gv-esep')?.value || '8',
                        node_sep: document.getElementById('gv-node-sep')?.value || '0.5',
                        rank_sep: document.getElementById('gv-rank-sep')?.value || '1.2',
                        fontname: document.getElementById('gv-fontname')?.value || 'Arial',
                        fontsize: parseInt(document.getElementById('gv-fontsize')?.value) || 18,
                        node_fontsize: parseInt(document.getElementById('gv-node-fontsize')?.value) || 14,
                        edge_fontsize: parseInt(document.getElementById('gv-edge-fontsize')?.value) || 12,
                        node_style: document.getElementById('gv-node-style')?.value || 'rounded,filled',
                        node_shape: document.getElementById('gv-node-shape')?.value || 'rect'
                    };

                    // Send request to regenerate focused ERD with the same tables
                    const response = await fetch('/api/apply_focused_settings', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            table_ids: graphData.includedTables,
                            graphviz_settings: graphvizSettings
                        })
                    });

                    const result = await response.json();

                    if (result.success) {
                        showStatus('Focused ERD settings applied! Reloading...', 'success');

                        // Reload the page with the updated focused ERD
                        setTimeout(() => {
                            window.location.href = `/${result.new_file}`;
                        }, 500);
                    } else {
                        showStatus(`Error: ${result.message || 'Failed to apply settings'}`, 'error');
                        applyFocusedBtn.textContent = '🔍 Apply Settings & Regenerate Focused ERD';
                        applyFocusedBtn.disabled = false;
                    }
                } catch (error) {
                    console.error('Error applying focused settings:', error);
                    showStatus(`Error: ${error.message}`, 'error');
                    applyFocusedBtn.textContent = '🔍 Apply Settings & Regenerate Focused ERD';
                    applyFocusedBtn.disabled = false;
                }
            });
        }

        // Apply Settings button handler (full ERD regeneration)
        applyBtn.addEventListener('click', async () => {
            applyBtn.disabled = true;
            applyBtn.textContent = '⏳ Applying Settings...';
            showStatus('Regenerating ERD with new settings...', 'info');

            try {
                // Collect Graphviz settings from UI
                const graphvizSettings = {
                    packmode: document.getElementById('gv-packmode')?.value || 'array',
                    rankdir: document.getElementById('gv-rankdir')?.value || 'TB',
                    esep: document.getElementById('gv-esep')?.value || '8',
                    node_sep: document.getElementById('gv-node-sep')?.value || '0.5',
                    rank_sep: document.getElementById('gv-rank-sep')?.value || '1.2',
                    fontname: document.getElementById('gv-fontname')?.value || 'Arial',
                    fontsize: parseInt(document.getElementById('gv-fontsize')?.value) || 18,
                    node_fontsize: parseInt(document.getElementById('gv-node-fontsize')?.value) || 14,
                    edge_fontsize: parseInt(document.getElementById('gv-edge-fontsize')?.value) || 12,
                    node_style: document.getElementById('gv-node-style')?.value || 'rounded,filled',
                    node_shape: document.getElementById('gv-node-shape')?.value || 'rect'
                };

                // Send request to apply settings
                const response = await fetch('/api/apply_graphviz_settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ graphviz_settings: graphvizSettings })
                });

                const result = await response.json();

                if (result.success) {
                    showStatus('Settings applied! Reloading...', 'success');

                    // Reload the page with the new ERD
                    if (result.new_file) {
                        // Open new file in this window
                        setTimeout(() => {
                            window.location.href = `/${result.new_file}`;
                        }, 500);
                    } else {
                        // Just reload the current page
                        setTimeout(() => {
                            window.location.reload();
                        }, 500);
                    }
                } else {
                    showStatus(`Error: ${result.message || 'Failed to apply settings'}`, 'error');
                    applyBtn.textContent = '🔄 Apply Settings & Regenerate ERD';
                    applyBtn.disabled = false;
                }
            } catch (error) {
                console.error('Error applying settings:', error);
                showStatus(`Error: ${error.message}`, 'error');
                applyBtn.textContent = '🔄 Apply Settings & Regenerate ERD';
                applyBtn.disabled = false;
            }
        });
    }

    /**
     * Initialize database connection controls (test and reload buttons)
     */
    function initializeDatabaseControls() {
        const testBtn = document.getElementById('test-connection-btn');
        const reloadBtn = document.getElementById('reload-from-db-btn');
        const statusDiv = document.getElementById('connection-status');
        
        // File-based controls
        const reloadFileBtn = document.getElementById('reload-from-file-btn');
        const fileStatusDiv = document.getElementById('file-status');

        // Handle file-based reload
        if (reloadFileBtn) {
            reloadFileBtn.addEventListener('click', async () => {
                const filepath = document.getElementById('file-path')?.value;
                
                if (!filepath) {
                    showFileStatus('Please enter a file path', 'error');
                    return;
                }
                
                reloadFileBtn.disabled = true;
                reloadFileBtn.textContent = '🔄 Loading...';
                showFileStatus('Reloading schema from file...', 'info');
                
                try {
                    // Try to call server API (will work if opened with --view)
                    const response = await fetch('/api/reload-erd', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ filepath })
                    });

                    if (response.ok) {
                        const result = await response.json();
                        if (result.success && result.reload) {
                            showFileStatus('✅ ERD reloaded! Refreshing page...', 'success');
                            // Reload the page after a brief delay
                            setTimeout(() => {
                                window.location.reload();
                            }, 1000);
                        } else if (result.success) {
                            showFileStatus('✅ ERD reloaded successfully!', 'success');
                        } else {
                            showFileStatus(`❌ Reload failed: ${result.message}`, 'error');
                        }
                    } else {
                        const error = await response.json();
                        showFileStatus(`❌ Reload failed: ${error.message || 'Unknown error'}`, 'error');
                    }
                    
                    reloadFileBtn.disabled = false;
                    reloadFileBtn.textContent = '🔄 Reload from File';
                } catch (error) {
                    // Server not available - provide instructions
                    showFileStatus(
                        `ℹ️ Server not available. To reload interactively, run:\n\n` +
                        `pypgsvg ${filepath} --view`,
                        'info'
                    );
                    reloadFileBtn.disabled = false;
                    reloadFileBtn.textContent = '🔄 Reload from File';
                }
            });
        }
        
        function showFileStatus(message, type) {
            if (!fileStatusDiv) return;
            
            fileStatusDiv.textContent = message;
            fileStatusDiv.className = type;
            fileStatusDiv.style.display = 'block';

            // Auto-hide success/error messages after 5 seconds
            if (type === 'success' || type === 'error') {
                setTimeout(() => {
                    fileStatusDiv.style.display = 'none';
                }, 5000);
            }
        }

        // Define showConnectionStatus function first so it's available to all handlers
        function showConnectionStatus(message, type) {
            if (!statusDiv) return;
            
            statusDiv.textContent = message;
            statusDiv.className = type;
            statusDiv.style.display = 'block';

            // Auto-hide success/error messages after 5 seconds
            if (type === 'success' || type === 'error') {
                setTimeout(() => {
                    statusDiv.style.display = 'none';
                }, 5000);
            }
        }

        if (!testBtn || !reloadBtn) {
            // No database controls present (file-based mode handled above)
            return;
        }

        // Shared state for database change tracking
        let lastSelectedDatabase = document.getElementById('db-database')?.value || '';
        
        // Refresh databases button handler
        const refreshDbBtn = document.getElementById('refresh-databases-btn');
        if (refreshDbBtn) {
            refreshDbBtn.addEventListener('click', async () => {
                const host = document.getElementById('db-host')?.value;
                const port = document.getElementById('db-port')?.value;
                const user = document.getElementById('db-user')?.value;
                const password = document.getElementById('db-password')?.value;
                const dbSelect = document.getElementById('db-database');
                
                if (!dbSelect) {
                    console.error('Database select element not found!');
                    showConnectionStatus('Error: Database dropdown not found', 'error');
                    return;
                }
                
                // Save current selection BEFORE any operations
                const currentDb = dbSelect.value || '';
                console.log('Saving current database before refresh:', currentDb);
                console.log('dbSelect element:', dbSelect);
                console.log('dbSelect options before clear:', dbSelect.options.length);
                
                if (!host || !port || !user) {
                    showConnectionStatus('Please fill in host, port, and user fields first', 'error');
                    return;
                }
                
                refreshDbBtn.disabled = true;
                refreshDbBtn.textContent = '🔄 Loading...';
                showConnectionStatus('Querying databases...', 'info');
                
                try {
                    const response = await fetch('/api/list-databases', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ host, port, user, password })
                    });
                    
                    if (response.ok) {
                        const result = await response.json();
                        console.log('Database query result:', result);
                        if (result.success && result.databases && Array.isArray(result.databases)) {
                            console.log('Current database to restore:', currentDb);
                            console.log('Available databases:', result.databases);
                            console.log('Number of databases returned:', result.databases.length);
                            
                            // Clear and populate dropdown (avoid innerHTML in SVG context)
                            while (dbSelect.firstChild) {
                                dbSelect.removeChild(dbSelect.firstChild);
                            }
                            console.log('Cleared dropdown, options count:', dbSelect.options.length);
                            
                            result.databases.forEach((db, index) => {
                                const option = document.createElementNS('http://www.w3.org/1999/xhtml', 'option');
                                option.value = db;
                                option.textContent = db;
                                if (db === currentDb) {
                                    option.selected = true;
                                    console.log('Marking database as selected:', db);
                                }
                                dbSelect.appendChild(option);
                                console.log(`Added option ${index + 1}: ${db}`);
                            });
                            
                            console.log('Dropdown populated with', dbSelect.options.length, 'databases');
                            console.log('Selected index:', dbSelect.selectedIndex);
                            console.log('Selected value:', dbSelect.value);
                            
                            // Update the shared last selected database state
                            lastSelectedDatabase = dbSelect.value;
                            console.log('Updated lastSelectedDatabase to:', lastSelectedDatabase);
                            
                            showConnectionStatus(`✅ Found ${result.databases.length} databases`, 'success');
                        } else {
                            showConnectionStatus(`❌ Failed to query databases: ${result.message}`, 'error');
                        }
                    } else {
                        const error = await response.json();
                        showConnectionStatus(`❌ Failed to query databases: ${error.message}`, 'error');
                    }
                } catch (error) {
                    showConnectionStatus(
                        `ℹ️ Server not available. To query databases, open with --view mode`,
                        'info'
                    );
                }
                
                refreshDbBtn.disabled = false;
                refreshDbBtn.textContent = '🔄 Refresh Databases';
            });
        }
        
        // Database selection change handler - auto-reload ERD when database changes
        const dbSelect = document.getElementById('db-database');
        
        // Test connection button handler
        testBtn.addEventListener('click', async () => {
            const host = document.getElementById('db-host')?.value;
            const port = document.getElementById('db-port')?.value;
            const database = document.getElementById('db-database')?.value;
            const user = document.getElementById('db-user')?.value;
            const password = document.getElementById('db-password')?.value;

            if (!host || !database || !user) {
                showConnectionStatus('Please fill in host, database, and user fields', 'error');
                return;
            }

            // Disable button and show testing status
            testBtn.disabled = true;
            testBtn.textContent = '🔄 Testing...';
            showConnectionStatus('Testing connection...', 'info');

            try {
                // Try to call server API (will work if opened with --view)
                const response = await fetch('/api/test-db-connection', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ host, port, database, user, password })
                });

                if (response.ok) {
                    const result = await response.json();
                    if (result.success) {
                        showConnectionStatus('✅ Connection successful!', 'success');
                    } else {
                        showConnectionStatus(`❌ Connection failed: ${result.message}`, 'error');
                    }
                } else {
                    const error = await response.json();
                    showConnectionStatus(`❌ Connection failed: ${error.message || 'Unknown error'}`, 'error');
                }
                
                testBtn.disabled = false;
                testBtn.textContent = '🔍 Test Connection';
            } catch (error) {
                // Server not available - provide instructions
                showConnectionStatus(
                    `ℹ️ Server not available. To test connections interactively, open the ERD with:\n\n` +
                    `pypgsvg -H ${host} -p ${port} -d ${database} -u ${user} --view`,
                    'info'
                );
                testBtn.disabled = false;
                testBtn.textContent = '🔍 Test Connection';
            }
        });

        // Reload ERD button handler
        reloadBtn.addEventListener('click', async () => {
            const host = document.getElementById('db-host')?.value;
            const port = document.getElementById('db-port')?.value;
            const database = document.getElementById('db-database')?.value;
            const user = document.getElementById('db-user')?.value;
            const password = document.getElementById('db-password')?.value;

            if (!host || !database || !user) {
                showConnectionStatus('Please fill in host, database, and user fields', 'error');
                return;
            }

            // Disable button and show reloading status
            reloadBtn.disabled = true;
            reloadBtn.textContent = '🔄 Loading...';
            showConnectionStatus('Reloading schema from database...', 'info');

            try {
                // Try to call server API (will work if opened with --view)
                const response = await fetch('/api/reload-erd', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ host, port, database, user, password })
                });

                if (response.ok) {
                    const result = await response.json();
                    if (result.success && result.reload) {
                        showConnectionStatus('✅ ERD regenerated! Opening new view...', 'success');
                        // Open the regenerated ERD in a new window and close current one
                        setTimeout(() => {
                            // Use new filename if provided, otherwise use current URL
                            const newUrl = result.new_file
                                ? window.location.origin + '/' + result.new_file
                                : window.location.href;
                            console.log('Opening new ERD at:', newUrl);
                            window.open(newUrl, '_blank');
                            setTimeout(() => window.close(), 500);
                        }, 1000);
                    } else if (result.success) {
                        showConnectionStatus('✅ ERD reloaded successfully!', 'success');
                    } else {
                        showConnectionStatus(`❌ Reload failed: ${result.message}`, 'error');
                    }
                } else {
                    const error = await response.json();
                    showConnectionStatus(`❌ Reload failed: ${error.message || 'Unknown error'}`, 'error');
                }
                
                reloadBtn.disabled = false;
                reloadBtn.textContent = '🔄 Reload ERD';
            } catch (error) {
                // Server not available - provide command-line instructions
                const outputFile = 'updated_erd';
                const command = `pypgsvg -H ${host} -p ${port} -d ${database} -u ${user} --view`;
                
                showConnectionStatus(
                    `ℹ️ Server not available. To reload interactively, run:\n\n${command}\n\n` +
                    `Or to just generate without opening: pypgsvg -H ${host} -p ${port} -d ${database} -u ${user} -o ${outputFile}`,
                    'info'
                );
                
                reloadBtn.disabled = false;
                reloadBtn.textContent = '🔄 Reload ERD';
            }
        });
    }

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
            let isSelectionMode = tablesToShow && tablesToShow.length > 0;
            
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
            
            // Enable multiple selection mode when showing selected tables
            if (isSelectionMode) {
                tableSelector.setAttribute('multiple', 'multiple');
                tableSelector.setAttribute('size', Math.min(tablesToDisplay.length, 8)); // Show up to 8 items
                tableSelector.style.height = 'auto';
            } else {
                tableSelector.removeAttribute('multiple');
                tableSelector.removeAttribute('size');
                tableSelector.style.height = '';
                
                // Add the default option only in single-select mode
                const defaultOption = document.createElementNS('http://www.w3.org/1999/xhtml', 'option');
                defaultOption.value = '';
                defaultOption.textContent = optionText;
                tableSelector.appendChild(defaultOption);
                console.log('Added default option, current option count:', tableSelector.options.length);
            }
            
            // Add table options
            let addedCount = 0;
            tablesToDisplay.sort().forEach((tableId, index) => {
                const option = document.createElementNS('http://www.w3.org/1999/xhtml', 'option');
                option.value = tableId;
                option.textContent = tableId;
                
                // In multi-select mode, pre-select all options
                if (isSelectionMode) {
                    option.selected = true;
                }
                
                tableSelector.appendChild(option);
                addedCount++;
                
                // Log progress for first few and last few
                if (index < 3 || index >= tablesToDisplay.length - 3) {
                    console.log(`Added option ${index + 1}: ${tableId}, total options now: ${tableSelector.options.length}`);
                }
            });

            console.log('Populated table selector with', tablesToDisplay.length, 'tables, final option count:', tableSelector.options.length);
            console.log('Multi-select mode:', isSelectionMode);
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

    // View Selector functionality (identical to Table Selector but for views)
    function initializeViewSelector() {
        const viewSelector = document.getElementById('view-selector');
        if (!viewSelector) {
            console.warn('View selector element not found');
            return;
        }

        // Make sure we have access to the views data
        if (!views || Object.keys(views).length === 0) {
            console.log('No views data available for view selector');
            // Still populate with empty selector
            const defaultOption = document.createElementNS('http://www.w3.org/1999/xhtml', 'option');
            defaultOption.value = '';
            defaultOption.textContent = 'No Views (0)';
            viewSelector.appendChild(defaultOption);
            return;
        }

        console.log('Initializing view selector with', Object.keys(views).length, 'views');

        // Function to populate the selector with views
        function populateViewSelector(viewsToShow = null) {
            // Clear existing options
            while (viewSelector.firstChild) {
                viewSelector.removeChild(viewSelector.firstChild);
            }
            
            let viewsToDisplay;
            let optionText;
            let isSelectionMode = viewsToShow && viewsToShow.length > 0;
            
            if (!viewsToShow) {
                // Show all views
                viewsToDisplay = Object.keys(views);
                optionText = `All Views (${viewsToDisplay.length})`;
            } else {
                // Show only highlighted/selected views
                viewsToDisplay = viewsToShow;
                optionText = `Selected Views (${viewsToDisplay.length})`;
            }
            
            console.log('About to populate view selector with options:', optionText);
            
            // Enable multiple selection mode when showing selected views
            if (isSelectionMode) {
                viewSelector.setAttribute('multiple', 'multiple');
                viewSelector.setAttribute('size', Math.min(viewsToDisplay.length, 8)); // Show up to 8 items
                viewSelector.style.height = 'auto';
            } else {
                viewSelector.removeAttribute('multiple');
                viewSelector.removeAttribute('size');
                viewSelector.style.height = '';
                
                // Add the default option only in single-select mode
                const defaultOption = document.createElementNS('http://www.w3.org/1999/xhtml', 'option');
                defaultOption.value = '';
                defaultOption.textContent = optionText;
                viewSelector.appendChild(defaultOption);
                console.log('Added default option, current option count:', viewSelector.options.length);
            }
            
            // Add view options
            let addedCount = 0;
            viewsToDisplay.sort().forEach((viewId, index) => {
                const option = document.createElementNS('http://www.w3.org/1999/xhtml', 'option');
                option.value = viewId;
                option.textContent = views[viewId].name || viewId;
                
                // In multi-select mode, pre-select all options
                if (isSelectionMode) {
                    option.selected = true;
                }
                
                viewSelector.appendChild(option);
                addedCount++;
                
                // Log progress for first few and last few
                if (index < 3 || index >= viewsToDisplay.length - 3) {
                    console.log(`Added view option ${index + 1}: ${viewId}, total options now: ${viewSelector.options.length}`);
                }
            });

            console.log('Populated view selector with', viewsToDisplay.length, 'views, final option count:', viewSelector.options.length);
            console.log('Multi-select mode:', isSelectionMode);
        }

        // Function to update selector based on current highlights
        function updateViewSelector() {
            const highlightedViews = document.querySelectorAll('.node.highlighted');
            const viewIds = Array.from(highlightedViews)
                .map(el => el.id)
                .filter(id => views[id]);
            
            if (viewIds.length > 0) {
                populateViewSelector(viewIds);
            } else {
                populateViewSelector(); // Show all views
            }
        }

        // Handle selector change
        viewSelector.addEventListener('change', function() {
            const selectedViewId = this.value;
            if (!selectedViewId) return;

            // Clear existing highlights
            clearAllHighlights();

            if (views[selectedViewId]) {
                // Set this view as highlighted
                highlightedElementId = selectedViewId;
                
                // Views might be in the tables structure too (for SVG rendering)
                // Try to highlight it if it exists as a node
                const viewElement = document.getElementById(selectedViewId);
                if (viewElement) {
                    // Get connected edges if any (views may not have connections)
                    const connectedEdges = tables[selectedViewId] ? tables[selectedViewId].edges : [];
                    const connectedTables = [selectedViewId];
                    if (connectedEdges.length > 0) {
                        connectedEdges.forEach(edgeId => {
                            if (edges[edgeId]) {
                                connectedTables.push(...edges[edgeId].tables);
                            }
                        });
                    }
                    const uniqueTables = [...new Set(connectedTables)];
                    
                    // Highlight the view and its connections
                    highlightElements(uniqueTables, connectedEdges);
                    
                    // Show selection window
                    showSelectionWindow(uniqueTables, connectedEdges, null);
                    
                    // Focus on the selected view
                    focusOnView(selectedViewId);
                }
            }
            
            // Reset selector to default option
            this.selectedIndex = 0;
        });

        // Prevent drag events from interfering with view selector interaction
        viewSelector.addEventListener('mousedown', function(event) {
            event.stopPropagation();
        });

        viewSelector.addEventListener('click', function(event) {
            event.stopPropagation();
        });

        viewSelector.addEventListener('focus', function(event) {
            event.stopPropagation();
        });

        // Function to focus on a view (zoom to it)
        function focusOnView(viewId) {
            const viewElement = document.getElementById(viewId);
            if (!viewElement) return;

            try {
                // Get the view's SVG bounding box
                const bbox = viewElement.getBBox();
                
                // Calculate the center of the view in SVG coordinates
                const viewCenterX = bbox.x + bbox.width / 2;
                const viewCenterY = bbox.y + bbox.height / 2;
                
                // Zoom to the view with a reasonable zoom level
                zoomToPoint(viewCenterX, viewCenterY, Math.max(userS, 1.2));
            } catch (error) {
                console.warn('Could not focus on view:', viewId, error);
            }
        }

        // Store the update function globally so it can be called from other parts
        window.updateViewSelector = updateViewSelector;

        // Initial population
        populateViewSelector();
    }

    // Function Selector functionality
    function initializeFunctionSelector() {
        const functionSelector = document.getElementById('function-selector');
        if (!functionSelector) {
            console.warn('Function selector element not found');
            return;
        }

        // Make sure we have access to the functions data
        const functions = graphData.functions || {};
        if (!functions || Object.keys(functions).length === 0) {
            console.log('No functions data available for function selector');
            // Still populate with empty selector
            const defaultOption = document.createElementNS('http://www.w3.org/1999/xhtml', 'option');
            defaultOption.value = '';
            defaultOption.textContent = 'No Functions (0)';
            functionSelector.appendChild(defaultOption);
            return;
        }

        console.log('Initializing function selector with', Object.keys(functions).length, 'functions');

        // Function to populate the selector with functions
        function populateFunctionSelector() {
            // Clear existing options
            while (functionSelector.firstChild) {
                functionSelector.removeChild(functionSelector.firstChild);
            }

            const functionsToDisplay = Object.keys(functions);
            const optionText = `All Functions (${functionsToDisplay.length})`;

            console.log('About to populate function selector with options:', optionText);

            // Add the default option
            const defaultOption = document.createElementNS('http://www.w3.org/1999/xhtml', 'option');
            defaultOption.value = '';
            defaultOption.textContent = optionText;
            functionSelector.appendChild(defaultOption);

            // Add function options (sorted)
            functionsToDisplay.sort().forEach((functionId, index) => {
                const option = document.createElementNS('http://www.w3.org/1999/xhtml', 'option');
                option.value = functionId;
                option.textContent = functions[functionId].name || functionId;
                functionSelector.appendChild(option);

                // Log progress for first few and last few
                if (index < 3 || index >= functionsToDisplay.length - 3) {
                    console.log(`Added function option ${index + 1}: ${functionId}, total options now: ${functionSelector.options.length}`);
                }
            });

            console.log('Populated function selector with', functionsToDisplay.length, 'functions, final option count:', functionSelector.options.length);
        }

        // Handle selector change
        functionSelector.addEventListener('change', function() {
            const selectedFunctionId = this.value;
            if (!selectedFunctionId) return;

            const functionData = functions[selectedFunctionId];
            if (functionData) {
                // Find all triggers that use this function
                const triggersUsingFunction = [];
                const tablesUsingFunction = [];

                for (const [tableId, tableData] of Object.entries(graphData.tables || {})) {
                    if (tableData.triggers && tableData.triggers.length > 0) {
                        tableData.triggers.forEach(trigger => {
                            const triggerFunctionName = sanitizeLabel(trigger.function);
                            if (triggerFunctionName === selectedFunctionId) {
                                triggersUsingFunction.push({
                                    tableName: tableData.originalName || tableId,
                                    triggerName: trigger.trigger_name,
                                    event: trigger.event
                                });
                                if (!tablesUsingFunction.includes(tableId)) {
                                    tablesUsingFunction.push(tableId);
                                }
                            }
                        });
                    }
                }

                // Show function definition window with usage info
                showFunctionWindow(functionData, triggersUsingFunction, tablesUsingFunction);
            }

            // Reset selector to default option
            this.selectedIndex = 0;
        });

        // Prevent drag events from interfering with function selector interaction
        functionSelector.addEventListener('mousedown', function(event) {
            event.stopPropagation();
        });

        functionSelector.addEventListener('click', function(event) {
            event.stopPropagation();
        });

        functionSelector.addEventListener('focus', function(event) {
            event.stopPropagation();
        });

        // Initial population
        populateFunctionSelector();
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

            updateViewportIndicator();

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
                    zoomItem.textContent = `Browser Zoom: ${browserZoom}%`;

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

            // Initialize view selector
            initializeViewSelector();

            // Initialize function selector
            initializeFunctionSelector();

            // Initialize database connection controls
            initializeDatabaseControls();

            // Initialize close server button
            initializeCloseButton();

            // Initialize collapsible sections
            initializeCollapsibleSections();

            // Initialize Graphviz settings
            initializeGraphvizSettings();

            // Parse and apply URL parameters after all containers are initialized
            parseUrlParameters();

            // Check if this is a focused ERD page and auto-expand settings + zoom to fit
            if (window.location.href.includes('focused')) {
                setTimeout(() => {
                    // Expand the Graphviz settings if metadata container is visible
                    const metadataContainer = document.getElementById('metadata-container');
                    const graphvizHeader = document.getElementById('graphviz-settings-header');
                    const graphvizContent = document.getElementById('graphviz-settings-content');
                    const isMetadataVisible = metadataContainer &&
                        metadataContainer.style.display !== 'none' &&
                        window.getComputedStyle(metadataContainer).display !== 'none';

                    if (isMetadataVisible && graphvizHeader && graphvizContent) {
                        // Expand the Graphviz settings section
                        graphvizContent.style.display = 'block';
                        const collapseIcon = graphvizHeader.querySelector('.collapse-icon');
                        if (collapseIcon) {
                            collapseIcon.textContent = '▼';
                        }
                    }

                    // Auto-expand the focused ERD settings panel in selection container
                    const focusedSettingsPanel = document.getElementById('focused-erd-settings');
                    const focusedErdBtn = document.getElementById('generate-focused-erd-btn');
                    if (focusedSettingsPanel && focusedErdBtn) {
                        focusedSettingsPanel.style.maxHeight = '800px';
                        focusedErdBtn.textContent = '🔼 Hide Settings';
                    }

                    // Zoom to fit the entire ERD in the viewable area
                    if (mainGroup) {
                        const mainBounds = mainGroup.getBBox();
                        const viewport = getViewportDimensions();

                        // Calculate scale to fit the entire ERD with some padding
                        const padding = 50; // pixels of padding
                        const scaleX = (viewport.width - padding * 2) / mainBounds.width;
                        const scaleY = (viewport.height - padding * 2) / mainBounds.height;
                        const scale = Math.min(scaleX, scaleY, 1.0); // Don't zoom in beyond 100%

                        // Calculate center point
                        const centerX = mainBounds.x + mainBounds.width / 2;
                        const centerY = mainBounds.y + mainBounds.height / 2;

                        // Apply zoom to fit
                        zoomToPoint(centerX, centerY, scale);
                    }
                }, 500); // Delay to ensure everything is loaded
            }
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
            }, 250);
        });
    });

    // Backup initialization for cases when DOMContentLoaded already fired
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        setTimeout(initializeSvgView, 300);
    }
    
    // Notify server when browser window closes (for --view mode)
    window.addEventListener('beforeunload', () => {
        // Send beacon to server to shut down
        // Using sendBeacon for reliability on page unload
        if (navigator.sendBeacon) {
            navigator.sendBeacon('/api/shutdown');
        } else {
            // Fallback for browsers without sendBeacon
            fetch('/api/shutdown', {
                method: 'POST',
                keepalive: true
            }).catch(() => {/* Server may already be shutting down */});
        }
    });
});
