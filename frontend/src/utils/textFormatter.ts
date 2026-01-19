/**
 * Text formatting utilities for LLM message content
 * Handles markdown-like syntax conversion to HTML with proper list formatting
 */

/**
 * Converts markdown tables to HTML tables
 * @param text - The text potentially containing markdown tables
 * @returns Text with markdown tables converted to HTML
 */
const convertMarkdownTables = (text: string): string => {
  const lines = text.split('\n');
  const result: string[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Check if this line looks like a table row (starts with |)
    if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
      // Collect all consecutive table lines
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        tableLines.push(lines[i]);
        i++;
      }

      // Need at least 2 lines for a valid table (header + separator)
      if (tableLines.length >= 2) {
        // Check if second line is a separator (contains dashes)
        const secondLine = tableLines[1].trim();
        const isSeparator = /^\|[\s\-:|]+\|$/.test(secondLine);

        if (isSeparator) {
          // Parse the table
          let tableHtml = '<table class="markdown-table">';

          // Header row
          const headerCells = tableLines[0].split('|').filter(cell => cell.trim() !== '');
          tableHtml += '<thead><tr>';
          headerCells.forEach(cell => {
            tableHtml += `<th>${cell.trim()}</th>`;
          });
          tableHtml += '</tr></thead>';

          // Body rows (skip separator at index 1)
          if (tableLines.length > 2) {
            tableHtml += '<tbody>';
            for (let j = 2; j < tableLines.length; j++) {
              const cells = tableLines[j].split('|').filter(cell => cell.trim() !== '');
              tableHtml += '<tr>';
              cells.forEach(cell => {
                tableHtml += `<td>${cell.trim()}</td>`;
              });
              tableHtml += '</tr>';
            }
            tableHtml += '</tbody>';
          }

          tableHtml += '</table>';
          result.push(tableHtml);
          continue;
        }
      }

      // Not a valid table, add lines as-is
      tableLines.forEach(tl => result.push(tl));
      continue;
    }

    result.push(line);
    i++;
  }

  return result.join('\n');
};

/**
 * Formats LLM message content with proper list handling, headers, and inline formatting
 * @param text - The raw text content to format
 * @returns HTML-formatted string
 */
export const formatMessage = (text: string): string => {
  // First, convert markdown tables to HTML
  const textWithTables = convertMarkdownTables(text);

  // Apply inline formatting (bold, links)
  const applyInlineFormatting = (str: string): string => {
    return str
      // Bold: **text** or __text__
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/__(.*?)__/g, '<strong>$1</strong>')
      // Links: [text](url)
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-primary hover:underline">$1</a>');
  };

  const lines = textWithTables.split('\n');
  const result: string[] = [];
  let inNumberedList = false;
  let inBulletList = false;
  let paragraphBuffer: string[] = [];
  let lastWasNumbered = false;
  let inNestedList = false; // Track if we're in a nested list under a brand/product item

  const flushParagraph = () => {
    if (paragraphBuffer.length > 0) {
      result.push(`<p>${applyInlineFormatting(paragraphBuffer.join('<br />'))}</p>`);
      paragraphBuffer = [];
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Empty line - only close lists if truly done
    if (trimmed === '') {
      flushParagraph();

      // Check if next non-empty line is also a list item
      let nextIsNumbered = false;
      let nextIsBullet = false;
      for (let j = i + 1; j < lines.length; j++) {
        const nextTrimmed = lines[j].trim();
        if (nextTrimmed !== '') {
          nextIsNumbered = /^\d+\.\s+/.test(nextTrimmed);
          nextIsBullet = /^[\•\-\*]\s+/.test(nextTrimmed);
          break;
        }
      }

      // Close nested bullet list if we had one
      if (lastWasNumbered && inBulletList) {
        result.push('</ul>');
        result.push('</li>'); // Close the numbered item containing the bullets
        inBulletList = false;
        lastWasNumbered = false;
      }

      // Only close standalone bullet list if next is not a bullet
      if (inBulletList && !lastWasNumbered && !nextIsBullet) {
        result.push('</ul>');
        inBulletList = false;
      }

      // Only close numbered list if next is not numbered
      if (inNumberedList && !nextIsNumbered) {
        result.push('</ol>');
        inNumberedList = false;
      }

      continue;
    }

    // Headers
    const h3Match = trimmed.match(/^###\s+(.+)$/);
    const h2Match = trimmed.match(/^##\s+(.+)$/);
    const h1Match = trimmed.match(/^#\s+(.+)$/);

    if (h3Match || h2Match || h1Match) {
      flushParagraph();
      if (inBulletList) { result.push('</ul>'); inBulletList = false; }
      if (inNumberedList) { result.push('</ol>'); inNumberedList = false; }
      const level = h3Match ? 3 : h2Match ? 2 : 1;
      const content = h3Match?.[1] || h2Match?.[1] || h1Match?.[1] || '';
      result.push(`<h${level}>${applyInlineFormatting(content)}</h${level}>`);
      lastWasNumbered = false;
      continue;
    }

    // Numbered list
    const numberedMatch = trimmed.match(/^\d+\.\s+(.+)$/);
    if (numberedMatch) {
      flushParagraph();

      // Close any nested bullet list from previous numbered item
      if (inBulletList && lastWasNumbered) {
        result.push('</ul>');
        result.push('</li>'); // Close previous numbered item
        inBulletList = false;
        lastWasNumbered = false;
      }

      // Close standalone bullet list if transitioning to numbered
      if (inBulletList && !inNumberedList) {
        result.push('</ul>');
        inBulletList = false;
      }

      // Start numbered list if not already in one
      if (!inNumberedList) {
        result.push('<ol>');
        inNumberedList = true;
      }

      // Check if next line is a bullet (nested list)
      const nextLine = i + 1 < lines.length ? lines[i + 1].trim() : '';
      const nextIsBullet = /^[\•\-\*]\s+/.test(nextLine);

      if (nextIsBullet) {
        // Start list item but don't close it yet (nested bullets coming)
        result.push(`<li>${applyInlineFormatting(numberedMatch[1])}`);
        lastWasNumbered = true;
      } else {
        result.push(`<li>${applyInlineFormatting(numberedMatch[1])}</li>`);
        lastWasNumbered = false;
      }
      continue;
    }

    // Bullet list - but check if it's actually a heading (bold text with colon)
    const bulletMatch = trimmed.match(/^[\•\-\*]\s+(.+)$/);
    if (bulletMatch) {
      const bulletContent = bulletMatch[1];

      // Check if the bullet content is bold text ending with a colon (e.g., • **Indian Brands:**)
      const boldHeadingMatch = bulletContent.match(/^\*\*([^*]+):\*\*$/);

      if (boldHeadingMatch) {
        // This is a heading, not a bullet point
        flushParagraph();
        if (inBulletList) { result.push('</ul>'); inBulletList = false; }
        if (inNumberedList) { result.push('</ol>'); inNumberedList = false; }
        if (lastWasNumbered) { result.push('</li>'); lastWasNumbered = false; }
        result.push(`<h4>${boldHeadingMatch[1]}</h4>`);
        continue;
      }

      // Check if bullet starts with bold text with colon but has more content after (e.g., • **Wildcraft:** (Indian Brand))
      // This is a sub-heading that should start a nested structure
      const boldSubHeadingMatch = bulletContent.match(/^\*\*([^*]+):\*\*\s+(.+)$/);

      if (boldSubHeadingMatch) {
        // Close any existing nested list first
        if (inNestedList) {
          result.push('</ul>'); // Close nested list
          result.push('</li>'); // Close parent li
          inNestedList = false;
        }

        flushParagraph();

        if (!inBulletList) {
          result.push('<ul>');
          inBulletList = true;
        }

        // Create a bullet with strong heading
        result.push(`<li><strong>${boldSubHeadingMatch[1]}:</strong> ${applyInlineFormatting(boldSubHeadingMatch[2])}`);

        // Check if next line is a sub-item (like "Description:")
        const nextLine = i + 1 < lines.length ? lines[i + 1].trim() : '';
        const nextIsBulletWithLabel = nextLine.match(/^[\•\-\*]\s+\*\*[^*]+:\*\*/);

        if (nextIsBulletWithLabel) {
          // Start nested list for sub-items
          result.push('<ul class="nested-list">');
          inNestedList = true;
          // Don't close the li yet, we'll close it when the nested list ends
        } else {
          result.push('</li>');
        }
        continue;
      }

      // Check if this is a description/feature item (bold label with colon at start)
      const labelMatch = bulletContent.match(/^\*\*([^*]+):\*\*\s+(.+)$/);

      if (labelMatch) {
        if (inNestedList) {
          // This is a labeled content item within a nested list
          result.push(`<li><strong>${labelMatch[1]}:</strong> ${applyInlineFormatting(labelMatch[2])}</li>`);
          continue;
        } else if (inBulletList) {
          // Regular labeled item at top level
          result.push(`<li><strong>${labelMatch[1]}:</strong> ${applyInlineFormatting(labelMatch[2])}</li>`);
          continue;
        }
      }

      flushParagraph();

      // If this is nested under a numbered item
      if (lastWasNumbered) {
        if (!inBulletList) {
          result.push('<ul>');
          inBulletList = true;
        }
        result.push(`<li>${applyInlineFormatting(bulletMatch[1])}</li>`);

        // Check if next line is also a bullet or numbered item
        const nextLine = i + 1 < lines.length ? lines[i + 1].trim() : '';
        const nextIsBullet = /^[\•\-\*]\s+/.test(nextLine);
        const nextIsNumbered = /^\d+\.\s+/.test(nextLine);

        // If next is numbered, close nested list and the numbered item
        if (nextIsNumbered) {
          result.push('</ul>');
          result.push('</li>'); // Close the numbered list item
          inBulletList = false;
          lastWasNumbered = false;
        }
        // If next is not a bullet and not numbered, close nested list
        else if (!nextIsBullet) {
          result.push('</ul>');
          result.push('</li>'); // Close the numbered list item
          inBulletList = false;
          lastWasNumbered = false;
        }
      } else {
        // Standalone bullet list
        if (inNumberedList) {
          result.push('</ol>');
          inNumberedList = false;
        }
        if (!inBulletList) {
          result.push('<ul>');
          inBulletList = true;
        }
        result.push(`<li>${applyInlineFormatting(bulletMatch[1])}</li>`);
      }
      continue;
    }

    // Check if line is an HTML table (already converted)
    if (trimmed.startsWith('<table')) {
      flushParagraph();
      if (inBulletList) { result.push('</ul>'); inBulletList = false; }
      if (inNumberedList) { result.push('</ol>'); inNumberedList = false; }
      if (lastWasNumbered) { result.push('</li>'); lastWasNumbered = false; }
      result.push(trimmed);
      continue;
    }

    // Regular text
    if (inBulletList && !lastWasNumbered) {
      result.push('</ul>');
      inBulletList = false;
    }
    if (inNumberedList && !lastWasNumbered) {
      result.push('</ol>');
      inNumberedList = false;
    }
    if (lastWasNumbered) {
      result.push('</li>');
      lastWasNumbered = false;
    }
    paragraphBuffer.push(trimmed);
  }

  flushParagraph();

  // Close any open lists
  if (inNestedList) {
    result.push('</ul>'); // Close nested list
    result.push('</li>'); // Close parent li
  }
  if (inBulletList) {
    result.push('</ul>');
    if (lastWasNumbered) result.push('</li>');
  }
  if (inNumberedList) {
    result.push('</ol>');
  }

  return result.join('');
};

/**
 * CSS classes for properly styled formatted content
 * Apply these to the container with dangerouslySetInnerHTML
 */
export const FORMATTED_MESSAGE_CLASSES = "text-[15px] leading-relaxed [&_p]:mb-3 [&_p]:leading-relaxed [&_h1]:text-xl [&_h1]:font-bold [&_h1]:mb-2 [&_h1]:mt-4 [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:mb-2 [&_h2]:mt-3 [&_h3]:text-base [&_h3]:font-semibold [&_h3]:mb-2 [&_h3]:mt-3 [&_h4]:text-[15px] [&_h4]:font-bold [&_h4]:mb-2 [&_h4]:mt-2 [&_ul]:my-2 [&_ul]:pl-6 [&_ul]:list-disc [&_ul_ul]:mt-1 [&_ul_ul]:mb-1 [&_.nested-list]:mt-2 [&_.nested-list]:mb-2 [&_.nested-list]:pl-6 [&_.nested-list]:list-circle [&_ol]:my-2 [&_ol]:pl-6 [&_ol]:list-decimal [&_li]:leading-relaxed [&_li]:mb-2 [&_li_ul]:mt-2 [&_strong]:font-semibold [&_a]:text-primary [&_a]:underline [&_a]:hover:text-primary/80 [&_table]:w-full [&_table]:my-4 [&_table]:border-collapse [&_table]:border [&_table]:border-border [&_table]:rounded-lg [&_table]:overflow-hidden [&_table]:text-sm [&_th]:bg-muted/50 [&_th]:px-4 [&_th]:py-2 [&_th]:text-left [&_th]:font-semibold [&_th]:border [&_th]:border-border [&_td]:px-4 [&_td]:py-2 [&_td]:border [&_td]:border-border [&_tr:hover]:bg-muted/30";
