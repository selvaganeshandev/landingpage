import logging
import requests
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from shared_models.models import ScheduledPublication, CMSProvider, GeneratedContent, Account
from .mailgun_email_service import MailgunEmailService


logger = logging.getLogger(__name__)


class CMSManagerProcessor:
    """
    Processor to publish scheduled content to configured CMS providers.
    Runs in the engine; relies on read-only shared_models mapped to backend tables.
    """

    def __init__(self, batch_size=20):
        self.batch_size = batch_size
        self.mailer = MailgunEmailService()

    # ------------------------- Public entrypoint ------------------------- #
    def schedule_tick(self):
        """
        Pick due scheduled publications and publish them.
        """
        now = timezone.now()
        # Lock a small batch to avoid double-processing
        due_qs = (
            ScheduledPublication.objects
            .select_related('content', 'cms_provider', 'cms_provider__domain')
            .filter(status='scheduled', scheduled_at__lte=now)
            .order_by('scheduled_at')[: self.batch_size]
        )

        picked = []
        for sp in due_qs:
            try:
                with transaction.atomic():
                    locked = ScheduledPublication.objects.select_for_update().get(id=sp.id)
                    if locked.status != 'scheduled':
                        continue
                    locked.status = 'publishing'
                    locked.save(update_fields=['status', 'modified_at'])
                    picked.append(locked)
            except ScheduledPublication.DoesNotExist:
                continue

        results = []
        for sp in picked:
            result = self._publish_single(sp)
            results.append(result)
        return {"processed": len(results), "details": results}

    # ------------------------- Publish helpers -------------------------- #
    def _publish_single(self, sp: ScheduledPublication):
        provider = sp.cms_provider
        content = sp.content
        try:
            if provider.provider_type == 'wordpress':
                success, data, error = self._publish_wordpress(content, provider)
            elif provider.provider_type == 'strapi':
                success, data, error = self._publish_strapi(content, provider)
            elif provider.provider_type == 'joomla':
                success, data, error = self._publish_joomla(content, provider)
            elif provider.provider_type == 'contentful':
                success, data, error = self._publish_contentful(content, provider)
            else:
                success, data, error = False, None, f"Provider {provider.provider_type} not supported"

            with transaction.atomic():
                sp = ScheduledPublication.objects.select_for_update().get(id=sp.id)
                if success:
                    sp.status = 'published'
                    sp.published_at = timezone.now()
                    sp.error_message = None
                    if provider.provider_type == 'wordpress':
                        sp.wordpress_post_id = data.get('id')
                        sp.wordpress_post_url = data.get('link')
                    if provider.provider_type == 'strapi':
                        sp.strapi_entry_id = data.get('id')
                        sp.strapi_entry_url = data.get('link') or data.get('url') or data.get('data', {}).get('url')
                    sp.save(update_fields=[
                        'status', 'published_at', 'error_message',
                        'wordpress_post_id', 'wordpress_post_url',
                        'strapi_entry_id', 'strapi_entry_url',
                        'modified_at'
                    ])
                    # Update content status
                    GeneratedContent.objects.filter(id=content.id).update(
                        status='published',
                        published_date=sp.published_at,
                        modified_at=timezone.now()
                    )
                    # Notify domain owners/admins
                    self._notify_publish(sp, provider, content, data)
                    return {"id": sp.id, "status": "published"}
                else:
                    sp.status = 'failed'
                    sp.error_message = error or 'Unknown error'
                    sp.save(update_fields=['status', 'error_message', 'modified_at'])
                    return {"id": sp.id, "status": "failed", "error": sp.error_message}
        except Exception as e:
            logger.error(f"[cmsmanager] Error publishing scheduled {sp.id}: {e}", exc_info=True)
            try:
                with transaction.atomic():
                    sp = ScheduledPublication.objects.select_for_update().get(id=sp.id)
                    sp.status = 'failed'
                    sp.error_message = str(e)
                    sp.save(update_fields=['status', 'error_message', 'modified_at'])
            except Exception:
                pass
            return {"id": sp.id, "status": "failed", "error": str(e)}

    # ------------------------- Provider implementations ------------------ #
    def _publish_wordpress(self, content, provider):
        settings = provider.settings or {}
        api_url = settings.get('api_url')
        username = settings.get('username')
        app_password = settings.get('app_password')
        content_type = settings.get('content_type', 'pages')
        site_url = settings.get('site_url', '')

        if not api_url or not username or not app_password:
            return False, None, "WordPress settings incomplete"

        endpoint = api_url.rstrip('/') + f'/{content_type}'
        payload = {
            "title": content.title,
            "content": content.content_html or content.title,
            "status": "publish"
        }
        try:
            resp = requests.post(
                endpoint,
                json=payload,
                auth=(username, app_password),
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            if not resp.ok:
                msg = self._extract_error(resp)
                return False, None, f"WordPress API error: {msg}"
            result = resp.json()
            # Normalize link
            if site_url and not result.get('link'):
                result['link'] = f"{site_url.rstrip('/')}/?p={result.get('id')}"
            return True, result, None
        except Exception as e:
            return False, None, str(e)

    def _publish_strapi(self, content, provider):
        settings = provider.settings or {}
        api_url = settings.get('api_url')
        token = settings.get('token')
        collection = settings.get('collection', '/api/articles')

        if not api_url or not token:
            return False, None, "Strapi settings incomplete"

        endpoint = api_url.rstrip('/') + collection
        payload = {
            "data": {
                "title": content.title,
                "content": content.content_html or content.title,
                "publishedAt": timezone.now().isoformat()
            }
        }
        try:
            resp = requests.post(
                endpoint,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                timeout=30,
            )
            if not resp.ok:
                msg = self._extract_error(resp, default_key_path=['error', 'message'])
                return False, None, f"Strapi API error: {msg}"
            return True, resp.json(), None
        except Exception as e:
            return False, None, str(e)

    def _publish_joomla(self, content, provider):
        settings = provider.settings or {}
        api_url = settings.get('api_url')
        token = settings.get('token')
        endpoint_path = settings.get('endpoint', '/api/index.php/v1/content/articles')
        catid = settings.get('catid')
        state = settings.get('state', 1)

        if not api_url or not token or not catid:
            return False, None, "Joomla settings incomplete"

        endpoint = api_url.rstrip('/') + endpoint_path
        payload = {
            "title": content.title,
            "catid": catid,
            "state": state,
            "introtext": content.content_html or content.title,
            "fulltext": content.content_html or "",
            "language": "*",
            "access": 1,
        }
        try:
            resp = requests.post(
                endpoint,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                timeout=30,
            )
            if not resp.ok:
                msg = self._extract_error(resp)
                return False, None, f"Joomla API error: {msg}"
            return True, resp.json(), None
        except Exception as e:
            return False, None, str(e)

    def _publish_contentful(self, content, provider):
        settings = provider.settings or {}
        api_url = settings.get('api_url') or 'https://api.contentful.com'
        management_token = settings.get('management_token')
        space_id = settings.get('space_id')
        environment_id = settings.get('environment_id') or 'master'
        content_type_id = settings.get('content_type_id')

        if not all([management_token, space_id, environment_id, content_type_id]):
            return False, None, "Contentful settings incomplete"

        base = api_url.rstrip('/')
        create_endpoint = f"{base}/spaces/{space_id}/environments/{environment_id}/entries"
        rich_body = self._html_to_contentful_rich_text(content.content_html or content.title)
        fields_payload = {
            "fields": {
                "title": {"en-US": content.title},
                "body": {"en-US": rich_body},
            }
        }

        try:
            create_resp = requests.post(
                create_endpoint,
                json=fields_payload,
                headers={
                    "Authorization": f"Bearer {management_token}",
                    "Content-Type": "application/vnd.contentful.management.v1+json",
                    "X-Contentful-Content-Type": content_type_id,
                },
                timeout=30,
            )
            if not create_resp.ok:
                msg = self._extract_error(create_resp)
                return False, None, f"Contentful create error: {msg}"

            entry_data = create_resp.json()
            entry_id = entry_data.get('sys', {}).get('id')
            entry_version = entry_data.get('sys', {}).get('version')
            if not entry_id or entry_version is None:
                return False, None, "Contentful response missing entry id/version"

            publish_endpoint = f"{base}/spaces/{space_id}/environments/{environment_id}/entries/{entry_id}/published"
            publish_resp = requests.put(
                publish_endpoint,
                headers={
                    "Authorization": f"Bearer {management_token}",
                    "X-Contentful-Version": str(entry_version),
                },
                timeout=30,
            )
            if not publish_resp.ok:
                msg = self._extract_error(publish_resp)
                return False, None, f"Contentful publish error: {msg}"

            return True, {"entry": entry_data, "publish": publish_resp.json()}, None
        except Exception as e:
            return False, None, str(e)

    # ------------------------- Utilities ------------------------- #
    def _extract_error(self, resp, default_key_path=None):
        try:
            data = resp.json()
            if default_key_path:
                d = data
                for key in default_key_path:
                    if isinstance(d, dict):
                        d = d.get(key)
                    else:
                        break
                if d:
                    return d
            return data.get('message') or str(data)
        except Exception:
            return resp.text

    def _html_to_contentful_rich_text(self, html_content: str):
        """
        Lightweight HTML -> Contentful Rich Text:
        - Splits by <p> tags into paragraphs
        - Strips HTML tags inside each paragraph
        - Falls back to a single paragraph if no <p> present
        - Text-only (no marks/links); safe default for CMS ingestion
        """
        import re
        if not html_content:
            return {"nodeType": "document", "data": {}, "content": []}

        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html_content, flags=re.IGNORECASE | re.DOTALL)
        if not paragraphs:
            paragraphs = [html_content]

        def strip_tags(txt: str) -> str:
            return re.sub(r'<[^>]+>', '', txt).strip()

        contents = []
        for para in paragraphs:
            text = strip_tags(para)
            if not text:
                continue
            contents.append(
                {
                    "nodeType": "paragraph",
                    "data": {},
                    "content": [
                        {
                            "nodeType": "text",
                            "value": text,
                            "marks": [],
                            "data": {}
                        }
                    ]
                }
            )

        return {
            "nodeType": "document",
            "data": {},
            "content": contents or [
                {
                    "nodeType": "paragraph",
                    "data": {},
                    "content": [
                        {
                            "nodeType": "text",
                            "value": strip_tags(html_content),
                            "marks": [],
                            "data": {}
                        }
                    ]
                }
            ]
        }

    def _notify_publish(self, sp, provider, content, data):
        """
        Send a simple notification email to org admins when a publish succeeds.
        """
        try:
            org_id = provider.domain.organisation_id
            recipients = list(
                Account.objects.filter(
                    organisation_id=org_id,
                    role__in=['super_admin', 'admin'],
                    is_active=True
                ).values_list('email', flat=True)
            )
            if not recipients:
                return

            link = None
            if provider.provider_type == 'wordpress':
                link = data.get('link')
            elif provider.provider_type == 'strapi':
                link = data.get('link') or data.get('url') or data.get('data', {}).get('url')

            subject = f"[CMS] Published: {content.title}"
            body_lines = [
                f"Title: {content.title}",
                f"Provider: {provider.provider_type}",
                f"CMS Config: {provider.name}",
                f"Scheduled ID: {sp.id}",
            ]
            if link:
                body_lines.append(f"Link: {link}")
            if provider.provider_type == 'contentful':
                entry = data.get('entry', {})
                entry_id = entry.get('sys', {}).get('id')
                if entry_id:
                    body_lines.append(f"Contentful Entry ID: {entry_id}")

            body = "\n".join(body_lines)
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com')
            self.mailer.send_email(
                subject=subject,
                text=body,
                recipients=recipients,
                from_email=from_email,
            )
        except Exception as e:
            logger.warning(f"[cmsmanager] Failed to send publish notification: {e}", exc_info=True)


