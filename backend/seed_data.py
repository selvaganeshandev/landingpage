"""
Seed script to populate the database with sample data.
Run with: python manage.py shell < seed_data.py
"""
import os
import django
from datetime import datetime, timedelta
from decimal import Decimal
import random

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor.settings')
django.setup()

from django.utils import timezone
from authentication.models import Organisation, Account, TeamInvitation, UserPermission
from domains.models import Domain, DomainAccess
from keywords.models import Keyword
from prompts.models import PromptGroup, Prompt, PromptAnalytics
from alerts.models import Alert, AlertRule, AlertNotification
from competitors.models import Competitor, CompetitorAnalytics, CompetitorPrompt
from topics.models import Topic, TopicAnalytics, TopicPrompt
from analytics.models import SentimentAnalytics, ShareOfVoiceAnalytics
from integrations.models import Integration

print("🌱 Starting database seeding...")

# Clear existing data
print("Clearing existing data...")
Alert.objects.all().delete()
AlertRule.objects.all().delete()
AlertNotification.objects.all().delete()
CompetitorPrompt.objects.all().delete()
CompetitorAnalytics.objects.all().delete()
Competitor.objects.all().delete()
TopicPrompt.objects.all().delete()
TopicAnalytics.objects.all().delete()
Topic.objects.all().delete()
SentimentAnalytics.objects.all().delete()
ShareOfVoiceAnalytics.objects.all().delete()
Integration.objects.all().delete()
PromptAnalytics.objects.all().delete()
Prompt.objects.all().delete()
PromptGroup.objects.all().delete()
Keyword.objects.all().delete()
DomainAccess.objects.all().delete()
Domain.objects.all().delete()
UserPermission.objects.all().delete()
TeamInvitation.objects.all().delete()
Account.objects.all().delete()
Organisation.objects.all().delete()

# ==================== AUTHENTICATION & ORGANIZATION ====================
print("\n📊 Creating organisations...")
organisations = []
org_names = [
    "TechCorp Solutions", "Digital Marketing Pro", "EcoFriendly Products",
    "HealthTech Innovations", "FinanceHub", "EduLearn Platform",
    "TravelExperts", "FoodieDelight", "FitnessPro", "AI Research Labs"
]

for i, name in enumerate(org_names, 1):
    org = Organisation.objects.create(
        name=name,
        team_count=random.randint(5, 50)
    )
    organisations.append(org)
    print(f"  ✓ Created organisation: {name}")

print(f"\n👤 Creating accounts...")
# Create a default organisation for superadmin
admin_org = organisations[0]  # Use the first organisation

# Create superadmin
superadmin = Account.objects.create_user(
    username='superadmin',
    email='admin@llmmonitor.com',
    password='Admin@123',
    first_name='Super',
    last_name='Admin',
    organisation=admin_org,
    role='super_admin',
    is_staff=True,
    is_superuser=True
)
print(f"  ✓ Created superadmin: {superadmin.email} (password: Admin@123)")

# Create regular accounts
accounts = [superadmin]
roles = ['admin', 'user', 'admin', 'user', 'admin', 'user', 'admin', 'user', 'admin']
for i, (org, role) in enumerate(zip(organisations, roles), 1):
    account = Account.objects.create_user(
        username=f'user{i}',
        email=f'user{i}@{org.name.lower().replace(" ", "")}.com',
        password='User@123',
        first_name=f'User{i}',
        last_name=f'Test{i}',
        organisation=org,
        role=role,
        is_active=True
    )
    accounts.append(account)
    print(f"  ✓ Created {role}: {account.email} for {org.name}")

print(f"\n📧 Creating team invitations...")
statuses = ['pending', 'accepted', 'expired']
for i in range(10):
    org = random.choice(organisations)
    invitation = TeamInvitation.objects.create(
        email=f'invite{i}@example.com',
        organisation=org,
        role=random.choice(['admin', 'user']),
        invited_by=random.choice([a for a in accounts if a.organisation == org] or [superadmin]),
        status=random.choice(statuses)
    )
    if invitation.status == 'accepted':
        invitation.accepted_at = timezone.now() - timedelta(days=random.randint(1, 30))
        invitation.save()
    print(f"  ✓ Created invitation for {invitation.email}")

print(f"\n🔐 Creating user permissions...")
modules = ['dashboard', 'mentions', 'alerts', 'competitors', 'topics', 'sentiment_analysis', 'share_of_voice']
for i, account in enumerate(accounts[1:11], 1):  # Skip superadmin
    num_permissions = random.randint(3, 7)
    selected_modules = random.sample(modules, min(num_permissions, len(modules)))
    # Find an admin from the same org to grant permissions
    granter = next((a for a in accounts if a.organisation == account.organisation and a.role in ['admin', 'super_admin']), superadmin)
    for module in selected_modules:
        UserPermission.objects.create(
            user=account,
            module=module,
            granted_by=granter
        )
    print(f"  ✓ Created {len(selected_modules)} permissions for {account.email}")

# ==================== DOMAINS ====================
print(f"\n🌐 Creating domains...")
domains = []
domain_names = [
    "techsolutions.com", "digitalmarket.io", "ecoproducts.com",
    "healthinnovate.com", "financehub.net", "edulearn.org",
    "travelexperts.com", "foodiedelight.com", "fitnesspro.com", "airesearch.ai"
]

for i, (org, name) in enumerate(zip(organisations, domain_names), 1):
    domain = Domain.objects.create(
        name=name,
        url=f"https://www.{name}",
        organisation=org
    )
    domains.append(domain)
    print(f"  ✓ Created domain: {name}")

print(f"\n🔑 Creating domain access...")
for domain in domains:
    # Grant access to users in the same organisation
    org_users = [a for a in accounts if a.organisation == domain.organisation]
    granter = next((a for a in org_users if a.role in ['admin', 'super_admin']), superadmin)
    for user in org_users[:3]:  # Grant to first 3 users
        DomainAccess.objects.create(
            domain=domain,
            user=user,
            granted_by=granter
        )
    print(f"  ✓ Created access for {domain.name}")

# ==================== KEYWORDS ====================
print(f"\n🔤 Creating keywords...")
keywords = []
keyword_texts = [
    "AI chatbot", "machine learning", "cloud computing", "digital marketing",
    "SEO optimization", "social media", "email campaigns", "content strategy",
    "data analytics", "customer engagement"
]

for i, domain in enumerate(domains):
    keyword = Keyword.objects.create(
        keyword=keyword_texts[i],
        domain=domain
    )
    keywords.append(keyword)
    print(f"  ✓ Created keyword: {keyword.keyword}")

# ==================== PROMPTS ====================
print(f"\n📝 Creating prompt groups...")
prompt_groups = []
for i, domain in enumerate(domains):
    group = PromptGroup.objects.create(
        group_id=f"group_{domain.name.split('.')[0].lower()}",
        domain=domain
    )
    prompt_groups.append(group)
    print(f"  ✓ Created prompt group: {group.group_id}")

print(f"\n💬 Creating prompts...")
prompts = []
prompt_texts = [
    "What is the best AI tool for content creation?",
    "How to improve SEO rankings in 2025?",
    "Top digital marketing strategies",
    "Best cloud computing platforms",
    "How to analyze customer data?",
    "Social media marketing tips",
    "Email marketing best practices",
    "Content marketing strategies",
    "Customer engagement tactics",
    "Data-driven decision making"
]

for i, group in enumerate(prompt_groups):
    prom = Prompt.objects.create(
        prompt=prompt_texts[i],
        group=group
    )
    prompts.append(prom)
    print(f"  ✓ Created prompt: {prom.prompt[:50]}...")

print(f"\n📊 Creating prompt analytics...")
platforms = ['ChatGPT', 'Claude', 'Gemini', 'Perplexity']
for prom in prompts:
    # Create one analytics record per platform (unique constraint)
    for platform in platforms:
        PromptAnalytics.objects.create(
            prompt=prom,
            platform=platform,
            position=Decimal(random.uniform(1, 10)),
            is_mention=random.choice([True, False, True]),
            total_mentions=random.randint(0, 50),
            total_citations=random.randint(0, 20),
            context_summary=f"Sample context for {prom.prompt[:30]}..."
        )
    print(f"  ✓ Created analytics for prompt: {prom.prompt[:30]}...")

# ==================== ALERTS ====================
print(f"\n🚨 Creating alerts...")
alert_types = ['visibility_drop', 'sentiment_negative', 'competitor_surge', 'anomaly', 'position_loss']
severities = ['high', 'medium', 'low']
statuses = ['active', 'investigating', 'resolved']

for i, domain in enumerate(domains):
    org_admin = next((a for a in accounts if a.organisation == domain.organisation and a.role in ['admin', 'super_admin']), superadmin)
    alert = Alert.objects.create(
        domain=domain,
        type=alert_types[i % len(alert_types)],
        severity=severities[i % len(severities)],
        title=f"Alert: {alert_types[i % len(alert_types)].replace('_', ' ').title()}",
        message=f"Detected {alert_types[i % len(alert_types)]} for {domain.name}",
        platform=random.choice(platforms),
        metric=Decimal(random.uniform(-50, 50)),
        status=statuses[i % len(statuses)],
        created_by=org_admin
    )
    if alert.status == 'resolved':
        alert.resolved_at = timezone.now() - timedelta(hours=random.randint(1, 48))
        alert.save()
    print(f"  ✓ Created alert: {alert.title}")

print(f"\n⚙️ Creating alert rules...")
for i, domain in enumerate(domains):
    org_admin = next((a for a in accounts if a.organisation == domain.organisation and a.role in ['admin', 'super_admin']), superadmin)
    rule = AlertRule.objects.create(
        domain=domain,
        name=f"Monitor {domain.name.split('.')[0]} visibility",
        description=f"Alert when visibility drops by more than 20%",
        enabled=random.choice([True, True, False]),
        conditions={
            'metric': 'visibility',
            'threshold': 20,
            'operator': 'less_than',
            'time_window': '24h'
        },
        notification_channel_list=['email', 'slack'],
        detection_count=random.randint(0, 50),
        last_triggered_at=timezone.now() - timedelta(days=random.randint(1, 30)) if random.choice([True, False]) else None,
        created_by=org_admin
    )
    print(f"  ✓ Created alert rule: {rule.name}")

print(f"\n📬 Creating alert notifications...")
channels = ['email', 'slack', 'sms']
notif_statuses = ['sent', 'failed', 'pending']
alerts_list = list(Alert.objects.all())
for i in range(10):
    alert = random.choice(alerts_list)
    notification = AlertNotification.objects.create(
        alert=alert,
        channel=channels[i % len(channels)],
        recipient=f"user{i}@example.com" if channels[i % len(channels)] == 'email' else f"#alerts-{i}",
        status=notif_statuses[i % len(notif_statuses)],
        error_message="SMTP connection timeout" if notif_statuses[i % len(notif_statuses)] == 'failed' else None
    )
    print(f"  ✓ Created notification via {notification.channel}")

# ==================== COMPETITORS ====================
print(f"\n🏆 Creating competitors...")
competitors = []
competitor_names = [
    ("Competitor A", "https://competitora.com"),
    ("Competitor B", "https://competitorb.com"),
    ("Competitor C", "https://competitorc.com"),
    ("Competitor D", "https://competitord.com"),
    ("Competitor E", "https://competitore.com"),
    ("Competitor F", "https://competitorf.com"),
    ("Competitor G", "https://competitorg.com"),
    ("Competitor H", "https://competitorh.com"),
    ("Competitor I", "https://competitori.com"),
    ("Competitor J", "https://competitorj.com"),
]

for i, domain in enumerate(domains):
    org_admin = next((a for a in accounts if a.organisation == domain.organisation and a.role in ['admin', 'super_admin']), superadmin)
    name, url = competitor_names[i]
    competitor = Competitor.objects.create(
        domain=domain,
        name=name,
        url=url,
        total_mentions=random.randint(50, 500),
        visibility_score=Decimal(random.uniform(60, 95)),
        sentiment_score=Decimal(random.uniform(0, 100)),
        average_position=Decimal(random.uniform(1, 10)),
        share_of_voice_percentage=Decimal(random.uniform(10, 40)),
        trend_percentage=Decimal(random.uniform(-20, 30)),
        created_by=org_admin
    )
    competitors.append(competitor)
    print(f"  ✓ Created competitor: {name}")

print(f"\n📈 Creating competitor analytics...")
for competitor in competitors:
    for day in range(10):
        CompetitorAnalytics.objects.create(
            competitor=competitor,
            platform=random.choice(platforms),
            total_mentions=random.randint(10, 100),
            position=Decimal(random.uniform(1, 10)),
            sentiment_score=Decimal(random.uniform(0, 100)),
            timestamp=timezone.now().date() - timedelta(days=day)
        )
    print(f"  ✓ Created analytics for {competitor.name}")

print(f"\n💡 Creating competitor prompts...")
comp_prompt_texts = [
    "Best AI tools for business automation",
    "Top marketing platforms 2025",
    "Cloud storage solutions comparison",
    "Healthcare software recommendations",
    "Financial planning tools",
    "Online learning platforms",
    "Travel booking services",
    "Food delivery apps",
    "Fitness tracking apps",
    "AI research tools"
]

for i, competitor in enumerate(competitors):
    org_admin = next((a for a in accounts if a.organisation == competitor.domain.organisation and a.role in ['admin', 'super_admin']), superadmin)
    CompetitorPrompt.objects.create(
        competitor=competitor,
        prompt_text=comp_prompt_texts[i],
        total_mentions=random.randint(20, 150),
        position=random.randint(1, 5),
        your_mentions=random.randint(0, 50),
        platform_list=random.sample(platforms, 2),
        created_by=org_admin
    )
    print(f"  ✓ Created prompt for {competitor.name}")

# ==================== TOPICS ====================
print(f"\n🏷️ Creating topics...")
topics = []
topic_data = [
    ("AI Technology", ["artificial intelligence", "machine learning", "deep learning"]),
    ("Digital Marketing", ["SEO", "SEM", "content marketing"]),
    ("Cloud Computing", ["AWS", "Azure", "cloud storage"]),
    ("Healthcare Tech", ["telemedicine", "health apps", "medical AI"]),
    ("FinTech", ["payments", "blockchain", "banking"]),
    ("EdTech", ["online learning", "e-learning", "education"]),
    ("Travel Tech", ["booking", "travel apps", "tourism"]),
    ("Food Tech", ["delivery", "restaurant tech", "food apps"]),
    ("Fitness Tech", ["wearables", "fitness apps", "health tracking"]),
    ("AI Research", ["NLP", "computer vision", "robotics"])
]

for i, domain in enumerate(domains):
    org_admin = next((a for a in accounts if a.organisation == domain.organisation and a.role in ['admin', 'super_admin']), superadmin)
    name, keywords_list = topic_data[i]
    topic = Topic.objects.create(
        domain=domain,
        name=name,
        keyword_list=keywords_list,
        total_mentions=random.randint(100, 1000),
        visibility_score=Decimal(random.uniform(60, 95)),
        sentiment_score=Decimal(random.uniform(0, 100)),
        trend_percentage=Decimal(random.uniform(-15, 35)),
        platform_list=random.sample(platforms, 3),
        created_by=org_admin
    )
    topics.append(topic)
    print(f"  ✓ Created topic: {name}")

print(f"\n📊 Creating topic analytics...")
for topic in topics:
    for day in range(10):
        TopicAnalytics.objects.create(
            topic=topic,
            total_mentions=random.randint(50, 200),
            visibility_score=Decimal(random.uniform(60, 95)),
            sentiment_score=Decimal(random.uniform(0, 100)),
            timestamp=timezone.now().date() - timedelta(days=day)
        )
    print(f"  ✓ Created analytics for {topic.name}")

print(f"\n💭 Creating topic prompts...")
search_volumes = ['high', 'medium', 'low']
for i, topic in enumerate(topics):
    TopicPrompt.objects.create(
        topic=topic,
        prompt_text=f"What are the latest trends in {topic.name.lower()}?",
        relevance_score=random.randint(70, 100),
        search_volume=search_volumes[i % len(search_volumes)],
        platform_list=random.sample(platforms, 2)
    )
    print(f"  ✓ Created prompt for {topic.name}")

# ==================== ANALYTICS ====================
print(f"\n😊 Creating sentiment analytics...")
themes = ["Product Quality", "Customer Service", "Pricing", "Features", "User Experience"]
for i, domain in enumerate(domains):
    for day in range(10):
        positive = Decimal(random.uniform(40, 70))
        negative = Decimal(random.uniform(5, 20))
        neutral = Decimal(100 - positive - negative)
        
        # CRITICAL: Only create SentimentAnalytics with valid platform names, never NULL
        # Platform must be a valid platform name (e.g., 'ChatGPT', 'Google Gemini', 'Perplexity')
        SentimentAnalytics.objects.create(
            domain=domain,
            theme=themes[day % len(themes)],
            positive_percentage=positive,
            neutral_percentage=neutral,
            negative_percentage=negative,
            mention_count=random.randint(50, 300),
            platform=random.choice(platforms),  # Only use valid platforms, never None
            snapshot_date=timezone.now().date() - timedelta(days=day),
            period_type='daily'
        )
    print(f"  ✓ Created sentiment analytics for {domain.name}")

print(f"\n📊 Creating share of voice analytics...")
for domain in domains:
    # Create your brand's SOV
    for day in range(10):
        ShareOfVoiceAnalytics.objects.create(
            domain=domain,
            competitor=None,  # Your brand
            platform=None,  # Overall
            share_percentage=Decimal(random.uniform(25, 45)),
            mention_count=random.randint(100, 500),
            market_position=1,
            timestamp=timezone.now().date() - timedelta(days=day)
        )
    
    # Create competitor SOV
    domain_competitors = Competitor.objects.filter(domain=domain)[:3]
    for position, competitor in enumerate(domain_competitors, 2):
        for day in range(10):
            ShareOfVoiceAnalytics.objects.create(
                domain=domain,
                competitor=competitor,
                platform=None,
                share_percentage=Decimal(random.uniform(10, 30)),
                mention_count=random.randint(50, 300),
                market_position=position,
                timestamp=timezone.now().date() - timedelta(days=day)
            )
    print(f"  ✓ Created SOV analytics for {domain.name}")

# ==================== INTEGRATIONS ====================
print(f"\n🔌 Creating integrations...")
integration_types = ['google_analytics', 'search_console', 'slack', 'sms', 'cms']
integration_statuses = ['active', 'error', 'disconnected']

for i, domain in enumerate(domains):
    org_admin = next((a for a in accounts if a.organisation == domain.organisation and a.role in ['admin', 'super_admin']), superadmin)
    integration_type = integration_types[i % len(integration_types)]
    
    # Mock credentials based on type
    credentials = {}
    if integration_type == 'google_analytics':
        credentials = {'property_id': f'GA-{random.randint(100000, 999999)}'}
    elif integration_type == 'search_console':
        credentials = {'site_url': f'https://{domain.name}'}
    elif integration_type == 'slack':
        credentials = {'webhook_url': f'https://hooks.slack.com/services/XXX/YYY/ZZZ{i}'}
    elif integration_type == 'sms':
        credentials = {'api_key': f'sk_live_{"x" * 20}{i}'}
    elif integration_type == 'cms':
        credentials = {'api_endpoint': f'https://{domain.name}/api'}
    
    integration = Integration.objects.create(
        domain=domain,
        type=integration_type,
        provider_id=f'{integration_type}_provider_{i}',
        credentials=credentials,
        status=integration_statuses[i % len(integration_statuses)],
        last_sync_at=timezone.now() - timedelta(hours=random.randint(1, 72)) if random.choice([True, False]) else None,
        error_message="Connection timeout" if integration_statuses[i % len(integration_statuses)] == 'error' else None,
        created_by=org_admin
    )
    print(f"  ✓ Created integration: {integration.get_type_display()} for {domain.name}")

print("\n" + "="*60)
print("✅ Database seeding completed successfully!")
print("="*60)
print("\n📊 Summary:")
print(f"  • Organisations: {Organisation.objects.count()}")
print(f"  • Accounts: {Account.objects.count()}")
print(f"  • Team Invitations: {TeamInvitation.objects.count()}")
print(f"  • User Permissions: {UserPermission.objects.count()}")
print(f"  • Domains: {Domain.objects.count()}")
print(f"  • Domain Access: {DomainAccess.objects.count()}")
print(f"  • Keywords: {Keyword.objects.count()}")
print(f"  • Prompt Groups: {PromptGroup.objects.count()}")
print(f"  • Prompts: {Prompt.objects.count()}")
print(f"  • Prompt Analytics: {PromptAnalytics.objects.count()}")
print(f"  • Alerts: {Alert.objects.count()}")
print(f"  • Alert Rules: {AlertRule.objects.count()}")
print(f"  • Alert Notifications: {AlertNotification.objects.count()}")
print(f"  • Competitors: {Competitor.objects.count()}")
print(f"  • Competitor Analytics: {CompetitorAnalytics.objects.count()}")
print(f"  • Competitor Prompts: {CompetitorPrompt.objects.count()}")
print(f"  • Topics: {Topic.objects.count()}")
print(f"  • Topic Analytics: {TopicAnalytics.objects.count()}")
print(f"  • Topic Prompts: {TopicPrompt.objects.count()}")
print(f"  • Sentiment Analytics: {SentimentAnalytics.objects.count()}")
print(f"  • Share of Voice Analytics: {ShareOfVoiceAnalytics.objects.count()}")
print(f"  • Integrations: {Integration.objects.count()}")
print("\n🔐 Superadmin Credentials:")
print("  Email: admin@llmmonitor.com")
print("  Password: Admin@123")
print("\n👤 Test User Credentials:")
print("  Email: user1@techcorpsolutions.com")
print("  Password: User@123")
print("  (Pattern: user[1-9]@[orgname].com)")
print("="*60)

