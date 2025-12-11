/**
 * Widget to Image Converter
 * Converts rendered widget DOM elements to base64 image data URLs
 * This ensures exact visual match in PDFs
 */

import html2canvas from 'html2canvas';

export interface WidgetImageData {
  widgetId: string;
  imageDataUrl: string;
  width: number;
  height: number;
}

/**
 * Converts a single widget DOM element to an image data URL
 */
export async function widgetToImage(
  element: HTMLElement,
  widgetId: string
): Promise<WidgetImageData> {
  try {
    const canvas = await html2canvas(element, {
      scale: 2, // High resolution for PDF
      useCORS: true,
      backgroundColor: null, // Preserve transparency
      logging: false,
    });

    const imageDataUrl = canvas.toDataURL('image/png');

    return {
      widgetId,
      imageDataUrl,
      width: element.offsetWidth,
      height: element.offsetHeight,
    };
  } catch (error) {
    console.error(`Failed to convert widget ${widgetId} to image:`, error);
    throw error;
  }
}

/**
 * Converts all widgets in the report preview to images
 */
export async function captureAllWidgetsAsImages(
  containerId: string = 'report-preview-canvas'
): Promise<WidgetImageData[]> {
  const container = document.getElementById(containerId);

  if (!container) {
    console.warn('Report preview container not found');
    return [];
  }

  // Find all widget elements
  const widgetElements = container.querySelectorAll('[data-widget-id]');

  if (widgetElements.length === 0) {
    console.warn('No widgets found in container');
    return [];
  }

  // Convert each widget to image
  const imagePromises = Array.from(widgetElements).map((element) => {
    const widgetId = element.getAttribute('data-widget-id');
    if (!widgetId) return null;

    return widgetToImage(element as HTMLElement, widgetId);
  });

  // Wait for all conversions
  const results = await Promise.all(imagePromises.filter(Boolean));

  return results.filter((r): r is WidgetImageData => r !== null);
}

/**
 * Generates HTML template with image placeholders
 * Images are embedded as base64 data URLs for PDF generation
 */
export function generateHTMLWithImages(
  gridRows: any[],
  widgetImages: WidgetImageData[],
  domainName: string = 'Domain'
): string {
  // Create map of widget ID to image data
  const imageMap = new Map<string, WidgetImageData>();
  widgetImages.forEach((img) => imageMap.set(img.widgetId, img));

  let html = `
    <div class="report-container" style="max-width: 850px; margin: 0 auto; padding: 3rem; background: white;">
      <!-- Header -->
      <div class="report-header" style="border-bottom: 1px solid #e5e7eb; padding-bottom: 1rem; margin-bottom: 1.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem;">
          <h2 style="font-size: 1.25rem; font-weight: 700; color: #111827; margin: 0;">{{domain_name}}</h2>
        </div>
        <p style="font-size: 0.875rem; color: #6b7280; margin: 0;">Report Period: {{start_date}} - {{end_date}}</p>
      </div>

      <!-- Grid Rows -->
  `;

  // Render each grid row
  gridRows.forEach((row) => {
    const gridColumns = {
      single: '1fr',
      double: '1fr 1fr',
      triple: '1fr 1fr 1fr',
      quad: '1fr 1fr 1fr 1fr',
    }[row.type];

    html += `
      <div style="display: grid; grid-template-columns: ${gridColumns}; gap: 1rem; margin-bottom: 1.5rem;">
    `;

    // Render each widget slot
    row.slots.forEach((widget: any) => {
      if (!widget) {
        html += '<div></div>';
        return;
      }

      const imageData = imageMap.get(widget.id);

      if (imageData) {
        // Use actual captured image
        html += `
          <div data-widget-id="${widget.id}" style="width: 100%;">
            <img
              src="${imageData.imageDataUrl}"
              alt="${widget.title}"
              style="width: 100%; height: auto; display: block;"
            />
          </div>
        `;
      } else {
        // Fallback: placeholder
        html += `
          <div data-widget-id="${widget.id}" style="
            background: #f3f4f6;
            border: 1px solid #e5e7eb;
            border-radius: 0.5rem;
            padding: 1.5rem;
            text-align: center;
            color: #6b7280;
          ">
            <p>${widget.title}</p>
            <p style="font-size: 0.875rem; margin-top: 0.5rem;">Widget preview not available</p>
          </div>
        `;
      }
    });

    html += `</div>`;
  });

  html += `</div>`;
  return html;
}

/**
 * Complete template payload generation with widget images
 */
export async function generateTemplateWithImages(
  name: string,
  description: string,
  gridRows: any[],
  domainName: string = 'Domain'
): Promise<{
  name: string;
  description: string;
  template_type: string;
  grid_rows: any[];
  html_template: string;
  css_template: string;
}> {
  // Capture all widgets as images
  const widgetImages = await captureAllWidgetsAsImages();

  // Generate HTML with embedded images
  const html_template = generateHTMLWithImages(gridRows, widgetImages, domainName);

  return {
    name,
    description,
    template_type: 'custom',
    grid_rows: gridRows,
    html_template,
    css_template: '', // Not needed with image approach
  };
}
