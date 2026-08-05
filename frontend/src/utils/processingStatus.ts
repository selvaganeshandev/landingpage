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

  // After prompt processing completes, check if competitor/misinfo analysis is
  // actually running.
  //
  // 'READY' deliberately does NOT count. It means "ready to analyse", and
  // nothing in the codebase ever advances competitor_analysis_status past it —
  // grep for COMPLETED, it is never assigned — so every finished domain rests
  // at READY permanently. Treating that as in-flight made this return true for
  // ~59 of 63 domains, pinning the "Processing Your Brand" card on screen
  // forever. Only the genuinely active states count.
  if (domain.processing_status === 'COMP') {
    const competitorProcessing = domain.competitor_analysis_status === 'ANALYZING';
    const misinfoProcessing = domain.misinformation_scan_status === 'SCANNING';

    return competitorProcessing || misinfoProcessing;
  }

  return false;
};

/**
 * Check if competitor analysis is processing
 */
export const isCompetitorProcessing = (domain: Domain | null | undefined): boolean => {
  if (!domain) return false;
  // 'READY' excluded on purpose — see isDomainProcessing above. It is written
  // once when analysis is triggered and never advanced, so it is the resting
  // state of a finished domain, not an in-flight one.
  //
  // isMisinformationProcessing below still counts READY, and correctly so:
  // there it is a genuine transient set moments before the scan task runs, and
  // the scan advances it to SCANNING and then a terminal state.
  return domain.competitor_analysis_status === 'ANALYZING';
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
