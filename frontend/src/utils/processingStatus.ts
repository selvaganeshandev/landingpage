import { Domain } from "@/stores/domainStore";

/**
 * Check if a domain is currently in a processing state
 */
export const isDomainProcessing = (domain: Domain | null | undefined): boolean => {
  if (!domain || !domain.processing_status) return false;

  const processingStatuses = ['INIT', 'SCHD', 'PROC'];
  return processingStatuses.includes(domain.processing_status);
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
