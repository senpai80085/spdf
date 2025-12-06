import { invoke } from '@tauri-apps/api/core';
import { open } from '@tauri-apps/plugin-dialog';
import * as pdfjsLib from 'pdfjs-dist';

// Configure PDF.js worker (use local copy)
pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.js';

// State
let pdfDoc: pdfjsLib.PDFDocumentProxy | null = null;
let currentPage = 1;
let zoomLevel = 1.0;
let permissions = {
  allow_print: false,
  allow_copy: false,
};
let watermarkText = '';

// Elements
const canvas = document.getElementById('pdf-canvas') as HTMLCanvasElement;
const ctx = canvas.getContext('2d')!;
const openFileBtn = document.getElementById('open-file-btn') as HTMLButtonElement;
const prevPageBtn = document.getElementById('prev-page') as HTMLButtonElement;
const nextPageBtn = document.getElementById('next-page') as HTMLButtonElement;
const zoomInBtn = document.getElementById('zoom-in') as HTMLButtonElement;
const zoomOutBtn = document.getElementById('zoom-out') as HTMLButtonElement;
const pageInfo = document.getElementById('page-info')!;
const zoomLevelSpan = document.getElementById('zoom-level')!;
const docIdSpan = document.getElementById('doc-id')!;
const userStatus = document.getElementById('user-status')!;
const statusMessage = document.getElementById('status-message')!;
const watermarkOverlay = document.getElementById('watermark-overlay')!;
const loginModal = document.getElementById('login-modal')!;
const loginForm = document.getElementById('login-form') as HTMLFormElement;
const licenseKeyInput = document.getElementById('license-key') as HTMLInputElement;
const cancelLoginBtn = document.getElementById('cancel-login')!;

// State for pending file open
let pendingFilePath: string | null = null;
let pendingServerUrl: string | null = null;

// Show status message
function showStatus(message: string, isError = false) {
  statusMessage.textContent = message;
  statusMessage.className = `status-message show ${isError ? 'error' : ''}`;
  setTimeout(() => {
    statusMessage.className = 'status-message';
  }, 3000);
}

// Show/Hide Login Modal
function showLogin(serverUrl: string) {
  pendingServerUrl = serverUrl;
  loginModal.classList.add('show');
  licenseKeyInput.focus();
}

function hideLogin() {
  loginModal.classList.remove('show');
  loginForm.reset();
  pendingServerUrl = null;
}

// Render PDF page
async function renderPage(pageNum: number) {
  if (!pdfDoc) return;

  const page = await pdfDoc.getPage(pageNum);
  const viewport = page.getViewport({ scale: zoomLevel });

  canvas.width = viewport.width;
  canvas.height = viewport.height;

  const renderContext = {
    canvasContext: ctx,
    viewport: viewport,
  };

  // @ts-ignore: pdf.js type definition mismatch for RenderParameters
  await page.render(renderContext).promise;

  // Update UI
  pageInfo.textContent = `Page ${pageNum} / ${pdfDoc.numPages}`;
  prevPageBtn.disabled = pageNum === 1;
  nextPageBtn.disabled = pageNum === pdfDoc.numPages;

  // Update watermark
  updateWatermark();
}

// Update watermark overlay
function updateWatermark() {
  if (!watermarkText) {
    watermarkOverlay.style.display = 'none';
    return;
  }

  watermarkOverlay.style.display = 'flex';

  // Create multiple watermark instances
  watermarkOverlay.innerHTML = '';
  for (let i = 0; i < 5; i++) {
    const watermarkDiv = document.createElement('div');
    watermarkDiv.textContent = watermarkText;
    watermarkDiv.style.width = '100%';
    watermarkDiv.style.textAlign = 'center';
    watermarkOverlay.appendChild(watermarkDiv);
  }
}

// Apply permissions
function applyPermissions() {
  // Disable text selection if copy not allowed
  if (!permissions.allow_copy) {
    document.body.classList.add('no-copy');
    document.addEventListener('copy', (e) => {
      e.preventDefault();
      showStatus('Copying is disabled for this document', true);
    });
  }

  // Remove print button if not allowed (would need to add print button first)
  // For now, just prevent Ctrl+P
  if (!permissions.allow_print) {
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
        e.preventDefault();
        showStatus('Printing is disabled for this document', true);
      }
    });
  }
}

// Open SPDF file
async function openSpdfFile(filePath?: string) {
  try {
    let selected = filePath;

    if (!selected) {
      // Open file dialog
      const result = await open({
        multiple: false,
        filters: [
          {
            name: 'SPDF',
            extensions: ['spdf'],
          },
        ],
      });

      if (!result || typeof result !== 'string') {
        return;
      }
      selected = result;
    }

    pendingFilePath = selected;
    showStatus('Opening SPDF file...');

    // Call Rust backend to open and decrypt SPDF
    interface OpenFileResult {
      success: boolean;
      message: string;
      header?: {
        doc_id: string;
        org_id: string;
        server_url: string;
        permissions: {
          allow_print: boolean;
          allow_copy: boolean;
          max_devices: number;
        };
        watermark: {
          enabled: boolean;
          text: string;
        };
      };
      pdf_base64?: string;
      needs_login: boolean;
      watermark_data?: {
        user_id: string;
        device_id: string;
      };
    }

    const result = await invoke<OpenFileResult>('open_spdf_file', {
      filePath: selected,
    });

    if (result.needs_login && result.header) {
      showStatus('Authentication required', false);
      showLogin(result.header.server_url);
      return;
    }

    if (!result.success) {
      showStatus(result.message, true);
      return;
    }

    // Update header info
    if (result.header) {
      docIdSpan.textContent = `Doc: ${result.header.doc_id}`;
      userStatus.textContent = `Org: ${result.header.org_id}`;

      // Store permissions
      permissions = result.header.permissions;
      applyPermissions();

      // Set watermark
      if (result.header.watermark.enabled) {
        // For Phase 2, use placeholder values
        watermarkText = result.header.watermark.text
          .replace('{{user_id}}', 'test@example.com') // This should come from auth user eventually
          .replace('{{device_id}}', 'DEVICE-TEST');
      }
    }

    // Load PDF from base64
    if (result.pdf_base64) {
      const pdfData = atob(result.pdf_base64);
      const pdfArray = new Uint8Array(pdfData.length);
      for (let i = 0; i < pdfData.length; i++) {
        pdfArray[i] = pdfData.charCodeAt(i);
      }

      // Load PDF with PDF.js
      const loadingTask = pdfjsLib.getDocument({ data: pdfArray });
      pdfDoc = await loadingTask.promise;

      // Render first page
      currentPage = 1;
      await renderPage(currentPage);

      // Enable controls
      zoomInBtn.disabled = false;
      zoomOutBtn.disabled = false;

      showStatus('SPDF loaded successfully!');
      pendingFilePath = null;
    }
  } catch (error) {
    showStatus(`Error: ${error}`, true);
    console.error(error);
  }
}

// Handle Login with License Key
loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();

  const licenseKey = licenseKeyInput.value.trim();

  if (!pendingServerUrl) {
    showStatus('Error: Unknown server URL', true);
    return;
  }

  if (!licenseKey) {
    showStatus('Please enter a license key', true);
    return;
  }

  try {
    showStatus('Authenticating...');

    interface LoginResult {
      success: boolean;
      message: string;
    }

    const result = await invoke<LoginResult>('login', {
      serverUrl: pendingServerUrl,
      licenseKey,
    });

    if (result.success) {
      showStatus('Authentication successful!');
      hideLogin();
      // Retry opening the pending file
      if (pendingFilePath) {
        openSpdfFile(pendingFilePath);
      }
    } else {
      showStatus(result.message, true);
    }
  } catch (error) {
    showStatus(`Authentication failed: ${error}`, true);
  }
});

cancelLoginBtn.addEventListener('click', () => {
  hideLogin();
  pendingFilePath = null;
  showStatus('Login cancelled', true);
});

// Navigation
prevPageBtn.addEventListener('click', async () => {
  if (currentPage > 1) {
    currentPage--;
    await renderPage(currentPage);
  }
});

nextPageBtn.addEventListener('click', async () => {
  if (pdfDoc && currentPage < pdfDoc.numPages) {
    currentPage++;
    await renderPage(currentPage);
  }
});

// Zoom
zoomInBtn.addEventListener('click', async () => {
  if (zoomLevel < 3.0) {
    zoomLevel += 0.25;
    zoomLevelSpan.textContent = `${Math.round(zoomLevel * 100)}%`;
    await renderPage(currentPage);
  }
});

zoomOutBtn.addEventListener('click', async () => {
  if (zoomLevel > 0.5) {
    zoomLevel -= 0.25;
    zoomLevelSpan.textContent = `${Math.round(zoomLevel * 100)}%`;
    await renderPage(currentPage);
  }
});

// Open file button
openFileBtn.addEventListener('click', () => openSpdfFile());

// Initial state
console.log('SPDF Viewer initialized');
showStatus('Ready - Open an SPDF file to begin');
