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
from . import weekly_sweep_guard
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

    # Reaper: any domain stuck in SCHD past STALE_SCHD_MINUTES is from a worker
    # that died (deploy, kill -9, OOM). Reset it to INIT so the picker below
    # re-queues it on this same tick. Default 15min — long enough that healthy
    # in-progress work isn't disturbed, short enough that crashes self-heal.
    from datetime import timedelta
    stale_minutes = getattr(settings, 'STALE_SCHD_MINUTES', 15)
    stale_cutoff = timezone.now() - timedelta(minutes=stale_minutes)
    reaped = Domain.objects.filter(
        processing_status='SCHD',
        tracked_at__lt=stale_cutoff,
    ).update(processing_status='INIT', modified_at=timezone.now())
    if reaped:
        logger.warning(
            "[scheduler_tick] Reaped %s stale SCHD domain(s) (older than %sm) back to INIT",
            reaped, stale_minutes,
        )

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


@shared_task(bind=True, ignore_result=True, max_retries=1)
def refresh_domain_prompts_task(self, domain_id):
    """Re-run all of ONE domain's prompts on demand (the per-domain twin of the
    weekly sweep, powering the 'Track Prompts' button). Resets the domain's
    prompts (except in-flight PROC) to INIT and enqueues a processing task for
    each, so their mention data is refreshed across every enabled platform.
    Costs tokens, which is why the UI confirms before calling this."""
    now = timezone.now()
    ids = list(
        Prompt.objects
        .filter(group__domain_id=domain_id)
        .exclude(track_status='PROC')  # never clobber in-flight work
        .order_by('id')
        .values_list('id', flat=True)
    )
    if not ids:
        logger.info(f"[Track Prompts] domain {domain_id}: no prompts to refresh")
        return {'domain_id': domain_id, 'count': 0}
    for pid in ids:
        Prompt.objects.filter(id=pid).update(
            track_status='INIT',
            track_message=f"Manual refresh scheduled at {now}",
            modified_at=now,
        )
        process_prompt_analytics_task.delay(pid)
    logger.info(f"[Track Prompts] domain {domain_id}: re-queued {len(ids)} prompts")
    return {'domain_id': domain_id, 'count': len(ids)}


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_prompt_analytics_task(self, prompt_id):
    processor = PromptAnalyticsProcessor(max_concurrent_prompts=getattr(settings, 'MAX_CONCURRENT_PROMPT_ANALYTICS', 10))
    return processor.process_single_prompt(prompt_id)


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_prompt_analytics_scheduler(self):
    processor = PromptAnalyticsProcessor(max_concurrent_prompts=getattr(settings, 'MAX_CONCURRENT_PROMPT_ANALYTICS', 10))
    return processor.schedule_tick()


# NOTE: max_retries here is inert — there is no autoretry_for and no self.retry()
# call, so a failure ends the task. Do not add a retry without also passing
# force=True on the retried entry call: a retry reuses the original args, so it
# would come back with last_id=0 and be refused by the cooldown this same run
# recorded, silently turning a retry into a no-op.
@shared_task(bind=True, ignore_result=True, max_retries=3)
def schedule_weekly_prompt_batches(self, last_id: int = 0, force: bool = False, tier: str = None):
    """
    Weekly batch re-scheduler for prompt analytics.
    - Resets prompts (excluding PROC) to INIT in batches
    - Enqueues prompt analytics tasks
    - Chains itself until all prompts are scheduled

    A full sweep is ~2,700 prompts x every enabled platform (~10,800 LLM calls),
    so it is cost-guarded on entry: refused inside the cooldown window, or when
    no enabled platform has a usable key. Pass force=True to override.

    `tier` selects which domains this run covers, per
    settings.WEEKLY_SWEEP_WEEKLY_DOMAIN_IDS:
      None       — every domain (the untiered default; unchanged behaviour)
      'weekly'   — only the listed domains
      'monthly'  — only the domains NOT listed
    The two tiers carry separate cooldown stamps so neither refuses the other,
    but they share one kill switch — see weekly_sweep_guard._KILLSWITCH_ALIAS.
    """
    weekly_ids = list(getattr(settings, 'WEEKLY_SWEEP_WEEKLY_DOMAIN_IDS', []) or [])
    # An empty list means tiering is not configured, so a 'weekly'/'monthly' run
    # would otherwise sweep everything (monthly) or nothing (weekly). Collapse to
    # the untiered sweep rather than silently doing the wrong-sized run.
    if not weekly_ids:
        tier = None

    sweep_key = (
        weekly_sweep_guard.PROMPTS_MONTHLY if tier == 'monthly'
        else weekly_sweep_guard.PROMPTS
    )
    label = f"Weekly Prompts[{tier}]" if tier else "Weekly Prompts"

    # Chained continuation batches always carry the last real prompt id (>= 1),
    # so last_id == 0 is the only true entry point. Guarding on that rather than
    # a separate flag also means in-flight chained messages from a previous
    # deploy keep running instead of being blocked by their own sweep's stamp.
    if last_id == 0:
        blocked = weekly_sweep_guard.sweep_blocked(sweep_key, force=force)
        if blocked:
            logger.warning(f"[{label}] Sweep refused: {blocked}")
            return blocked
        weekly_sweep_guard.record_sweep_start(sweep_key)

    # Skip organisations that have switched AI monitoring off. A sweep is the one
    # job that re-queries an entire org at once, so an org that is not using the
    # feature would otherwise pay for a full platform fan-out nobody reads.
    # NULL means the flag was never set — treat that as ON, so only an explicit
    # False opts an org out and no existing client is silently dropped.
    qs = (
        Prompt.objects
        .exclude(track_status='PROC')  # don't clobber in-flight work
        .exclude(group__domain__organisation__using_ai_monitoring=False)
        .filter(id__gt=last_id)
    )
    if tier == 'weekly':
        qs = qs.filter(group__domain_id__in=weekly_ids)
    elif tier == 'monthly':
        qs = qs.exclude(group__domain_id__in=weekly_ids)
    qs = qs.order_by('id').values_list('id', flat=True)[:WEEKLY_PROMPT_BATCH_SIZE]

    ids = list(qs)
    if not ids:
        logger.info(f"[{label}] No more prompts to schedule")
        return {'done': True}

    now = timezone.now()
    try:
        for pid in ids:
            Prompt.objects.filter(id=pid).update(
                track_status='INIT',
                track_message=f"Weekly reprocess scheduled at {now}",
                modified_at=now,
            )
            process_prompt_analytics_task.delay(pid)

        # Chain next batch. `tier` MUST ride along: without it the continuation
        # would drop back to the untiered queryset and sweep the whole corpus,
        # which is the exact cost this tiering exists to avoid.
        schedule_weekly_prompt_batches.delay(last_id=ids[-1], tier=tier)
    except Exception:
        # The cooldown was stamped before any work was enqueued, so a crash here
        # leaves a partial sweep that will NOT retry on its own and will be
        # refused for the next WEEKLY_SWEEP_COOLDOWN_DAYS. Say so loudly — a
        # generic task-failure line does not tell an operator what to do.
        # The recovery commands carry `tier` for the same reason the chain does —
        # resuming without it would restart as a full-corpus sweep.
        tier_arg = f", tier={tier!r}" if tier else ""
        if last_id == 0:
            logger.error(
                f"[{label}] Entry batch failed AFTER the cooldown was recorded. "
                f"The sweep is partial and will be refused until the cooldown expires. "
                f"Re-run with: schedule_weekly_prompt_batches.delay(force=True{tier_arg})",
                exc_info=True,
            )
        else:
            logger.error(
                f"[{label}] Batch failed at last_id={last_id}; sweep is incomplete. "
                f"Resume with: schedule_weekly_prompt_batches.delay(last_id={last_id}{tier_arg})",
                exc_info=True,
            )
        raise

    logger.info(f"[{label}] Scheduled batch of {len(ids)} prompts (last_id={ids[-1]})")
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


@shared_task(bind=True, ignore_result=True, max_retries=1)
def quota_alert_scheduler(self):
    """
    Periodic LLM credit/quota monitor.

    Probes every configured (paid) provider key and emails QUOTA_ALERT_RECIPIENTS
    when a key is depleted/erroring or recovers (deduped via a state file). Never
    raises into the beat loop — quota checks must not break processing.
    """
    try:
        from .quota_monitor import run_quota_check_and_alert
        result = run_quota_check_and_alert()
        logger.info(f"Quota alert check completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in quota alert scheduler: {str(e)}", exc_info=True)
        return {'error': str(e)}


@shared_task(bind=True, ignore_result=True, max_retries=1)
def send_daily_usage_digests(self):
    """
    Nightly Content Generation usage digest.

    Emails every active super-admin of each organisation with a configured
    Content Generation key a consolidated today + month-to-date token report.
    Always sends (even on zero usage). Never raises into the beat loop.
    """
    try:
        from .usage_digest import run_daily_usage_digests
        result = run_daily_usage_digests()
        logger.info(f"Daily usage digest completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in daily usage digest task: {str(e)}", exc_info=True)
        return {'error': str(e)}


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
def schedule_weekly_competitor_batches(self, last_id: int = 0, force: bool = False):
    """
    Weekly batch re-scheduler for competitor analytics.
    - Resets competitors (excluding PROC) to INIT in batches
    - Enqueues competitor processing tasks
    - Chains itself until all competitors are scheduled

    Cost-guarded on entry exactly like schedule_weekly_prompt_batches, under its
    own cooldown so the two sweeps never consume each other's window.
    """
    if last_id == 0:
        blocked = weekly_sweep_guard.sweep_blocked(weekly_sweep_guard.COMPETITORS, force=force)
        if blocked:
            logger.warning(f"[Weekly Competitors] Sweep refused: {blocked}")
            return blocked
        weekly_sweep_guard.record_sweep_start(weekly_sweep_guard.COMPETITORS)

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
    try:
        for cid in ids:
            Competitor.objects.filter(id=cid).update(
                track_status='INIT',
                track_message=f"Weekly reprocess scheduled at {now}",
                modified_at=now,
            )
            process_single_competitor_task.delay(cid)

        # Chain next batch
        schedule_weekly_competitor_batches.delay(last_id=ids[-1])
    except Exception:
        # See the note in schedule_weekly_prompt_batches — the cooldown is
        # already spent, so the operator needs to know to force a re-run.
        if last_id == 0:
            logger.error(
                "[Weekly Competitors] Entry batch failed AFTER the cooldown was recorded. "
                "The sweep is partial and will be refused until the cooldown expires. "
                "Re-run with: schedule_weekly_competitor_batches.delay(force=True)",
                exc_info=True,
            )
        else:
            logger.error(
                f"[Weekly Competitors] Batch failed at last_id={last_id}; sweep is incomplete. "
                f"Resume with: schedule_weekly_competitor_batches.delay(last_id={last_id})",
                exc_info=True,
            )
        raise

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
    from core import topic_progress

    try:
        domain = Domain.objects.get(id=domain_id)

        # Step 1: Group keywords into topics
        logger.info(f"Starting topic processing for domain {domain_id}")
        topic_progress.write(domain_id, state='running', stage='grouping', task_id=self.request.id)
        topic_processor = TopicProcessor()
        result = topic_processor.process_topics_for_domain(domain)

        if not result.get('success'):
            logger.error(f"Topic processing failed for domain {domain_id}: {result.get('message')}")
            topic_progress.fail(domain_id, result.get('message') or 'Topic grouping failed')
            return result

        topic_progress.write(
            domain_id,
            stage='analytics',
            topics_created=result.get('topics_created', 0),
        )
        
        # Step 2: Process topic analytics
        logger.info(f"Starting topic analytics processing for domain {domain_id}")
        analytics_processor = TopicAnalyticsProcessor()
        analytics_result = analytics_processor.process_analytics_for_domain(domain)
        
        if not analytics_result.get('success'):
            logger.error(f"Topic analytics processing failed for domain {domain_id}: {analytics_result.get('message')}")
            # The topics themselves exist by this point, so the run is finished
            # as far as the page is concerned — analytics fill in on the next
            # scheduler tick.
            topic_progress.finish(domain_id, result.get('topics_created', 0))
            return analytics_result

        logger.info(f"Successfully completed topic processing for domain {domain_id}")
        topic_progress.finish(domain_id, result.get('topics_created', 0))
        return {
            'success': True,
            'topics_created': result.get('topics_created', 0),
            'keywords_processed': analytics_result.get('keywords_processed', 0),
            'topics_processed': analytics_result.get('topics_processed', 0)
        }

    except Domain.DoesNotExist:
        logger.error(f"Domain {domain_id} not found")
        topic_progress.fail(domain_id, 'Domain not found')
        return {'error': 'domain_not_found'}
    except Exception as e:
        logger.error(f"Error processing topics for domain {domain_id}: {str(e)}", exc_info=True)
        topic_progress.fail(domain_id, str(e))
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
def process_misinformation_scan_task(self, domain_id: int, prompt_analytics_ids: list = None,
                                     own_links_only: bool = False):
    """
    Process misinformation scan for a domain.

    Args:
        domain_id: ID of the domain to scan
        prompt_analytics_ids: Optional list of specific prompt analytics IDs to scan
        own_links_only: Skip citations that don't point at the domain's own site
    """
    try:
        processor = MisinformationProcessor()
        scan = processor.process_domain(domain_id, prompt_analytics_ids, own_links_only)
        logger.info(f"Misinformation scan completed for domain {domain_id}: scan_id={scan.id}")
        return {'scan_id': scan.id, 'status': 'completed'}
    except Exception as e:
        logger.error(f"Error processing misinformation scan for domain {domain_id}: {str(e)}", exc_info=True)
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_ga_insights_task(self, integration_id: int, days_back: int = 30):
    """Build and fetch today's rolling `days_back`-day GA insight for an integration.

    Dispatched by schedule_all_rolling_insights_task. Also callable ad hoc to
    force a refresh for one integration.
    """
    processor = GAInsightsProcessor()
    return processor.process_integration(integration_id, days_back)


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_gsc_insights_task(self, integration_id: int, days_back: int = 30):
    """Build and fetch today's rolling `days_back`-day GSC insight for an integration.

    Dispatched by schedule_all_rolling_insights_task. Also callable ad hoc to
    force a refresh for one integration.
    """
    processor = GSCInsightsProcessor()
    return processor.process_integration(integration_id, days_back)


@shared_task(bind=True, ignore_result=True, max_retries=1)
def sync_gsc_keyword_metrics_task(self, integration_id: int):
    """Copy per-keyword Search Console clicks/impressions onto tracked SEO keywords.

    Dispatched by schedule_all_rolling_insights_task. Also callable ad hoc to
    refresh one integration.
    """
    processor = GSCInsightsProcessor()
    result = processor.sync_keyword_metrics(integration_id)
    logger.info(f"[GSC Keywords] integration={integration_id} result={result}")
    return result


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


@shared_task(bind=True, ignore_result=True, max_retries=2)
def schedule_ga_monthly_insights_task(self, integration_id: int):
    """
    Create/reset the three calendar-month GA insight records (current_month,
    prev_month, yoy_month) so the integration scheduler can pick them up and
    fetch data from the GA API.  Should be triggered once per day per integration.
    """
    try:
        processor = GAInsightsProcessor()
        result = processor.process_monthly_insights(integration_id)
        logger.info(f"[GA Monthly] integration={integration_id} result={result}")
        return result
    except Exception as e:
        logger.error(f"[GA Monthly] Error for integration {integration_id}: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, ignore_result=True, max_retries=2)
def schedule_gsc_monthly_insights_task(self, integration_id: int):
    """
    Create/reset the three calendar-month GSC insight records (current_month,
    prev_month, yoy_month) so the integration scheduler can pick them up and
    fetch data from the GSC API.  Should be triggered once per day per integration.
    """
    try:
        processor = GSCInsightsProcessor()
        result = processor.process_monthly_insights(integration_id)
        logger.info(f"[GSC Monthly] integration={integration_id} result={result}")
        return result
    except Exception as e:
        logger.error(f"[GSC Monthly] Error for integration {integration_id}: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, ignore_result=True, max_retries=0)
def schedule_all_monthly_insights_task(self):
    """
    Daily beat task: iterate all active GA and GSC integrations and schedule
    their monthly insight records for MOM/YOY reporting.
    """
    from integrations.models import Integration
    scheduled = {'ga': 0, 'gsc': 0}

    ga_integrations = Integration.objects.filter(type='google_analytics', status='active').exclude(provider_id='')
    for integration in ga_integrations:
        schedule_ga_monthly_insights_task.delay(integration.id)
        scheduled['ga'] += 1

    gsc_integrations = Integration.objects.filter(type='search_console', status='active').exclude(provider_id='')
    for integration in gsc_integrations:
        schedule_gsc_monthly_insights_task.delay(integration.id)
        scheduled['gsc'] += 1

    logger.info(f"[Monthly Insights] Scheduled GA={scheduled['ga']} GSC={scheduled['gsc']} integrations")
    return scheduled


@shared_task(bind=True, ignore_result=True, max_retries=1)
def schedule_all_rolling_insights_task(self):
    """
    Daily beat task: refresh the rolling 30-day GA and GSC insight for every
    active integration.

    Without this the rolling window is built exactly once — at connect time by
    select_ga_property / select_gsc_site — and then frozen forever: the hourly
    INIT scheduler only picks up records that already exist, and nothing ever
    re-INITs the rolling window. Only the monthly records refreshed daily.

    Each run creates that day's (start_date, end_date) record and fetches it, so
    readers that do `.order_by('-end_date').first()` see current data, and the
    current/previous pair used for period-over-period comparison can resolve two
    distinct rows instead of collapsing onto one frozen record.

    Dispatches the per-integration tasks rather than creating INIT rows, because
    the hourly INIT scheduler deliberately processes only ONE record per tick —
    seeding it would drain at one integration per hour.
    """
    from integrations.models import Integration
    scheduled = {'ga': 0, 'gsc': 0}

    # Same filter the INIT scheduler uses: an integration with no selected
    # property/site cannot be fetched and must not be dispatched.
    ga_integrations = Integration.objects.filter(
        type='google_analytics', status='active', provider_id__isnull=False
    ).exclude(provider_id='')
    for integration in ga_integrations:
        process_ga_insights_task.delay(integration.id)
        scheduled['ga'] += 1

    gsc_integrations = Integration.objects.filter(
        type='search_console', status='active', provider_id__isnull=False
    ).exclude(provider_id='')
    for integration in gsc_integrations:
        process_gsc_insights_task.delay(integration.id)
        # Keyword table CLKS/IMPS. Separate task so a failure in one never
        # blocks the other.
        sync_gsc_keyword_metrics_task.delay(integration.id)
        scheduled['gsc'] += 1

    logger.info(f"[Rolling Insights] Scheduled GA={scheduled['ga']} GSC={scheduled['gsc']} integrations (GSC incl. keyword metrics)")
    return scheduled


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

@shared_task(bind=True, ignore_result=True, max_retries=1)
def process_seo_keyword_task(self, seo_keyword_rank_id: int):
    """
    Process a single SEO keyword: fetch SERP data via DataBlue, parse, save rank.

    max_retries=1 (not 3) because each Celery retry re-issues a full DataBlue
    request, burning an extra credit. One Celery retry covers transient infra
    issues (DB connection, OOM); transport-level failures inside the request
    surface as auto_call_status='fail' and get retried by the daily scheduler.

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
    soft_time_limit=3600,   # 1 hour soft limit
    time_limit=3900,
    acks_late=True,
    reject_on_worker_lost=True,
)
def process_new_keywords_task(
    self, domain_id: int, keyword_ids: list, batch_num: int = 1, retry_round: int = 0
):
    """
    Scrape a specific set of just-added keywords, immediately.

    This is the "someone just added keywords" path, and it is deliberately kept
    apart from `process_seo_domain_task`:

      * It runs on the `seo_instant` queue, which has its own worker. The `seo`
        queue is routinely saturated for hours by the 02:00 sweep chaining
        500-keyword batches, and a task queued behind that is not "instant" in
        any sense the person who just clicked Add would recognise.
      * It scrapes only `keyword_ids`. The domain task takes every 'avail' row
        on the domain, so on a domain with a nightly backlog an import of 20
        keywords would drag thousands of unrelated rows in with it.

    The nightly scheduler and the domain task are untouched — they remain the
    safety net for anything this path misses.
    """
    from shared_models.seo_models import SeoKeywordRank

    keyword_ids = [int(k) for k in (keyword_ids or [])]
    if not keyword_ids:
        return {'processed': 0, 'success': 0, 'failed': 0}

    result = None
    try:
        from core.seo_ranking_processor import SeoRankingProcessor
        processor = SeoRankingProcessor()
        result = processor.process_domain_rankings(
            domain_id, batch_size=500, only_ids=keyword_ids
        )
        logger.info(
            f"[SEO instant] Domain {domain_id} batch {batch_num} "
            f"({len(keyword_ids)} new keywords) complete: {result}"
        )
    except Exception as e:
        logger.error(
            f"[SEO instant] Error processing new keywords for domain {domain_id}: {e}",
            exc_info=True,
        )
    finally:
        # Release rows this run left mid-flight (worker crash / time limit), so
        # a follow-up batch or tonight's sweep can pick them up again.
        try:
            stuck = SeoKeywordRank.objects.filter(
                id__in=keyword_ids, auto_call_status='busy'
            ).update(auto_call_status='avail')
            if stuck:
                logger.warning(
                    f"[SEO instant] Reset {stuck} stuck 'busy' keywords for domain {domain_id}"
                )
        except Exception:
            pass

        # Chain the next batch over OUR keywords only, then exactly one retry
        # round for those that failed — same 2-attempt cap as the domain task.
        remaining = failed_count = 0
        try:
            remaining = SeoKeywordRank.objects.filter(
                id__in=keyword_ids, auto_call_status='avail'
            ).count()
            failed_count = SeoKeywordRank.objects.filter(
                id__in=keyword_ids, auto_call_status='fail'
            ).count()
        except Exception:
            pass

        try:
            if remaining > 0:
                process_new_keywords_task.apply_async(
                    args=[domain_id, keyword_ids],
                    kwargs={'batch_num': batch_num + 1, 'retry_round': retry_round},
                    queue='seo_instant',
                    countdown=5,
                )
            elif retry_round < 1 and failed_count > 0:
                reset = SeoKeywordRank.objects.filter(
                    id__in=keyword_ids, auto_call_status='fail'
                ).update(auto_call_status='avail')
                logger.info(
                    f"[SEO instant] Domain {domain_id}: retry round 1 — reset {reset} failed keywords"
                )
                process_new_keywords_task.apply_async(
                    args=[domain_id, keyword_ids],
                    kwargs={'batch_num': 1, 'retry_round': 1},
                    queue='seo_instant',
                    countdown=5,
                )
        except Exception as e:
            logger.error(
                f"[SEO instant] Failed to schedule follow-up for domain {domain_id}: {e}"
            )

    return result or {'processed': 0, 'success': 0, 'failed': 0}


@shared_task(
    bind=True,
    ignore_result=True,
    max_retries=0,
    soft_time_limit=7200,   # 2 hours soft limit (raises SoftTimeLimitExceeded)
    time_limit=7500,        # 2h 5min hard kill
    acks_late=True,         # Re-deliver task if worker crashes before completion
    reject_on_worker_lost=True,  # Reject task if worker is killed (prevents re-queue loop)
)
def process_seo_domain_task(self, domain_id: int, batch_num: int = 1, retry_round: int = 0):
    """
    Process SEO keywords for a domain in batches of 500.

    Each batch picks up only 'avail' keywords. When all 'avail' have drained,
    we do exactly ONE retry round: any 'fail' keywords (DataBlue timeouts,
    transient `success:false`, etc.) are reset to 'avail' and the chain
    continues. After the retry round, anything still in 'fail' stays there
    and will be picked up by tomorrow's daily scheduler — this caps the cost
    of persistent failures at 2 attempts per keyword per run.

    Chains batches until all keywords are either 'done' or 'fail' (after one
    retry). No infinite loop risk: retry_round is capped at 1 and each batch
    only picks 'avail', so the unprocessed pool strictly shrinks.

    Args:
        domain_id: ID of Domain to process SEO keywords for
        batch_num: Current batch number (1-based), used for logging
        retry_round: 0 = first pass, 1 = retry-failed pass. Capped at 1.
    """

    result = None
    try:
        from core.seo_ranking_processor import SeoRankingProcessor
        processor = SeoRankingProcessor()
        result = processor.process_domain_rankings(domain_id, batch_size=500)
        logger.info(f"[SEO] Domain {domain_id} batch {batch_num} complete: {result}")
        return result
    except Exception as e:
        logger.error(f"[SEO] Error processing domain {domain_id}: {e}", exc_info=True)
    finally:
        # Clean up keywords stuck in 'busy' (worker crashed mid-processing).
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

        # Auto-schedule follow-up task for remaining unprocessed keywords.
        # Only check 'avail' here — 'fail' keywords are handled separately
        # by the retry round below (so they get exactly one second chance
        # before being deferred to tomorrow's scheduler).
        remaining = 0
        failed_count = 0
        try:
            from shared_models.seo_models import SeoKeywordRank
            remaining = SeoKeywordRank.objects.filter(
                domain_id=domain_id,
                auto_call_status='avail'
            ).count()
            failed_count = SeoKeywordRank.objects.filter(
                domain_id=domain_id,
                auto_call_status='fail'
            ).count()
        except Exception:
            pass

        if remaining > 0:
            logger.info(
                f"[SEO] Domain {domain_id}: {remaining} keywords remaining, "
                f"scheduling batch {batch_num + 1} in 10s"
            )
            try:
                process_seo_domain_task.apply_async(
                    args=[domain_id],
                    kwargs={'batch_num': batch_num + 1, 'retry_round': retry_round},
                    countdown=10,
                )
            except Exception as e:
                logger.error(f"[SEO] Failed to schedule follow-up for domain {domain_id}: {e}")
        elif retry_round < 1 and failed_count > 0:
            # Single retry pass: reset transient failures (DataBlue timeouts,
            # success:false, etc.) back to 'avail' and run them through once
            # more. Bounded by retry_round < 1 so a keyword that fails twice
            # in the same run stays 'fail' for tomorrow's scheduler.
            try:
                from shared_models.seo_models import SeoKeywordRank
                reset = SeoKeywordRank.objects.filter(
                    domain_id=domain_id,
                    auto_call_status='fail'
                ).update(auto_call_status='avail')
                logger.info(
                    f"[SEO] Domain {domain_id}: retry round 1 — reset {reset} "
                    f"failed keywords back to 'avail', scheduling in 10s"
                )
                process_seo_domain_task.apply_async(
                    args=[domain_id],
                    kwargs={'batch_num': 1, 'retry_round': 1},
                    countdown=10,
                )
            except Exception as e:
                logger.error(f"[SEO] Failed to schedule retry for domain {domain_id}: {e}")


@shared_task(bind=True, ignore_result=True)
def seo_rankings_daily_scheduler(self):
    """
    Daily scheduler: resets keywords back to 'avail' for processing.

    Only resets keywords that were NOT already ranked today (to avoid
    re-processing keywords that completed in an earlier batch today).
    Keywords still in 'avail' from a prior incomplete run are left as-is
    so they get picked up naturally.
    """
    from shared_models.seo_models import SeoKeywordRank
    from datetime import date
    from django.utils import timezone

    today_start = timezone.make_aware(
        timezone.datetime.combine(date.today(), timezone.datetime.min.time())
    )

    try:
        # Find all domains that have SEO keywords
        domain_ids = list(
            SeoKeywordRank.objects.values_list('domain_id', flat=True).distinct()
        )
        logger.info(f"[SEO Scheduler] Found {len(domain_ids)} domains with SEO keywords")

        for domain_id in domain_ids:
            # Reset keywords that haven't been ranked today
            # (skip keywords already processed today to avoid wasting API credits)
            reset_count = SeoKeywordRank.objects.filter(
                domain_id=domain_id,
                auto_call_status__in=['done', 'fail', 'busy']
            ).exclude(
                auto_call_status='done',
                last_ranked_date__gte=today_start
            ).update(auto_call_status='avail')

            # Count total pending (including any already in 'avail' from prior runs)
            pending = SeoKeywordRank.objects.filter(
                domain_id=domain_id,
                auto_call_status='avail'
            ).count()

            if pending > 0:
                logger.info(
                    f"[SEO Scheduler] Domain {domain_id}: reset {reset_count}, "
                    f"{pending} total pending — dispatching task"
                )
                process_seo_domain_task.delay(domain_id)
            else:
                logger.info(f"[SEO Scheduler] Domain {domain_id}: all keywords already processed today")

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


@shared_task(bind=True, ignore_result=True)
def sync_keyword_volume_task(self):
    """Fetch search volume for keywords that don't have it yet.

    This is what makes a newly added brand work without anyone intervening:
    add a domain, import its keywords, and the next sweep picks them all up.

    Deliberately a sweep rather than a per-keyword hook on the add endpoints.
    DataForSEO bills per REQUEST, not per keyword — one keyword costs the same
    $0.09 as a thousand — so reacting to each insert would turn a 500-keyword
    import into 500 paid calls instead of one. Letting keywords accumulate and
    batching them is both cheaper and simpler.

    Costs nothing when there is nothing new: with no missing keywords the
    processor builds no batches and makes no API calls.
    """
    from django.conf import settings

    if not getattr(settings, 'VOLUME_SWEEP_ENABLED', True):
        logger.info("[VOLUME] Sweep disabled via VOLUME_SWEEP_ENABLED — skipping")
        return

    if not getattr(settings, 'DATAFORSEO_LOGIN', None):
        logger.warning("[VOLUME] DATAFORSEO_LOGIN not configured — skipping sweep")
        return

    from core.volume_processor import sync_keyword_volume

    try:
        result = sync_keyword_volume(only_missing=True)
    except Exception as exc:
        logger.error(f"[VOLUME] Sweep failed: {exc}", exc_info=True)
        return

    if result['requests']:
        logger.info(
            "[VOLUME] Sweep: %d keywords, %d request(s), ~$%.2f, %d written, %d no-data, %d failed batches",
            result['keywords_considered'], result['requests'], result['estimated_cost'],
            result['updated'], result['no_data'], result['failed_batches'],
        )
    else:
        logger.debug("[VOLUME] Sweep: nothing new, no API calls made")


@shared_task(bind=True, ignore_result=True, max_retries=2)
def sync_domain_volume_task(self, domain_id: int):
    """Fetch search volume for one domain's keywords, right away.

    The hourly sweep already covers every domain, but a brand whose keywords
    were just imported should not sit with blank volumes until the next :20.
    Still batched by volume_processor — DataForSEO bills per request, not per
    keyword, so a 500-keyword import is one call, not 500.
    """
    from core.volume_processor import sync_keyword_volume
    try:
        result = sync_keyword_volume(domain_id=domain_id, only_missing=True)
        logger.info(f"[VOLUME] Domain {domain_id} on-demand sweep: {result}")
        return result
    except Exception as exc:
        logger.error(f"[VOLUME] Domain {domain_id} sweep failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, ignore_result=True, max_retries=2)
def reap_stale_domain_scans(self):
    """Fail misinformation scans whose task died, and release their domains.

    A scan writes a MisinformationScan row at 'running' and the domain's
    misinformation_scan_status='SCANNING', and clears both only on completion.
    If the worker is restarted mid-run — a deploy, an OOM, a kill -9 — nothing
    ever finishes them, and the trigger skips domains with a running scan, so
    the domain is locked out for good and the UI shows "Processing" forever.
    UTI Mutual Fund and Racold were stranded this way, Racold for 13 days.

    The earlier version of this task keyed off the DOMAIN field alone, on a
    60-minute threshold, and reset it to READY while leaving the scan row at
    'running'. Two things went wrong with that once scans started taking
    hours: a healthy long scan had its domain flipped to READY an hour in (so
    the field could no longer tell "queued" from "running for hours"), and the
    stranded rows were never failed — three sat at 'running' for five days.

    Now the SCAN ROW is the source of truth. A row still 'running' after
    STALE_SCAN_HOURS is marked failed and its domain released; a row younger
    than that is left alone, and so is its domain, however long SCANNING has
    been showing. Domains at SCANNING with no running row at all (died before
    the row was written) are released as before.

    Reset rather than re-dispatch: the next completion cycle, or a user
    pressing Scan, starts it cleanly. Re-queuing from a reaper risks stacking
    duplicate scans if the original is merely slow.
    """
    from django.utils import timezone
    from datetime import timedelta
    from shared_models.models import Domain, MisinformationScan

    hours = getattr(settings, 'STALE_SCAN_HOURS', 12)
    cutoff = timezone.now() - timedelta(hours=hours)
    now = timezone.now()

    try:
        stale_scans = MisinformationScan.objects.filter(status='running', started_at__lt=cutoff)
        scan_ids = list(stale_scans.values_list('id', flat=True))
        dead_domain_ids = list(stale_scans.values_list('domain_id', flat=True).distinct())
        if scan_ids:
            stale_scans.update(
                status='failed',
                completed_at=now,
                error_message=f'Reaped: still running after {hours}h, worker presumed dead',
            )

        # Domains showing SCANNING with no live scan row behind them.
        live_domain_ids = set(
            MisinformationScan.objects.filter(status='running').values_list('domain_id', flat=True)
        )
        orphaned = Domain.objects.filter(misinformation_scan_status='SCANNING').exclude(id__in=live_domain_ids)
        orphan_ids = list(orphaned.values_list('id', flat=True))

        release = set(dead_domain_ids) | set(orphan_ids)
        if release:
            Domain.objects.filter(id__in=release, misinformation_scan_status='SCANNING').update(
                misinformation_scan_status='READY',
                modified_at=now,
            )
        if scan_ids or orphan_ids:
            logger.warning(
                "[Reaper] Failed %s scan(s) running over %sh: %s; released %s domain(s): %s",
                len(scan_ids), hours, scan_ids, len(release), sorted(release),
            )
        return {'reaped': len(scan_ids), 'scan_ids': scan_ids, 'domain_ids': sorted(release)}
    except Exception as e:
        logger.error(f"[Reaper] Error reaping stale scans: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=120)

@shared_task(bind=True, ignore_result=True, max_retries=2)
def process_prompt_generation(self, run_id: int):
    """Run one AI prompt-generation job end to end."""
    from core.prompt_generation import run_generation
    try:
        return run_generation(run_id)
    except Exception as e:
        logger.error(f"[PromptGen] task failed for run {run_id}: {e}", exc_info=True)
        raise


@shared_task(bind=True, ignore_result=True, max_retries=3)
def prompt_generation_scheduler(self):
    """Pick up queued generation runs.

    The backend has no Celery, so it hands work over by writing a row with
    status INIT — the same DB-handoff the competitor scheduler uses. Runs are
    claimed with a guarded update so two ticks can't start the same job.
    """
    from shared_models.models import PromptGenerationRun
    try:
        queued = list(
            PromptGenerationRun.objects
            .filter(status='INIT')
            .order_by('created_at')
            .values_list('id', flat=True)[:5]
        )
        started = 0
        for run_id in queued:
            # Claim it: only the tick that flips INIT -> PROC gets to enqueue.
            claimed = PromptGenerationRun.objects.filter(
                id=run_id, status='INIT'
            ).update(status='PROC', stage='ground', progress=1)
            if claimed:
                process_prompt_generation.delay(run_id)
                started += 1
        if started:
            logger.info(f"[PromptGen] started {started} run(s)")
        return {'started': started}
    except Exception as e:
        logger.error(f"[PromptGen] scheduler error: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, ignore_result=True, max_retries=0)
def fetch_backlinks_task(self, snapshot_id: int):
    """Fill in one backlink snapshot from DataForSEO.

    max_retries=0 deliberately: every attempt spends real money against a
    shared prepaid balance, so a failure must surface to the user rather than
    silently bill three times. The snapshot row records the error and leaves
    next_refresh_allowed_at null, so the user can simply press Fetch again.
    """
    from core.backlinks_processor import run_snapshot

    try:
        result = run_snapshot(int(snapshot_id))
        logger.info(f"[BL] Snapshot {snapshot_id} finished: {result}")
        return result
    except Exception as e:
        logger.error(f"[BL] Snapshot {snapshot_id} failed: {e}", exc_info=True)
        # run_snapshot already marked the row FAIL and stored the message.
        return {'snapshot_id': snapshot_id, 'status': 'FAIL', 'error': str(e)}
