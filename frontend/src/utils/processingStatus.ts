import { Domain } from "@/stores/domainStore";

/**
 * Check if a domain is currently in a processing state
 * This includes prompt processing, competitor analysis, and misinformation scanning
 */
export const isDomainProcessing = (domain: Domain | null | undefined): boolean => {
  if (!domain || !domain.processing_status) return false;

  // Check if prompt processing is ongoing
  const promptProcessingStatuses = ['INIT', 'SCHD', 'PROC'];
  if (promptProcessingStatuses.includes(domain.processing_status)) {
    return true;
  }

  // After prompt processing completes, check if competitor/misinfo analysis is ongoing
  if (domain.processing_status === 'COMP') {
    const competitorProcessing = domain.competitor_analysis_status &&
      (domain.competitor_analysis_status === 'READY' || domain.competitor_analysis_status === 'ANALYZING');
    const misinfoProcessing = domain.misinformation_scan_status &&
      (domain.misinformation_scan_status === 'READY' || domain.misinformation_scan_status === 'SCANNING');

    return competitorProcessing || misinfoProcessing;
  }

  return false;
};

/**
 * Check if competitor analysis is processing
 */
export const isCompetitorProcessing = (domain: Domain | null | undefined): boolean => {
  if (!domain) return false;
  return domain.competitor_analysis_status === 'ANALYZING' ||
         domain.competitor_analysis_status === 'READY';
};

/**
 * Check if misinformation scan is processing
 */
export const isMisinformationProcessing = (domain: Domain | null | undefined): boolean => {
  if (!domain) return false;
  return domain.misinformation_scan_status === 'SCANNING' ||
         domain.misinformation_scan_status === 'READY';
};

/**
 * Check if citations are being processed (citations are extracted during prompt analytics)
 */
export const isCitationsProcessing = (domain: Domain | null | undefined): boolean => {
  if (!domain) return false;
  // Citations are extracted during prompt analytics, so check if domain is still processing
  // or if prompt analytics just completed but citations haven't been fully processed
  const promptProcessing = ['INIT', 'SCHD', 'PROC'].includes(domain.processing_status || '');
  return promptProcessing || isDomainProcessing(domain);
};

/**
 * Check if a domain processing has failed
 */
export const isDomainProcessingFailed = (domain: Domain | null | undefined): boolean => {
  if (!domain || !domain.processing_status) return false;
  return domain.processing_status === 'FAIL';
};

/**
 * Check if a domain processing is complete
 */
export const isDomainProcessingComplete = (domain: Domain | null | undefined): boolean => {
  if (!domain || !domain.processing_status) return false;
  return domain.processing_status === 'COMP';
};

/**
 * Get human-readable status label
 */
export const getProcessingStatusLabel = (status?: string): string => {
  switch (status) {
    case 'INIT':
      return 'Initializing...';
    case 'SCHD':
      return 'Scheduled...';
    case 'PROC':
      return 'Processing...';
    case 'COMP':
      return 'Completed';
    case 'FAIL':
      return 'Failed';
    default:
      return 'Unknown';
  }
};
