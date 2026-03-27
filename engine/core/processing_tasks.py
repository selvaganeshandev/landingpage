from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from shared_models.models import Domain
from shared_models.models import Prompt, Competitor
from .domain_processor import DomainProcessor
from .prompt_analytics_processor import PromptAnalyticsProcessor
from .competitor_processor import CompetitorProcessor
from .misinformation_processor import MisinformationProcessor
from .ga_insights_processor import GAInsightsProcessor
from .gsc_insights_processor import GSCInsightsProcessor
from .cms_manager_processor import CMSManagerProcessor
import logging

# Import from engine's integrations app
from integrations.models import Integration

logger = logging.getLogger(__name__)

# Batch sizes for weekly reprocessing (tunable via settings if desired)
WEEKLY_PROMPT_BATCH_SIZE = getattr(settings, 'WEEKLY_PROMPT_BATCH_SIZE', 5000)
WEEKLY_COMPETITOR_BATCH_SIZE = getattr(settings, 'WEEKLY_COMPETITOR_BATCH_SIZE', 2000)


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_domain_task(self, domain_id: int):
    processor = DomainProcessor()
    processor._process_single_domain(domain_id)


@shared_task(bind=True, ignore_result=True, max_retries=3)
def scheduler_tick(self):
    max_concurrent = getattr(settings, 'MAX_CONCURRENT_DOMAINS', 10)

    # Count current in-flight (scheduled) domains
    currently_processing = Domain.objects.filter(processing_status='SCHD').count()
    available_slots = max(0, max_concurrent - currently_processing)
    if available_slots <= 0:
        return
    
    # Pick up to available_slots domains in INIT (not yet scheduled)
    domain_ids = list(
        Domain.objects.filter(processing_status__in=['INIT'])
        .order_by('modified_at')
        .values_list('id', flat=True)[:available_slots]
    )

    for domain_id in domain_ids:
        # Mark as scheduled if INIT
        with transaction.atomic():
            domain = Domain.objects.select_for_update().get(id=domain_id)
            if domain.processing_status == 'INIT':
                domain.processing_status = 'SCHD'
                domain.tracked_at = timezone.now()
                domain.save(update_fields=['processing_status', 'tracked_at', 'modified_at'])

        process_domain_task.delay(domain_id)


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_prompt_analytics_task(self, prompt_id):
    processor = PromptAnalyticsProcessor(max_concurrent_prompts=getattr(settings, 'MAX_CONCURRENT_PROMPT_ANALYTICS', 10))
    return processor.process_single_prompt(prompt_id)


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_prompt_analytics_scheduler(self):
    processor = PromptAnalyticsProcessor(max_concurrent_prompts=getattr(settings, 'MAX_CONCURRENT_PROMPT_ANALYTICS', 10))
    return processor.schedule_tick()


@shared_task(bind=True, ignore_result=True, max_retries=3)
def schedule_weekly_prompt_batches(self, last_id: int = 0):
    """
    Weekly batch re-scheduler for prompt analytics.
    - Resets prompts (excluding PROC) to INIT in batches
    - Enqueues prompt analytics tasks
    - Chains itself until all prompts are scheduled
    """
    qs = (
        Prompt.objects
        .exclude(track_status='PROC')  # don't clobber in-flight work
        .filter(id__gt=last_id)
        .order_by('id')
        .values_list('id', flat=True)[:WEEKLY_PROMPT_BATCH_SIZE]
    )

    ids = list(qs)
    if not ids:
        logger.info("[Weekly Prompts] No more prompts to schedule")
        return {'done': True}

    now = timezone.now()
    for pid in ids:
        Prompt.objects.filter(id=pid).update(
            track_status='INIT',
            track_message=f"Weekly reprocess scheduled at {now}",
            modified_at=now,
        )
        process_prompt_analytics_task.delay(pid)

    # Chain next batch
    schedule_weekly_prompt_batches.delay(last_id=ids[-1])
    logger.info(f"[Weekly Prompts] Scheduled batch of {len(ids)} prompts (last_id={ids[-1]})")
    return {'queued': len(ids), 'last_id': ids[-1]}


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_competitor_scheduler(self):
    """
    Periodic scheduler for competitor processing.
    Processes competitors with status INIT or FAIL.
    Runs every 15 seconds (configurable via CELERY_BEAT_SCHEDULE_COMPETITOR).
    """
    try:
        processor = CompetitorProcessor(
            max_concurrent_prompts=getattr(settings, 'MAX_CONCURRENT_COMPETITOR_PROMPTS', 10)
        )
        result = processor.schedule_tick()
        logger.info(f"Competitor scheduler tick completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in competitor scheduler: {str(e)}", exc_info=True)
        raise self.retry(exc=e, countdown=60)  # Retry after 60 seconds on error


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_cmsmanager_scheduler(self):
    """
    Periodic scheduler for CMS publishing.
    Picks due scheduled publications and publishes them.
    """
    try:
        processor = CMSManagerProcessor(batch_size=getattr(settings, 'CMS_MANAGER_BATCH_SIZE', 20))
        result = processor.schedule_tick()
        logger.info(f"CMS manager tick completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in CMS manager scheduler: {str(e)}", exc_info=True)
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_single_competitor_task(self, competitor_id: int):
    """
    Process a single competitor (manual/on-demand processing only).
    This is the primary method for processing competitors - triggered via API endpoint.
    
    Args:
        competitor_id: ID of competitor to process
    """
    from shared_models.models import Competitor
    try:
        processor = CompetitorProcessor(max_concurrent_prompts=getattr(settings, 'MAX_CONCURRENT_COMPETITOR_PROMPTS', 10))
        
        # Get the competitor
        with transaction.atomic():
            competitor = Competitor.objects.select_for_update().get(id=competitor_id)
            
            # Allow reprocessing if COMP or failed before, or if INIT
            # Reset to INIT if it's already COMP (for reprocessing)
            if competitor.track_status == 'COMP':
                logger.info(f"Competitor {competitor_id} is already COMP, resetting to INIT for reprocessing")
                competitor.track_status = 'INIT'
                competitor.track_message = 'Resetting for reprocessing'
                competitor.save(update_fields=['track_status', 'track_message', 'modified_at'])
            elif competitor.track_status not in ['INIT', 'FAIL']:
                logger.warning(f"Competitor {competitor_id} is in status {competitor.track_status}, skipping")
                return {'error': f'Competitor already in status {competitor.track_status}'}
            
            # Mark as SCHD
            competitor.track_status = 'SCHD'
            competitor.track_message = f"Scheduled for processing at {timezone.now()}"
            competitor.save(update_fields=['track_status', 'track_message', 'modified_at'])
        
        logger.info(f"Processing competitor {competitor_id} ({competitor.name})")
        
        # Link prompts to competitor
        processor._link_prompts_to_competitor(competitor)
        
        # Mark as processing
        with transaction.atomic():
            competitor = Competitor.objects.select_for_update().get(id=competitor_id)
            competitor.track_status = 'PROC'
            competitor.track_message = "Processing competitor analytics"
            competitor.save(update_fields=['track_status', 'track_message', 'modified_at'])
        
        # Process prompts
        processor._process_competitor_prompts(competitor)
        
        # Aggregate analytics
        processor._aggregate_competitor_analytics(competitor)
        
        # Mark as complete
        with transaction.atomic():
            competitor = Competitor.objects.select_for_update().get(id=competitor_id)
            competitor.track_status = 'COMP'
            competitor.track_message = f"Completed at {timezone.now()}"
            competitor.tracked_at = timezone.now()
            competitor.save(update_fields=['track_status', 'track_message', 'tracked_at', 'modified_at'])
        
        logger.info(f"Successfully completed competitor {competitor_id}")
        return {'success': True, 'competitor_id': competitor_id}
        
    except Competitor.DoesNotExist:
        logger.error(f"Competitor {competitor_id} not found")
        return {'error': 'competitor_not_found'}
    except Exception as e:
        logger.error(f"Error processing competitor {competitor_id}: {str(e)}")
        # Mark as failed
        try:
            with transaction.atomic():
                competitor = Competitor.objects.select_for_update().get(id=competitor_id)
                competitor.track_status = 'FAIL'
                competitor.track_message = f"Processing failed: {str(e)}"
                competitor.save(update_fields=['track_status', 'track_message', 'modified_at'])
        except:
            pass
        return {'error': str(e)}


@shared_task(bind=True, ignore_result=True, max_retries=3)
def schedule_weekly_competitor_batches(self, last_id: int = 0):
    """
    Weekly batch re-scheduler for competitor analytics.
    - Resets competitors (excluding PROC) to INIT in batches
    - Enqueues competitor processing tasks
    - Chains itself until all competitors are scheduled
    """
    qs = (
        Competitor.objects
        .exclude(track_status='PROC')  # don't clobber in-flight work
        .filter(id__gt=last_id)
        .order_by('id')
        .values_list('id', flat=True)[:WEEKLY_COMPETITOR_BATCH_SIZE]
    )

    ids = list(qs)
    if not ids:
        logger.info("[Weekly Competitors] No more competitors to schedule")
        return {'done': True}

    now = timezone.now()
    for cid in ids:
        Competitor.objects.filter(id=cid).update(
            track_status='INIT',
            track_message=f"Weekly reprocess scheduled at {now}",
            modified_at=now,
        )
        process_single_competitor_task.delay(cid)

    # Chain next batch
    schedule_weekly_competitor_batches.delay(last_id=ids[-1])
    logger.info(f"[Weekly Competitors] Scheduled batch of {len(ids)} competitors (last_id={ids[-1]})")
    return {'queued': len(ids), 'last_id': ids[-1]}


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_topics_for_domain_task(self, domain_id: int):
    """
    Process topics for a domain by grouping keywords using NLP
    Triggered when domain processing_status becomes COMP
    
    Args:
        domain_id: ID of domain to process topics for
    """
    from shared_models.models import Domain
    from core.topic_processor import TopicProcessor
    from core.topic_analytics_processor import TopicAnalyticsProcessor
    
    try:
        domain = Domain.objects.get(id=domain_id)
        
        # Step 1: Group keywords into topics
        logger.info(f"Starting topic processing for domain {domain_id}")
        topic_processor = TopicProcessor()
        result = topic_processor.process_topics_for_domain(domain)
        
        if not result.get('success'):
            logger.error(f"Topic processing failed for domain {domain_id}: {result.get('message')}")
            return result
        
        # Step 2: Process topic analytics
        logger.info(f"Starting topic analytics processing for domain {domain_id}")
        analytics_processor = TopicAnalyticsProcessor()
        analytics_result = analytics_processor.process_analytics_for_domain(domain)
        
        if not analytics_result.get('success'):
            logger.error(f"Topic analytics processing failed for domain {domain_id}: {analytics_result.get('message')}")
            return analytics_result
        
        logger.info(f"Successfully completed topic processing for domain {domain_id}")
        return {
            'success': True,
            'topics_created': result.get('topics_created', 0),
            'keywords_processed': analytics_result.get('keywords_processed', 0),
            'topics_processed': analytics_result.get('topics_processed', 0)
        }
        
    except Domain.DoesNotExist:
        logger.error(f"Domain {domain_id} not found")
        return {'error': 'domain_not_found'}
    except Exception as e:
        logger.error(f"Error processing topics for domain {domain_id}: {str(e)}", exc_info=True)
        return {'error': str(e)}


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_topic_analytics_scheduler(self):
    """
    Periodic scheduler for topic analytics updates.
    Runs via Celery Beat to continuously update topic analytics when new prompts are processed.
    """
    from core.topic_analytics_processor import TopicAnalyticsProcessor
    
    try:
        processor = TopicAnalyticsProcessor()
        result = processor.schedule_tick()
        logger.debug(f"Topic analytics scheduler tick: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in topic analytics scheduler: {str(e)}", exc_info=True)
        return {'scheduled': False, 'error': str(e)}


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_misinformation_scan_task(self, domain_id: int, prompt_analytics_ids: list = None):
    """
    Process misinformation scan for a domain.
    
    Args:
        domain_id: ID of the domain to scan
        prompt_analytics_ids: Optional list of specific prompt analytics IDs to scan
    """
    try:
        processor = MisinformationProcessor()
        scan = processor.process_domain(domain_id, prompt_analytics_ids)
        logger.info(f"Misinformation scan completed for domain {domain_id}: scan_id={scan.id}")
        return {'scan_id': scan.id, 'status': 'completed'}
    except Exception as e:
        logger.error(f"Error processing misinformation scan for domain {domain_id}: {str(e)}", exc_info=True)
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_ga_insights_task(self, integration_id: int, days_back: int = 30):
    """Process GA insights for an integration (legacy - kept for backward compatibility)"""
    processor = GAInsightsProcessor()
    return processor.process_integration(integration_id, days_back)


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_gsc_insights_task(self, integration_id: int, days_back: int = 30):
    """Process GSC insights for an integration (legacy - kept for backward compatibility)"""
    processor = GSCInsightsProcessor()
    return processor.process_integration(integration_id, days_back)


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_ga_insight_task(self, insight_id: int):
    """Process a single GA insight record"""
    try:
        logger.info(f"[GA Task] Starting processing for insight {insight_id}")
        processor = GAInsightsProcessor()
        result = processor.process_insight(insight_id)
        logger.info(f"[GA Task] Completed processing for insight {insight_id}: {result.get('success', False)}")
        return result
    except Exception as e:
        logger.error(f"[GA Task] Error processing insight {insight_id}: {str(e)}", exc_info=True)
        raise


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_gsc_insight_task(self, insight_id: int):
    """Process a single GSC insight record"""
    try:
        logger.info(f"[GSC Task] Starting processing for insight {insight_id}")
        processor = GSCInsightsProcessor()
        result = processor.process_insight(insight_id)
        logger.info(f"[GSC Task] Completed processing for insight {insight_id}: {result.get('success', False)}")
        return result
    except Exception as e:
        logger.error(f"[GSC Task] Error processing insight {insight_id}: {str(e)}", exc_info=True)
        raise


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_integration_insights_scheduler(self):
    """Scheduler to pick up INIT records and process them one by one"""
    from integrations.models import GATrafficInsight, GSCTrafficInsight
    
    logger.info("[Integration Scheduler] Starting scheduler run")
    processed = 0
    
    # Process GA insights with INIT status (one at a time)
    # Use select_for_update to prevent race conditions
    try:
        # First, count how many INIT records match criteria
        init_count = GATrafficInsight.objects.filter(
            track_status='INIT',
            integration__status='active',
            integration__provider_id__isnull=False
        ).exclude(integration__provider_id='').count()
        logger.info(f"[Integration Scheduler] Found {init_count} GA INIT records matching criteria")
        
        with transaction.atomic():
            # Change nowait=True to nowait=False to wait for locks instead of failing silently
            ga_insight = GATrafficInsight.objects.select_for_update(nowait=False).filter(
                track_status='INIT',
                integration__status='active',  # Only process active integrations
                integration__provider_id__isnull=False
            ).exclude(integration__provider_id='').order_by('created_at').first()
            
            if ga_insight:
                logger.info(f"[Integration Scheduler] Found GA insight {ga_insight.id} (domain {ga_insight.domain_id}, integration {ga_insight.integration.id})")
                # Check if same integration is already processing
                proc_exists = GATrafficInsight.objects.filter(
                    integration=ga_insight.integration,
                    track_status='PROC'
                ).exists()
                
                if not proc_exists:
                    logger.info(f"[Integration Scheduler] Dispatching process_ga_insight_task for insight {ga_insight.id}")
                    process_ga_insight_task.delay(ga_insight.id)
                    processed += 1
                else:
                    logger.info(f"[Integration Scheduler] Integration {ga_insight.integration.id} already has a PROC insight, skipping")
            else:
                logger.info("[Integration Scheduler] No GA insight found matching criteria")
    except Exception as e:
        logger.error(f"[Integration Scheduler] Error processing GA insights: {str(e)}", exc_info=True)
    
    # Process GSC insights with INIT status (one at a time)
    try:
        # Count GSC INIT records
        gsc_init_count = GSCTrafficInsight.objects.filter(
            track_status='INIT',
            integration__status='active',
            integration__provider_id__isnull=False
        ).exclude(integration__provider_id='').count()
        logger.info(f"[Integration Scheduler] Found {gsc_init_count} GSC INIT records matching criteria")
        
        with transaction.atomic():
            # Change nowait=True to nowait=False to wait for locks instead of failing silently
            gsc_insight = GSCTrafficInsight.objects.select_for_update(nowait=False).filter(
                track_status='INIT',
                integration__status='active',  # Only process active integrations
                integration__provider_id__isnull=False
            ).exclude(integration__provider_id='').order_by('created_at').first()
            
            if gsc_insight:
                logger.info(f"[Integration Scheduler] Found GSC insight {gsc_insight.id} (domain {gsc_insight.domain_id}, integration {gsc_insight.integration.id})")
                # Check if same integration is already processing
                proc_exists = GSCTrafficInsight.objects.filter(
                    integration=gsc_insight.integration,
                    track_status='PROC'
                ).exists()
                
                if not proc_exists:
                    logger.info(f"[Integration Scheduler] Dispatching process_gsc_insight_task for insight {gsc_insight.id}")
                    process_gsc_insight_task.delay(gsc_insight.id)
                    processed += 1
                else:
                    logger.info(f"[Integration Scheduler] Integration {gsc_insight.integration.id} already has a PROC insight, skipping")
            else:
                logger.info("[Integration Scheduler] No GSC insight found matching criteria")
    except Exception as e:
        logger.error(f"[Integration Scheduler] Error processing GSC insights: {str(e)}", exc_info=True)
    
    logger.info(f"[Integration Scheduler] Scheduler run completed. Processed: {processed}")
    return {'processed': processed}


# ==================== REPORT EMAIL PROCESSING ====================

@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_report_email_scheduler(self):
    """
    Periodic scheduler for report email delivery.
    Checks for due scheduled reports and sends them via email.
    Runs every 15 seconds (configurable via CELERY_BEAT_SCHEDULE_REPORT_EMAIL).
    """
    try:
        from .report_email_processor import ReportEmailProcessor
        
        processor = ReportEmailProcessor()
        result = processor.process_due_reports()
        
        logger.info(
            f"Report email scheduler tick completed: "
            f"processed={result['processed']}, "
            f"successful={result['successful']}, "
            f"failed={result['failed']}"
        )
        
        return result
    except Exception as e:
        logger.error(f"Error in report email scheduler: {str(e)}", exc_info=True)
        raise self.retry(exc=e, countdown=60)  # Retry after 60 seconds on error


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_single_report_email_task(self, scheduled_report_id: int):
    """
    Process a single scheduled report immediately (manual trigger).
    
    Args:
        scheduled_report_id: ID of scheduled report to process
    """
    from shared_models.models import ScheduledReport
    from .report_email_processor import ReportEmailProcessor
    
    try:
        scheduled_report = ScheduledReport.objects.get(id=scheduled_report_id)
        
        processor = ReportEmailProcessor()
        result = processor._process_single_scheduled_report(scheduled_report)
        
        logger.info(f"Processed scheduled report {scheduled_report_id}: {result['message']}")
        return result
    except ScheduledReport.DoesNotExist:
        logger.error(f"Scheduled report {scheduled_report_id} not found")
        return {'success': False, 'message': 'Scheduled report not found'}
    except Exception as e:
        logger.error(f"Error processing scheduled report {scheduled_report_id}: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60)


# ==================== SEO RANKING PROCESSING ====================

@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_seo_keyword_task(self, seo_keyword_rank_id: int):
    """
    Process a single SEO keyword: fetch SERP data via ScrapingDog, parse, save rank.

    Args:
        seo_keyword_rank_id: ID of SeoKeywordRank to process
    """
    try:
        from core.seo_ranking_processor import SeoRankingProcessor
        processor = SeoRankingProcessor()
        result = processor.process_single_keyword(seo_keyword_rank_id)
        logger.info(f"[SEO] Processed keyword {seo_keyword_rank_id}: success={result}")
        return {'success': result, 'seo_keyword_rank_id': seo_keyword_rank_id}
    except Exception as e:
        logger.error(f"[SEO] Error processing keyword {seo_keyword_rank_id}: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=30)


@shared_task(
    bind=True,
    ignore_result=True,
    max_retries=0,
    soft_time_limit=7200,   # 2 hours soft limit (raises SoftTimeLimitExceeded)
    time_limit=7500,        # 2h 5min hard kill
    acks_late=True,         # Re-deliver task if worker crashes before completion
    reject_on_worker_lost=True,  # Reject task if worker is killed (prevents re-queue loop)
)
def process_seo_domain_task(self, domain_id: int):
    """
    Process all SEO keywords for a domain: fetch SERP, parse, save, recalculate metrics.

    This task never retries because process_domain_rankings handles all errors
    internally (per-keyword try/except). Retrying would re-process already-done
    keywords, wasting API credits.

    Args:
        domain_id: ID of Domain to process all SEO keywords for
    """
    try:
        from core.seo_ranking_processor import SeoRankingProcessor
        processor = SeoRankingProcessor()
        result = processor.process_domain_rankings(domain_id)
        logger.info(f"[SEO] Domain {domain_id} processing complete: {result}")
        return result
    except Exception as e:
        logger.error(f"[SEO] Error processing domain {domain_id}: {e}", exc_info=True)
    finally:
        # Clean up keywords stuck in 'busy' (worker crashed mid-processing).
        # Do NOT mark 'avail' as 'fail' — they should remain available for the next run.
        try:
            from shared_models.seo_models import SeoKeywordRank
            stuck = SeoKeywordRank.objects.filter(
                domain_id=domain_id,
                auto_call_status='busy'
            ).update(auto_call_status='avail')
            if stuck > 0:
                logger.warning(f"[SEO] Reset {stuck} stuck 'busy' keywords back to 'avail' for domain {domain_id}")
        except Exception:
            pass


@shared_task(bind=True, ignore_result=True)
def seo_rankings_daily_scheduler(self):
    """
    Daily scheduler: resets all 'done'/'fail'/'busy' keywords back to 'avail'
    for every domain that has SEO keywords, then dispatches processing tasks.
    """
    from shared_models.seo_models import SeoKeywordRank
    try:
        # Find all domains that have SEO keywords
        domain_ids = list(
            SeoKeywordRank.objects.values_list('domain_id', flat=True).distinct()
        )
        logger.info(f"[SEO Scheduler] Found {len(domain_ids)} domains with SEO keywords")

        for domain_id in domain_ids:
            # Reset all keyword statuses to 'avail'
            reset_count = SeoKeywordRank.objects.filter(
                domain_id=domain_id,
                auto_call_status__in=['done', 'fail', 'busy']
            ).update(auto_call_status='avail')

            if reset_count > 0:
                logger.info(f"[SEO Scheduler] Domain {domain_id}: reset {reset_count} keywords to 'avail'")
                # Dispatch processing task for this domain
                process_seo_domain_task.delay(domain_id)

    except Exception as e:
        logger.error(f"[SEO Scheduler] Error: {e}", exc_info=True)


@shared_task(bind=True, ignore_result=True, max_retries=3)
def analyze_seo_competitors_task(self, domain_id: int):
    """
    Aggregate competitor domains from stored SERP snippets_details for a domain.
    Reads snippets_details.competitors from each keyword and tallies frequency.

    Args:
        domain_id: ID of Domain to analyze competitors for
    """
    try:
        from core.seo_competitor_processor import analyze_competitors_for_domain
        result = analyze_competitors_for_domain(domain_id)
        logger.info(f"[CompAnalysis] Domain {domain_id}: {result}")
        return result
    except Exception as e:
        logger.error(f"[CompAnalysis] Error for domain {domain_id}: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=30)
