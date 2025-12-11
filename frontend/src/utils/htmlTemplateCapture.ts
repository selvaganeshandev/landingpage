/**
 * HTML Template Capture Utility
 * Captures rendered HTML from report preview and converts it to a template with placeholders
 */

interface Widget {
  id: string;
  type: string;
  title: string;
}

interface GridRow {
  id: string;
  type: string;
  slots: (Widget | null)[];
}

/**
 * Captures the ACTUAL rendered HTML from the browser DOM
 * This preserves all inline styles, computed styles, and exact layout
 */
export function captureHTMLTemplate(containerId: string = 'report-preview-canvas'): string {
  const container = document.getElementById(containerId);

  if (!container) {
    console.warn('Report preview container not found');
    return '';
  }

  // Clone the container to avoid modifying the original
  const clone = container.cloneNode(true) as HTMLElement;

  // Convert all computed styles to inline styles (critical for PDF!)
  inlineAllComputedStyles(clone, container);

  // Replace widget values with placeholders
  replaceWithPlaceholders(clone);

  return clone.innerHTML;
}

/**
 * Converts all computed CSS styles to inline styles
 * This ensures the exact visual appearance is preserved in the HTML
 */
function inlineAllComputedStyles(clonedElement: HTMLElement, originalElement: HTMLElement): void {
  // Get computed styles from the original element
  const computedStyle = window.getComputedStyle(originalElement);

  // Copy important styles to inline style attribute
  const importantStyles = [
    'background',
    'background-color',
    'background-image',
    'background-gradient',
    'color',
    'font-size',
    'font-weight',
    'font-family',
    'padding',
    'padding-top',
    'padding-right',
    'padding-bottom',
    'padding-left',
    'margin',
    'margin-top',
    'margin-right',
    'margin-bottom',
    'margin-left',
    'border',
    'border-width',
    'border-style',
    'border-color',
    'border-radius',
    'width',
    'height',
    'display',
    'flex-direction',
    'align-items',
    'justify-content',
    'gap',
    'line-height',
    'text-align'
  ];

  let inlineStyle = '';
  importantStyles.forEach(prop => {
    const value = computedStyle.getPropertyValue(prop);
    if (value && value !== 'none' && value !== 'normal') {
      inlineStyle += `${prop}: ${value}; `;
    }
  });

  if (inlineStyle) {
    const existingStyle = clonedElement.getAttribute('style') || '';
    clonedElement.setAttribute('style', existingStyle + ' ' + inlineStyle);
  }

  // Recursively process all child elements
  const originalChildren = Array.from(originalElement.children);
  const clonedChildren = Array.from(clonedElement.children);

  originalChildren.forEach((originalChild, index) => {
    if (clonedChildren[index]) {
      inlineAllComputedStyles(
        clonedChildren[index] as HTMLElement,
        originalChild as HTMLElement
      );
    }
  });
}

/**
 * Replaces actual widget values with placeholder syntax
 */
function replaceWithPlaceholders(element: HTMLElement): void {
  // Find all metric cards and replace values
  const metricCards = element.querySelectorAll('[data-widget-id]');

  metricCards.forEach((card) => {
    const widgetId = card.getAttribute('data-widget-id');
    if (!widgetId) return;

    // Replace metric value
    const valueElement = card.querySelector('[data-value]');
    if (valueElement) {
      valueElement.textContent = `{{${widgetId}.value}}`;
    }

    // Replace label
    const labelElement = card.querySelector('[data-label]');
    if (labelElement) {
      labelElement.textContent = `{{${widgetId}.label}}`;
    }

    // Replace growth
    const growthElement = card.querySelector('[data-growth]');
    if (growthElement) {
      growthElement.textContent = `{{${widgetId}.growth}}`;
    }

    // Replace growth indicator
    const indicatorElement = card.querySelector('[data-indicator]');
    if (indicatorElement) {
      indicatorElement.textContent = `{{${widgetId}.indicator}}`;
    }
  });

  // Replace charts with placeholders
  const charts = element.querySelectorAll('[data-chart-id]');
  charts.forEach((chart) => {
    const widgetId = chart.getAttribute('data-chart-id');
    if (!widgetId) return;

    // Replace chart content with placeholder
    chart.innerHTML = `{{${widgetId}.chart}}`;
  });

  // Replace tables with placeholders
  const tables = element.querySelectorAll('[data-table-id]');
  tables.forEach((table) => {
    const widgetId = table.getAttribute('data-table-id');
    if (!widgetId) return;

    // Replace table content with placeholder
    table.innerHTML = `{{${widgetId}.table}}`;
  });
}

/**
 * Generates HTML template with placeholders from grid rows
 * This is used when we can't capture from DOM (e.g., during save without preview)
 */
export function generateHTMLTemplate(gridRows: GridRow[], domainName: string = 'Domain'): string {
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
    const gridClass = `grid-${row.type}`;
    const gridColumns = {
      single: '1fr',
      double: '1fr 1fr',
      triple: '1fr 1fr 1fr',
      quad: '1fr 1fr 1fr 1fr'
    }[row.type];

    html += `
      <div class="${gridClass}" style="display: grid; grid-template-columns: ${gridColumns}; gap: 1rem; margin-bottom: 1.5rem;">
    `;

    // Render each widget slot
    row.slots.forEach((widget) => {
      if (!widget) {
        html += '<div class="empty-slot"></div>';
        return;
      }

      if (widget.type === 'metric') {
        html += generateMetricWidgetHTML(widget);
      } else if (widget.type === 'chart') {
        html += generateChartWidgetHTML(widget);
      } else if (widget.type === 'table') {
        html += generateTableWidgetHTML(widget);
      }
    });

    html += `</div>`;
  });

  html += `</div>`;
  return html;
}

/**
 * Generate metric widget HTML with placeholders
 * Matches the exact styling from ReportPreviewDialog.tsx
 */
function generateMetricWidgetHTML(widget: Widget): string {
  // Determine color scheme based on widget ID - EXACT colors from frontend
  let gradientFrom = 'from-blue-500/10';
  let gradientTo = 'to-blue-500/5';
  let borderColor = 'border-blue-200';
  let textColor = 'text-blue-600';
  let bgColor = '#eff6ff'; // blue-50 fallback

  const widgetId = widget.id.toLowerCase();

  // Platform metrics
  if (widgetId.includes('platform')) {
    gradientFrom = 'from-purple-500/10';
    gradientTo = 'to-purple-500/5';
    borderColor = 'border-purple-200';
    textColor = 'text-purple-600';
    bgColor = '#faf5ff';
  }
  // Sentiment/positive/health
  else if (widgetId.includes('sentiment') || widgetId.includes('positive') || widgetId.includes('health')) {
    gradientFrom = 'from-green-500/10';
    gradientTo = 'to-green-500/5';
    borderColor = 'border-green-200';
    textColor = 'text-green-600';
    bgColor = '#f0fdf4';
  }
  // Competitor/position/rank
  else if (widgetId.includes('competitor') || widgetId.includes('position') || widgetId.includes('rank')) {
    gradientFrom = 'from-purple-500/10';
    gradientTo = 'to-purple-500/5';
    borderColor = 'border-purple-200';
    textColor = 'text-purple-600';
    bgColor = '#faf5ff';
  }
  // Share/voice/market
  else if (widgetId.includes('share') || widgetId.includes('voice') || widgetId.includes('market')) {
    gradientFrom = 'from-orange-500/10';
    gradientTo = 'to-orange-500/5';
    borderColor = 'border-orange-200';
    textColor = 'text-orange-600';
    bgColor = '#fff7ed';
  }
  // Mentions
  else if (widgetId.includes('mention')) {
    gradientFrom = 'from-blue-500/10';
    gradientTo = 'to-blue-500/5';
    borderColor = 'border-blue-200';
    textColor = 'text-blue-600';
    bgColor = '#eff6ff';
  }

  // Map to actual hex colors for PDF gradients
  const colorMap: Record<string, {gradient1: string, gradient2: string, border: string, text: string}> = {
    'blue': {
      gradient1: 'rgba(59, 130, 246, 0.1)',   // blue-500 at 10%
      gradient2: 'rgba(59, 130, 246, 0.05)',  // blue-500 at 5%
      border: '#bfdbfe',  // blue-200
      text: '#2563eb'     // blue-600
    },
    'purple': {
      gradient1: 'rgba(139, 92, 246, 0.1)',
      gradient2: 'rgba(139, 92, 246, 0.05)',
      border: '#e9d5ff',  // purple-200
      text: '#9333ea'     // purple-600
    },
    'green': {
      gradient1: 'rgba(34, 197, 94, 0.1)',
      gradient2: 'rgba(34, 197, 94, 0.05)',
      border: '#bbf7d0',  // green-200
      text: '#16a34a'     // green-600
    },
    'orange': {
      gradient1: 'rgba(249, 115, 22, 0.1)',
      gradient2: 'rgba(249, 115, 22, 0.05)',
      border: '#fed7aa',  // orange-200
      text: '#ea580c'     // orange-600
    }
  };

  // Determine which color to use
  let colorScheme = 'blue'; // default
  if (widgetId.includes('platform') || widgetId.includes('competitor') || widgetId.includes('position') || widgetId.includes('rank')) {
    colorScheme = 'purple';
  } else if (widgetId.includes('sentiment') || widgetId.includes('positive') || widgetId.includes('health')) {
    colorScheme = 'green';
  } else if (widgetId.includes('share') || widgetId.includes('voice') || widgetId.includes('market')) {
    colorScheme = 'orange';
  }

  const colors = colorMap[colorScheme];

  // Use inline styles with REAL gradient colors for PDF
  return `
    <div class="metric-widget"
         style="
           background: linear-gradient(to bottom right, ${colors.gradient1}, ${colors.gradient2});
           border: 1px solid ${colors.border};
           border-radius: 0.5rem;
           padding: 1.5rem;
           margin-bottom: 1rem;
         "
         data-widget-id="${widget.id}">
      <p style="font-size: 0.875rem; color: #9ca3af; margin-bottom: 0.5rem; font-weight: 500;">
        {{${widget.id}.label}}
      </p>
      <p style="font-size: 2.25rem; font-weight: 700; color: ${colors.text}; margin-bottom: 0.5rem; line-height: 1;">
        {{${widget.id}.value}}
      </p>
      <p style="font-size: 0.875rem; display: flex; align-items: center; gap: 0.25rem; margin-top: 0.5rem;">
        <span style="font-size: 1rem;">{{${widget.id}.indicator}}</span>
        <span class="{{${widget.id}.growth_color}}" style="font-weight: 600;">{{${widget.id}.growth}}</span>
      </p>
    </div>
  `;
}

/**
 * Generate chart widget HTML with placeholder
 */
function generateChartWidgetHTML(widget: Widget): string {
  return `
    <div class="chart-widget bg-white border border-gray-200"
         style="padding: 1.5rem; border: 1px solid #e5e7eb; border-radius: 0.5rem;"
         data-widget-id="${widget.id}">
      <h3 style="font-size: 1rem; font-weight: 600; margin-bottom: 1rem;">{{${widget.id}.label}}</h3>
      <div class="chart-container" data-chart-id="${widget.id}">
        {{${widget.id}.chart}}
      </div>
    </div>
  `;
}

/**
 * Generate table widget HTML with placeholder
 */
function generateTableWidgetHTML(widget: Widget): string {
  return `
    <div class="table-widget bg-white border border-gray-200"
         style="padding: 1.5rem; border: 1px solid #e5e7eb; border-radius: 0.5rem;"
         data-widget-id="${widget.id}">
      <h3 style="font-size: 1rem; font-weight: 600; margin-bottom: 1rem;">{{${widget.id}.label}}</h3>
      <div class="table-container" data-table-id="${widget.id}">
        {{${widget.id}.table}}
      </div>
    </div>
  `;
}

/**
 * Extract critical CSS from current page
 * This captures the Tailwind CSS classes used in the template
 */
export function extractCriticalCSS(): string {
  // For now, return empty string
  // In production, you might want to use a CSS extraction library
  // or include a pre-compiled Tailwind CSS bundle
  return '';
}

/**
 * Generates complete payload for saving template with HTML
 */
export function generateTemplatePayload(
  name: string,
  description: string,
  gridRows: GridRow[],
  domainName: string = 'Domain'
): {
  name: string;
  description: string;
  template_type: string;
  grid_rows: GridRow[];
  html_template: string;
  css_template: string;
} {
  // Try to capture from DOM first
  let html_template = captureHTMLTemplate();

  // Fallback to generated template if capture fails
  if (!html_template || html_template.trim().length === 0) {
    html_template = generateHTMLTemplate(gridRows, domainName);
  }

  const css_template = extractCriticalCSS();

  return {
    name,
    description,
    template_type: 'custom',
    grid_rows: gridRows,
    html_template,
    css_template,
  };
}
