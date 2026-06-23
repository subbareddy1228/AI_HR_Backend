from sqlalchemy.orm import Session


class PayrollReportsService:
    def __init__(self, db: Session):
        self.db = db

    # ── Dashboard ─────────────────────────────────────────────────────────
    def get_summary_metrics(self, period=None):
        raise NotImplementedError

    def get_ai_insights(self):
        raise NotImplementedError

    def dismiss_insight(self, insight_id):
        raise NotImplementedError

    # ── Standard Reports ─────────────────────────────────────────────────
    def list_standard_reports(self, search=None, department=None, frequency=None):
        raise NotImplementedError

    def create_standard_report(self, data):
        raise NotImplementedError

    def update_standard_report(self, report_id, data):
        raise NotImplementedError

    def delete_standard_report(self, report_id):
        raise NotImplementedError

    def generate_standard_report(self, report_id, data):
        raise NotImplementedError

    def schedule_standard_report(self, report_id, data):
        raise NotImplementedError

    def export_standard_reports(self, format):
        raise NotImplementedError

    # ── Compliance ───────────────────────────────────────────────────────
    def list_compliance_reports(self, type=None):
        raise NotImplementedError

    def get_overdue_compliance_count(self):
        raise NotImplementedError

    def create_compliance_report(self, data):
        raise NotImplementedError

    def get_compliance_file(self, report_id):
        raise NotImplementedError

    def delete_compliance_report(self, report_id):
        raise NotImplementedError

    # ── Analytics ─────────────────────────────────────────────────────────
    def list_analytics_dashboards(self):
        raise NotImplementedError

    def get_analytics_data(self, dashboard_id, data):
        raise NotImplementedError

    # ── Generated ─────────────────────────────────────────────────────────
    def list_generated_reports(self):
        raise NotImplementedError

    def get_generated_report_file(self, report_id):
        raise NotImplementedError

    def delete_generated_report(self, report_id):
        raise NotImplementedError

    # ── Scheduled ─────────────────────────────────────────────────────────
    def list_scheduled_reports(self):
        raise NotImplementedError

    def create_scheduled_report(self, data):
        raise NotImplementedError

    def update_scheduled_report(self, schedule_id, data):
        raise NotImplementedError

    def pause_scheduled_report(self, schedule_id):
        raise NotImplementedError

    def resume_scheduled_report(self, schedule_id):
        raise NotImplementedError

    def delete_scheduled_report(self, schedule_id):
        raise NotImplementedError

    # ── Configuration ─────────────────────────────────────────────────────
    def get_configuration(self):
        raise NotImplementedError

    def update_configuration(self, data):
        raise NotImplementedError

    def reset_configuration(self):
        raise NotImplementedError

    def export_configuration(self):
        raise NotImplementedError

    def get_configuration_export_file(self):
        raise NotImplementedError

    def list_custom_reports(self):
        raise NotImplementedError

    def delete_custom_report(self, report_id):
        raise NotImplementedError

    # ── Report Builder ────────────────────────────────────────────────────
    def list_column_definitions(self, group=None):
        raise NotImplementedError

    def create_custom_report(self, data):
        raise NotImplementedError

    def get_custom_report(self, report_id):
        raise NotImplementedError

    def update_custom_report(self, report_id, data):
        raise NotImplementedError

    def run_custom_report(self, report_id):
        raise NotImplementedError
