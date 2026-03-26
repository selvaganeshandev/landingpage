from rest_framework import serializers
from .models import ReportTemplate, ScheduledReport, GeneratedReport


class ReportTemplateListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for template list — excludes large JSON fields."""
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        model = ReportTemplate
        fields = [
            'id', 'name', 'description', 'template_type',
            'created_by', 'created_by_email',
            'is_active', 'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']


class ReportTemplateSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    organisation_name = serializers.CharField(source='organisation.name', read_only=True)
    description = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta:
        model = ReportTemplate
        fields = [
            'id', 'name', 'description', 'template_type', 'sections', 'grid_rows',
            'html_template', 'css_template',
            'organisation', 'organisation_name', 'created_by', 'created_by_email',
            'is_active', 'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']

    def create(self, validated_data):
        # Set organisation and created_by from request user for custom templates
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            if validated_data.get('template_type') == 'custom':
                validated_data['organisation'] = request.user.organisation
                validated_data['created_by'] = request.user
        return super().create(validated_data)


class ScheduledReportSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True)
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        model = ScheduledReport
        fields = [
            'id', 'organisation', 'domain', 'domain_name', 'name', 'description',
            'template', 'template_name', 'frequency', 'schedule_day', 'schedule_time',
            'sections', 'formats', 'recipients', 'status', 'last_generated_at',
            'next_run_at', 'created_by', 'created_by_email', 'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at', 'last_generated_at']

    def create(self, validated_data):
        # Set organisation and created_by from request user
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['organisation'] = request.user.organisation
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class ScheduledReportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating scheduled reports"""
    class Meta:
        model = ScheduledReport
        fields = [
            'domain', 'name', 'description', 'template', 'frequency',
            'schedule_day', 'schedule_time', 'sections', 'formats', 'recipients'
        ]

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['organisation'] = request.user.organisation
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class ScheduledReportUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating scheduled reports"""
    class Meta:
        model = ScheduledReport
        fields = [
            'name', 'description', 'frequency', 'schedule_day', 'schedule_time',
            'sections', 'formats', 'recipients', 'status'
        ]


class GeneratedReportSerializer(serializers.ModelSerializer):
    domain_name = serializers.SerializerMethodField()
    generated_by_email = serializers.SerializerMethodField()
    scheduled_report_name = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = GeneratedReport
        fields = [
            'id', 'scheduled_report', 'scheduled_report_name', 'organisation', 'domain',
            'domain_name', 'name', 'report_type', 'format', 'file_path', 'file_size',
            'page_count', 'data_period_start', 'data_period_end', 'generated_at',
            'generated_by', 'generated_by_email', 'summary_data', 'download_url'
        ]
        read_only_fields = ['id', 'generated_at']

    def get_domain_name(self, obj):
        return obj.domain.name if obj.domain else None

    def get_generated_by_email(self, obj):
        return obj.generated_by.email if obj.generated_by else None

    def get_scheduled_report_name(self, obj):
        return obj.scheduled_report.name if obj.scheduled_report else None

    def get_download_url(self, obj):
        if obj.file_path:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file_path.url)
        return None


class GenerateReportRequestSerializer(serializers.Serializer):
    """Serializer for on-demand report generation request"""
    domain_id = serializers.IntegerField(required=True)
    template_id = serializers.IntegerField(required=True)
    sections = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    format = serializers.ChoiceField(choices=['PDF', 'Excel', 'PowerPoint'], default='PDF')
    data_period_days = serializers.IntegerField(default=30, min_value=1, max_value=365)
