"""
Quick manual test for GA monthly MOM/YOY report widget.

Usage:
    python test_ga_monthly.py "CanaraHSBCLife Insurance"
    python test_ga_monthly.py "Appkodes"
    python test_ga_monthly.py "Hitasoft"
"""
import sys, os, django, calendar
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor.settings')
django.setup()

from integrations.models import Integration, GATrafficInsight
from integrations.utils.prorate import apply_prorate_ga

# ── 1. Domain ──────────────────────────────────────────────────────────────
DOMAIN = sys.argv[1] if len(sys.argv) > 1 else 'CanaraHSBCLife Insurance'

try:
    integration = Integration.objects.get(
        domain__name=DOMAIN, type='google_analytics', status='active'
    )
except Integration.DoesNotExist:
    print(f"No active GA integration found for domain: '{DOMAIN}'")
    print("Available domains:")
    for i in Integration.objects.filter(type='google_analytics').select_related('domain'):
        print(f"  [{i.status}] {i.domain.name}  (integration_id={i.id})")
    sys.exit(1)

print(f"\n Domain : {integration.domain.name}")
print(f" Integration ID : {integration.id}")

# ── 2. Build date ranges ────────────────────────────────────────────────────
today = date.today()

cur_start = today.replace(day=1)
cur_end   = today.replace(day=calendar.monthrange(today.year, today.month)[1])

pm = today.month - 1 if today.month > 1 else 12
py = today.year      if today.month > 1 else today.year - 1
prv_start = date(py, pm, 1)
prv_end   = date(py, pm, calendar.monthrange(py, pm)[1])

yoy_start = date(today.year - 1, today.month, 1)
yoy_end   = date(today.year - 1, today.month,
                 calendar.monthrange(today.year - 1, today.month)[1])

# ── 3. Create/reset INIT records ────────────────────────────────────────────
print("\n Creating monthly records ...")
periods = [
    ('current_month', cur_start, cur_end),
    ('prev_month',    prv_start, prv_end),
    ('yoy_month',     yoy_start, yoy_end),
]
for period_type, start, end in periods:
    obj, created = GATrafficInsight.objects.get_or_create(
        integration=integration, start_date=start, end_date=end,
        defaults={'domain': integration.domain, 'track_status': 'INIT',
                  'period_type': period_type}
    )
    if not created:
        GATrafficInsight.objects.filter(id=obj.id).update(
            period_type=period_type, track_status='INIT', track_message=None)
    status = 'created' if created else 'reset  '
    print(f"  {status} [{period_type:15s}] {start} → {end}  id={obj.id}")

# ── 4. Check if records already have COMP data ─────────────────────────────
cur = GATrafficInsight.objects.get(integration=integration, period_type='current_month')
prv = GATrafficInsight.objects.get(integration=integration, period_type='prev_month')
yoy = GATrafficInsight.objects.get(integration=integration, period_type='yoy_month')

if cur.track_status != 'COMP' or prv.track_status != 'COMP':
    print("\n No COMP data yet — injecting sample values for widget test.")
    print(" (Run with real Celery to fetch actual GA data)\n")
    GATrafficInsight.objects.filter(id=cur.id).update(
        track_status='COMP', total_sessions=16990, total_users=5000,
        total_page_views=25000, total_conversions=120, bounce_rate=31.58)
    GATrafficInsight.objects.filter(id=prv.id).update(
        track_status='COMP', total_sessions=124457, total_users=74148,
        total_page_views=200000, total_conversions=860, bounce_rate=29.49)
    GATrafficInsight.objects.filter(id=yoy.id).update(
        track_status='COMP', total_sessions=66700, total_users=40000,
        total_page_views=120000, total_conversions=420, bounce_rate=28.0)
    cur.refresh_from_db(); prv.refresh_from_db(); yoy.refresh_from_db()
else:
    print("\n Real COMP data found — using actual GA values.")

# ── 5. Prorate current month ────────────────────────────────────────────────
raw = {
    'total_sessions':       cur.total_sessions,
    'total_users':          cur.total_users,
    'total_page_views':     cur.total_page_views,
    'total_conversions':    cur.total_conversions,
    'total_revenue':        float(cur.total_revenue),
    'bounce_rate':          float(cur.bounce_rate),
    'avg_session_duration': float(cur.avg_session_duration),
}
prorated = apply_prorate_ga(raw, cur.start_date, cur.end_date)

print(f"\n Prorate: ({prorated['days_elapsed']} days elapsed / {prorated['total_days']} total)"
      f"  factor = {prorated['prorate_factor']}x")

# ── 6. Print MOM / YOY table ────────────────────────────────────────────────
def pct(cur_v, base_v):
    if base_v and base_v != 0:
        return f"{round((cur_v - base_v) / base_v * 100, 1):+.1f}%"
    return 'N/A'

prv_label = prv.start_date.strftime('%b %Y')
cur_label = f"{cur.start_date.strftime('%b %Y')} (PR)"

print(f"\n {'Metric':<22} {'Last Month ':>15} {'Current (PR)':>14} {'MOM %':>8} {'YOY %':>8}")
print(" " + "-" * 72)

metrics = [
    ('Sessions',        'total_sessions',       False),
    ('Users',           'total_users',           False),
    ('Page Views',      'total_page_views',      False),
    ('Conversions',     'total_conversions',     False),
    ('Bounce Rate',     'bounce_rate',           True),
]
for label, key, is_rate in metrics:
    prv_v = getattr(prv, key)
    yoy_v = getattr(yoy, key)
    cur_v = prorated[key] if not is_rate else float(getattr(cur, key))
    prv_f = f"{float(prv_v):.2f}%" if is_rate else f"{int(prv_v):,}"
    cur_f = f"{float(cur_v):.2f}%" if is_rate else f"{int(cur_v):,}"
    mom   = pct(cur_v, float(prv_v))
    yoy_p = pct(cur_v, float(yoy_v))
    print(f" {label:<22} {prv_f:>15} {cur_f:>14} {mom:>8} {yoy_p:>8}")

# ── 7. Widget output ─────────────────────────────────────────────────────────
print("\n" + "=" * 72)
print(" Widget output (ga-overview-table):")
print("=" * 72)

from datetime import datetime
from django.utils import timezone
from domains.models import Domain
from reports.services.widget_data_fetcher import WidgetDataFetcher

domain_obj = integration.domain
end_dt     = timezone.now()
start_dt   = end_dt - timedelta(days=30)

fetcher = WidgetDataFetcher(domain=domain_obj, start_date=start_dt,
                             end_date=end_dt, organisation=domain_obj.organisation)
result  = fetcher.fetch_widget_data('ga-overview-table')

print(f" Columns : {result['columns']}")
print(f" Prorated: {result.get('is_prorated')}  ({result.get('days_elapsed')}/{result.get('total_days')} days)\n")
for row in result['rows']:
    print(f"  {row}")
